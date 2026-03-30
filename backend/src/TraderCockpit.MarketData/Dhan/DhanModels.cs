using System.Text.Json.Serialization;

namespace TraderCockpit.MarketData.Dhan;

// ── Request ──────────────────────────────────────────────────────────────────

internal sealed class IntradayRequest
{
    [JsonPropertyName("securityId")]
    public required string SecurityId        { get; init; }

    [JsonPropertyName("exchangeSegment")]
    public required string ExchangeSegment   { get; init; }

    [JsonPropertyName("instrument")]
    public string Instrument                 { get; init; } = "EQUITY";

    [JsonPropertyName("interval")]
    public string Interval                   { get; init; } = "1";   // 1-minute

    [JsonPropertyName("fromDate")]
    public required string FromDate          { get; init; }          // yyyy-MM-dd

    [JsonPropertyName("toDate")]
    public required string ToDate            { get; init; }          // yyyy-MM-dd
}

// ── Response ─────────────────────────────────────────────────────────────────

/// <summary>
/// Dhan returns parallel arrays. Timestamps are Unix epoch seconds (UTC).
/// </summary>
internal sealed class IntradayResponse
{
    [JsonPropertyName("open")]
    public decimal[] Open      { get; init; } = [];

    [JsonPropertyName("high")]
    public decimal[] High      { get; init; } = [];

    [JsonPropertyName("low")]
    public decimal[] Low       { get; init; } = [];

    [JsonPropertyName("close")]
    public decimal[] Close     { get; init; } = [];

    [JsonPropertyName("volume")]
    public long[]    Volume    { get; init; } = [];

    [JsonPropertyName("timestamp")]
    public long[]    Timestamp { get; init; } = [];
}
