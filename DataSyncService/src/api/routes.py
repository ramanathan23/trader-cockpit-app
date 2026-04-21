from fastapi import APIRouter

from ._symbol_routes import router as _symbol_router
from ._sync_routes   import router as _sync_router
from ._data_routes   import router as _data_router
from ._config_routes import router as _config_router

router = APIRouter()
router.include_router(_symbol_router)
router.include_router(_sync_router)
router.include_router(_data_router)
router.include_router(_config_router)
