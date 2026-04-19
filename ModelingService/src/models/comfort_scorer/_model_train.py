"""Training pipeline for ComfortScorerModel."""

import json
import logging
import os
import time
from datetime import date, datetime

from ...core.base_model import ModelMetadata
from .features import FeatureExtractor
from .trainer import ComfortScorerTrainer

logger = logging.getLogger(__name__)


async def train_comfort_model(
    db_pool,
    model_base_path: str,
    name: str,
    start_date: date,
    end_date: date,
    reason: str = "manual",
) -> ModelMetadata:
    """Train new comfort scorer model and save to disk."""
    logger.info(f"Training {name}: {start_date} to {end_date}, reason={reason}")

    trainer = ComfortScorerTrainer(db_pool)
    X, y = await trainer.build_dataset(start_date, end_date)

    if len(X) < 1000:
        raise ValueError(f"Insufficient training samples: {len(X)} (need >1000)")

    model, metrics = trainer.train_lightgbm(X, y)

    new_version = f"v{int(time.time())}"
    save_path = os.path.join(model_base_path, name, new_version)
    os.makedirs(save_path, exist_ok=True)
    model.save_model(os.path.join(save_path, "comfort_model.txt"))

    metadata = ModelMetadata(
        name=name, version=new_version,
        model_type="regression", framework="lightgbm",
        trained_at=datetime.now(),
        feature_names=FeatureExtractor.FEATURE_NAMES,
        feature_count=len(FeatureExtractor.FEATURE_NAMES),
        target_metric="rmse", performance=metrics,
        file_path=save_path,
        is_active=False, is_shadow=True,
    )

    meta_dict = {
        'name': metadata.name, 'version': metadata.version,
        'model_type': metadata.model_type, 'framework': metadata.framework,
        'trained_at': metadata.trained_at.isoformat(),
        'feature_names': metadata.feature_names,
        'feature_count': metadata.feature_count,
        'target_metric': metadata.target_metric,
        'performance': metadata.performance,
        'file_path': metadata.file_path,
        'is_active': metadata.is_active,
        'is_shadow': metadata.is_shadow,
    }
    with open(os.path.join(save_path, "metadata.json"), "w") as f:
        json.dump(meta_dict, f, indent=2)

    logger.info(f"Saved new model: {new_version} at {save_path}")
    return metadata
