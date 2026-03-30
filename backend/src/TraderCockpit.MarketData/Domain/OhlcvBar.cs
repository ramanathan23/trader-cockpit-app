namespace TraderCockpit.MarketData.Domain;

/// <summary>A single OHLCV candle — either from the Dhan API or from the DB.</summary>
public sealed record OhlcvBar(
    DateTime Time,
    decimal  Open,
    decimal  High,
    decimal  Low,
    decimal  Close,
    long     Volume
);
