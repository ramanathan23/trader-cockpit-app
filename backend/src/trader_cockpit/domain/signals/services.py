"""
SignalEngine — pure domain service for scoring trading setups.

Encodes the 5-factor scoring model:
  Trend Alignment   (0-20)
  Volume Confirmation (0-20)
  Sector Momentum   (0-20)
  Market Context    (0-20)
  Risk/Reward       (0-20)

No I/O, no framework imports. All inputs are domain value objects.
"""
from dataclasses import dataclass
from decimal import Decimal

from trader_cockpit.domain.market_data.entities import OHLCV
from .score import ScoreFactors
from .entities import SignalDirection


@dataclass
class MarketContextSnapshot:
    """Inputs representing broader market state at signal time."""
    nifty_above_ema20: bool
    nifty_above_ema50: bool
    banknifty_above_ema20: bool
    vix: Decimal              # India VIX
    nifty_pct_change_today: Decimal
    advancing_stocks_pct: Decimal  # % of NSE 500 advancing


@dataclass
class SectorSnapshot:
    """Sector index relative performance vs Nifty."""
    sector_pct_change: Decimal    # Sector index % change today
    nifty_pct_change: Decimal     # Nifty % change today

    @property
    def relative_strength(self) -> Decimal:
        return self.sector_pct_change - self.nifty_pct_change


@dataclass
class TrendInputs:
    """Price/MA data for trend scoring."""
    price: Decimal
    ema9: Decimal
    ema20: Decimal
    ema50: Decimal
    ema200: Decimal
    prev_swing_high: Decimal
    prev_swing_low: Decimal
    is_higher_high: bool
    is_higher_low: bool


