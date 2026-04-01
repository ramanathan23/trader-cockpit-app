namespace TraderCockpit.MarketData.Dhan;

public sealed class DhanOptions
{
    public const string SectionName = "DhanApi";

    public string BaseUrl           { get; init; } = "https://api.dhan.co";
    public string ClientId          { get; init; } = "";
    public string AccessToken       { get; init; } = "";
    /// <summary>Max parallel Dhan API requests in flight at once.</summary>
    public int    MaxConcurrency      { get; init; } = 3;
    /// <summary>Milliseconds to wait between requests per worker.</summary>
    public int    DelayBetweenCallsMs { get; init; } = 0;
    /// <summary>Global requests-per-second cap across all workers (token bucket).</summary>
    public int    RateLimitPerSecond  { get; init; } = 3;
    /// <summary>Max retries on 429 before giving up. Each retry waits RetryBackoffMs × 2^attempt.</summary>
    public int    MaxRetries          { get; init; } = 5;
    /// <summary>Base backoff in milliseconds on 429 (doubles each retry). Overridden by Retry-After header.</summary>
    public int    RetryBackoffMs      { get; init; } = 2_000;
    /// <summary>How many years of 1-minute data to backfill when a symbol has no data.</summary>
    public int    Backfill1mYears     { get; init; } = 1;
    /// <summary>How many years of daily (EOD) data to backfill when a symbol has no daily data.</summary>
    public int    BackfillDailyYears  { get; init; } = 5;
}
