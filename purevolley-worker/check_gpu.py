#!/usr/bin/env python3
"""
Script de vérification GPU pour PureVolley Worker
À exécuter dans Coolify pour confirmer que le GPU AMD RX 6600 est bien détecté
"""

import sys
import torch
import platform
import os

def check_gpu():
    """Vérifie la disponibilité et les spécifications du GPU."""
    
    print("=" * 60)
    print("PureVolley Worker - Vérification GPU")
    print("=" * 60)
    
    # Informations système
    print(f"Système: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print(f"PyTorch: {torch.__version__}")
    
    # Variables d'environnement GPU
    print("\nVariables d'environnement GPU:")
    gpu_env_vars = [
        'HSA_OVERRIDE_GFX_VERSION',
        'ROCM_PATH',
        'HIP_VISIBLE_DEVICES',
        'CUDA_VISIBLE_DEVICES'
    ]
    
    for var in gpu_env_vars:
        value = os.getenv(var)
        if value:
            print(f"  {var}: {value}")
        else:
            print(f"  {var}: Non définie")
    
    # Vérification GPU
    print("\nVérification GPU:")
    gpu_available = torch.cuda.is_available()
    
    if gpu_available:
        print("✅ GPU disponible!")
        
        # Nombre de GPUs
        gpu_count = torch.cuda.device_count()
        print(f"  Nombre de GPU: {gpu_count}")
        
        # Détails de chaque GPU
        for i in range(gpu_count):
            print(f"\n  GPU {i}:")
            print(f"    Nom: {torch.cuda.get_device_name(i)}")
            print(f"    Mémoire totale: {torch.cuda.get_device_properties(i).total_memory / 1e9:.2f} GB")
            print(f"    Mémoire allouée: {torch.cuda.memory_allocated(i) / 1e9:.2f} GB")
            print(f"    Mémoire réservée: {torch.cuda.memory_reserved(i) / 1e9:.2f} GB")
        
        # Informations ROCm
        if hasattr(torch.version, 'hip'):
            print(f"\n  Version ROCm/HIP: {torch.version.hip}")
        
        # Test de performance simple
        print("\n  Test de performance GPU:")
        try:
            # Créer des tenseurs sur GPU
            a = torch.randn(1000, 1000, device='cuda')
            b = torch.randn(1000, 1000, device='cuda')
            
            # Opération matricielle
            c = a @ b
            
            print(f"    Opération matricielle réussie: {c.shape}")
            print(f"    Valeur moyenne: {c.mean().item():.4f}")
            
            # Test de mémoire
            del a, b, c
            torch.cuda.empty_cache()
            print("    Nettoyage mémoire GPU: OK")
            
        except Exception as e:
            print(f"    ❌ Erreur lors du test GPU: {e}")
    
    else:
        print("❌ Aucun GPU disponible")
        
        # Vérifier si c'est un problème ROCm
        print("\n  Dépannage:")
        print("  1. Vérifiez que ROCm 6.1 est installé sur l'hôte")
        print("  2. Vérifiez les devices Docker: /dev/kfd et /dev/dri")
        print("  3. Vérifiez les groupes: video et render")
        print("  4. Vérifiez HSA_OVERRIDE_GFX_VERSION=10.3.0 pour RX 6600")
        
        # Vérifier les devices
        print("\n  Vérification des devices:")
        import subprocess
        try:
            result = subprocess.run(['ls', '-la', '/dev/kfd'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("    /dev/kfd: Présent")
            else:
                print("    /dev/kfd: Absent")
                
            result = subprocess.run(['ls', '-la', '/dev/dri'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("    /dev/dri: Présent")
            else:
                print("    /dev/dri: Absent")
        except:
            print("    Impossible de vérifier les devices")
    
    # Vérification des dépendances
    print("\nVérification des dépendances:")
    try:
        import cv2
        print("  OpenCV: OK")
    except ImportError:
        print("  OpenCV: Manquant")
    
    try:
        import boto3
        print("  boto3 (AWS S3): OK")
    except ImportError:
        print("  boto3: Manquant")
    
    try:
        from supabase import create_client
        print("  supabase: OK")
    except ImportError:
        print("  supabase: Manquant")
    
    print("\n" + "=" * 60)
    
    return gpu_available

def main():
    """Point d'entrée principal."""
    try:
        success = check_gpu()
        
        # Message final
        if success:
            print("🎉 PureVolley Worker est prêt à fonctionner sur GPU!")
            print("   Le système peut maintenant traiter les matchs de volley.")
            print("\n   Prochaine étape:")
            print("   1. Vérifiez les logs Coolify pour 'Connexion à Supabase établie'")
            print("   2. Vérifiez les logs Coolify pour 'Connexion à Wasabi S3 établie'")
            print("   3. Créez un match avec status='pending' dans Supabase")
            print("   4. Le worker devrait le détecter et le traiter automatiquement")
        else:
            print("⚠️  Configuration GPU requise")
            print("   Consultez le README.md pour la configuration GPU Passthrough")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()