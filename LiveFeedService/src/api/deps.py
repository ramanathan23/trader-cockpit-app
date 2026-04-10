from typing import Annotated

from fastapi import Depends, Request

from ..infrastructure.redis.publisher import SignalPublisher
from ..services.feed_service import FeedService


def _feed_service(request: Request) -> FeedService:
    return request.app.state.feed_service


def _publisher(request: Request) -> SignalPublisher:
    return request.app.state.publisher


FeedServiceDep = Annotated[FeedService,     Depends(_feed_service)]
PublisherDep   = Annotated[SignalPublisher, Depends(_publisher)]
