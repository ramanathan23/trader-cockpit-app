import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .db.connection import create_pool, run_migrations
from .api.routes import router
from shared.config_store import load_overrides, apply_overrides
from .core.model_registry import ModelRegistry
from .repositories.prediction_repository import PredictionRepository
from .services.scoring_service import ScoringService
from .services.session_classifier_service import SessionClassifierService
from .services.training_data_service import TrainingDataService

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database connection pool
    pool = await create_pool(
        settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
        command_timeout=settings.db_command_timeout,
    )
    await run_migrations(pool, timeout=settings.db_migration_timeout)
    apply_overrides(settings, await load_overrides(pool, "modeling"))

    # Initialize repositories
    prediction_repo = PredictionRepository(pool)
    
    # Initialize model registry
    registry = ModelRegistry(
        model_base_path=settings.model_base_path,
        db_pool=pool,
    )
    await registry.initialize()
    
    # Initialize services
    scoring_service = ScoringService(pool, registry, prediction_repo)
    training_data_service = TrainingDataService(pool)
    session_classifier_service = SessionClassifierService(pool)

    # Store in app state
    app.state.pool = pool
    app.state.registry = registry
    app.state.prediction_repo = prediction_repo
    app.state.scoring_service = scoring_service
    app.state.training_data_service = training_data_service
    app.state.session_classifier_service = session_classifier_service

    logger.info(f"ModelingService ready. Models loaded: {len(registry.models)}")
    yield
    
    await pool.close()
    logger.info("ModelingService shut down")


app = FastAPI(
    title="ModelingService",
    description="ML model hosting and management for trader-cockpit. Supports multiple models with versioning, A/B testing, and drift monitoring.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")
