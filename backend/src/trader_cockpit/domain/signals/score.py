from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class SignalGrade(str, Enum):
    A = "A"   # Score 80-100 — strongest conviction
    B = "B"   # Score 60-79  — good setup
    C = "C"   # Score 40-59  — watchlist only
    D = "D"   # Score < 40   — reject

    @classmethod
    def from_score(cls, score: int) -> "SignalGrade":
        if score >= 80:
            return cls.A
        if score >= 60:
            return cls.B
        if score >= 40:
            return cls.C
        return cls.D


# Per-factor minimums — any factor below its minimum rejects the signal
# regardless of total score. Prevents "all-mediocre" combos from passing.
EOD_FACTOR_MINIMUMS = {
    "trend": 10,
    "volume": 8,
    "sector": 6,
    "market_ctx": 8,
    "rr": 12,  # Hard minimum — bad R:R is always a reject
}

INTRADAY_FACTOR_MINIMUMS = {
    "trend": 10,
    "volume": 8,
    "sector": 6,
    "market_ctx": 8,
    "rr": 12,
}

# Factor weights (EOD / Intraday)
EOD_WEIGHTS = {
    "trend": Decimal("0.22"),
    "volume": Decimal("0.18"),
    "sector": Decimal("0.20"),
    "market_ctx": Decimal("0.18"),
    "rr": Decimal("0.22"),
}

INTRADAY_WEIGHTS = {
    "trend": Decimal("0.18"),
    "volume": Decimal("0.22"),
    "sector": Decimal("0.18"),
    "market_ctx": Decimal("0.22"),
    "rr": Decimal("0.20"),
}


@dataclass(frozen=True)
class ScoreFactors:
    """
    Each raw factor scored 0-20 (per-factor max).
    Total score = weighted sum scaled to 0-100.

    - trend:      Price vs EMAs, MA slope, swing structure
    - volume:     Time-of-day normalized volume vs historical average
    - sector:     Sector relative strength vs Nifty
    - market_ctx: Nifty/BankNifty breadth, index trend, VIX
    - rr:         Risk/Reward ratio quality (target / stop distance), ATR validity
    """
    trend: int       # 0-20
    volume: int      # 0-20
    sector: int      # 0-20
    market_ctx: int  # 0-20
    rr: int          # 0-20

    def __post_init__(self) -> None:
        for field_name in ("trend", "volume", "sector", "market_ctx", "rr"):
            v = getattr(self, field_name)
            if not 0 <= v <= 20:
                raise ValueError(f"ScoreFactors.{field_name} must be 0-20, got {v}")

    def weighted_total(self, is_eod: bool = True) -> int:
        weights = EOD_WEIGHTS if is_eod else INTRADAY_WEIGHTS
        total = (
            Decimal(self.trend) * weights["trend"]
            + Decimal(self.volume) * weights["volume"]
            + Decimal(self.sector) * weights["sector"]
            + Decimal(self.market_ctx) * weights["market_ctx"]
            + Decimal(self.rr) * weights["rr"]
        )
        # Scale raw (0-20 max per factor) to 0-100
        return int((total / Decimal("20")) * Decimal("100"))

    def passes_minimums(self, is_eod: bool = True) -> tuple[bool, list[str]]:
        """Returns (passes, list_of_failed_factors)."""
        minimums = EOD_FACTOR_MINIMUMS if is_eod else INTRADAY_FACTOR_MINIMUMS
        failed = [
            f for f, min_val in minimums.items()
            if getattr(self, f) < min_val
        ]
        return len(failed) == 0, failed

    def grade(self, is_eod: bool = True) -> SignalGrade:
        passes, _ = self.passes_minimums(is_eod)
        if not passes:
            return SignalGrade.D
        return SignalGrade.from_score(self.weighted_total(is_eod))
