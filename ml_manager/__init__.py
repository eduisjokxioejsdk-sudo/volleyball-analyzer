"""
Volleyball Analytics ML Manager Module

This module provides a unified interface for all machine learning models
used in volleyball analytics, including object detection, segmentation,
action recognition, and game state classification.
"""

from .ml_manager import MLManager
from .settings import ModelWeightsConfig
from .enums import YOLOModelType, PlayerDetectionMode, GameState, VolleyballAction

# Training module is optional (requires pandas, etc.)
try:
    from .settings import YOLOTrainingConfig, VideoMAETrainingConfig
    from .training.trainer import UnifiedTrainer
except ImportError:
    UnifiedTrainer = None
    YOLOTrainingConfig = None
    VideoMAETrainingConfig = None

__version__ = "1.0.0"
__author__ = "Volleyball Analytics Team"

__all__ = [
    "MLManager",
    "ModelWeightsConfig",
    "GameState",
    "VolleyballAction",
    "YOLOModelType",
    "PlayerDetectionMode",
]
