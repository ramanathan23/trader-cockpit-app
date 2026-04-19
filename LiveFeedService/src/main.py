import logging

from fastapi import FastAPI

from .config import settings
from ._lifespan import lifespan
from .api.routes import router

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)

app = FastAPI(
    title="LiveFeedService",
    description=(
        "Real-time tick aggregation, signal detection, and WebSocket alerts "
        "for NSE instruments"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1")
