INSERT INTO symbol_metrics (
    symbol,
    computed_at,
    week52_high,
    week52_low,
    atr_14,
    adv_20_cr,
    ema_50,
    ema_200,
    week_return_pct,
    week_gain_pct,
    week_decline_pct,
    trading_days,
    prev_day_high,
    prev_day_low,
    prev_day_close,
    prev_week_high,
    prev_week_low,
    prev_month_high,
    prev_month_low
)
WITH RECURSIVE base AS (
    SELECT
        symbol,
        time,
        high::float,
        low::float,
        close::float,
        volume::float,
        LAG(close::float) OVER (PARTITION BY symbol ORDER BY time ASC) AS prev_close,
        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY time ASC)      AS rn,
        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY time DESC)     AS rn_desc,
        COUNT(*)         OVER (PARTITION BY symbol)                    AS total
    FROM price_data_daily
    WHERE time >= NOW() - INTERVAL '366 days'
),
ema_calc AS (
    SELECT
        symbol,
        time,
        high,
        low,
        close,
        volume,
        prev_close,
        rn,
        rn_desc,
        total,
        close AS ema_50,
        close AS ema_200
    FROM base
    WHERE rn = 1

    UNION ALL

    SELECT
        b.symbol,
        b.time,
        b.high,
        b.low,
        b.close,
        b.volume,
        b.prev_close,
        b.rn,
        b.rn_desc,
        b.total,
        (b.close * (2.0 / 51.0))  + (e.ema_50  * (1.0 - (2.0 / 51.0)))  AS ema_50,
        (b.close * (2.0 / 201.0)) + (e.ema_200 * (1.0 - (2.0 / 201.0))) AS ema_200
    FROM base b
    JOIN ema_calc e
      ON e.symbol = b.symbol
     AND b.rn = e.rn + 1
),
with_tr AS (
    SELECT
        symbol,
        time,
        high, low, close, volume,
        prev_close,
        ema_50,
        ema_200,
        rn_desc,
        GREATEST(
            high - low,
            ABS(high - COALESCE(prev_close, close)),
            ABS(low  - COALESCE(prev_close, close))
        ) AS tr,
        rn, total
    FROM ema_calc
)
SELECT
    symbol,
    NOW()                                                    AS computed_at,
    MAX(high)                                                AS week52_high,
    MIN(low)                                                 AS week52_low,
    AVG(tr)          FILTER (WHERE rn > total - 14)          AS atr_14,
    AVG(close * volume / 1e7)
                     FILTER (WHERE rn > total - 20)          AS adv_20_cr,
    MAX(ema_50)       FILTER (WHERE rn = total)              AS ema_50,
    MAX(ema_200)      FILTER (WHERE rn = total)              AS ema_200,
    (
        (
            MAX(close) FILTER (WHERE rn = total)
            - MAX(close) FILTER (
                WHERE rn_desc = CASE WHEN total >= 6 THEN 6 ELSE total END
            )
        )
        / NULLIF(
            MAX(close) FILTER (
                WHERE rn_desc = CASE WHEN total >= 6 THEN 6 ELSE total END
            ),
            0
        )
    ) * 100                                                  AS week_return_pct,
    (
        (
            MAX(close) FILTER (WHERE rn = total)
            - MIN(low) FILTER (WHERE rn_desc <= 5)
        )
        / NULLIF(MIN(low) FILTER (WHERE rn_desc <= 5), 0)
    ) * 100                                                  AS week_gain_pct,
    (
        (
            MAX(high) FILTER (WHERE rn_desc <= 5)
            - MAX(close) FILTER (WHERE rn = total)
        )
        / NULLIF(MAX(high) FILTER (WHERE rn_desc <= 5), 0)
    ) * 100                                                  AS week_decline_pct,
    COUNT(*)                                                 AS trading_days,
    MAX(high)        FILTER (WHERE rn = total)               AS prev_day_high,
    MAX(low)         FILTER (WHERE rn = total)               AS prev_day_low,
    MAX(close)       FILTER (WHERE rn = total)               AS prev_day_close,
    MAX(high) FILTER (
        WHERE time >= date_trunc('week', CURRENT_DATE) - INTERVAL '7 days'
          AND time  < date_trunc('week', CURRENT_DATE)
    )                                                        AS prev_week_high,
    MIN(low)  FILTER (
        WHERE time >= date_trunc('week', CURRENT_DATE) - INTERVAL '7 days'
          AND time  < date_trunc('week', CURRENT_DATE)
    )                                                        AS prev_week_low,
    MAX(high) FILTER (
        WHERE time >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
          AND time  < date_trunc('month', CURRENT_DATE)
    )                                                        AS prev_month_high,
    MIN(low)  FILTER (
        WHERE time >= date_trunc('month', CURRENT_DATE) - INTERVAL '1 month'
          AND time  < date_trunc('month', CURRENT_DATE)
    )                                                        AS prev_month_low
FROM with_tr
GROUP BY symbol
HAVING COUNT(*) >= 5
ON CONFLICT (symbol) DO UPDATE SET
    computed_at      = EXCLUDED.computed_at,
    week52_high      = EXCLUDED.week52_high,
    week52_low       = EXCLUDED.week52_low,
    atr_14           = EXCLUDED.atr_14,
    adv_20_cr        = EXCLUDED.adv_20_cr,
    ema_50           = EXCLUDED.ema_50,
    ema_200          = EXCLUDED.ema_200,
    week_return_pct  = EXCLUDED.week_return_pct,
    week_gain_pct    = EXCLUDED.week_gain_pct,
    week_decline_pct = EXCLUDED.week_decline_pct,
    trading_days     = EXCLUDED.trading_days,
    prev_day_high    = EXCLUDED.prev_day_high,
    prev_day_low     = EXCLUDED.prev_day_low,
    prev_day_close   = EXCLUDED.prev_day_close,
    prev_week_high   = EXCLUDED.prev_week_high,
    prev_week_low    = EXCLUDED.prev_week_low,
    prev_month_high  = EXCLUDED.prev_month_high,
    prev_month_low   = EXCLUDED.prev_month_low
