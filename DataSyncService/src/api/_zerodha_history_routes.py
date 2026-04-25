from fastapi import APIRouter, HTTPException

from .deps import ZerodhaServiceDep

router = APIRouter(prefix="/zerodha/history", tags=["zerodha-history"])


@router.post("/tradebook")
async def import_tradebook(payload: dict, svc: ZerodhaServiceDep):
    account_id = str(payload.get("account_id") or "").strip()
    csv_text = str(payload.get("csv_text") or "")
    if not account_id or not csv_text.strip():
        raise HTTPException(status_code=422, detail="account_id and csv_text are required")
    try:
        return await svc.import_tradebook_csv(account_id, csv_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/pnl-statement")
async def import_pnl_statement(payload: dict, svc: ZerodhaServiceDep):
    account_id = str(payload.get("account_id") or "").strip()
    csv_text = str(payload.get("csv_text") or "")
    if not account_id or not csv_text.strip():
        raise HTTPException(status_code=422, detail="account_id and csv_text are required")
    try:
        return await svc.import_pnl_csv(account_id, csv_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/pnl-statement-xlsx")
async def import_pnl_statement_xlsx(payload: dict, svc: ZerodhaServiceDep):
    account_id = str(payload.get("account_id") or "").strip()
    xlsx_base64 = str(payload.get("xlsx_base64") or "")
    if not account_id or not xlsx_base64.strip():
        raise HTTPException(status_code=422, detail="account_id and xlsx_base64 are required")
    try:
        return await svc.import_pnl_xlsx(account_id, xlsx_base64)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
