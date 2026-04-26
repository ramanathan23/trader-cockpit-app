# Operations Guide — Trader Cockpit

Day-to-day operating manual. Where to look, what it means, how to decide.

---

## System at a Glance

```
DAILY PIPELINE (automated post-market)
  sync → indicators → ISS → scoring → comfort v2 → session predictions → comfort v3

LIVE SESSION (continuous)
  Dhan WS ticks → 5-min candles → signal engine → SSE → dashboard
                                → regime detector → regime badge on signals

WHAT YOU SEE IN THE UI
  Dashboard: daily scores + ISS + session prediction for tomorrow
  Signal tape: live signals with regime context
```

---

## Information Map: Where to Find What

### Dashboard (CockpitUI main view)

| Column / Badge | What It Is | When to Use It |
|---|---|---|
| `total_score` | Composite 0-100 daily rank. Momentum + Trend + Volatility + Structure (25% each) | Initial filter: focus on >65 |
| `comfort_v3` | Chart quality score adjusted for intraday character. v2 − ISS penalty − pullback penalty + session modifier | Primary comfort indicator. Use v3 not v2 |
| `ISS` badge | Intraday Suitability Score 0-100 computed from 90d of 1-min data | Tells you if stock is actually tradeable intraday vs looks good on daily |
| Session badge `TREND_UP` / `CHOP` etc | Tomorrow's predicted session type from LightGBM | Use for day selection (which stocks to watch tomorrow) |
| `↩ 28%` | Predicted pullback depth on up days. 28% means expect retrace of 28% of daily range before continuation | Sets mental stop tolerance. High pullback pred → don't panic on dip |
| `trend_up_prob` | Probability of trending up session | Higher = more confidence in prediction |
| `stage` badge | Weinstein Stage 1-4. Stage 2 = uptrend, Stage 4 = downtrend | Only trade Stage 2 (long) or Stage 4 (short). Ignore 1/3 |
| `weekly_bias` | BULLISH / NEUTRAL / BEARISH. Computed from EMA-50 position | Avoid longs on BEARISH bias |

### Signal Tape (live during session)

| Element | What It Is | When to Use It |
|---|---|---|
| Signal type badge | `RANGE_BREAKOUT`, `CAM_H3_REVERSAL`, etc. | Entry trigger type |
| Regime badge | `TRENDING_UP` / `CHOPPY` / `SQUEEZE` / `NEUTRAL` | Current intraday regime for this stock. Changes every 5 min |
| Score chip | 0-100 signal quality | Prefer score > 65 |
| `bias_15m` / `bias_1h` | Multi-timeframe directional bias | Confluence check |
| `watchlist_conflict` | Signal direction conflicts weekly_bias | Caution flag — weaker trade |
| Entry / Stop / Target levels | Pre-computed R-multiples | Direct use for order placement |

---

## Decision Framework

### Pre-Market (9:00–9:15 AM)

Open dashboard. Filter: **Watchlist only**.

**Step 1 — ISS filter (hard gate)**
```
ISS < 40 → skip regardless of daily score or comfort
Reason: stock is intraday noisy, will eat stop before setup plays out
```

**Step 2 — Session prediction filter**
```
CHOP predicted → skip or reduce size by 50%
VOLATILE predicted → tighten target (don't expect full T2), use trailing stop
TREND_UP + prob > 0.55 → primary focus list
NEUTRAL → secondary, trade only on strong signal (score > 75)
TREND_DOWN → short bias only (Stage 4 stocks)
```

**Step 3 — Comfort v3 check**
```
comfort_v3 < 50 → skip
comfort_v3 50-65 → smaller size, tighter stop
comfort_v3 65-80 → standard size
comfort_v3 > 80 → full size (strong setup)
```

**Result:** From 25 watchlist stocks → 4-8 primary focus stocks.

**Step 4 — Pullback tolerance**
```
Before the session:
  Note pullback_depth_pred for each primary stock
  e.g., RELIANCE: pullback_pred = 32%

During session:
  If ATR = 25 pts and stock retraces 8 pts from high → that's 32% of range
  → expected, don't exit
  If it retraces 55% → beyond prediction → re-evaluate
```

---

### During Session (9:15–15:30)

