from typing import Annotated

from fastapi import Depends, Request

from ..services.indicators_service import IndicatorsService


def _get_service(request: Request) -> IndicatorsService:
    return request.app.state.indicators_service


IndicatorsServiceDep = Annotated[IndicatorsService, Depends(_get_service)]
