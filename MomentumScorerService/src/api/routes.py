import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request

from ..signals import momentum

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/scores/compute", summary="Trigger momentum score computation (background)")
async def trigger_compute(
    background_tasks: BackgroundTasks,
    request: Request,
    timeframe: str = Query(default="1d", pattern="^(1d|1m)$"),
):
    pool = request.app.state.pool
    background_tasks.add_task(momentum.compute_all_scores, pool, timeframe)
    return {"status": "started", "timeframe": timeframe}


@router.get("/scores", summary="Top-N symbols by momentum score")
async def get_scores(
    request: Request,
    timeframe: str = Query(default="1d", pattern="^(1d|1m)$"),
    limit:     int   = Query(default=50, ge=1, le=500),
    min_score: float = Query(default=0.0, ge=0.0, le=100.0),
):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                ms.symbol,
                s.company_name,
                ms.score,
                ms.rsi,
                ms.macd_score,
                ms.roc_score,
                ms.vol_score,
                ms.computed_at
            FROM   momentum_scores ms
            JOIN   symbols s ON s.symbol = ms.symbol
            WHERE  ms.timeframe = $1
               AND ms.score >= $2
            ORDER  BY ms.score DESC
            LIMIT  $3
        """, timeframe, min_score, limit)
    return [dict(r) for r in rows]


@router.get("/scores/{symbol}", summary="Full score breakdown for a symbol")
async def get_symbol_score(symbol: str, request: Request):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM momentum_scores WHERE symbol = $1 ORDER BY timeframe",
            symbol.upper(),
        )
    if not rows:
        raise HTTPException(404, f"No scores found for '{symbol}' — run /scores/compute first")
    return [dict(r) for r in rows]


@router.get("/scores/summary/distribution", summary="Score distribution histogram")
async def score_distribution(
    request: Request,
    timeframe: str = Query(default="1d", pattern="^(1d|1m)$"),
    buckets: int = Query(default=10, ge=2, le=20),
):
    """Returns score distribution across `buckets` equal-width buckets (0–100)."""
    pool = request.app.state.pool
    bucket_width = 100.0 / buckets
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                floor(score / $2) * $2            AS bucket_start,
                floor(score / $2) * $2 + $2       AS bucket_end,
                COUNT(*)                           AS count
            FROM momentum_scores
            WHERE timeframe = $1
            GROUP BY bucket_start
            ORDER BY bucket_start
        """, timeframe, bucket_width)
    return [dict(r) for r in rows]
