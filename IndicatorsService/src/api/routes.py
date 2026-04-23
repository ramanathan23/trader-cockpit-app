import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

from .deps import IndicatorsServiceDep

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
