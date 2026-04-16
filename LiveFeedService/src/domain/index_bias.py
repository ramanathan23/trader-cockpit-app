from dataclasses import dataclass

from .direction import Direction


@dataclass
class IndexBias:
    """Aggregated directional bias from index futures (market proxy)."""
    nifty:     Direction = Direction.NEUTRAL
    banknifty: Direction = Direction.NEUTRAL
    sensex:    Direction = Direction.NEUTRAL

    def majority(self) -> Direction:
        votes   = [self.nifty, self.banknifty, self.sensex]
        bullish = votes.count(Direction.BULLISH)
        bearish = votes.count(Direction.BEARISH)
        if bullish > bearish:
            return Direction.BULLISH
        if bearish > bullish:
            return Direction.BEARISH
        return Direction.NEUTRAL
