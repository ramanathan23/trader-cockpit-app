# ModelingService — Port 8004

ML model registry: train, predict, and score-all for named models. Active model: `comfort_scorer`.

## Key files
```
src/main.py                              # FastAPI app + lifespan + pool
src/api/_train_routes.py                 # POST /models/{name}/retrain
src/api/_predict_routes.py               # POST /models/{name}/predict
src/api/_score_all_routes.py             # POST /models/{name}/score-all
src/api/_status_routes.py               # GET /models, GET /models/{name}/metrics
src/api/_config_routes.py               # GET/PATCH /config
src/models/comfort_scorer/               # ComfortScorer implementation
src/repositories/                        # asyncpg reads (symbol_indicators, symbol_metrics, daily_scores)
models/comfort_scorer/active/            # Persisted active model artifact
models/comfort_scorer/v{timestamp}/      # Versioned model snapshots
```

## Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET    | /models | List registered models + active versions |
| GET    | /models/{model_name}/metrics | Training metrics for a model version |
| POST   | /models/{model_name}/retrain | Retrain model on latest DB data |
| POST   | /models/{model_name}/predict | Predict comfort score for symbols (body: list of symbols) |
| POST   | /models/{model_name}/score-all | Score all symbols + write comfort scores to daily_scores |
| GET    | /config | Current tunable config |
| PATCH  | /config | Update config (persists + applies immediately) |

## DB tables read (not owned)
- `symbol_indicators` — features for training/prediction
- `symbol_metrics` — additional features
- `daily_scores` — reads total_score as a feature; writes comfort_score back

## Model: comfort_scorer
- sklearn pipeline (StandardScaler + GradientBoostingRegressor or similar)
- Features: indicator values from symbol_indicators + symbol_metrics
- Output: 0–100 comfort score appended to daily_scores.comfort_score
- Active model stored as pickle in `models/comfort_scorer/active/`
- Versioned snapshots kept for rollback

## Pattern notes
- Must run AFTER RankingService (reads daily_scores total_score as feature)
- score-all writes back to daily_scores.comfort_score — idempotent upsert
- Model artifacts are NOT in Docker volumes — they live in the repo directory
- Never write new models outside the ModelingService registry pattern
