namespace TraderCockpit.MarketData.Domain;

/// <summary>Row from the <c>symbols</c> table.</summary>
public sealed class MarketSymbol
{
    public int     Id               { get; init; }
    public string  Symbol           { get; init; } = "";
    public string  CompanyName      { get; init; } = "";
    public string  Series           { get; init; } = "";
    public string  Isin             { get; init; } = "";
    /// <summary>
    /// Dhan's internal numeric security ID.
    /// Must be populated from Dhan's securities master before sync can run.
    /// Symbols with a NULL value are skipped during ingestion.
    /// </summary>
    public string? DhanSecurityId   { get; init; }
    public string  ExchangeSegment  { get; init; } = "NSE_EQ";
    public bool    IsActive         { get; init; } = true;
}
