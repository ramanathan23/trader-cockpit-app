namespace TraderCockpit.MarketData.Domain;

/// <summary>
/// Represents an NSE-listed equity symbol, as stored in the <c>symbols</c> table.
/// </summary>
/// <remarks>
/// <para>
/// The <see cref="DhanSecurityId"/> column starts as <c>null</c> for newly seeded rows.
/// It is populated at startup by <c>DhanSecurityIdSeeder</c> from Dhan's scrip-master CSV.
/// Symbols with a <c>null</c> ID cannot be synced and are excluded by
/// <c>ISymbolRepository.GetSyncableAsync</c>.
/// </para>
/// </remarks>
public sealed class MarketSymbol
{
    // ── Identity ──────────────────────────────────────────────────────────────

    /// <summary>Database primary key (auto-incremented).</summary>
    public int Id { get; init; }

    /// <summary>NSE ticker (e.g. <c>RELIANCE</c>). Unique across the table.</summary>
    public string Symbol { get; init; } = "";

    /// <summary>Full registered company name (e.g. <c>Reliance Industries Limited</c>).</summary>
    public string CompanyName { get; init; } = "";

    /// <summary>NSE trading series (e.g. <c>EQ</c>, <c>BE</c>).</summary>
    public string Series { get; init; } = "";

    /// <summary>12-character ISIN used for cross-exchange identification.</summary>
    public string Isin { get; init; } = "";

    // ── Dhan-specific fields ──────────────────────────────────────────────────

    /// <summary>
    /// Dhan's internal numeric security ID required for API calls.
    /// <c>null</c> until populated by <c>DhanSecurityIdSeeder</c>.
    /// Check <see cref="CanBeSynced"/> before scheduling ingestion.
    /// </summary>
    public string? DhanSecurityId { get; init; }

    /// <summary>
    /// Exchange segment string passed to the Dhan API (e.g. <c>NSE_EQ</c>).
    /// Defaults to <c>NSE_EQ</c> for all NSE equity symbols.
    /// </summary>
    public string ExchangeSegment { get; init; } = "NSE_EQ";

    // ── Status ────────────────────────────────────────────────────────────────

    /// <summary>
    /// <c>false</c> for delisted or otherwise excluded symbols.
    /// Only active symbols are returned by <c>ISymbolRepository.GetActiveAsync</c>.
    /// </summary>
    public bool IsActive { get; init; } = true;

    // ── Domain behaviour ──────────────────────────────────────────────────────

    /// <summary>
    /// Returns <c>true</c> when this symbol is eligible for data ingestion —
    /// i.e. it is active and its <see cref="DhanSecurityId"/> has been mapped.
    /// </summary>
    public bool CanBeSynced => IsActive && DhanSecurityId is not null;
}
