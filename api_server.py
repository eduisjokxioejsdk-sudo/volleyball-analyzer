#!/usr/bin/env python3
"""
CourtVision v2 — API REST (FastAPI)
====================================
Expose l'analyse VideoMAE + YOLO via une API REST.
Met à jour Supabase en direct pendant l'analyse.
"""
import os, sys, json, uuid, threading, tempfile
from pathlib import Path

# PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from analyze_video import VolleyballAnalyzer

# ---------------------------------------------------------------------------
# Supabase (optionnel)
# ---------------------------------------------------------------------------
supabase_client = None
try:
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if SUPABASE_URL and SUPABASE_KEY:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"✅ Supabase connecté: {SUPABASE_URL[:40]}...")
    else:
        print("ℹ️  Pas de SUPABASE_SERVICE_KEY — le frontend gère via polling")
except Exception:
    print("ℹ️  Supabase non configuré")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="CourtVision v2 — VideoMAE + YOLO API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

analyses = {}
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "cv_uploads")
OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "cv_outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def update_supabase_video(video_id, status, progress, points_data=None):
    if not supabase_client or not video_id:
        return
    try:
        data = {"status": status, "progress": progress}
        if points_data is not None:
            data["points_data"] = points_data
        supabase_client.table("videos").update(data).eq("id", video_id).execute()
        print(f"📝 Supabase: {video_id[:8]}... → {status} ({progress}%)")
    except Exception as e:
        print(f"⚠️  Supabase update error: {e}")


def download_video(url, dest):
    import requests as req
    print(f"⬇️  Téléchargement: {url[:80]}...")
    r = req.get(url, stream=True, timeout=600)
    r.raise_for_status()
    with open(dest, 'wb') as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"   ✅ {mb:.1f} MB téléchargés")


def _position_to_number(pos_str):
    try:
        return int(pos_str.replace('P', ''))
    except Exception:
        return 1


# ---------------------------------------------------------------------------
# Background analysis
# ---------------------------------------------------------------------------

def run_analysis(analysis_id, video_path_or_url, params):
    video_id = params.get('video_id')
    video_path = video_path_or_url

    try:
        # Télécharger si URL
        if isinstance(video_path_or_url, str) and video_path_or_url.startswith('http'):
            analyses[analysis_id]['status'] = 'downloading'
            analyses[analysis_id]['progress'] = 'Téléchargement...'
            analyses[analysis_id]['percent'] = 1
            update_supabase_video(video_id, "PROCESSING", 1)

            ext = video_path_or_url.split('?')[0].split('.')[-1][:4] or 'mp4'
            video_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.{ext}")
            try:
                download_video(video_path_or_url, video_path)
            except Exception as e:
                update_supabase_video(video_id, "ERROR", 0)
                analyses[analysis_id].update(status='error', error=f'Download failed: {e}')
                return

        # Lancer l'analyse
        analyses[analysis_id].update(status='running', progress='Chargement des modèles...', percent=3)
        update_supabase_video(video_id, "PROCESSING", 3)

        output_dir = os.path.join(OUTPUT_DIR, analysis_id)

        analyzer = VolleyballAnalyzer(
            video_path=video_path,
            output_dir=output_dir,
            team_left=params.get('team_left', 'Equipe A'),
            team_right=params.get('team_right', 'Equipe B'),
            setter_start_left=params.get('setter_start_left', 'P1'),
            setter_start_right=params.get('setter_start_right', 'P1'),
            first_serve=params.get('first_serve', 'left'),
            use_gpu=params.get('use_gpu', False),
        )

        # Progress callback pour le scan vidéo
        def on_progress(pct):
            global_pct = 5 + int(pct * 0.90)  # 5% → 95%
            analyses[analysis_id].update(percent=global_pct, progress=f'Analyse... {pct}%')
            update_supabase_video(video_id, "PROCESSING", global_pct)

        analyses[analysis_id].update(progress='Analyse vidéo...', percent=5)
        update_supabase_video(video_id, "PROCESSING", 5)

        # Pipeline complet (scan + build + score + export)
        analyzer.run(progress_callback=on_progress)

        # Lire les résultats JSON
        results_path = os.path.join(output_dir, "analysis_results.json")
        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)

        # Convertir au format frontend (DetectedPoint[])
        detected_points = []
        for rally in results.get('rallies', []):
            rot = rally.get('rotation', {})
            team_left = params.get('team_left', 'Equipe A')
            team_right = params.get('team_right', 'Equipe B')
            detected_points.append({
                'id': rally['rally_num'],
                'startTime': rally['start_time'],
                'endTime': rally['end_time'],
                'label': f"Point {rally['rally_num']}",
                'winner': 'A' if rally['scored_by'] == team_left else 'B' if rally['scored_by'] == team_right else None,
                'servingTeamAtStart': 'A' if rot.get('serving_team') == team_left else 'B',
                'rotationAtStart': _position_to_number(rot.get('setter_left', 'P1')),
            })

        analyses[analysis_id].update(
            status='completed', progress='Terminé', percent=100,
            results=results, detected_points=detected_points,
        )
        update_supabase_video(video_id, "READY", 100, detected_points)
        print(f"🏐 Terminé: {len(detected_points)} points pour video {video_id}")

        # Cleanup
        if os.path.exists(video_path) and video_path.startswith(tempfile.gettempdir()):
            try:
                os.remove(video_path)
            except Exception:
                pass

    except Exception as e:
        analyses[analysis_id].update(status='error', error=str(e), percent=0)
        update_supabase_video(video_id, "ERROR", 0)
        import traceback
        print(traceback.format_exc())


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "CourtVision v2 — VideoMAE + YOLO API",
        "supabase_connected": supabase_client is not None,
    }


