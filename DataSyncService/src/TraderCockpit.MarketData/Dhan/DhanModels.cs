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
    public int    Interval                   { get; init; } = 1;     // 1-minute (API requires integer)

    [JsonPropertyName("fromDate")]
    public required string FromDate          { get; init; }          // yyyy-MM-dd

    [JsonPropertyName("toDate")]
    public required string ToDate            { get; init; }          // yyyy-MM-dd
}

// ── Historical (EOD) request ──────────────────────────────────────────────────

/// <summary>
/// Request body for POST /v2/charts/historical (daily EOD bars).
/// Dhan allows up to ~1 year per call; SyncManager batches accordingly.
/// </summary>
internal sealed class HistoricalRequest
{
    [JsonPropertyName("securityId")]
    public required string SecurityId      { get; init; }

    [JsonPropertyName("exchangeSegment")]
    public required string ExchangeSegment { get; init; }

    [JsonPropertyName("instrument")]
    public string Instrument               { get; init; } = "EQUITY";

    [JsonPropertyName("expiryCode")]
    public int ExpiryCode                  { get; init; } = 0;

    [JsonPropertyName("fromDate")]
    public required string FromDate        { get; init; }  // yyyy-MM-dd

    [JsonPropertyName("toDate")]
    public required string ToDate          { get; init; }  // yyyy-MM-dd
}

// ── Error ─────────────────────────────────────────────────────────────────────

internal sealed class DhanErrorResponse
{
    [JsonPropertyName("errorCode")]
    public string ErrorCode { get; init; } = "";
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

    // Dhan returns volume as float (e.g. 12345.0), so deserialize as double then cast.
    [JsonPropertyName("volume")]
    public double[]  Volume    { get; init; } = [];

    // Dhan returns timestamp as float (e.g. 1234567890.0), so deserialize as double then cast.
    [JsonPropertyName("timestamp")]
    public double[]  Timestamp { get; init; } = [];
}