**Watch for signals from primary focus list only** (the 4-8 from pre-market filter).

**On signal arrival:**
1. Check **regime badge** — must be `TRENDING_UP` (for longs) or `TRENDING_DOWN` (for shorts)
   - `CHOPPY` regime → skip signal, don't trade
   - `SQUEEZE` regime → valid entry point, breakout likely imminent
   - `NEUTRAL` → trade with reduced size

2. Check **signal score** (>65 preferred)

3. Check **multi-timeframe bias** (`bias_15m` and `bias_1h` must align with direction)

4. Note **pullback_depth_pred** from morning → this is your drawdown tolerance

5. Enter using provided `entry_low / entry_high` band. Set stop at `stop`. T1 = `target_1`.

**Regime change during trade:**

| Regime flips to | Action |
|---|---|
| `TRENDING_UP → NEUTRAL` | Move stop to breakeven, partial exit |
| `TRENDING_UP → CHOPPY` | Exit immediately. Setup failed |
| `NEUTRAL → TRENDING_UP` | Resume holding, re-add on pullback |
| `any → SQUEEZE` | Watch for direction break, hold |

---

### Post-Session (after 15:30)

Run daily pipeline (or verify it ran):

```bash
make sync                   # daily + 1-min OHLCV
# or individually:
# POST /datasync/sync/run-sse
# POST /datasync/sync/run-1min-sse

make scores-compute         # indicators + unified scoring
# = POST /indicators/compute-sse
# + POST /scorer/scores/compute-sse

make comfort-score          # comfort v2
# = POST /modeling/models/comfort_scorer/score-all

# Then session predictions + comfort v3:
POST /modeling/models/session_classifier/score-all?score_date=YYYY-MM-DD
```

After pipeline runs, dashboard reflects tomorrow's predictions. Review watchlist before next session.

---

## Weekly Maintenance

### Every Monday (or first trading day of week)

**1. Retrain session classifier** (15-20 min, one-time trigger)

```
POST /modeling/models/session_classifier/build-training-data
  → rebuilds intraday_training_sessions with latest week's sessions

POST /modeling/models/session_classifier/train
  → retrains LightGBM with new data
  → check accuracy in response — target >55% for 6-class
```

If accuracy drops below 50%, check for data quality issues (missing 1-min data, symbol list changes).

**2. Check ISS staleness**

```
GET /indicators/intraday-profile/{symbol}  → check computed_at
```

ISS should be recomputed nightly. If any symbol shows `computed_at` > 2 days old, run:
```
POST /indicators/compute-intraday-profile
```

**3. Review low-ISS watchlist items**

Dashboard stats show `low_iss_watchlist_count` (watchlist stocks with ISS < 40). If this is more than 5, the watchlist has quality issues — check if those stocks still make sense to watch intraday.

**4. Verify 1-min data coverage**

```
GET /datasync/data-quality/1min
```

Stocks with stale 1-min data won't have valid ISS. Resync if needed.

---

## Monthly Maintenance

**1. Check model metrics**

```
POST /modeling/models/session_classifier/evaluate
```

Response includes accuracy, per-class F1, and pullback regressor MAE. Track these over time:
- Accuracy < 50% sustained → retrain with more data or reconsider features
- Pullback MAE > 0.25 → regressor degrading, retrain

**2. Review comfort v2 vs v3 divergence**

Stocks where `|v3 - v2| > 20` consistently deserve manual review. Large divergence means their intraday character is very different from daily appearance.

**3. Sync historical 1-min data gaps**

```
GET /datasync/sync/gaps?timeframe=1m
```

Fill gaps for any symbol showing `gap_large`. ISS quality depends on continuous 90d window.

---

## Signal Quality Reference

### Session Type → Trading Approach

| Session Pred | Approach | Size | Target | Stop |
|---|---|---|---|---|
| `TREND_UP` | Momentum, hold for T2 | Full | T2 (2R) | Wide per ATR |
| `TREND_DOWN` | Short momentum only | Full (shorts) | T2 | Wide per ATR |
| `VOLATILE` | Trade ORB only, take T1, trail | 50-75% | T1 (1R) | ATR-based |
| `CHOP` | Skip or paper only | 0-25% | Skip | N/A |
| `GAP_FADE` | Watch for gap fill setup specifically | 50% | Gap fill level | Tight |
| `NEUTRAL` | Trade only strong signals (score >75) | 50% | T1 | Tight |

