import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from ._zerodha_callback_page import callback_page
from .deps import ZerodhaServiceDep

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/zerodha", tags=["zerodha"])


@router.get("/accounts")
async def accounts(svc: ZerodhaServiceDep):
    return {"accounts": await svc.list_accounts()}


@router.post("/accounts")
async def save_account(payload: dict, svc: ZerodhaServiceDep):
    try:
        return await svc.save_account(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: str, svc: ZerodhaServiceDep):
    return await svc.delete_account(account_id)


@router.get("/login/{account_id}")
async def login(account_id: str, svc: ZerodhaServiceDep):
    try:
        return RedirectResponse(await svc.login_url(account_id), status_code=302)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/callback")
async def callback(
    svc: ZerodhaServiceDep,
    request_token: str | None = Query(default=None),
    account_id: str | None = Query(default=None),
    state: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    callback_account_id = account_id or state
    if status and status != "success":
        return callback_page("error", callback_account_id, f"Zerodha login returned status={status}")
    callback_account_id = callback_account_id or await svc.infer_single_account_id()
    if not callback_account_id or not request_token:
        raise HTTPException(status_code=422, detail="Missing account_id or request_token. Start login from Accounts.")
    try:
        result = await svc.complete_login(callback_account_id, request_token)
        return callback_page("connected", callback_account_id, f"Connected until {result.get('expires_at')}")
    except Exception as exc:
        logger.exception("Zerodha callback failed")
        return callback_page("error", callback_account_id, str(exc))


@router.post("/sync")
async def sync(svc: ZerodhaServiceDep):
    return await svc.sync_all()


@router.get("/performance")
async def performance(svc: ZerodhaServiceDep, start: date | None = None, end: date | None = None):
    return await svc.performance_summary(start=start, end=end)


@router.get("/dashboard")
async def dashboard(svc: ZerodhaServiceDep, start: date | None = None, end: date | None = None):
    return await svc.dashboard(start=start, end=end)


@router.get("/trades")
async def trades(
    svc: ZerodhaServiceDep,
    start: date | None = None,
    end: date | None = None,
    account_id: str | None = Query(default=None),
):
    return await svc.reconstructed_trades(start=start, end=end, account_id=account_id)
