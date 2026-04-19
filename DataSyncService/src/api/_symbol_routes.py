import logging

from fastapi import APIRouter

from .deps import SymbolRepoDep, SyncServiceDep

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", summary="Liveness check")
async def health():
    return {"status": "ok", "service": "DataSyncService"}


@router.post("/symbols/load", summary="Load/refresh symbols from CSV into DB")
async def load_symbols(svc: SyncServiceDep):
    count = await svc.bootstrap_symbols()
    return {"symbols_loaded": count}


@router.post("/symbols/refresh-master",
             summary="Re-download Dhan security master CSV and sync security IDs")
async def refresh_security_master(svc: SyncServiceDep):
    result = await svc.refresh_security_master()
    return {
        "equities_matched":        result.equities_matched,
        "equities_unmatched":      result.equities_unmatched,
        "index_futures_upserted":  result.index_futures_upserted,
        "index_futures_activated": result.index_futures_activated,
    }


@router.get("/symbols/dhan-status", summary="Dhan security ID mapping coverage")
async def dhan_mapping_status(repo: SymbolRepoDep):
    return await repo.get_dhan_mapping_stats()


@router.get("/symbols", summary="List symbols")
async def list_symbols(repo: SymbolRepoDep, series: str = "EQ"):
    return await repo.list_by_series(series)
