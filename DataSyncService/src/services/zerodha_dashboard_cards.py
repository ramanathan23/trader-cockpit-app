from .zerodha_utils import money_float, payload


def account_card(account, margin_row, position_row, run, perf):
    equity = payload(margin_row["payload"] if margin_row else {}).get("equity", {})
    available, utilised = equity.get("available", {}), equity.get("utilised", {})
    positions = payload(position_row["payload"] if position_row else {}).get("net", [])
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
        "return_pct": round(((realized + unrealized) / capital) * 100, 2) if capital else 0,
        "open_exposure": round(exposure, 2), "utilization_pct": round((exposure / capital) * 100, 2) if capital else 0,
        "open_winners": count_pnl(open_positions, 1), "open_losers": count_pnl(open_positions, -1),
        "concentration_pct": round((max(abs_pnls) / sum(abs_pnls)) * 100, 2) if sum(abs_pnls) else 0,
        "ce_count": count_suffix(open_positions, "CE"), "pe_count": count_suffix(open_positions, "PE"),
        "closed_trades": int(perf.get("closed_trades") or 0), "win_rate_pct": money_float(perf.get("win_rate_pct")),
        "trade_return_pct": money_float(perf.get("trade_return_pct")), "open_positions_count": len(open_positions),
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


def count_pnl(positions, sign: int):
    return sum(1 for p in positions if money_float(p.get("unrealised") or p.get("pnl")) * sign > 0)


def count_suffix(positions, suffix: str):
    return sum(1 for p in positions if str(p.get("symbol") or "").endswith(suffix))
