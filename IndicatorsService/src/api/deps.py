from typing import Annotated

from fastapi import Depends, Request

from ..services.indicators_service import IndicatorsService
from ..services.intraday_profile_service import IntradayProfileService


def _get_service(request: Request) -> IndicatorsService:
    return request.app.state.indicators_service


IndicatorsServiceDep = Annotated[IndicatorsService, Depends(_get_service)]


def _get_intraday_service(request: Request) -> IntradayProfileService:
    return request.app.state.intraday_profile_service


IntradayProfileServiceDep = Annotated[IntradayProfileService, Depends(_get_intraday_service)]
