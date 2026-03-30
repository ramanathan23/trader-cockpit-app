namespace TraderCockpit.MarketData.Dhan;

/// <summary>
/// Thrown when Dhan returns DH-905 — no data for the requested date range.
/// This is expected for newly-listed symbols where the backfill start pre-dates listing.
/// </summary>
public sealed class DhanNoDataException(string securityId, DateTime from, DateTime to)
    : Exception($"No data for {securityId} [{from:yyyy-MM-dd}–{to:yyyy-MM-dd}] (DH-905).")
{
    public string   SecurityId { get; } = securityId;
    public DateTime From       { get; } = from;
    public DateTime To         { get; } = to;
}
