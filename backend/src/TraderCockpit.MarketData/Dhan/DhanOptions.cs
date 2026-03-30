namespace TraderCockpit.MarketData.Dhan;

public sealed class DhanOptions
{
    public const string SectionName = "DhanApi";

    public string BaseUrl           { get; init; } = "https://api.dhan.co";
    public string ClientId          { get; init; } = "";
    public string AccessToken       { get; init; } = "";
    /// <summary>Max parallel Dhan API requests in flight at once.</summary>
    public int    MaxConcurrency    { get; init; } = 5;
    /// <summary>Milliseconds to wait between requests per worker (basic rate limit).</summary>
    public int    DelayBetweenCallsMs { get; init; } = 100;
}
