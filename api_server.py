#!/usr/bin/env python3
"""
CourtVision - API REST pour l'analyse de volleyball
Met à jour Supabase directement quand l'analyse est terminée.
"""
import os, sys, json, uuid, threading, tempfile
from pathlib import Path

# Permettre de configurer le chemin VolleyVision via env
if os.environ.get("VOLLEYVISION_DIR"):
    import analyze_video
    analyze_video.VOLLEYVISION_DIR = os.environ["VOLLEYVISION_DIR"]
    analyze_video.ACTIONS_MODEL_PATH = os.path.join(
        os.environ["VOLLEYVISION_DIR"], "Stage II - Players & Actions", "actions", "yV8_medium", "weights", "best.pt"
    )
    analyze_video.PLAYERS_MODEL_PATH = os.path.join(
        os.environ["VOLLEYVISION_DIR"], "Stage II - Players & Actions", "players", "yV8_medium", "weights", "best.pt"
    )

try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    print("pip install flask flask-cors")
    sys.exit(1)

# Supabase client pour mise à jour directe de la DB
try:
    from supabase import create_client, Client as SupabaseClient
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    supabase_client: SupabaseClient | None = None
    if SUPABASE_URL and SUPABASE_KEY:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"✅ Supabase connecté: {SUPABASE_URL[:40]}...")
    else:
        print("⚠️  SUPABASE_URL ou SUPABASE_SERVICE_KEY non configurées - pas de mise à jour DB")
except ImportError:
    supabase_client = None
    print("⚠️  supabase-py non installé - pas de mise à jour DB")

from analyze_video import VolleyballAnalyzer

app = Flask(__name__)
CORS(app)

analyses = {}
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "cv_uploads")
OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "cv_outputs")


def update_supabase_video(video_id, status, progress, points_data=None):
    """Met à jour le statut de la vidéo dans Supabase."""
    if not supabase_client or not video_id:
        return
    try:
        update_data = {"status": status, "progress": progress}
        if points_data is not None:
            update_data["points_data"] = points_data
        supabase_client.table("videos").update(update_data).eq("id", video_id).execute()
        print(f"📝 Supabase: video {video_id[:8]}... → {status} ({progress}%)")
    except Exception as e:
        print(f"⚠️  Erreur Supabase update: {e}")


def download_video(url, dest_path):
    """Télécharge une vidéo depuis une URL."""
    import requests as req
    print(f"⬇️  Téléchargement: {url[:80]}...")
    r = req.get(url, stream=True, timeout=600)
    r.raise_for_status()
    with open(dest_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    size_mb = os.path.getsize(dest_path) / (1024 * 1024)
    print(f"   ✅ Téléchargé: {size_mb:.1f} MB")
    return dest_path


def run_analysis(analysis_id, video_path, params):
    """Lance une analyse en arrière-plan et met à jour Supabase."""
    video_id = params.get('video_id')  # ID de la vidéo dans Supabase
    
    try:
        analyses[analysis_id]['status'] = 'running'
        analyses[analysis_id]['progress'] = 'Chargement du modèle...'
        analyses[analysis_id]['percent'] = 5
        update_supabase_video(video_id, "PROCESSING", 5)

        output_dir = os.path.join(OUTPUT_DIR, analysis_id)

        analyzer = VolleyballAnalyzer(
            video_path=video_path,
            output_dir=output_dir,
            confidence=params.get('confidence', 0.4),
            use_gpu=params.get('use_gpu', False),
            frame_skip=params.get('frame_skip', 5),
            team_left=params.get('team_left', 'Equipe A'),
            team_right=params.get('team_right', 'Equipe B'),
            setter_start_left=params.get('setter_start_left', 'P1'),
            setter_start_right=params.get('setter_start_right', 'P1'),
            first_serve=params.get('first_serve', 'left'),
        )

        analyses[analysis_id]['progress'] = 'Detection des actions...'
        analyses[analysis_id]['percent'] = 15
        update_supabase_video(video_id, "PROCESSING", 15)
        analyzer.detect_actions()

        analyses[analysis_id]['progress'] = 'Detection des evenements...'
        analyses[analysis_id]['percent'] = 60
        update_supabase_video(video_id, "PROCESSING", 60)
        analyzer.detect_events()

        analyses[analysis_id]['progress'] = 'Decoupage des rallyes...'
        analyses[analysis_id]['percent'] = 80
        update_supabase_video(video_id, "PROCESSING", 80)
        analyzer.detect_rallies()

        analyses[analysis_id]['progress'] = 'Export des resultats...'
        analyses[analysis_id]['percent'] = 90
        update_supabase_video(video_id, "PROCESSING", 90)
        analyzer.export_results()

        # Lire le JSON
        results_path = os.path.join(output_dir, "analysis_results.json")
        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)

        # Convertir les rallyes au format frontend (DetectedPoint[])
        detected_points = []
        for rally in results.get('rallies', []):
            rot = rally.get('rotation', {})
            detected_points.append({
                'id': rally['rally_num'],
                'startTime': rally['start_time'],
                'endTime': rally['end_time'],
                'label': f"Point {rally['rally_num']}",
                'winner': 'A' if rally['scored_by'] == params.get('team_left', 'Equipe A') else 'B' if rally['scored_by'] == params.get('team_right', 'Equipe B') else None,
                'servingTeamAtStart': 'A' if rot.get('serving_team') == params.get('team_left', 'Equipe A') else 'B',
                'rotationAtStart': _position_to_number(rot.get('setter_left', 'P1')),
            })

        analyses[analysis_id]['status'] = 'completed'
        analyses[analysis_id]['progress'] = 'Termine'
        analyses[analysis_id]['percent'] = 100
        analyses[analysis_id]['results'] = results
        analyses[analysis_id]['detected_points'] = detected_points

        # ✅ Mettre à jour Supabase avec les résultats finaux
        update_supabase_video(video_id, "READY", 100, detected_points)
        print(f"🏐 Analyse terminée: {len(detected_points)} points détectés pour video {video_id}")

        analyzer.cap.release()

        # Nettoyer le fichier vidéo temporaire
        if os.path.exists(video_path) and video_path.startswith(tempfile.gettempdir()):
            try: os.remove(video_path)
            except: pass

    except Exception as e:
        analyses[analysis_id]['status'] = 'error'
        analyses[analysis_id]['error'] = str(e)
        analyses[analysis_id]['percent'] = 0
        # ❌ Mettre à jour Supabase avec le statut erreur
        update_supabase_video(video_id, "ERROR", 0)
        import traceback
        print(traceback.format_exc())


