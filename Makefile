.PHONY: up down build logs shell-db sync scores-top scores-compute feed-status dhan-map dhan-status ui

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

# Database shell
shell-db:
	docker compose exec timescaledb psql -U trader -d trader_cockpit

# Unified sync — auto-classifies every symbol (initial pull / gap fill / skip)
sync:
	curl -s -X POST http://localhost:8001/api/v1/sync/run | python -m json.tool

# Show which symbols have data gaps (dry-run, no fetching)
sync-gaps:
	curl -s http://localhost:8001/api/v1/sync/gaps | python -m json.tool

# Check sync status
sync-status:
	curl -s http://localhost:8001/api/v1/sync/status | python -m json.tool

# Load symbols from CSV into DB
symbols-load:
	curl -s -X POST http://localhost:8001/api/v1/symbols/load | python -m json.tool

# Trigger momentum score computation
scores-compute:
	curl -s -X POST http://localhost:8002/api/v1/scores/compute | python -m json.tool

# Top 20 momentum scores
scores-top:
	curl -s "http://localhost:8002/api/v1/scores?limit=20" | python -m json.tool

# ── Live Feed ─────────────────────────────────────────────────────────────────

# Download Dhan instrument master and sync security IDs into DB
dhan-map:
	curl -s -X POST http://localhost:8001/api/v1/symbols/refresh-master | python -m json.tool

# Check Dhan mapping coverage (how many of 2000+ stocks have a security ID)
dhan-status:
	curl -s http://localhost:8001/api/v1/symbols/dhan-status | python -m json.tool

# Live feed health: instrument count, WebSocket connections, index bias
feed-status:
	curl -s http://localhost:8003/api/v1/status | python -m json.tool

# Open trading dashboard in default browser (Windows)
ui:
	start http://localhost:8003/api/v1/ui
