.PHONY: up down build logs shell-db sync-initial sync-patch scores-compute

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build --no-cache

logs:
	docker compose logs -f

# Database shell
shell-db:
	docker compose exec timescaledb psql -U trader -d trader_cockpit

# Trigger full historical sync (runs in background)
sync-initial:
	curl -s -X POST http://localhost:8001/api/v1/sync/initial | python -m json.tool

# Trigger incremental patch sync
sync-patch:
	curl -s -X POST http://localhost:8001/api/v1/sync/patch | python -m json.tool

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
