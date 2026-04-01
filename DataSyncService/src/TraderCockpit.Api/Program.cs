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

// ── Startup ───────────────────────────────────────────────────────────────────
//
// 1. DatabaseInitializer  — idempotent DDL (creates tables/hypertables if missing)
// 2. SymbolSeeder         — upserts NSE equities from embedded CSV
// 3. DhanSecurityIdSeeder — maps dhan_security_id from Dhan's scrip-master CSV
// 4. ReconcileStuckRuns   — marks any InProgress runs from a crashed process as
//                           Failed so the guard does not block new syncs.
//                           price_data_1m is untouched; the next POST /sync
//                           resumes each symbol incrementally from its last bar.
//
await using (var scope = app.Services.CreateAsyncScope())
{
    var sp = scope.ServiceProvider;

    await sp.GetRequiredService<DatabaseInitializer>().InitializeAsync();
    await sp.GetRequiredService<SymbolSeeder>().SeedAsync();
    await sp.GetRequiredService<DhanSecurityIdSeeder>().SeedAsync();

    var stuckCount = await sp
        .GetRequiredService<ISyncRunRepository>()
        .ReconcileStuckRunsAsync();

    if (stuckCount > 0)
        app.Logger.LogWarning(
            "Reconciled {Count} stuck sync run(s) from the previous process. " +
            "POST /api/market-data/sync to resume — price data already saved is preserved.",
            stuckCount);
}

app.UseSwagger();
app.UseSwaggerUI(c => c.ConfigObject.AdditionalItems["tryItOutEnabled"] = true);

// ── Symbols ───────────────────────────────────────────────────────────────────

var marketData = app.MapGroup("/api/market-data").WithTags("MarketData");

marketData.MapGet("/symbols", async (ISymbolRepository repo, CancellationToken ct) =>
    Results.Ok(await repo.GetActiveAsync(ct)))
.WithName("GetSymbols")
.WithSummary("List all active symbols. dhan_security_id is null until populated.");

marketData.MapPut("/symbols/{symbol}/security-id", async (
    string symbol, SecurityIdRequest body,
    ISymbolRepository repo, CancellationToken ct) =>
{
    await repo.SetDhanSecurityIdAsync(symbol, body.DhanSecurityId, ct);
    return Results.NoContent();
})
.WithName("SetDhanSecurityId")
.WithSummary("Map a symbol to its Dhan security ID (required before sync).");

// ── Sync ──────────────────────────────────────────────────────────────────────

marketData.MapPost("/sync", async (SyncManager manager, CancellationToken ct) =>
{
    var result = await manager.TriggerAsync(ct);
    return result.Status switch
    {
        SyncTriggerStatus.Started      => Results.Accepted(
            $"/api/market-data/sync/{result.RunId}",
            new { runId = result.RunId }),
        SyncTriggerStatus.AlreadyRunning => Results.Conflict(
            new { message = "A sync is already running. Poll GET /api/market-data/sync for status." }),
        _ => Results.Ok(
            new { message = "No syncable symbols found. Ensure dhan_security_id is populated." }),
    };
})
.WithName("TriggerSync")
.WithSummary(
    "Start a full-universe sync. " +
    "Each symbol is checked: if its latest bar is < 15 min old it is skipped; otherwise data is fetched from that point. " +
    "Returns 409 if a run is already in progress.");

marketData.MapGet("/sync", async (ISyncRunRepository repo, CancellationToken ct) =>
    Results.Ok(await repo.GetAllAsync(ct)))
.WithName("GetSyncRuns")
.WithSummary("List the last 100 sync runs with their current status and progress counters.");

marketData.MapGet("/sync/{id:guid}", async (
    Guid id, ISyncRunRepository repo, CancellationToken ct) =>
{
    var run = await repo.GetByIdAsync(id, ct);
    return run is null ? Results.NotFound() : Results.Ok(run);
})
.WithName("GetSyncRun")
.WithSummary("Poll a specific sync run by ID.");

// ── Reset ─────────────────────────────────────────────────────────────────────

marketData.MapDelete("/reset", (
    IPriceDataRepository priceRepo,
    ISyncRunRepository   syncRepo,
    ILogger<Program>     log) =>
{
    // Fire and forget — TRUNCATE on a large hypertable can take many seconds.
    // Returns 202 immediately; the wipe continues in the background.
    _ = Task.Run(async () =>
    {
        try
        {
            await priceRepo.ResetAsync(CancellationToken.None);
            await syncRepo.ResetAllAsync(CancellationToken.None);
            log.LogInformation("Reset complete — price_data_1m, price_data_daily_raw and sync_runs cleared.");
        }
        catch (Exception ex)
        {
            log.LogError(ex, "Reset failed.");
        }
    });

    return Results.Accepted((string?)null,
        new { message = "Reset started. price_data_1m, price_data_daily_raw and sync_runs are being cleared." });
})
.WithName("ResetMarketData")
.WithSummary("Wipes all price data and sync runs in the background. Returns 202 immediately.");

// ── OHLCV query ───────────────────────────────────────────────────────────────

marketData.MapGet("/{symbol}/ohlcv", async (
    string symbol, string timeframe, DateTime from, DateTime to,
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

// ── DTOs ──────────────────────────────────────────────────────────────────────
record SecurityIdRequest(string DhanSecurityId);