def _position_to_number(pos_str):
    """Convertit P1-P6 en 1-6."""
    try:
        return int(pos_str.replace('P', ''))
    except:
        return 1


@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'CourtVision YOLO Volleyball Analyzer',
        'supabase_connected': supabase_client is not None,
    })


@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    """Lancer une analyse. Accepte: upload fichier OU JSON { video_url: "...", video_id: "..." }"""
    video_path = None
    params = {}

    if request.content_type and 'multipart' in request.content_type:
        if 'video' in request.files:
            video_file = request.files['video']
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            video_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{video_file.filename}")
            video_file.save(video_path)
        params = {
            'video_id': request.form.get('video_id'),
            'confidence': float(request.form.get('confidence', 0.4)),
            'frame_skip': int(request.form.get('frame_skip', 5)),
            'team_left': request.form.get('team_left', 'Equipe A'),
            'team_right': request.form.get('team_right', 'Equipe B'),
            'setter_start_left': request.form.get('setter_start_left', 'P1'),
            'setter_start_right': request.form.get('setter_start_right', 'P1'),
            'first_serve': request.form.get('first_serve', 'left'),
        }
    else:
        data = request.get_json() or {}
        video_url = data.get('video_url')
        if video_url:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            ext = video_url.split('?')[0].split('.')[-1][:4] or 'mp4'
            video_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.{ext}")
            try:
                download_video(video_url, video_path)
            except Exception as e:
                # Mettre à jour Supabase avec erreur si on a le video_id
                video_id = data.get('video_id')
                update_supabase_video(video_id, "ERROR", 0)
                return jsonify({'error': f'Impossible de telecharger la video: {e}'}), 400
        elif data.get('video_path') and os.path.exists(data['video_path']):
            video_path = data['video_path']
        params = {
            'video_id': data.get('video_id'),
            'confidence': float(data.get('confidence', 0.4)),
            'frame_skip': int(data.get('frame_skip', 5)),
            'team_left': data.get('team_left', 'Equipe A'),
            'team_right': data.get('team_right', 'Equipe B'),
            'setter_start_left': data.get('setter_start_left', 'P1'),
            'setter_start_right': data.get('setter_start_right', 'P1'),
            'first_serve': data.get('first_serve', 'left'),
        }

    if not video_path:
        return jsonify({'error': 'Pas de video fournie. Envoyez un fichier ou video_url.'}), 400

    analysis_id = uuid.uuid4().hex[:12]
    analyses[analysis_id] = {
        'id': analysis_id, 'status': 'queued', 'progress': 'En attente...',
        'percent': 0, 'results': None, 'detected_points': None, 'error': None,
    }

    thread = threading.Thread(target=run_analysis, args=(analysis_id, video_path, params), daemon=True)
    thread.start()

    return jsonify({'analysis_id': analysis_id, 'status': 'queued', 'video_id': params.get('video_id')}), 202


@app.route('/api/analyze/<analysis_id>', methods=['GET'])
def get_analysis(analysis_id):
    if analysis_id not in analyses:
        return jsonify({'error': 'Analyse non trouvee'}), 404
    a = analyses[analysis_id]
    resp = {'id': analysis_id, 'status': a['status'], 'progress': a['progress'], 'percent': a.get('percent', 0)}
    if a['status'] == 'completed':
        resp['detected_points'] = a['detected_points']
    elif a['status'] == 'error':
        resp['error'] = a['error']
    return jsonify(resp)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=int(os.environ.get('PORT', 5000)))
    args = parser.parse_args()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n🏐 CourtVision YOLO Volleyball API - http://localhost:{args.port}/api/health\n")
    app.run(host='0.0.0.0', port=args.port, debug=False)
