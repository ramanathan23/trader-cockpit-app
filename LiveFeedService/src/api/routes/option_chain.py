import logging

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from ..schemas.option_chain_request import OptionChainRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _normalize_chain(symbol: str, expiry: str, raw: dict) -> dict:
    """Convert raw Dhan option chain response to frontend-expected shape."""
    spot_price = raw.get("last_price") or raw.get("lastPrice") or 0.0
    oc: dict = raw.get("oc", {}) or {}

    strikes = []
    for strike_key, sides in oc.items():
        try:
            strike_price = float(strike_key)
        except (ValueError, TypeError):
            continue

        ce: dict = (sides.get("ce") or sides.get("CE") or {})
        pe: dict = (sides.get("pe") or sides.get("PE") or {})

        def _f(d: dict, *keys):
            for k in keys:
                v = d.get(k)
                if v is not None:
                    return v
            return None

        def _greek(d: dict, key: str):
            """Extract a Greek from nested 'greeks' dict or flat key."""
            g = d.get("greeks")
            if isinstance(g, dict):
                v = g.get(key)
                if v is not None:
                    return v
            return d.get(key)

        strikes.append({
            "strike_price": strike_price,
            "call_ltp":    _f(ce, "last_price", "lastPrice", "ltp"),
            "call_iv":     _f(ce, "implied_volatility", "iv", "impliedVolatility"),
            "call_delta":  _greek(ce, "delta"),
            "call_theta":  _greek(ce, "theta"),
            "call_gamma":  _greek(ce, "gamma"),
            "call_vega":   _greek(ce, "vega"),
            "call_oi":     _f(ce, "oi", "open_interest", "openInterest"),
            "call_volume": _f(ce, "volume"),
            "call_bid":    _f(ce, "top_bid_price", "bid_price", "bidPrice", "bid"),
            "call_ask":    _f(ce, "top_ask_price", "ask_price", "askPrice", "ask"),
            "put_ltp":     _f(pe, "last_price", "lastPrice", "ltp"),
            "put_iv":      _f(pe, "implied_volatility", "iv", "impliedVolatility"),
            "put_delta":   _greek(pe, "delta"),
            "put_theta":   _greek(pe, "theta"),
            "put_gamma":   _greek(pe, "gamma"),
            "put_vega":    _greek(pe, "vega"),
            "put_oi":      _f(pe, "oi", "open_interest", "openInterest"),
            "put_volume":  _f(pe, "volume"),
            "put_bid":     _f(pe, "top_bid_price", "bid_price", "bidPrice", "bid"),
            "put_ask":     _f(pe, "top_ask_price", "ask_price", "askPrice", "ask"),
        })

    strikes.sort(key=lambda x: x["strike_price"])
    return {
        "symbol":      symbol,
        "expiry":      expiry,
        "spot_price":  spot_price,
        "strikes":     strikes,
    }


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

    segment = row["exchange_segment"].strip().upper()
    oc_segment = "NSE_EQ" if segment in ("E", "NSE_EQ") else ("BSE_EQ" if segment == "BSE_EQ" else segment)
    return int(row["dhan_security_id"]), oc_segment


@router.post("/optionchain", summary="Fetch option chain for a symbol (on-demand)")
async def get_option_chain(body: OptionChainRequest, request: Request):
    oc_client = request.app.state.option_chain_client
    if oc_client is None:
        raise HTTPException(503, "Option chain client not configured")

    security_id, oc_segment = await _resolve_dhan_instrument(request.app.state.pool, body.symbol)

    try:
        if body.expiry:
            chain = await oc_client.get_option_chain(security_id, oc_segment, body.expiry)
            return _normalize_chain(body.symbol.upper(), body.expiry, chain)
        else:
            expiries = await oc_client.get_expiry_list(security_id, oc_segment)
            if not expiries:
                raise HTTPException(404, f"No option expiries found for {body.symbol}")
            nearest = expiries[0]
            chain = await oc_client.get_option_chain(security_id, oc_segment, nearest)
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

    security_id, oc_segment = await _resolve_dhan_instrument(request.app.state.pool, body.symbol)

    try:
        expiries = await oc_client.get_expiry_list(security_id, oc_segment)
        return {"symbol": body.symbol.upper(), "expiries": expiries}
    except Exception as exc:
        raise HTTPException(502, f"Expiry list fetch failed: {exc}")
