#!/usr/bin/env python3
"""
PureVolley Worker - Analyse GPU de vidéos de volley
====================================================
Surveille la table 'videos' dans Supabase (status='PROCESSING'),
télécharge la vidéo depuis Wasabi S3, exécute l'analyse IA avec GPU,
et met à jour les résultats dans Supabase.
"""

import os
import sys
import time
import json
import logging
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import boto3
import requests
from botocore.exceptions import ClientError
from supabase import create_client, Client
from dotenv import load_dotenv
import torch

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('worker.log')
    ]
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()

# Ajouter le dossier parent au path pour importer ml_manager et analyze_video
WORKER_DIR = Path(__file__).parent
sys.path.insert(0, str(WORKER_DIR))

# Lazy import de VolleyballAnalyzer
VolleyballAnalyzer = None

ROTATION_ORDER = ['P1', 'P6', 'P5', 'P4', 'P3', 'P2']


def _position_to_number(pos_str):
    try:
        return int(pos_str.replace('P', ''))
    except Exception:
        return 1


class PureVolleyWorker:
    """Worker principal pour le traitement GPU des vidéos de volley."""

    def __init__(self):
        self.supabase: Optional[Client] = None
        self.s3_client = None
        self.gpu_available = False
        self.initialize_services()
        self.check_gpu()
        self.ensure_models()

    def initialize_services(self):
        """Initialise les connexions à Supabase et Wasabi S3."""
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            if not supabase_url or not supabase_key:
                raise ValueError("Variables SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY manquantes")
            self.supabase = create_client(supabase_url, supabase_key)
            logger.info("✅ Connexion à Supabase établie")

            wasabi_access = os.getenv('WASABI_ACCESS_KEY')
            wasabi_secret = os.getenv('WASABI_SECRET_KEY')
            wasabi_endpoint = os.getenv('WASABI_ENDPOINT', 'https://s3.eu-west-2.wasabisys.com')
            wasabi_region = os.getenv('WASABI_REGION', 'eu-west-2')
            if not wasabi_access or not wasabi_secret:
                raise ValueError("Variables WASABI_ACCESS_KEY / WASABI_SECRET_KEY manquantes")
            self.s3_client = boto3.client(
                's3', endpoint_url=wasabi_endpoint, region_name=wasabi_region,
                aws_access_key_id=wasabi_access, aws_secret_access_key=wasabi_secret
            )
            self.wasabi_bucket = os.getenv('WASABI_BUCKET', 'courtvision')
            logger.info("✅ Connexion à Wasabi S3 établie")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            raise

    def check_gpu(self):
        """Vérifie la disponibilité GPU."""
        try:
            self.gpu_available = torch.cuda.is_available()
            if self.gpu_available:
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"✅ GPU: {gpu_name} | PyTorch {torch.__version__} | CUDA {torch.version.cuda}")
            else:
                logger.warning("⚠️ Pas de GPU - CPU uniquement")
        except Exception as e:
            logger.error(f"❌ Erreur GPU: {e}")
            self.gpu_available = False

    def ensure_models(self):
        """Télécharge les poids ML si nécessaire."""
        weights_dir = WORKER_DIR / "weights"
        if not weights_dir.exists() or not any(weights_dir.rglob("*.pt")):
            logger.info("📦 Téléchargement des poids ML depuis Google Drive...")
            try:
                import gdown
                import zipfile
                weights_dir.mkdir(exist_ok=True)
                zip_path = weights_dir / "all_weights.zip"
                gdown.download(id='1__zkTmGwZo2z0EgbJvC14I_3kOpgQx3o', output=str(zip_path), quiet=False)
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(weights_dir)
                zip_path.unlink()
                logger.info("✅ Poids ML installés")
            except Exception as e:
                logger.error(f"❌ Erreur téléchargement poids: {e}")
        else:
            logger.info("✅ Poids ML déjà présents")

    def get_pending_videos(self) -> List[Dict]:
        """Récupère les vidéos avec status='PROCESSING' depuis Supabase."""
        try:
            response = self.supabase.table('videos') \
                .select('*') \
                .eq('status', 'PROCESSING') \
                .order('created_at', desc=False) \
                .limit(5) \
                .execute()
            videos = response.data if hasattr(response, 'data') else []
            if videos:
                logger.info(f"📊 {len(videos)} vidéo(s) à traiter trouvée(s)")
            return videos
        except Exception as e:
            logger.error(f"❌ Erreur récupération vidéos: {e}")
            return []

    def update_video(self, video_id: str, status: str, progress: int, points_data=None):
        """Met à jour le statut d'une vidéo dans Supabase."""
        try:
            data = {"status": status, "progress": progress}
            if points_data is not None:
                data["points_data"] = points_data
            self.supabase.table('videos').update(data).eq('id', video_id).execute()
            logger.info(f"📝 Video {video_id[:8]}... → {status} ({progress}%)")
        except Exception as e:
            logger.error(f"❌ Erreur update Supabase: {e}")

    def _extract_s3_key(self, video_url: str) -> str:
        """Extrait la clé S3 depuis une URL presignée ou un chemin S3."""
        if not video_url.startswith('http'):
            return video_url  # Déjà une clé S3

        # Extraire la clé depuis l'URL presignée Wasabi
        # Format: https://s3.eu-west-2.wasabisys.com/courtvision/user-id/timestamp-file.mp4?X-Amz-...
        from urllib.parse import urlparse, unquote
        parsed = urlparse(video_url)
        path = unquote(parsed.path)  # /courtvision/user-id/timestamp-file.mp4

        # Retirer le bucket du path si présent
        bucket = self.wasabi_bucket
        if path.startswith(f'/{bucket}/'):
            return path[len(f'/{bucket}/'):]
        elif path.startswith('/'):
            return path[1:]
        return path

    def download_video(self, video_url: str, local_path: Path) -> bool:
        """Télécharge une vidéo depuis Wasabi S3 (génère une URL fraîche)."""
        try:
            # Toujours extraire la clé S3 et télécharger directement via boto3
            s3_key = self._extract_s3_key(video_url)
            logger.info(f"⬇️ Téléchargement S3: bucket={self.wasabi_bucket}, key={s3_key}")
            self.s3_client.download_file(self.wasabi_bucket, s3_key, str(local_path))

            size_mb = local_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Vidéo téléchargée: {size_mb:.1f} MB")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur téléchargement S3: {e}")
            # Fallback: essayer l'URL directement (si pas expirée)
            if video_url.startswith('http'):
                try:
                    logger.info("🔄 Fallback: téléchargement via URL directe...")
                    r = requests.get(video_url, stream=True, timeout=600)
                    r.raise_for_status()
                    with open(local_path, 'wb') as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)
                    size_mb = local_path.stat().st_size / (1024 * 1024)
                    logger.info(f"✅ Vidéo téléchargée (URL directe): {size_mb:.1f} MB")
                    return True
                except Exception as e2:
                    logger.error(f"❌ Fallback URL aussi échoué: {e2}")
            return False

    def run_analysis(self, video_path: Path, video_data: Dict) -> List[Dict]:
        """Exécute l'analyse VolleyballAnalyzer avec GPU."""
        global VolleyballAnalyzer

        # Lazy import
        if VolleyballAnalyzer is None:
            logger.info("📦 Import de VolleyballAnalyzer (torch + transformers)...")
            try:
                from analyze_video import VolleyballAnalyzer as _VA
                VolleyballAnalyzer = _VA
                logger.info("✅ VolleyballAnalyzer importé")
            except ImportError as e:
                logger.error(f"❌ Impossible d'importer VolleyballAnalyzer: {e}")
                logger.info("🔄 Fallback: détection basique par intervalle")
                return self._fallback_analysis(video_path, video_data)

        video_id = video_data.get('id', 'unknown')
        team_left = video_data.get('team_a_name', 'Équipe A')
        team_right = video_data.get('team_b_name', 'Équipe B')
        serving_team = video_data.get('serving_team', 'A')
        initial_rotation = video_data.get('initial_rotation', 1)
        first_serve = 'left' if serving_team == 'A' else 'right'
        setter_start = ROTATION_ORDER[initial_rotation - 1] if 1 <= initial_rotation <= 6 else 'P1'

        output_dir = Path(tempfile.mkdtemp(prefix=f"cv_{video_id[:8]}_"))

        try:
            analyzer = VolleyballAnalyzer(
                video_path=str(video_path),
                output_dir=str(output_dir),
                team_left=team_left,
                team_right=team_right,
                setter_start_left=setter_start,
                setter_start_right='P1',
                first_serve=first_serve,
                use_gpu=self.gpu_available,
            )

            def on_progress(pct):
                global_pct = 5 + int(pct * 0.90)
                self.update_video(video_id, "PROCESSING", global_pct)

            self.update_video(video_id, "PROCESSING", 5)
            analyzer.run(progress_callback=on_progress)

            # Lire les résultats
            results_path = output_dir / "analysis_results.json"
            if results_path.exists():
                with open(results_path, 'r', encoding='utf-8') as f:
                    results = json.load(f)

                detected_points = []
                for rally in results.get('rallies', []):
                    rot = rally.get('rotation', {})
                    detected_points.append({
                        'id': rally['rally_num'],
                        'startTime': rally['start_time'],
                        'endTime': rally['end_time'],
                        'label': f"Point {rally['rally_num']}",
                        'winner': 'A' if rally['scored_by'] == team_left else 'B' if rally['scored_by'] == team_right else None,
                        'servingTeamAtStart': 'A' if rot.get('serving_team') == team_left else 'B',
                        'rotationAtStart': _position_to_number(rot.get('setter_left', 'P1')),
                    })
                logger.info(f"🏐 Analyse terminée: {len(detected_points)} points détectés")
                return detected_points
            else:
                logger.warning("⚠️ Pas de fichier résultats trouvé")
                return []

        except Exception as e:
            logger.error(f"❌ Erreur analyse: {e}")
            logger.error(traceback.format_exc())
            logger.info("🔄 Fallback: détection basique")
            return self._fallback_analysis(video_path, video_data)
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)

    def _fallback_analysis(self, video_path: Path, video_data: Dict) -> List[Dict]:
        """Analyse basique si les modèles ML ne sont pas disponibles."""
        import cv2
        logger.info("🔧 Analyse fallback: découpage par intervalle régulier")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()

        # Découper en segments de ~30 secondes comme approximation de points
        segment_duration = 30.0
        points = []
        current_time = 5.0  # Commencer à 5s

        serving_team = video_data.get('serving_team', 'A')
        rotation = video_data.get('initial_rotation', 1)

        while current_time + segment_duration < duration - 5:
            points.append({
                'id': len(points) + 1,
                'startTime': round(current_time, 1),
                'endTime': round(current_time + segment_duration, 1),
                'label': f"Point {len(points) + 1}",
                'winner': None,
                'servingTeamAtStart': serving_team,
                'rotationAtStart': rotation,
            })
            current_time += segment_duration + 5  # 5s de pause entre points

        logger.info(f"📊 Fallback: {len(points)} segments créés ({segment_duration}s chacun)")
        return points

    def process_video(self, video_data: Dict) -> bool:
        """Traite une vidéo de bout en bout."""
        video_id = video_data.get('id')
        video_url = video_data.get('video_url')

        if not video_id or not video_url:
            logger.error(f"❌ Données vidéo incomplètes: {video_data}")
            return False

        logger.info(f"🎬 Traitement vidéo {video_id[:8]}... - {video_data.get('title', 'Sans titre')}")

        try:
            # 1. Update status
            self.update_video(video_id, "PROCESSING", 1)

            # 2. Télécharger la vidéo
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
                temp_path = Path(f.name)

            if not self.download_video(video_url, temp_path):
                self.update_video(video_id, "ERROR", 0)
                return False

            self.update_video(video_id, "PROCESSING", 3)

            # 3. Lancer l'analyse
            detected_points = self.run_analysis(temp_path, video_data)

            # 4. Mettre à jour Supabase
            self.update_video(video_id, "READY", 100, detected_points)
            logger.info(f"🎉 Vidéo {video_id[:8]}... terminée: {len(detected_points)} points!")

            # 5. Cleanup
            if temp_path.exists():
                temp_path.unlink()

            return True

        except Exception as e:
            logger.error(f"❌ Erreur traitement vidéo {video_id[:8]}...: {e}")
            logger.error(traceback.format_exc())
            self.update_video(video_id, "ERROR", 0)
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            return False

    def run(self):
        """Boucle principale du worker."""
        logger.info("🚀 Démarrage du PureVolley Worker")
        logger.info(f"   GPU: {self.gpu_available} | PyTorch: {torch.__version__}")

        poll_interval = 15  # secondes

        while True:
            try:
                pending = self.get_pending_videos()
                if pending:
                    for video in pending:
                        self.process_video(video)
                else:
                    logger.debug(f"😴 Aucune vidéo en attente. Attente {poll_interval}s...")

                time.sleep(poll_interval)

            except KeyboardInterrupt:
                logger.info("👋 Arrêt demandé")
                break
            except Exception as e:
                logger.error(f"❌ Erreur boucle: {e}")
                logger.error(traceback.format_exc())
                time.sleep(poll_interval)


if __name__ == "__main__":
    try:
        worker = PureVolleyWorker()
        worker.run()
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
