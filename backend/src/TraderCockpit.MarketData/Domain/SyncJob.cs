namespace TraderCockpit.MarketData.Domain;

public enum SyncJobStatus { Pending, InProgress, Completed, Failed }

/// <summary>Row from the <c>sync_jobs</c> table. Exposed to clients for polling.</summary>
public sealed class SyncJob
{
    public Guid           Id           { get; init; }
    public int?           SymbolId     { get; init; }
    public string         Symbol       { get; init; } = "";
    public SyncJobStatus  Status       { get; set;  }
    public DateTime?      FromTime     { get; init; }
    public DateTime?      ToTime       { get; init; }
    public int            BarsFetched  { get; set;  }
    public string?        ErrorMessage { get; set;  }
    public DateTime       CreatedAt    { get; init; }
    public DateTime       UpdatedAt    { get; set;  }
}

/// <summary>Work item enqueued into the ingestion channel.</summary>
public sealed record SyncRequest(
    Guid   JobId,
    int    SymbolId,
    string Symbol,
    string DhanSecurityId,
    string ExchangeSegment,
    DateTime FromTime,
    DateTime ToTime
);
