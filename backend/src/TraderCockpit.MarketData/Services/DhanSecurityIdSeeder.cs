using Microsoft.Extensions.Logging;
using TraderCockpit.MarketData.Repositories;

namespace TraderCockpit.MarketData.Services;

/// <summary>
/// Downloads Dhan's public scrip master CSV on startup and bulk-populates
/// <c>dhan_security_id</c> in the symbols table by matching on ISIN.
///
/// The CSV is filtered to NSE_EQ EQUITY rows only, matching our symbol universe.
/// Safe to re-run: the underlying UPDATE skips rows where the ID hasn't changed.
/// </summary>
public sealed class DhanSecurityIdSeeder(
    IHttpClientFactory            httpFactory,
    ISymbolRepository             symbolRepo,
    ILogger<DhanSecurityIdSeeder> logger)
{
    private const string ScripMasterUrl =
        "https://images.dhan.co/api-data/api-scrip-master.csv";

    public async Task SeedAsync(CancellationToken ct = default)
    {
        logger.LogInformation("DhanSecurityIdSeeder: downloading scrip master from Dhan...");

        using var http     = httpFactory.CreateClient();
        using var response = await http.GetAsync(
            ScripMasterUrl, HttpCompletionOption.ResponseHeadersRead, ct);

        if (!response.IsSuccessStatusCode)
        {
            logger.LogWarning(
                "DhanSecurityIdSeeder: scrip master download failed ({Status}). Skipping.",
                (int)response.StatusCode);
            return;
        }

        await using var stream = await response.Content.ReadAsStreamAsync(ct);
        using var       reader = new StreamReader(stream);

        // ── Parse header row ──────────────────────────────────────────────────
        var headerLine = await reader.ReadLineAsync(ct);
        if (headerLine is null)
        {
            logger.LogWarning("DhanSecurityIdSeeder: CSV was empty.");
            return;
        }

        var headers       = headerLine.Split(',');
        int idxSecId      = Array.IndexOf(headers, "SEM_SMST_SECURITY_ID");
        int idxSymbol     = Array.IndexOf(headers, "SEM_TRADING_SYMBOL");
        int idxExchange   = Array.IndexOf(headers, "SEM_EXM_EXCH_ID");
        int idxSegment    = Array.IndexOf(headers, "SEM_SEGMENT");
        int idxInstrument = Array.IndexOf(headers, "SEM_INSTRUMENT_NAME");

        if (idxSecId < 0 || idxSymbol < 0 || idxExchange < 0 || idxSegment < 0 || idxInstrument < 0)
        {
            logger.LogError(
                "DhanSecurityIdSeeder: unexpected CSV header format — required columns not found. " +
                "Header: {Header}", headerLine);
            return;
        }

        int minCols = new[] { idxSecId, idxSymbol, idxExchange, idxSegment, idxInstrument }.Max() + 1;

        // ── Parse rows: NSE equity (exchange=NSE, segment=E, instrument=EQUITY) ─
        var symbolToSecurityId = new Dictionary<string, string>(
            capacity: 3000, StringComparer.OrdinalIgnoreCase);

        string? line;
        while ((line = await reader.ReadLineAsync(ct)) is not null)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;

            var cols = line.Split(',');
            if (cols.Length < minCols) continue;

            if (!cols[idxExchange].Trim().Equals("NSE", StringComparison.OrdinalIgnoreCase))
                continue;
            if (!cols[idxSegment].Trim().Equals("E", StringComparison.OrdinalIgnoreCase))
                continue;
            if (!cols[idxInstrument].Trim().Equals("EQUITY", StringComparison.OrdinalIgnoreCase))
                continue;

            var symbol = cols[idxSymbol].Trim();
            var secId  = cols[idxSecId].Trim();

            if (!string.IsNullOrEmpty(symbol) && !string.IsNullOrEmpty(secId))
                symbolToSecurityId[symbol] = secId;
        }

        if (symbolToSecurityId.Count == 0)
        {
            logger.LogWarning(
                "DhanSecurityIdSeeder: no NSE / E / EQUITY rows found in scrip master. " +
                "Check if Dhan changed the CSV format.");
            return;
        }

        logger.LogInformation(
            "DhanSecurityIdSeeder: parsed {Count} NSE EQ security IDs.", symbolToSecurityId.Count);

        // ── Bulk-update symbols table ─────────────────────────────────────────
        var updated = await symbolRepo.BulkSetDhanSecurityIdBySymbolAsync(symbolToSecurityId, ct);
        logger.LogInformation(
            "DhanSecurityIdSeeder: updated dhan_security_id for {Count} symbols.", updated);
    }
}
