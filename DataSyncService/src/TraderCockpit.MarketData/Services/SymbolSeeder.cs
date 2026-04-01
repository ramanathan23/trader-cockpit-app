using Microsoft.Extensions.Logging;
using TraderCockpit.MarketData.Domain;
using TraderCockpit.MarketData.Repositories;

namespace TraderCockpit.MarketData.Services;

/// <summary>
/// Reads the embedded symbols.csv (NSE equity master) and upserts all rows into
/// the <c>symbols</c> table on startup. Existing rows are updated in place;
/// new rows are inserted. The <c>dhan_security_id</c> column is NOT touched here —
/// populate it separately from Dhan's securities master CSV.
/// </summary>
public sealed class SymbolSeeder(
    ISymbolRepository  symbolRepo,
    ILogger<SymbolSeeder> logger)
{
    // CSV column indices (header: SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE)
    private const int ColSymbol      = 0;
    private const int ColCompanyName = 1;
    private const int ColSeries      = 2;
    private const int ColIsin        = 6;

    public async Task SeedAsync(CancellationToken ct = default)
    {
        var symbols = ParseCsv().ToList();
        if (symbols.Count == 0)
        {
            logger.LogWarning("SymbolSeeder: CSV produced no rows — skipping upsert.");
            return;
        }

        await symbolRepo.UpsertManyAsync(symbols, ct);
        logger.LogInformation("SymbolSeeder: upserted {Count} symbols.", symbols.Count);
    }

    private static IEnumerable<MarketSymbol> ParseCsv()
    {
        using var stream = typeof(SymbolSeeder).Assembly
            .GetManifestResourceStream("symbols.csv")
            ?? throw new InvalidOperationException("Embedded resource 'symbols.csv' not found.");

        using var reader = new StreamReader(stream);

        // Skip header
        reader.ReadLine();

        string? line;
        while ((line = reader.ReadLine()) is not null)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;

            var cols = line.Split(',');
            if (cols.Length < 7) continue;

            var symbol  = cols[ColSymbol].Trim();
            var series  = cols[ColSeries].Trim();
            var isin    = cols[ColIsin].Trim();

            if (string.IsNullOrEmpty(symbol) || string.IsNullOrEmpty(isin)) continue;

            yield return new MarketSymbol
            {
                Symbol          = symbol,
                CompanyName     = cols[ColCompanyName].Trim(),
                Series          = series,
                Isin            = isin,
                ExchangeSegment = "NSE_EQ",
            };
        }
    }
}
