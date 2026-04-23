PYTHON ?= python

.PHONY: up down build logs shell-db \
        sync sync-1min reset-1min sync-all sync-gaps sync-status \
        symbols-load dhan-map dhan-status \
        indicators-compute indicators-compute-sse \
        scores-compute scores-top scores-dashboard \
        comfort-score comfort-score-date \
        models-list \
        feed-status token-status screener \
        notebooks ui \
        test-python coverage-python

up:
	docker compose up -d --build --remove-orphans

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

# Database shell
shell-db:
	docker compose run --rm --entrypoint sh db-init -lc 'psql -h "$${PGHOST}" -p "$${PGPORT}" -U "$${DB_USER}" -d "$${DB_NAME}"'

# ── DataSyncService (8001) ────────────────────────────────────────────────────

# Daily sync — auto-classifies every symbol (initial pull / gap fill / skip)
sync:
	curl -s -X POST http://localhost:8001/api/v1/sync/run | python -m json.tool

# 1-min sync — fetch Dhan 1-min OHLCV for F&O stocks only
sync-1min:
	curl -s -X POST http://localhost:8001/api/v1/sync/run-1min | python -m json.tool

# Reset 1-min data — truncates price_data_1min and clears sync_state (forces full re-fetch)
reset-1min:
	curl -s -X POST http://localhost:8001/api/v1/sync/reset-1min | python -m json.tool

# Full sync — daily (yfinance) + 1-min (Dhan) in parallel
sync-all:
	curl -s -X POST http://localhost:8001/api/v1/sync/run-all | python -m json.tool

# Show which symbols have data gaps (dry-run, no fetching)
sync-gaps:
	curl -s http://localhost:8001/api/v1/sync/gaps | python -m json.tool

# Check sync status
sync-status:
	curl -s http://localhost:8001/api/v1/sync/status | python -m json.tool

# Load symbols from CSV into DB
symbols-load:
	curl -s -X POST http://localhost:8001/api/v1/symbols/load | python -m json.tool

# Download Dhan instrument master and sync security IDs into DB
dhan-map:
	curl -s -X POST http://localhost:8001/api/v1/symbols/refresh-master | python -m json.tool

# Check Dhan mapping coverage (how many of 2000+ stocks have a security ID)
dhan-status:
	curl -s http://localhost:8001/api/v1/symbols/dhan-status | python -m json.tool

# ── IndicatorsService (8005) ──────────────────────────────────────────────────

# Compute all indicators + patterns for all symbols (background)
indicators-compute:
	curl -s -X POST http://localhost:8005/api/v1/compute | python -m json.tool

# Compute indicators + patterns: SSE stream (for UI pipeline)
indicators-compute-sse:
	curl -s -X POST http://localhost:8005/api/v1/compute-sse

# ── RankingService (8002) ─────────────────────────────────────────────────────

# Trigger ranking score computation
scores-compute:
	curl -s -X POST http://localhost:8002/api/v1/scores/compute | python -m json.tool

# Scoring dashboard — stats + top 20 scored symbols
scores-top:
	curl -s "http://localhost:8002/api/v1/dashboard?limit=20" | python -m json.tool

# Full scoring dashboard (stats + symbols, default limit 50)
scores-dashboard:
	curl -s "http://localhost:8002/api/v1/dashboard" | python -m json.tool

# ── ModelingService (8004) ────────────────────────────────────────────────────

# Compute and persist comfort scores for all symbols (today's date)
comfort-score:
	curl -s -X POST "http://localhost:8004/api/v1/models/comfort_scorer/score-all" | python -m json.tool

# Compute comfort scores for a specific date: make comfort-score-date DATE=2026-04-18
comfort-score-date:
	curl -s -X POST "http://localhost:8004/api/v1/models/comfort_scorer/score-all?score_date=$(DATE)" | python -m json.tool

# List all registered models
models-list:
	curl -s "http://localhost:8004/api/v1/models" | python -m json.tool

# ── LiveFeedService (8003) ────────────────────────────────────────────────────

# Live feed health: instrument count, WebSocket connections, index bias
feed-status:
	curl -s http://localhost:8003/api/v1/status | python -m json.tool

# Dhan access token presence and expiry
token-status:
	curl -s http://localhost:8003/api/v1/token/status | python -m json.tool

# All instruments with pre-computed daily metrics for screening
screener:
	curl -s "http://localhost:8003/api/v1/screener" | python -m json.tool

# ── UI / Notebooks ────────────────────────────────────────────────────────────

# Open trading dashboard in default browser (Windows)
ui:
	start http://localhost:8003/api/v1/ui

# Open Jupyter notebooks in default browser (Windows)
notebooks:
	start http://localhost:8888

# ── Tests ─────────────────────────────────────────────────────────────────────

test-python:
	$(PYTHON) scripts/run_python_tests.py --no-report

coverage-python:
	$(PYTHON) scripts/run_python_tests.py
