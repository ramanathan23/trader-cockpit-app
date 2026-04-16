import logging

from fastapi import APIRouter

from ..deps import FeedServiceDep
from ..schemas.token_update import TokenUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status", summary="Feed health and index bias")
async def status(svc: FeedServiceDep):
    return svc.status()


@router.post("/token", summary="Update Dhan access token and reconnect WebSocket feeds")
async def update_token(body: TokenUpdate, svc: FeedServiceDep):
    await svc.update_token(body.access_token)
    return {"status": "ok", "message": "Token updated and WebSocket feeds reconnecting"}
