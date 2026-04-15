-- Extend symbol_metrics with trend-following and short-horizon breadth fields.

ALTER TABLE symbol_metrics
    ADD COLUMN IF NOT EXISTS ema_50            NUMERIC(14,4),
    ADD COLUMN IF NOT EXISTS ema_200           NUMERIC(14,4),
    ADD COLUMN IF NOT EXISTS week_return_pct   NUMERIC(9,4),
    ADD COLUMN IF NOT EXISTS week_gain_pct     NUMERIC(9,4),
    ADD COLUMN IF NOT EXISTS week_decline_pct  NUMERIC(9,4);