class SignalEngine:
    """
    Stateless domain service. Score a setup given its inputs.
    All methods are pure functions — same inputs always produce same output.
    """

    ATR_SL_MULTIPLIER_INTRADAY = Decimal("0.5")  # SL >= 0.5x ATR14
    ATR_SL_MULTIPLIER_SWING    = Decimal("1.0")  # SL >= 1.0x ATR14
    MIN_RR_INTRADAY = Decimal("2.0")
    MIN_RR_SWING    = Decimal("1.5")

    def score_trend(
        self,
        inputs: TrendInputs,
        direction: SignalDirection,
    ) -> int:
        """Score trend alignment 0-20."""
        score = 0

        if direction == SignalDirection.LONG:
            if inputs.price > inputs.ema20:
                score += 4
            if inputs.price > inputs.ema50:
                score += 4
            if inputs.price > inputs.ema200:
                score += 3
            if inputs.ema20 > inputs.ema50:
                score += 3  # MA alignment bullish
            if inputs.is_higher_high and inputs.is_higher_low:
                score += 4  # Higher highs and higher lows = uptrend
            if inputs.price > inputs.ema9:
                score += 2
        else:  # SHORT
            if inputs.price < inputs.ema20:
                score += 4
            if inputs.price < inputs.ema50:
                score += 4
            if inputs.price < inputs.ema200:
                score += 3
            if inputs.ema20 < inputs.ema50:
                score += 3
            if not inputs.is_higher_high and not inputs.is_higher_low:
                score += 4
            if inputs.price < inputs.ema9:
                score += 2

        return min(score, 20)

    def score_volume(
        self,
        current_volume: int,
        avg_volume_at_time: int,    # Historical avg at this time-of-day
        signal_candle_volume: int,
        avg_signal_candle_volume: int,
    ) -> int:
        """
        Score volume confirmation 0-20.
        Uses time-of-day normalized volume — prevents early-morning volume spikes
        from scoring the same as sustained accumulation.
        """
        score = 0

        if avg_volume_at_time > 0:
            vol_ratio = Decimal(current_volume) / Decimal(avg_volume_at_time)
            if vol_ratio >= Decimal("2.0"):
                score += 10
            elif vol_ratio >= Decimal("1.5"):
                score += 7
            elif vol_ratio >= Decimal("1.2"):
                score += 4
            elif vol_ratio >= Decimal("1.0"):
                score += 2

        # Signal candle volume
        if avg_signal_candle_volume > 0:
            candle_ratio = Decimal(signal_candle_volume) / Decimal(avg_signal_candle_volume)
            if candle_ratio >= Decimal("2.0"):
                score += 10
            elif candle_ratio >= Decimal("1.5"):
                score += 7
            elif candle_ratio >= Decimal("1.2"):
                score += 4
            elif candle_ratio >= Decimal("1.0"):
                score += 2

        return min(score, 20)

    def score_sector(self, sector: SectorSnapshot, direction: SignalDirection) -> int:
        """Score sector momentum 0-20."""
        rs = sector.relative_strength

        if direction == SignalDirection.LONG:
            if rs >= Decimal("1.0"):
                return 20
            if rs >= Decimal("0.5"):
                return 16
            if rs >= Decimal("0.0"):
                return 10
            if rs >= Decimal("-0.5"):
                return 5
            return 2
        else:  # SHORT
            if rs <= Decimal("-1.0"):
                return 20
            if rs <= Decimal("-0.5"):
                return 16
            if rs <= Decimal("0.0"):
                return 10
            if rs <= Decimal("0.5"):
                return 5
            return 2

    def score_market_context(
        self,
        ctx: MarketContextSnapshot,
        direction: SignalDirection,
    ) -> int:
        """Score broad market alignment 0-20."""
        score = 0

        # High VIX penalizes both directions (too uncertain)
        if ctx.vix > Decimal("25"):
            score = max(score, 0)
            return 4  # Cap at 4 during high VIX

        if direction == SignalDirection.LONG:
            if ctx.nifty_above_ema20:
                score += 5
            if ctx.nifty_above_ema50:
                score += 4
            if ctx.banknifty_above_ema20:
                score += 3
            if ctx.nifty_pct_change_today > Decimal("0.3"):
                score += 4
            if ctx.advancing_stocks_pct > Decimal("60"):
                score += 4
        else:  # SHORT
            if not ctx.nifty_above_ema20:
                score += 5
            if not ctx.nifty_above_ema50:
                score += 4
            if not ctx.banknifty_above_ema20:
                score += 3
            if ctx.nifty_pct_change_today < Decimal("-0.3"):
                score += 4
            if ctx.advancing_stocks_pct < Decimal("40"):
                score += 4

        return min(score, 20)

    def score_risk_reward(
        self,
        entry: Decimal,
        sl: Decimal,
        target: Decimal,
        atr14: Decimal,
        is_intraday: bool,
        direction: SignalDirection,
    ) -> int:
        """
        Score R:R quality 0-20.
        Enforces ATR minimum stop rule:
          INTRADAY: SL distance >= 0.5 * ATR14
          SWING:    SL distance >= 1.0 * ATR14

        This prevents unrealistically tight stops gaming the R:R score.
        """
        score = 0

        sl_dist = abs(entry - sl)
        target_dist = abs(target - entry)

        if sl_dist == 0:
            return 0

        rr = target_dist / sl_dist
        min_rr = self.MIN_RR_INTRADAY if is_intraday else self.MIN_RR_SWING
        atr_mult = self.ATR_SL_MULTIPLIER_INTRADAY if is_intraday else self.ATR_SL_MULTIPLIER_SWING

        # ATR validation — SL must be at least atr_mult * ATR14
        min_sl_distance = atr14 * atr_mult
        if sl_dist < min_sl_distance:
            return 0  # Hard reject: SL too tight, gaming R:R

        # Score R:R ratio
        if rr >= Decimal("4.0"):
            score += 20
        elif rr >= Decimal("3.0"):
            score += 16
        elif rr >= Decimal("2.5"):
            score += 13
        elif rr >= min_rr:
            score += 8
        else:
            return 0  # R:R below minimum

        return min(score, 20)

    def compute_score(
        self,
        trend: TrendInputs,
        direction: SignalDirection,
        current_volume: int,
        avg_volume_at_time: int,
        signal_candle_volume: int,
        avg_signal_candle_volume: int,
        sector: SectorSnapshot,
        market_ctx: MarketContextSnapshot,
        entry: Decimal,
        sl: Decimal,
        target: Decimal,
        atr14: Decimal,
        is_intraday: bool = False,
    ) -> ScoreFactors:
        """Compute all 5 factors and return ScoreFactors."""
        return ScoreFactors(
            trend=self.score_trend(trend, direction),
            volume=self.score_volume(
                current_volume, avg_volume_at_time,
                signal_candle_volume, avg_signal_candle_volume,
            ),
            sector=self.score_sector(sector, direction),
            market_ctx=self.score_market_context(market_ctx, direction),
            rr=self.score_risk_reward(entry, sl, target, atr14, is_intraday, direction),
        )

    @staticmethod
    def compute_atr(candles: list[OHLCV], period: int = 14) -> Decimal:
        """
        Compute ATR(period) from a list of OHLCV candles.
        Uses Wilder's True Range method.
        """
        if len(candles) < period + 1:
            raise ValueError(f"Need at least {period + 1} candles to compute ATR({period})")

        true_ranges = []
        for i in range(1, len(candles)):
            prev_close = candles[i - 1].close
            curr = candles[i]
            tr = max(
                curr.high - curr.low,
                abs(curr.high - prev_close),
                abs(curr.low - prev_close),
            )
            true_ranges.append(tr)

        # Wilder's smoothed average
        atr = sum(true_ranges[:period]) / Decimal(period)
        for tr in true_ranges[period:]:
            atr = (atr * Decimal(period - 1) + tr) / Decimal(period)

        return atr

    @staticmethod
    def find_confluence_zones(
        key_levels: list[Decimal],
        tolerance_pct: Decimal = Decimal("0.5"),
    ) -> list[Decimal]:
        """
        Identify price levels where 2+ methods agree (within tolerance_pct %).
        Returns representative prices for each confluence cluster.
        """
        if not key_levels:
            return []

        sorted_levels = sorted(key_levels)
        clusters: list[list[Decimal]] = [[sorted_levels[0]]]

        for price in sorted_levels[1:]:
            ref = clusters[-1][0]
            pct_diff = abs((price - ref) / ref) * 100
            if pct_diff <= tolerance_pct:
                clusters[-1].append(price)
            else:
                clusters.append([price])

        # Only return clusters with 2+ levels (true confluence)
        return [
            sum(c) / Decimal(len(c))
            for c in clusters if len(c) >= 2
        ]
