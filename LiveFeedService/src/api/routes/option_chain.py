from __future__ import annotations

import logging

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from ..schemas.option_chain_request import OptionChainRequest
from ._chain_normalizer import _normalize_chain

logger = logging.getLogger(__name__)
router = APIRouter()


async def _resolve_dhan_instrument(pool: asyncpg.Pool, symbol: str) -> tuple[int, str]:
    """Look up Dhan security ID and exchange segment; raises HTTPException on miss."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT dhan_security_id, exchange_segment
            FROM symbols
            WHERE symbol = $1 AND dhan_security_id IS NOT NULL
        """, symbol.upper())
    if not row:
        raise HTTPException(404, f"Symbol '{symbol}' not found or has no Dhan ID")
    segment    = row["exchange_segment"].strip().upper()
    oc_segment = (
        "NSE_EQ" if segment in ("E", "NSE_EQ")
        else ("BSE_EQ" if segment == "BSE_EQ" else segment)
    )
    return int(row["dhan_security_id"]), oc_segment


@router.post("/optionchain", summary="Fetch option chain for a symbol (on-demand)")
async def get_option_chain(body: OptionChainRequest, request: Request):
    oc_client = request.app.state.option_chain_client
    if oc_client is None:
        raise HTTPException(503, "Option chain client not configured")
    security_id, oc_segment = await _resolve_dhan_instrument(
        request.app.state.pool, body.symbol,
    )
    try:
        if body.expiry:
            chain = await oc_client.get_option_chain(security_id, oc_segment, body.expiry)
            return _normalize_chain(body.symbol.upper(), body.expiry, chain)
        else:
            expiries = await oc_client.get_expiry_list(security_id, oc_segment)
            if not expiries:
                raise HTTPException(404, f"No option expiries found for {body.symbol}")
            nearest    = expiries[0]
            chain      = await oc_client.get_option_chain(security_id, oc_segment, nearest)
            normalized = _normalize_chain(body.symbol.upper(), nearest, chain)
            normalized["expiries"] = expiries
            return normalized
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Option chain fetch failed for %s: %s", body.symbol, exc)
        raise HTTPException(502, f"Option chain fetch failed: {exc}")


@router.post("/optionchain/expiries", summary="Get available expiry dates for a symbol")
async def get_expiry_list(body: OptionChainRequest, request: Request):
    oc_client = request.app.state.option_chain_client
    if oc_client is None:
        raise HTTPException(503, "Option chain client not configured")
    security_id, oc_segment = await _resolve_dhan_instrument(
        request.app.state.pool, body.symbol,
    )
    try:
        expiries = await oc_client.get_expiry_list(security_id, oc_segment)
        return {"symbol": body.symbol.upper(), "expiries": expiries}
    except Exception as exc:
        raise HTTPException(502, f"Expiry list fetch failed: {exc}")
