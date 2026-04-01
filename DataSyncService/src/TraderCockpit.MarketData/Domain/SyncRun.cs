namespace TraderCockpit.MarketData.Domain;

/// <summary>
/// Tracks one full-universe sync run (a single POST /sync trigger).
/// One row covers all symbols — use the per-symbol counters for progress.
/// Status transitions: InProgress → Completed | Failed.
/// </summary>
public sealed class SyncRun
{
    public Guid     Id              { get; init; }

    /// <summary>InProgress | Completed | Failed</summary>
    public string   Status          { get; set; } = "InProgress";

    public int      TotalSymbols    { get; set; }
    public int      SymbolsUpdated  { get; set; }
    public int      SymbolsSkipped  { get; set; }
    public int      SymbolsFailed   { get; set; }

    /// <summary>Ticker currently being processed (approximate during parallel runs).</summary>
    public string?  CurrentSymbol   { get; set; }

    public DateTime StartedAt       { get; init; }
    public DateTime? FinishedAt     { get; set; }
    public string?  ErrorMessage    { get; set; }

    // ── Computed helpers ──────────────────────────────────────────────────────

    public int SymbolsProcessed => SymbolsUpdated + SymbolsSkipped + SymbolsFailed;

    public bool IsActive => Status == "InProgress";
}
