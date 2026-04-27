import asyncio
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from .deps import IndicatorsServiceDep, SetupBehaviorServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/compute", summary="Compute all indicators and patterns (background)")
async def trigger_compute(background_tasks: BackgroundTasks, svc: IndicatorsServiceDep):
    background_tasks.add_task(svc.compute)
    return {"status": "started", "message": "Indicator compute running in background."}


@router.post("/compute-sse", summary="Compute indicators: streams SSE progress until complete (use for pipeline UI)")
async def trigger_compute_sse(svc: IndicatorsServiceDep):
    async def generate():
        yield f"data: {json.dumps({'status': 'running', 'message': 'Computing indicators…'})}\n\n"
        task = asyncio.create_task(svc.compute())
        elapsed = 0
        while not task.done():
            await asyncio.sleep(3)
            elapsed += 3
            yield f"data: {json.dumps({'status': 'running', 'message': f'Computing indicators… {elapsed}s'})}\n\n"
        try:
            result = task.result()
            msg = (
                f"Done — {result['symbols']} symbols: "
                f"{result['indicators']} indicators, {result['patterns']} patterns"
            )
            yield f"data: {json.dumps({'status': 'ok', 'message': msg, 'result': result})}\n\n"
        except Exception as exc:
            logger.exception("compute_sse task failed")
            yield f"data: {json.dumps({'status': 'error', 'message': str(exc) or type(exc).__name__})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/compute-setup-behavior", summary="Compute setup behavior profiles for synced symbols")
async def compute_setup_behavior(svc: SetupBehaviorServiceDep):
    started = time.perf_counter()
    result = await svc.compute_all()
    result["status"] = "ok"
    result["duration_s"] = round(time.perf_counter() - started, 2)
    return result


@router.post("/compute-setup-behavior-sse", summary="Compute setup behavior profiles with SSE progress")
async def compute_setup_behavior_sse(svc: SetupBehaviorServiceDep):
    async def generate():
        yield f"data: {json.dumps({'status': 'running', 'message': 'Computing setup behavior...'})}\n\n"
        started = time.perf_counter()
        task = asyncio.create_task(svc.compute_all())
        elapsed = 0
        while not task.done():
            await asyncio.sleep(3)
            elapsed += 3
            yield f"data: {json.dumps({'status': 'running', 'message': f'Computing setup behavior... {elapsed}s'})}\n\n"
        try:
            result = task.result()
            result["duration_s"] = round(time.perf_counter() - started, 2)
            message = f"Done - {result['symbols_computed']} symbols"
            yield f"data: {json.dumps({'status': 'ok', 'message': message, 'result': result})}\n\n"
        except Exception as exc:
            logger.exception("compute_setup_behavior_sse task failed")
            yield f"data: {json.dumps({'status': 'error', 'message': str(exc) or type(exc).__name__})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/setup-behavior/{symbol}", summary="Get latest setup behavior profile")
async def get_setup_behavior(symbol: str, svc: SetupBehaviorServiceDep):
    profile = await svc.get_profile(symbol.upper())
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No setup behavior profile for {symbol}")
    return profile
