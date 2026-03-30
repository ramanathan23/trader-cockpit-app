using TraderCockpit.Infrastructure;
using TraderCockpit.MarketData;
using TraderCockpit.MarketData.Database;
using TraderCockpit.MarketData.Repositories;
using TraderCockpit.MarketData.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services
    .AddInfrastructure()
    .AddMarketData(builder.Configuration);

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

// ── Startup: schema migration + symbol seed ───────────────────────────────
await using (var scope = app.Services.CreateAsyncScope())
{
    await scope.ServiceProvider
        .GetRequiredService<DatabaseInitializer>()
        .InitializeAsync();

    await scope.ServiceProvider
        .GetRequiredService<SymbolSeeder>()
        .SeedAsync();

    await scope.ServiceProvider
        .GetRequiredService<DhanSecurityIdSeeder>()
        .SeedAsync();
}

app.UseSwagger();
app.UseSwaggerUI(c =>
{
    c.ConfigObject.AdditionalItems["tryItOutEnabled"] = true;
});

// ── Market Data — Symbols ─────────────────────────────────────────────────
var marketData = app.MapGroup("/api/market-data").WithTags("MarketData");

marketData.MapGet("/symbols", async (
    ISymbolRepository repo,
    CancellationToken ct) =>
    Results.Ok(await repo.GetActiveAsync(ct)))
.WithName("GetSymbols")
.WithSummary("List all active symbols. dhan_security_id is null until populated.");

marketData.MapPut("/symbols/{symbol}/security-id", async (
    string symbol,
    SecurityIdRequest body,
    ISymbolRepository repo,
    CancellationToken ct) =>
{
    await repo.SetDhanSecurityIdAsync(symbol, body.DhanSecurityId, ct);
    return Results.NoContent();
})
.WithName("SetDhanSecurityId")
.WithSummary("Map a symbol to its Dhan internal security ID (required before sync).");

// ── Market Data — Sync ────────────────────────────────────────────────────

marketData.MapPost("/sync", async (
    SyncTriggerRequest? body,
    SyncManager manager,
    CancellationToken ct) =>
{
    if (!string.IsNullOrWhiteSpace(body?.Symbol))
    {
        var jobId = await manager.EnqueueSymbolSyncAsync(body.Symbol, ct);
        return jobId is null
            ? Results.Conflict(new { message = "Sync already in progress, or symbol not found / missing dhan_security_id." })
            : Results.Accepted($"/api/market-data/sync/{jobId}", new { jobId });
    }

    var count = await manager.EnqueueFullSyncAsync(ct);
    return count == -1
        ? Results.Conflict(new { message = "Sync already in progress. Poll /api/market-data/sync to check status." })
        : Results.Accepted("/api/market-data/sync", new { enqueued = count });
})
.WithName("TriggerSync")
.WithSummary("Trigger sync for all syncable symbols, or a single symbol via { \"symbol\": \"RELIANCE\" }. Returns 409 if a sync is already running.");

marketData.MapGet("/sync", async (
    ISyncJobRepository repo,
    CancellationToken ct) =>
    Results.Ok(await repo.GetAllAsync(ct)))
.WithName("GetSyncJobs")
.WithSummary("List the last 500 sync jobs with their current status.");

marketData.MapGet("/sync/{id:guid}", async (
    Guid id,
    ISyncJobRepository repo,
    CancellationToken ct) =>
{
    var job = await repo.GetByIdAsync(id, ct);
    return job is null ? Results.NotFound() : Results.Ok(job);
})
.WithName("GetSyncJob")
.WithSummary("Poll a specific sync job by ID.");

marketData.MapDelete("/reset", async (
    IPriceDataRepository priceRepo,
    ISyncJobRepository   syncRepo,
    CancellationToken    ct) =>
{
    await priceRepo.ResetAsync(ct);
    await syncRepo.ResetAllAsync(ct);
    return Results.Ok(new { message = "All price data and sync jobs cleared. Ready for a fresh sync." });
})
.WithName("ResetMarketData")
.WithSummary("Wipes all price_data_1m rows and sync_jobs. Does NOT touch symbols or dhan_security_id.");

// ── Market Data — OHLCV query ─────────────────────────────────────────────

marketData.MapGet("/{symbol}/ohlcv", async (
    string symbol,
    string timeframe,
    DateTime from,
    DateTime to,
    ISymbolRepository symbolRepo,
    IPriceDataRepository priceRepo,
    CancellationToken ct) =>
{
    var symbols = await symbolRepo.GetActiveAsync(ct);
    var sym = symbols.FirstOrDefault(s =>
        string.Equals(s.Symbol, symbol, StringComparison.OrdinalIgnoreCase));

    if (sym is null)
        return Results.NotFound(new { message = $"Symbol '{symbol}' not found." });

    try
    {
        var bars = await priceRepo.GetBarsAsync(sym.Id, timeframe, from, to, ct);
        return Results.Ok(bars);
    }
    catch (ArgumentException ex)
    {
        return Results.BadRequest(new { ex.Message });
    }
})
.WithName("GetOhlcv")
.WithSummary("Query OHLCV bars. timeframe: 1m | 5m | 15m | daily.");

app.Run();

// ── Request DTOs ──────────────────────────────────────────────────────────
record SecurityIdRequest(string DhanSecurityId);
record SyncTriggerRequest(string? Symbol);
