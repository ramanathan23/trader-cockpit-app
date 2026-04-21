from fastapi import APIRouter

from .status import router as status_router
from .signals import router as signals_router
from .instruments import router as instruments_router
from .option_chain import router as option_chain_router
from .config import router as config_router

router = APIRouter()
router.include_router(status_router)
router.include_router(signals_router)
router.include_router(instruments_router)
router.include_router(option_chain_router)
router.include_router(config_router)
