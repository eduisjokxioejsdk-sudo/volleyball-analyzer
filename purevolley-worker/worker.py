#!/usr/bin/env python3
"""
PureVolley Worker - Système de découpage de matchs de volley par IA
Worker local tournant sur PC Ubuntu avec carte graphique AMD RX 6600 (ROCm 6.1)

Fonctionnalités :
1. Connexion à Supabase pour surveiller les matchs avec status='pending'
2. Téléchargement des vidéos depuis Wasabi S3
3. Vérification de la disponibilité GPU (RX 6600 avec ROCm)
4. Simulation de traitement (5 secondes)
5. Mise à jour du statut dans Supabase
6. Upload de logs sur Wasabi S3
"""

import os
import sys
import time
import logging
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError
from supabase import create_client, Client
from dotenv import load_dotenv
import torch
import cv2

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

class PureVolleyWorker:
    """Worker principal pour le traitement des vidéos de volley."""
    
    def __init__(self):
        """Initialise le worker avec les connexions aux services."""
        self.supabase: Optional[Client] = None
        self.s3_client = None
        self.gpu_available = False
        self.initialize_services()
        self.check_gpu()
    
    def initialize_services(self):
        """Initialise les connexions à Supabase et Wasabi S3."""
        try:
            # Connexion à Supabase
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not supabase_url or not supabase_key:
                raise ValueError("Variables d'environnement Supabase manquantes")
            
            self.supabase = create_client(supabase_url, supabase_key)
            logger.info("✅ Connexion à Supabase établie")
            
            # Connexion à Wasabi S3
            wasabi_access_key = os.getenv('WASABI_ACCESS_KEY')
            wasabi_secret_key = os.getenv('WASABI_SECRET_KEY')
            wasabi_endpoint = os.getenv('WASABI_ENDPOINT', 'https://s3.wasabisys.com')
            wasabi_region = os.getenv('WASABI_REGION', 'us-east-1')
            
            if not wasabi_access_key or not wasabi_secret_key:
                raise ValueError("Variables d'environnement Wasabi manquantes")
            
            self.s3_client = boto3.client(
                's3',
                endpoint_url=wasabi_endpoint,
                region_name=wasabi_region,
                aws_access_key_id=wasabi_access_key,
                aws_secret_access_key=wasabi_secret_key
            )
            logger.info("✅ Connexion à Wasabi S3 établie")
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation des services: {e}")
            raise
    
    def check_gpu(self):
        """Vérifie la disponibilité du GPU AMD RX 6600 avec ROCm."""
        try:
            self.gpu_available = torch.cuda.is_available()
            
            if self.gpu_available:
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"✅ GPU disponible: {gpu_name}")
                logger.info(f"   Nombre de GPU: {gpu_count}")
                logger.info(f"   Version PyTorch: {torch.__version__}")
                logger.info(f"   Version CUDA: {torch.version.cuda}")
                
                # Vérification spécifique pour ROCm
                if hasattr(torch, 'version') and hasattr(torch.version, 'hip'):
                    logger.info(f"   Version ROCm/HIP: {torch.version.hip}")
            else:
                logger.warning("⚠️  Aucun GPU disponible - Le traitement sera exécuté sur CPU")
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification GPU: {e}")
            self.gpu_available = False
    
    def get_pending_matches(self):
        """Récupère les matchs avec status='pending' depuis Supabase."""
        try:
            response = self.supabase.table('matches')\
                .select('*')\
                .eq('status', 'pending')\
                .order('created_at', desc=False)\
                .limit(10)\
                .execute()
            
            matches = response.data if hasattr(response, 'data') else []
            logger.info(f"📊 {len(matches)} match(s) en attente trouvé(s)")
            return matches
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des matchs: {e}")
            return []
    
    def download_video_from_s3(self, video_url: str, local_path: Path) -> bool:
        """
        Télécharge une vidéo depuis Wasabi S3.
        
        Args:
            video_url: URL S3 de la vidéo
            local_path: Chemin local où sauvegarder la vidéo
            
        Returns:
            bool: True si le téléchargement a réussi
        """
        try:
            # Extraction du bucket et de la clé depuis l'URL
            # Format attendu: s3://bucket-name/path/to/video.mp4
            if video_url.startswith('s3://'):
                bucket_key = video_url[5:]  # Retire 's3://'
                parts = bucket_key.split('/', 1)
                if len(parts) == 2:
                    bucket, key = parts
                else:
                    bucket = os.getenv('WASABI_BUCKET', 'purevolley')
                    key = parts[0]
            else:
                # Supposons que c'est juste la clé S3
                bucket = os.getenv('WASABI_BUCKET', 'purevolley')
                key = video_url
            
            logger.info(f"📥 Téléchargement depuis S3: bucket={bucket}, key={key}")
            
            # Téléchargement du fichier
            self.s3_client.download_file(bucket, key, str(local_path))
            
            # Vérification que le fichier existe et n'est pas vide
            if local_path.exists() and local_path.stat().st_size > 0:
                logger.info(f"✅ Vidéo téléchargée: {local_path} ({local_path.stat().st_size} bytes)")
                return True
            else:
                logger.error(f"❌ Fichier téléchargé vide ou inexistant: {local_path}")
                return False
                
        except ClientError as e:
            logger.error(f"❌ Erreur S3 lors du téléchargement: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur inattendue lors du téléchargement: {e}")
            return False
    
    def process_video(self, video_path: Path, match_id: str) -> Dict[str, Any]:
        """
        Traite une vidéo de match de volley.
        
        Args:
            video_path: Chemin vers la vidéo à traiter
            match_id: ID du match dans Supabase
            
        Returns:
            Dict contenant les résultats du traitement
        """
        logger.info(f"🎬 Début du traitement pour le match {match_id}")
        
        try:
            # 1. Vérification de base de la vidéo avec OpenCV
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise ValueError(f"Impossible d'ouvrir la vidéo: {video_path}")
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0
            
            logger.info(f"   📹 Informations vidéo: {frame_count} frames, {fps:.2f} FPS, {duration:.2f} secondes")
            cap.release()
            
            # 2. Simulation de traitement IA (5 secondes)
            logger.info("   🤖 Simulation de traitement IA (5 secondes)...")
            start_time = time.time()
            
            # Simulation de travail sur GPU si disponible
            if self.gpu_available:
                # Création d'un tenseur sur GPU pour tester
                test_tensor = torch.randn(1000, 1000, device='cuda')
                # Opération simple pour vérifier le GPU
                result = test_tensor @ test_tensor.T
                logger.info(f"   🚀 Opération GPU testée: {result.shape}")
            
            # Attente de 5 secondes pour simuler le traitement
            time.sleep(5)
            
            processing_time = time.time() - start_time
            logger.info(f"   ⏱️  Temps de traitement simulé: {processing_time:.2f} secondes")
            
            # 3. Génération de résultats simulés
            results = {
                'match_id': match_id,
                'processing_time': processing_time,
                'video_duration': duration,
                'frame_count': frame_count,
                'fps': fps,
                'gpu_used': self.gpu_available,
                'detected_rallies': 12,  # Simulation
                'detected_actions': 45,  # Simulation
                'processing_date': datetime.utcnow().isoformat(),
                'status': 'completed'
            }
            
            logger.info(f"✅ Traitement terminé pour le match {match_id}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement de la vidéo: {e}")
            raise
    
    def update_match_status(self, match_id: str, status: str, results: Dict[str, Any] = None):
        """
        Met à jour le statut d'un match dans Supabase.
        
        Args:
            match_id: ID du match
            status: Nouveau statut ('processing', 'completed', 'failed')
            results: Résultats du traitement à sauvegarder
        """
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if results:
                # Ajout des résultats au champ metadata ou création d'un champ dédié
                update_data['metadata'] = results
            
            response = self.supabase.table('matches')\
                .update(update_data)\
                .eq('id', match_id)\
                .execute()
            
            logger.info(f"📝 Statut du match {match_id} mis à jour: {status}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la mise à jour du statut: {e}")
            return False
    
    def upload_log_to_s3(self, log_content: str, match_id: str) -> bool:
        """
        Upload un fichier de log sur Wasabi S3.
        
        Args:
            log_content: Contenu du log
            match_id: ID du match pour le nom du fichier
            
        Returns:
            bool: True si l'upload a réussi
        """
        try:
            bucket = os.getenv('WASABI_BUCKET', 'purevolley')
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            log_key = f"logs/match_{match_id}_{timestamp}.log"
            
            # Création d'un fichier temporaire
            with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
                f.write(log_content)
                temp_log_path = f.name
            
            # Upload vers S3
            self.s3_client.upload_file(temp_log_path, bucket, log_key)
            
            # Nettoyage du fichier temporaire
            os.unlink(temp_log_path)
            
            logger.info(f"📤 Log uploadé sur S3: {log_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'upload du log: {e}")
            return False
    
    def process_single_match(self, match: Dict[str, Any]) -> bool:
        """
        Traite un seul match de bout en bout.
        
        Args:
            match: Dictionnaire contenant les données du match
            
        Returns:
            bool: True si le traitement a réussi
        """
        match_id = match.get('id')
        video_url = match.get('video_url')
        
        if not match_id or not video_url:
            logger.error(f"❌ Données de match incomplètes: {match}")
            return False
        
        logger.info(f"🔍 Traitement du match {match_id}")
        
        try:
            # 1. Mise à jour du statut à 'processing'
            self.update_match_status(match_id, 'processing')
            
            # 2. Téléchargement de la vidéo
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_video_path = Path(temp_file.name)
            
            if not self.download_video_from_s3(video_url, temp_video_path):
                self.update_match_status(match_id, 'failed')
                return False
            
            # 3. Traitement de la vidéo
            results = self.process_video(temp_video_path, match_id)
            
            # 4. Mise à jour du statut à 'completed'
            self.update_match_status(match_id, 'completed', results)
            
            # 5. Upload d'un log de confirmation
            log_content = f"Traitement réussi pour le match {match_id}\n"
            log_content += f"Date: {datetime.utcnow().isoformat()}\n"
            log_content += f"Résultats: {results}\n"
            self.upload_log_to_s3(log_content, match_id)
            
            # 6. Nettoyage du fichier temporaire
            if temp_video_path.exists():
                temp_video_path.unlink()
            
            logger.info(f"🎉 Match {match_id} traité avec succès!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement du match {match_id}: {e}")
            logger.error(traceback.format_exc())
            
            # Mise à jour du statut à 'failed'
            self.update_match_status(match_id, 'failed')
            
            # Upload du log d'erreur
            error_log = f"Erreur lors du traitement du match {match_id}\n"
            error_log += f"Date: {datetime.utcnow().isoformat()}\n"
            error_log += f"Erreur: {str(e)}\n"
            error_log += f"Traceback: {traceback.format_exc()}\n"
            self.upload_log_to_s3(error_log, match_id)
            
            return False
    
    def run(self):
        """Boucle principale du worker."""
        logger.info("🚀 Démarrage du PureVolley Worker")
        logger.info(f"   GPU disponible: {self.gpu_available}")
        logger.info(f"   PyTorch version: {torch.__version__}")
        
        poll_interval = 30  # secondes entre chaque vérification
        
        while True:
            try:
                logger.info("🔎 Vérification des matchs en attente...")
                
                # Récupération des matchs en attente
                pending_matches = self.get_pending_matches()
                
                if pending_matches:
                    for match in pending_matches:
                        success = self.process_single_match(match)
                        if not success:
                            logger.warning(f"⚠️  Échec du traitement pour le match {match.get('id')}")
                
                else:
                    logger.info(f"😴 Aucun match en attente. Attente de {poll_interval} secondes...")
                
                # Attente avant la prochaine vérification
                time.sleep(poll_interval)
                
            except KeyboardInterrupt:
                logger.info("👋 Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle principale: {e}")
                logger.error(traceback.format_exc())
                logger.info(f"⏳ Nouvelle tentative dans {poll_interval} secondes...")
                time.sleep(poll_interval)

def main():
    """Point d'entrée principal."""
    try:
        worker = PureVolleyWorker()
        worker.run()
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()