### ISS → Stock Quality

| ISS | Interpretation | Action |
|---|---|---|
| 75-100 | Clean intraday mover. Trends well, respects levels | Trade freely |
| 60-74 | Good intraday character. Minor noise | Trade normally |
| 40-59 | Average. Some choppiness, occasional stop-hunts | Reduce size, wider stop |
| 20-39 | Noisy. Will likely eat stop before setup plays | Skip or paper only |
| 0-19 | Dangerous intraday. High volatility compression — looks calm on daily, violent intraday | Never trade intraday |

### Regime → Immediate Action

| Regime | Choppiness | Autocorr | What It Means |
|---|---|---|---|
| `TRENDING_UP` | < 40 | > 0.15 | Stock is in flow. Every dip is buyable | 
| `TRENDING_DOWN` | < 40 | > 0.15 | Stock is breaking down. Every bounce is sellable |
| `NEUTRAL` | 40-61.8 | -0.10 to 0.15 | Directional but not strong. Normal trading |
| `CHOPPY` | > 61.8 or autocorr < -0.10 | Negative | Random walk. Stop will be hit regardless of direction. Exit or wait |
| `SQUEEZE` | Any | Any | Bar range < 30% of average. Imminent breakout. Watch, don't act yet |

---

## Comfort v3 vs v2: What Changed

**v2 (daily only):** Sees clean chart, trending indicators → scores high.

**v3 = v2 adjusted for intraday reality:**
- **ISS penalty:** If ISS < 50, comfort reduced. Stock looks good daily but trades badly intraday.
- **Pullback penalty:** If predicted pullback > 45%, comfort reduced. Deep pullback = hard to hold.
- **Session modifier:** TREND_UP adds +5, CHOP subtracts -8, TREND_DOWN subtracts -10.

**When v2 and v3 diverge significantly (>15 pts):**

| v2 high, v3 low | v2 low, v3 high |
|---|---|
| Classic trap. Daily chart is beautiful but intraday is violent | Boring daily chart but actually very clean intraday mover |
| Verify by checking ISS score — will be < 40 | Verify by checking ISS score — will be > 65 |
| Do not trade intraday | Good for intraday even if daily isn't exciting |

---

## First-Time Setup (after new deployment)

### 1. Build training data (one-time, takes 20-40 min)

```
POST /modeling/models/session_classifier/build-training-data
```

Reads 5 years of daily OHLCV, generates ~625,000 labeled sessions. Watch progress via SSE.

### 2. Train models (5-10 min)

```
POST /modeling/models/session_classifier/train
```

Check response for accuracy. Expect 55-65% on 6-class. Model artifacts saved to `/models/session_classifier/`.

### 3. Build ISS profiles (10-15 min)

```
POST /indicators/compute-intraday-profile-sse
```

Reads 90 days of 1-min data per symbol. Requires 1-min sync to be current first.

### 4. Run full pipeline once

```
make scores-compute && make comfort-score
POST /modeling/models/session_classifier/score-all?score_date=TODAY
```

Dashboard now shows complete data including ISS, session predictions, comfort v3.

### 5. Verify in UI

- Open dashboard → watchlist view
- Confirm ISS column shows values (not blank)
- Confirm Session badge shows TREND_UP / CHOP etc
- Confirm comfort_v3 column present
- Open a signal (if market is open) → confirm regime badge visible

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| ISS shows blank for all symbols | ISS not computed or 1-min data stale | Run `POST /compute-intraday-profile`, check 1-min sync |
| Session prediction = NEUTRAL for all | Models not trained or score-all not run | Run `train` then `score-all` |
| comfort_v3 same as comfort_v2 | Session predictions missing for date | Run `score-all` for correct date |
| Regime badge stuck on UNKNOWN | LiveFeedService not receiving ticks | Check Dhan WS connection: `GET /api/v1/status` |
| Session accuracy < 50% | Data drift or insufficient training data | Rebuild training data + retrain |
| ISS computed_at is old | Nightly pipeline skipped ISS step | Run `POST /compute-intraday-profile` manually |
