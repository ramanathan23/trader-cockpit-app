from typing import Annotated

from fastapi import Depends, Request

from ..services.indicators_service import IndicatorsService
from ..services.setup_behavior_service import SetupBehaviorService


def _get_service(request: Request) -> IndicatorsService:
    return request.app.state.indicators_service


IndicatorsServiceDep = Annotated[IndicatorsService, Depends(_get_service)]


def _get_setup_behavior_service(request: Request) -> SetupBehaviorService:
    return request.app.state.setup_behavior_service


SetupBehaviorServiceDep = Annotated[SetupBehaviorService, Depends(_get_setup_behavior_service)]
