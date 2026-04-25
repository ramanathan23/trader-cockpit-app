from __future__ import annotations

from collections import defaultdict
from typing import Any


def base_metrics() -> dict[str, Any]:
    return {
        "avg_trades_per_day": 0.0, "winning_days": 0, "losing_days": 0,
        "flat_days": 0, "avg_trades_on_winning_days": 0.0, "avg_trades_on_losing_days": 0.0,
        "loss_peak_after_trades": 0, "loss_peak_pnl": 0.0,
        "win_peak_after_days": 0, "win_peak_pnl": 0.0,
        "day_outcomes": [], "trade_expectancy": 0.0, "profit_factor": 0.0,
    }


def trade_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    if not trades:
        return base_metrics()
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ordered = sorted(trades, key=lambda t: t.get("exit_time") or "")
    for trade in ordered:
        if trade.get("exit_time"):
            by_day[trade["exit_time"][:10]].append(trade)
    days = [{"date": d, "pnl": round(sum(t["pnl"] for t in rows), 2), "trades": len(rows)} for d, rows in by_day.items()]
    wins = [d for d in days if d["pnl"] > 0]
    losses = [d for d in days if d["pnl"] < 0]
    peak_loss, peak_trade, running = 0.0, 0, 0.0
    for idx, trade in enumerate(ordered, 1):
        running += trade["pnl"]
        if running < peak_loss:
            peak_loss, peak_trade = running, idx
    peak_win, peak_day, running = 0.0, 0, 0.0
    for idx, day in enumerate(days, 1):
        running += day["pnl"]
        if running > peak_win:
            peak_win, peak_day = running, idx
    gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
    out = base_metrics()
    out.update({
        "avg_trades_per_day": round(len(trades) / len(days), 2) if days else 0,
        "winning_days": len(wins), "losing_days": len(losses),
        "flat_days": len(days) - len(wins) - len(losses),
        "avg_trades_on_winning_days": avg_trades(wins),
        "avg_trades_on_losing_days": avg_trades(losses),
        "loss_peak_after_trades": peak_trade, "loss_peak_pnl": round(peak_loss, 2),
        "win_peak_after_days": peak_day, "win_peak_pnl": round(peak_win, 2),
        "day_outcomes": days[-30:],
        "trade_expectancy": round(sum(t["pnl"] for t in trades) / len(trades), 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss else round(gross_profit, 2),
    })
    return out


def avg_trades(days: list[dict[str, Any]]) -> float:
    return round(sum(day["trades"] for day in days) / len(days), 2) if days else 0.0
