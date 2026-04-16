from typing import Annotated

from fastapi import Depends
from starlette.requests import HTTPConnection

from ..infrastructure.redis.publisher import SignalPublisher
from ..services.feed_service import FeedService


def _feed_service(connection: HTTPConnection) -> FeedService:
    return connection.app.state.feed_service


def _publisher(connection: HTTPConnection) -> SignalPublisher:
    return connection.app.state.publisher


FeedServiceDep = Annotated[FeedService,     Depends(_feed_service)]
PublisherDep   = Annotated[SignalPublisher, Depends(_publisher)]
