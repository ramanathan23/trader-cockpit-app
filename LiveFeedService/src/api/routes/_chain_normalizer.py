from __future__ import annotations


def _normalize_chain(symbol: str, expiry: str, raw: dict) -> dict:
    """Convert raw Dhan option chain response to frontend-expected shape."""
    spot_price = raw.get("last_price") or raw.get("lastPrice") or 0.0
    oc: dict   = raw.get("oc", {}) or {}
    strikes    = []

    for strike_key, sides in oc.items():
        try:
            strike_price = float(strike_key)
        except (ValueError, TypeError):
            continue
        ce: dict = sides.get("ce") or sides.get("CE") or {}
        pe: dict = sides.get("pe") or sides.get("PE") or {}

        def _f(d: dict, *keys):
            for k in keys:
                v = d.get(k)
                if v is not None:
                    return v
            return None

        def _greek(d: dict, key: str):
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
    return {"symbol": symbol, "expiry": expiry, "spot_price": spot_price, "strikes": strikes}
