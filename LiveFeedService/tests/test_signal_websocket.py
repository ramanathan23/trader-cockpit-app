import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import router
import src.api.routes as routes_module


class _FakePublisher:
    def __init__(self, catchup: list[dict]) -> None:
        self._url = "redis://example"
        self._catchup = catchup

    async def recent_signals(self) -> list[dict]:
        return self._catchup


class _FakePubSub:
    def __init__(self, messages: list[dict[str, str]]) -> None:
        self._messages = messages
        self.subscribed: list[str] = []
        self.unsubscribed: list[str] = []

    async def subscribe(self, channel: str) -> None:
        self.subscribed.append(channel)

    async def unsubscribe(self, channel: str) -> None:
        self.unsubscribed.append(channel)

    async def listen(self):
        for message in self._messages:
            yield message


class _FakeRedisClient:
    def __init__(self, messages: list[dict[str, str]]) -> None:
        self.pubsub_instance = _FakePubSub(messages)
        self.closed = False

    def pubsub(self) -> _FakePubSub:
        return self.pubsub_instance

    async def aclose(self) -> None:
        self.closed = True


def test_signal_websocket_replays_catchup_then_streams_live(monkeypatch) -> None:
    catchup = [
        {"id": "catchup-1", "symbol": "ABC", "signal_type": "ORB_BREAKOUT", "timestamp": "t1"},
        {"id": "catchup-2", "symbol": "XYZ", "signal_type": "VWAP_BREAKOUT", "timestamp": "t2"},
    ]
    live_payload = json.dumps({
        "id": "live-1",
        "symbol": "ABC",
        "signal_type": "ORB_BREAKOUT",
        "timestamp": "t3",
    })
    fake_redis = _FakeRedisClient([
        {"type": "message", "data": live_payload},
    ])

    monkeypatch.setattr(routes_module.aioredis, "from_url", lambda *args, **kwargs: fake_redis)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.state.publisher = _FakePublisher(catchup)

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/signals/ws") as websocket:
            assert json.loads(websocket.receive_text())["id"] == "catchup-1"
            assert json.loads(websocket.receive_text())["id"] == "catchup-2"
            assert json.loads(websocket.receive_text())["id"] == "live-1"

    assert fake_redis.pubsub_instance.subscribed == ["signals"]
    assert fake_redis.pubsub_instance.unsubscribed == ["signals"]
    assert fake_redis.closed is True