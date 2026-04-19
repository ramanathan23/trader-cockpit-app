"""Model file loading for ComfortScorerModel."""

import json
import logging
import os
from datetime import datetime
from typing import Optional

import lightgbm as lgb

from ...core.base_model import ModelMetadata, get_active_version
from .features import FeatureExtractor

logger = logging.getLogger(__name__)


async def load_comfort_model(
    model_base_path: str,
    name: str,
    version: Optional[str],
    db_pool,
) -> tuple:
    """
    Load LightGBM model + metadata + feature extractor.

    Returns (lgb.Booster|None, ModelMetadata|None, FeatureExtractor|None, version_str)
    """
    if not version:
        try:
            version = get_active_version(model_base_path, name)
        except Exception:
            logger.warning(f"No active version for {name}, using v1")
            version = "v1"

    model_path = os.path.join(model_base_path, name, version)
    model_file = os.path.join(model_path, "comfort_model.txt")

    if not os.path.exists(model_file):
        logger.warning(f"Model file not found: {model_file}. Model not loaded.")
        return None, None, None, version

    booster = lgb.Booster(model_file=model_file)
    metadata = None

    metadata_file = os.path.join(model_path, "metadata.json")
    if os.path.exists(metadata_file):
        with open(metadata_file) as f:
            meta = json.load(f)
        metadata = ModelMetadata(
            name=meta['name'], version=meta['version'],
            model_type=meta['model_type'], framework=meta['framework'],
            trained_at=datetime.fromisoformat(meta['trained_at']),
            feature_names=meta['feature_names'], feature_count=meta['feature_count'],
            target_metric=meta['target_metric'], performance=meta['performance'],
            file_path=model_path,
            is_active=meta.get('is_active', False),
            is_shadow=meta.get('is_shadow', False),
        )

    extractor = FeatureExtractor(db_pool) if db_pool else None
    logger.info(f"Loaded {name} {version}")
    return booster, metadata, extractor, version
