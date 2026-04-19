"""Rule-set loading for ComfortScorerModel."""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ...core.base_model import ModelMetadata
from .features import FeatureExtractor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChartComfortRuleSet:
    """Loaded marker for the active chart-comfort rule set."""

    version: str = "chart_comfort_v2"


async def load_comfort_model(
    model_base_path: str,
    name: str,
    version: Optional[str],
    db_pool,
) -> tuple:
    """
    Load chart-comfort rule set + metadata + feature extractor.

    Returns (ChartComfortRuleSet, ModelMetadata, FeatureExtractor|None, version_str).
    """
    version = version or "chart_comfort_v2"
    model_path = os.path.join(model_base_path, name, version)
    rule_set = ChartComfortRuleSet(version=version)
    extractor = FeatureExtractor(db_pool) if db_pool else None
    metadata = ModelMetadata(
        name=name,
        version=version,
        model_type="rule_based",
        framework="chart_comfort_rules",
        trained_at=datetime.now(),
        feature_names=FeatureExtractor.FEATURE_NAMES,
        feature_count=len(FeatureExtractor.FEATURE_NAMES),
        target_metric="not_applicable",
        performance={},
        file_path=model_path,
        is_active=True,
        is_shadow=False,
    )
    logger.info("Loaded %s %s rule set", name, version)
    return rule_set, metadata, extractor, version