@app.post("/api/analyze")
async def start_analysis_endpoint(
    video_url: str = Form(None),
    video_id: str = Form(None),
    team_left: str = Form("Equipe A"),
    team_right: str = Form("Equipe B"),
    setter_start_left: str = Form("P1"),
    setter_start_right: str = Form("P1"),
    first_serve: str = Form("left"),
    video: UploadFile = File(None),
):
    """Lancer une analyse. Accepte: upload ou video_url."""
    video_path = None
    params = dict(
        video_id=video_id, team_left=team_left, team_right=team_right,
        setter_start_left=setter_start_left, setter_start_right=setter_start_right,
        first_serve=first_serve, use_gpu=False,
    )

    if video is not None:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        video_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{video.filename}")
        with open(video_path, 'wb') as f:
            content = await video.read()
            f.write(content)
    elif video_url:
        video_path = video_url  # sera téléchargé dans le thread
    else:
        raise HTTPException(400, "Pas de vidéo fournie (video_url ou fichier)")

    aid = uuid.uuid4().hex[:12]
    analyses[aid] = dict(id=aid, status='queued', progress='En attente...', percent=0,
                         results=None, detected_points=None, error=None)
    thread = threading.Thread(target=run_analysis, args=(aid, video_path, params), daemon=True)
    thread.start()
    return JSONResponse({"analysis_id": aid, "status": "queued", "video_id": video_id}, 202)


# Aussi accepter du JSON brut
@app.post("/api/analyze/json")
async def start_analysis_json(body: dict):
    """Lancer une analyse via JSON body."""
    video_url = body.get('video_url')
    if not video_url:
        raise HTTPException(400, "video_url requis")

    params = {
        'video_id': body.get('video_id'),
        'team_left': body.get('team_left', 'Equipe A'),
        'team_right': body.get('team_right', 'Equipe B'),
        'setter_start_left': body.get('setter_start_left', 'P1'),
        'setter_start_right': body.get('setter_start_right', 'P1'),
        'first_serve': body.get('first_serve', 'left'),
        'use_gpu': False,
    }

    aid = uuid.uuid4().hex[:12]
    analyses[aid] = dict(id=aid, status='queued', progress='En attente...', percent=0,
                         results=None, detected_points=None, error=None)
    thread = threading.Thread(target=run_analysis, args=(aid, video_url, params), daemon=True)
    thread.start()
    return JSONResponse({"analysis_id": aid, "status": "queued", "video_id": params.get('video_id')}, 202)


@app.get("/api/analyze/{analysis_id}")
def get_analysis(analysis_id: str):
    if analysis_id not in analyses:
        raise HTTPException(404, "Analyse non trouvée")
    a = analyses[analysis_id]
    resp = {"id": analysis_id, "status": a['status'], "progress": a['progress'], "percent": a.get('percent', 0)}
    if a['status'] == 'completed':
        resp['detected_points'] = a['detected_points']
    elif a['status'] == 'error':
        resp['error'] = a['error']
    return resp


@app.get("/api/analyses")
def list_analyses():
    return {
        "count": len(analyses),
        "analyses": [
            {"id": a['id'], "status": a['status'], "progress": a['progress'],
             "percent": a.get('percent', 0), "error": a.get('error')}
            for a in analyses.values()
        ]
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"\n🏐 CourtVision v2 API — http://localhost:{port}/api/health\n")
    uvicorn.run(app, host='0.0.0.0', port=port)
