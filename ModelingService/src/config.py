from pydantic import Field

from shared.base_config import BaseServiceSettings


class Settings(BaseServiceSettings):

    db_pool_min_size: int = Field(default=3)
    db_pool_max_size: int = Field(default=10)

    # ── Model Storage ─────────────────────────────────────────────────────────
    model_base_path: str = Field(default="/models")
    
    # ── Training ──────────────────────────────────────────────────────────────
    auto_retrain_enabled: bool = Field(default=True)
    max_model_age_days: int = Field(default=90)
    training_concurrency: int = Field(default=1)
    
    # ── Scoring ───────────────────────────────────────────────────────────────
    score_concurrency: int = Field(default=20)

    # ── Comfort Scorer ────────────────────────────────────────────────────────
    comfort_scorer_retrain_threshold_rmse: float = Field(default=8.0)
    comfort_scorer_shadow_days: int = Field(default=7)
    comfort_scorer_min_train_samples: int = Field(default=50000)
    
    # ── Regime Classifier ─────────────────────────────────────────────────────
    regime_classifier_update_frequency: str = Field(default="daily")
    regime_classifier_cache_ttl: int = Field(default=300)  # seconds
    
    # ── Pattern Detector ──────────────────────────────────────────────────────
    pattern_detector_confidence_threshold: float = Field(default=0.75)


settings = Settings()
