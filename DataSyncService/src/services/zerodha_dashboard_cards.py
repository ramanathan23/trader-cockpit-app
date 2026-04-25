from .zerodha_utils import money_float, payload


def account_card(account, margin_row, position_row, holding_row, run, perf):
    equity = payload(margin_row["payload"] if margin_row else {}).get("equity", {})
    available, utilised = equity.get("available", {}), equity.get("utilised", {})
    positions = payload(position_row["payload"] if position_row else {}).get("net", [])
    holdings = holding_list(payload(holding_row["payload"] if holding_row else []))
    open_positions = [position_item(p) for p in positions if p.get("quantity")]
    unrealized, exposure = unrealized_of(open_positions), exposure_of(open_positions)
    abs_pnls = [abs(money_float(p.get("unrealised") or p.get("pnl"))) for p in open_positions]
    capital, realized = money_float(account["strategy_capital"]), money_float(perf.get("realized_pnl"))
    return {
        "account_id": account["account_id"], "client_id": account["client_id"], "display_name": account["display_name"],
        "strategy_capital": capital, "broker_net": money_float(equity.get("net")),
        "cash": money_float(available.get("cash") or available.get("live_balance")),
        "opening_balance": money_float(available.get("opening_balance")),
        "utilised": sum(money_float(v) for v in utilised.values()) if isinstance(utilised, dict) else 0,
        "realized_pnl": realized, "unrealized_pnl": round(unrealized, 2), "net_pnl": round(realized + unrealized, 2),
        "statement_realized_pnl": money_float(perf.get("statement_realized_pnl")),
        "charges": money_float(perf.get("charges")), "realized_after_charges": money_float(perf.get("realized_after_charges")),
        "return_pct": round(((realized + unrealized) / capital) * 100, 2) if capital else 0,
        "open_exposure": round(exposure, 2), "utilization_pct": round((exposure / capital) * 100, 2) if capital else 0,
        "open_winners": count_pnl(open_positions, 1), "open_losers": count_pnl(open_positions, -1),
        "concentration_pct": round((max(abs_pnls) / sum(abs_pnls)) * 100, 2) if sum(abs_pnls) else 0,
        "ce_count": count_suffix(open_positions, "CE"), "pe_count": count_suffix(open_positions, "PE"),
        "closed_trades": int(perf.get("closed_trades") or 0), "win_rate_pct": money_float(perf.get("win_rate_pct")),
        "trade_return_pct": money_float(perf.get("trade_return_pct")), "open_positions_count": len(open_positions),
        "avg_trades_per_day": money_float(perf.get("avg_trades_per_day")), "winning_days": int(perf.get("winning_days") or 0),
        "losing_days": int(perf.get("losing_days") or 0), "avg_trades_on_winning_days": money_float(perf.get("avg_trades_on_winning_days")),
        "avg_trades_on_losing_days": money_float(perf.get("avg_trades_on_losing_days")),
        "loss_peak_after_trades": int(perf.get("loss_peak_after_trades") or 0), "loss_peak_pnl": money_float(perf.get("loss_peak_pnl")),
        "win_peak_after_days": int(perf.get("win_peak_after_days") or 0), "win_peak_pnl": money_float(perf.get("win_peak_pnl")),
        "trade_expectancy": money_float(perf.get("trade_expectancy")), "profit_factor": money_float(perf.get("profit_factor")),
        "day_outcomes": perf.get("day_outcomes") or [], "holdings": holding_items(holdings),
        "holdings_count": len(holdings), "holdings_value": holding_value(holdings), "holdings_pnl": holding_pnl(holdings),
        "open_positions": open_positions[:12], "latest_sync": sync_info(run),
        "margin_snapshot_at": margin_row["synced_at"].isoformat() if margin_row else None,
        "position_snapshot_at": position_row["synced_at"].isoformat() if position_row else None,
    }


def position_item(pos):
    return {k: pos.get(k) for k in ["product", "exchange"]} | {
        "symbol": pos.get("tradingsymbol"), "quantity": pos.get("quantity"),
        "average_price": pos.get("average_price"), "last_price": pos.get("last_price"),
        "pnl": pos.get("pnl"), "unrealised": pos.get("unrealised"),
    }


def holding_items(items):
    return [{
        "symbol": h.get("tradingsymbol"), "quantity": h.get("quantity"),
        "average_price": h.get("average_price"), "last_price": h.get("last_price"),
        "pnl": h.get("pnl"), "product": h.get("product"), "exchange": h.get("exchange"),
    } for h in items[:12]]


def holding_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        data = value.get("data") or value.get("holdings") or value.get("net") or []
        return data if isinstance(data, list) else []
    return []


def sync_info(run):
    return {
        "status": run["status"] if run else "never",
        "started_at": run["started_at"].isoformat() if run else None,
        "finished_at": run["finished_at"].isoformat() if run and run["finished_at"] else None,
        "orders_count": int(run["orders_count"] or 0) if run else 0,
        "trades_count": int(run["trades_count"] or 0) if run else 0,
        "error_msg": run["error_msg"] if run else None,
    }


def unrealized_of(positions):
    return sum(money_float(p.get("unrealised") or p.get("pnl")) for p in positions)


def exposure_of(positions):
    return sum(abs(money_float(p.get("average_price")) * money_float(p.get("quantity"))) for p in positions)


def holding_value(items):
    return round(sum(money_float(h.get("last_price")) * money_float(h.get("quantity")) for h in items), 2)


def holding_pnl(items):
    return round(sum(money_float(h.get("pnl")) for h in items), 2)


def count_pnl(positions, sign: int):
    return sum(1 for p in positions if money_float(p.get("unrealised") or p.get("pnl")) * sign > 0)


def count_suffix(positions, suffix: str):
    return sum(1 for p in positions if str(p.get("symbol") or "").endswith(suffix))
