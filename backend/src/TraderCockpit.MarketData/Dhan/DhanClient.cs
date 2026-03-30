using System.Net;
using System.Net.Http.Json;
using System.Threading.RateLimiting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using TraderCockpit.MarketData.Domain;

namespace TraderCockpit.MarketData.Dhan;

/// <summary>
/// Thin async wrapper around the Dhan v2 intraday charts API.
/// </summary>
/// <remarks>
/// <para>
/// <b>Rate limiting:</b> A shared <see cref="RateLimiter"/> (token-bucket, default 3 req/s)
/// is acquired before every attempt, regardless of retries.
/// </para>
/// <para>
/// <b>Retry policy:</b> The following responses are retried up to <see cref="DhanOptions.MaxRetries"/>
/// times with exponential backoff (<see cref="DhanOptions.RetryBackoffMs"/> × 2^attempt):
/// <list type="bullet">
///   <item><b>429 Too Many Requests</b> — Dhan rate limit exceeded.</item>
///   <item><b>5xx Server Error</b> — transient server-side faults (502, 503, 504, etc.).</item>
/// </list>
/// All other non-success responses are treated as permanent failures and throw immediately.
/// </para>
/// <para>
/// <b>DH-905:</b> A 400 response with error code <c>DH-905</c> means Dhan has no data for
/// the requested date range. This is thrown as <see cref="DhanNoDataException"/> so callers
/// can handle it specifically (e.g. seek the listing date by jumping forward).
/// </para>
/// </remarks>
public sealed class DhanClient(
    HttpClient              http,
    RateLimiter             rateLimiter,
    IOptions<DhanOptions>   options,
    ILogger<DhanClient>     logger)
{
    private readonly DhanOptions _opts = options.Value;

    /// <summary>
    /// Fetches 1-minute OHLCV bars for <paramref name="securityId"/> between
    /// <paramref name="from"/> and <paramref name="to"/> (inclusive, UTC).
    /// </summary>
    /// <remarks>
    /// Dhan caps each request at ~90 days; the caller is responsible for batching.
    /// </remarks>
    /// <exception cref="DhanNoDataException">
    /// Dhan returned DH-905 — no data exists for this security in the given range.
    /// </exception>
    /// <exception cref="HttpRequestException">
    /// A non-retryable HTTP error was returned after all retry attempts were exhausted.
    /// </exception>
    public async Task<IReadOnlyList<OhlcvBar>> GetIntradayAsync(
        string            securityId,
        string            exchangeSegment,
        DateTime          from,
        DateTime          to,
        CancellationToken ct = default)
    {
        var request = new IntradayRequest
        {
            SecurityId      = securityId,
            ExchangeSegment = exchangeSegment,
            FromDate        = from.ToString("yyyy-MM-dd"),
            ToDate          = to.ToString("yyyy-MM-dd"),
        };

        int attempt = 0;

        while (true)
        {
            // Acquire a rate-limit token before every attempt (including retries).
            using var lease = await rateLimiter.AcquireAsync(permitCount: 1, ct);

            using var response = await http.PostAsJsonAsync(
                "/v2/charts/intraday", request, ct);

            if (response.IsSuccessStatusCode)
                return ParseBars(await response.Content.ReadFromJsonAsync<IntradayResponse>(ct));

            var body = await response.Content.ReadAsStringAsync(ct);

            // ── Retryable errors ──────────────────────────────────────────────
            if (IsRetryable(response.StatusCode) && attempt < _opts.MaxRetries)
            {
                var backoff = TimeSpan.FromMilliseconds(_opts.RetryBackoffMs * (1 << attempt));
                logger.LogWarning(
                    "Dhan {Status} for {SecurityId} (attempt {Attempt}/{Max}). Retrying in {Backoff}s.",
                    (int)response.StatusCode, securityId,
                    attempt + 1, _opts.MaxRetries,
                    backoff.TotalSeconds);

                await Task.Delay(backoff, ct);
                attempt++;
                continue;
            }

            // ── DH-905: no data for this range — not an error, just no data ──
            if (response.StatusCode == HttpStatusCode.BadRequest)
            {
                var err = System.Text.Json.JsonSerializer
                    .Deserialize<DhanErrorResponse>(body);

                if (err?.ErrorCode == "DH-905")
                    throw new DhanNoDataException(securityId, from, to);
            }

            // ── Permanent failure or retries exhausted ────────────────────────
            logger.LogWarning(
                "Dhan API {Status} for {SecurityId} [{From}–{To}]: {Body}",
                (int)response.StatusCode, securityId,
                from.ToString("D"), to.ToString("D"), body);

            response.EnsureSuccessStatusCode();  // throws HttpRequestException
            break; // unreachable — EnsureSuccessStatusCode always throws above
        }

        return []; // unreachable
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    /// <summary>
    /// Returns <c>true</c> for status codes that represent transient conditions
    /// worth retrying: 429 (rate limited) and 5xx (server errors).
    /// </summary>
    private static bool IsRetryable(HttpStatusCode status)
        => status == HttpStatusCode.TooManyRequests
        || (int)status >= 500;

    /// <summary>
    /// Converts a <see cref="IntradayResponse"/> (parallel arrays) into an
    /// array of <see cref="OhlcvBar"/> records.
    /// Returns an empty array if the response is null or contains no timestamps.
    /// </summary>
    private static OhlcvBar[] ParseBars(IntradayResponse? payload)
    {
        if (payload is null || payload.Timestamp.Length == 0)
            return [];

        var bars = new OhlcvBar[payload.Timestamp.Length];
        for (int i = 0; i < bars.Length; i++)
        {
            bars[i] = new OhlcvBar(
                Time:   DateTimeOffset.FromUnixTimeSeconds((long)payload.Timestamp[i]).UtcDateTime,
                Open:   payload.Open[i],
                High:   payload.High[i],
                Low:    payload.Low[i],
                Close:  payload.Close[i],
                Volume: (long)payload.Volume[i]);
        }
        return bars;
    }
}
