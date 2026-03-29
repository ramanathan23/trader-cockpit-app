# API Layer Design

**Project:** Trader Cockpit App
**Layer:** API (FastAPI thin routers + WebSocket endpoints)
**Last Updated:** 2026-03-29

---

## Table of Contents

1. [Router Architecture](#router-architecture)
2. [Authentication](#authentication)
3. [REST Endpoints](#rest-endpoints)
   - [Signals](#signals)
   - [Equity](#equity)
   - [Risk](#risk)
   - [Orders](#orders)
   - [Options](#options)
   - [Portfolio](#portfolio)
   - [Market Data](#market-data)
4. [WebSocket Endpoints](#websocket-endpoints)
   - [WS /ws/market-feed](#ws-wsmarket-feed)
   - [WS /ws/cockpit](#ws-wscockpit)
5. [Error Response Format](#error-response-format)
6. [Rate Limiting](#rate-limiting)
7. [Request/Response Schema Conventions](#requestresponse-schema-conventions)
8. [Main App Assembly](#main-app-assembly)

---

## Router Architecture

Each domain gets one FastAPI `APIRouter`. All routers are registered under `/api/v1/`. Routers contain zero business logic — they validate inputs, call one application handler, and return the response.

```
POST /api/v1/equity/convert
        ↓
[equity/router.py]
  validate ConvertRequest (Pydantic)
  get current_user (Depends)
  get handler (Depends)
  await handler.handle(ConvertToDeliveryCommand(...))
  return ConvertResponse
```

```
backend/api/v1/
├── deps.py                # All Depends() factories
├── market_data/router.py
├── signals/router.py
├── equity/router.py
├── orders/router.py
├── risk/router.py
├── options/router.py
├── portfolio/router.py
└── ws/
    ├── market_feed.py
    └── cockpit_feed.py
```

---

## Authentication

The frontend authenticates with a JWT (PyJWT). The Dhan access token is internal — the frontend never sees it.

### JWT Structure

```python
# Payload:
{
    "sub": "user_id",
    "exp": 1234567890,  # Unix timestamp
    "iat": 1234567800,
    "scope": "trader"
}
```

### JWT Dependency

```python
# api/v1/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from config.settings import get_settings
from dataclasses import dataclass

security = HTTPBearer()

@dataclass
class CurrentUser:
    id: str

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
        )
        return CurrentUser(id=payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### WebSocket Auth

WebSocket connections pass the JWT as a query parameter (browser WebSocket API does not support custom headers):

```
WS /ws/market-feed?token=<jwt>
WS /ws/cockpit?token=<jwt>
```

---

## REST Endpoints

### Signals

#### GET /api/v1/signals/watchlist

Return today's watchlist with scores, grades, and entry zones.

**Request:** No body. Optional query params:
- `grade`: filter by grade (`A`, `B`, `C`)
- `direction`: filter by `LONG` or `SHORT`

**Response:**
```json
{
  "date": "2026-03-29",
  "generated_at": "2026-03-29T16:05:23Z",
  "scan_duration_seconds": 42.1,
  "entries": [
    {
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "grade": "A",
      "score": {
        "total": 84,
        "trend": 18,
        "volume": 16,
        "sector": 18,
        "market_ctx": 16,
        "rr": 16
      },
      "direction": "LONG",
      "entry_zone_low": 2940.0,
      "entry_zone_high": 2960.0,
      "sl_price": 2900.0,
      "target_price": 3080.0,
      "risk_reward": 3.0,
      "notes": "Breakout from 3-week consolidation, sector outperforming"
    }
  ]
}
```

**Router:**
```python
# api/v1/signals/router.py
from fastapi import APIRouter, Depends, Query
from api.v1.deps import get_current_user, get_watchlist_handler
from application.signals.queries.get_watchlist import GetWatchlistQuery

router = APIRouter(prefix="/signals", tags=["signals"])

@router.get("/watchlist")
async def get_watchlist(
    grade: str | None = Query(None, pattern="^[ABCD]$"),
    direction: str | None = Query(None, pattern="^(LONG|SHORT)$"),
    handler = Depends(get_watchlist_handler),
    user: CurrentUser = Depends(get_current_user),
):
    watchlist = await handler.handle(GetWatchlistQuery(user_id=user.id))
    entries = watchlist.entries if watchlist else []
    if grade:
        entries = [e for e in entries if e.grade.value == grade]
    if direction:
        entries = [e for e in entries if e.direction.value == direction]
    return serialize_watchlist(watchlist, entries)
```

#### GET /api/v1/signals/{symbol}

Signal for a specific symbol at a given interval.

**Request:** Path param `symbol`. Query param `interval` (default: `15`).

**Response:**
```json
{
  "symbol": "HDFCBANK",
  "exchange": "NSE",
  "interval": "15",
  "signal": {
    "direction": "LONG",
    "grade": "B",
    "score": { "total": 72, "trend": 16, "volume": 14, "sector": 14, "market_ctx": 14, "rr": 14 },
    "entry_price": 1720.0,
    "sl_price": 1695.0,
    "target_price": 1790.0,
    "risk_reward": 2.8,
    "generated_at": "2026-03-29T09:47:00Z",
    "valid_until": "2026-03-29T15:30:00Z"
  }
}
```

**Response when no signal:** `{ "symbol": "HDFC", "signal": null }`

---

### Equity

#### GET /api/v1/equity/positions

All open positions split by product type.

**Response:**
```json
{
  "intraday": [
    {
      "position_id": "uuid",
      "symbol": "TATASTEEL",
      "exchange": "NSE",
      "qty": 500,
      "entry_price": 148.50,
      "sl_price": 146.00,
      "target_price": 154.00,
      "sl_order_id": "1234567890",
      "current_price": 150.20,
      "unrealized_pnl": 850.0,
      "capital_at_risk": 1250.0,
      "sl_distance_pct": 1.68,
      "opened_at": "2026-03-29T09:32:00Z"
    }
  ],
  "cnc": [
    {
      "position_id": "uuid",
      "symbol": "INFY",
      "exchange": "NSE",
      "qty": 25,
      "avg_price": 1850.00,
      "swing_sl": 1780.00,
      "swing_target": 2050.00,
      "current_price": 1920.00,
      "unrealized_pnl": 1750.0,
      "sl_distance_pct": 3.78,
      "hold_days": 3
    }
  ],
  "summary": {
    "total_unrealized_pnl": 2600.0,
    "intraday_capital_at_risk": 1250.0,
    "positions_count": 2
  }
}
```

#### GET /api/v1/equity/conversion-candidates

Pre-calculated conversion panel for EOD decision making.

**Response:**
```json
{
  "as_of": "2026-03-29T15:10:00Z",
  "candidates": [
    {
      "position_id": "uuid",
      "symbol": "TATASTEEL",
      "exchange": "NSE",
      "intraday_qty": 500,
      "intraday_entry": 148.50,
      "current_price": 150.20,
      "eligible": true,
      "swing_qty": 80,
      "intra_qty_to_close": 420,
      "suggested_swing_sl": 144.00,
      "suggested_swing_target": null,
      "available_capital": 250000.0,
      "reason": "Eligible for conversion",
      "conversion_note": "80 CNC shares @ ₹250K capital (₹1,250/lot). 420 INTRADAY shares to close."
    }
  ]
}
```

#### POST /api/v1/equity/convert

Execute INTRADAY → CNC conversion.

**Request:**
```json
{
  "position_id": "uuid",
  "cnc_qty": 80,
  "swing_sl": 144.00,
  "swing_target": 162.00
}
```

**Response (success):**
```json
{
  "success": true,
  "cnc_position_id": "uuid",
  "cnc_qty": 80,
  "closed_intra_qty": 420,
  "message": "Converted 80 shares to CNC. Closed 420 intraday shares. CNC SL set at ₹144.00."
}
```

**Response (failure):**
```json
{
  "success": false,
  "error": "CNC qty (500) must be less than intraday qty (500). Full conversion not supported."
}
```

#### POST /api/v1/equity/intraday

Place a new intraday trade.

**Request:**
```json
{
  "symbol": "TATASTEEL",
  "exchange": "NSE",
  "direction": "BUY",
  "entry_price": 148.50,
  "sl_price": 146.00,
  "qty": 0
}
```

`qty: 0` means "auto-calculate from risk profile". The handler uses `PositionSizer`.

**Response:**
```json
{
  "position_id": "uuid",
  "order_id": "uuid",
  "dhan_order_id": "1234567890",
  "sl_order_id": "1234567891",
  "qty": 500,
  "capital_at_risk": 1250.0,
  "message": "INTRADAY BUY placed: 500 × TATASTEEL @ ₹148.50, SL @ ₹146.00"
}
```

---

### Risk

#### GET /api/v1/risk/position-size

Calculate position size without placing an order.

**Request query params:**
- `symbol`: e.g. `RELIANCE`
- `exchange`: e.g. `NSE`
- `mode`: `INTRADAY` or `CNC`
- `entry_price`: float
- `sl_price`: float

**Response:**
```json
{
  "mode": "INTRADAY",
  "qty": 420,
  "risk_per_share": 2.50,
  "total_risk": 1050.0,
  "capital_required": 62580.0,
  "warning": null,
  "atr_validation": {
    "valid": true,
    "message": "SL distance ₹2.50 meets minimum ₹1.80 (0.5×ATR=₹3.60)"
  }
}
```

#### GET /api/v1/risk/daily-state

Current daily risk consumption.

**Response:**
```json
{
  "date": "2026-03-29",
  "daily_loss_limit": 5000.0,
  "consumed_loss": 850.0,
  "remaining_limit": 4150.0,
  "utilization_pct": 17.0,
  "realized_pnl": -850.0,
  "positions_open": 2,
  "intra_trades_today": 3,
  "can_trade": true
}
```

#### GET /api/v1/risk/profile

User's risk profile settings.

#### PUT /api/v1/risk/profile

Update risk parameters.

**Request:**
```json
{
  "intra_risk_pct": 0.5,
  "cnc_risk_pct": 1.0,
  "daily_loss_limit": 5000.0,
  "max_intra_positions": 5,
  "max_cnc_positions": 10,
  "total_capital": 500000.0
}
```

---

### Orders

#### GET /api/v1/orders

Today's order book.

**Query params:** `status` (filter), `product_type` (filter)

**Response:**
```json
{
  "orders": [
    {
      "order_id": "uuid",
      "dhan_order_id": "1234567890",
      "symbol": "TATASTEEL",
      "exchange": "NSE",
      "side": "BUY",
      "qty": 500,
      "price": null,
      "trigger_price": null,
      "order_type": "MARKET",
      "product_type": "INTRADAY",
      "status": "FILLED",
      "filled_qty": 500,
      "fill_price": 148.55,
      "created_at": "2026-03-29T09:32:01Z"
    }
  ],
  "total": 1
}
```

#### POST /api/v1/orders

Place a generic order (used for manual order placement outside of named workflows).

**Request:**
```json
{
  "symbol": "RELIANCE",
  "exchange": "NSE",
  "side": "BUY",
  "qty": 10,
  "price": null,
  "trigger_price": null,
  "order_type": "MARKET",
  "product_type": "CNC",
  "validity": "DAY"
}
```

#### DELETE /api/v1/orders/{order_id}

Cancel an order.

**Response:**
```json
{ "cancelled": true, "dhan_order_id": "1234567890" }
```

#### PATCH /api/v1/orders/{order_id}

Modify an open order (price/qty).

---

### Options

#### GET /api/v1/options/strategies

All active option strategies with live Greeks.

**Response:**
```json
{
  "strategies": [
    {
      "strategy_id": "uuid",
      "basket_id": "uuid",
      "strategy_type": "BULL_CALL_SPREAD",
      "csl_status": "ACTIVE",
      "csl_amount": 5000.0,
      "combined_pnl": 1200.0,
      "net_premium": -3500.0,
      "created_at": "2026-03-29T10:15:00Z",
      "legs": [
        {
          "leg_id": "uuid",
          "symbol": "NIFTY26JAN24000CE",
          "exchange": "NFO",
          "side": "BUY",
          "qty": 50,
          "entry_price": 120.0,
          "lsl_price": 60.0,
          "lsl_order_id": "9876543210",
          "current_price": 145.0,
          "unrealized_pnl": 1250.0,
          "delta": 0.42,
          "gamma": 0.003,
          "theta": -8.5,
          "vega": 12.1
        },
        {
          "leg_id": "uuid",
          "symbol": "NIFTY26JAN24200CE",
          "side": "SELL",
          "qty": 50,
          "entry_price": 65.0,
          "lsl_price": null,
          "current_price": 62.0,
          "unrealized_pnl": 150.0,
          "delta": -0.28
        }
      ]
    }
  ]
}
```

#### POST /api/v1/options/strategies

Place a new option strategy (sequential leg placement).

**Request:**
```json
{
  "basket_id": null,
  "strategy_type": "BULL_CALL_SPREAD",
  "legs": [
    {
      "symbol": "NIFTY26JAN24000CE",
      "exchange": "NFO",
      "side": "BUY",
      "qty": 50,
      "entry_price": 0,
      "lsl_price": 60.0
    },
    {
      "symbol": "NIFTY26JAN24200CE",
      "exchange": "NFO",
      "side": "SELL",
      "qty": 50,
      "entry_price": 0,
      "lsl_price": 0
    }
  ],
  "csl_amount": 5000.0
}
```

`entry_price: 0` means MARKET order.

**Response:**
```json
{
  "strategy_id": "uuid",
  "placed_legs": 2,
  "total_legs": 2,
  "net_premium": -2750.0,
  "status": "FULLY_PLACED",
  "message": "BULL_CALL_SPREAD placed: 2/2 legs filled. Net debit ₹2,750."
}
```

**Response on partial failure:**
```json
{
  "strategy_id": "uuid",
  "placed_legs": 1,
  "total_legs": 2,
  "net_premium": 0,
  "status": "FAILED",
  "message": "Leg 2 placement failed. Leg 1 has been closed (aborted). No open position."
}
```

#### DELETE /api/v1/options/strategies/{strategy_id}

Close all legs of a strategy (triggers CSL logic).

**Response:**
```json
{
  "strategy_id": "uuid",
  "legs_closed": 2,
  "failed_legs": [],
  "status": "CLOSED",
  "message": "Strategy closed manually. 2 legs exited at market."
}
```

#### GET /api/v1/options/baskets

List all baskets with their strategies.

#### POST /api/v1/options/baskets

Create a named basket.

---

### Portfolio

#### GET /api/v1/portfolio

Full portfolio snapshot.

**Response:**
```json
{
  "allocation": {
    "equity_intraday": 62580.0,
    "equity_cnc": 46250.0,
    "options": 17500.0,
    "cash": 373670.0,
    "total_deployed": 126330.0,
    "utilization_pct": 25.27
  },
  "daily_pnl": {
    "date": "2026-03-29",
    "realized_pnl": 2400.0,
    "unrealized_pnl": 2600.0,
    "charges": 185.0,
    "net_pnl": 4815.0
  },
  "cnc_position_count": 1,
  "active_strategy_count": 1
}
```

---

### Market Data

#### GET /api/v1/market-data/candles

**Query params:** `symbol`, `exchange`, `interval`, `from` (date), `to` (date)

**Response:**
```json
{
  "symbol": "NIFTY",
  "exchange": "NSE",
  "interval": "15",
  "candles": [
    { "ts": "2026-03-29T09:15:00Z", "open": 22100, "high": 22145, "low": 22090, "close": 22130, "volume": 12500000 }
  ]
}
```

#### GET /api/v1/market-data/search

**Query param:** `q` (search string)
Returns list of matching instruments from the Dhan instrument master.

---

## WebSocket Endpoints

### WS /ws/market-feed

Streams live quotes for symbols subscribed by the frontend.

**Connection:** `WS /ws/market-feed?token=<jwt>`

**Client sends (subscribe):**
```json
{
  "action": "subscribe",
  "symbols": ["NSE:RELIANCE", "NSE:HDFCBANK", "NFO:NIFTY26JAN24000CE"]
}
```

**Client sends (unsubscribe):**
```json
{
  "action": "unsubscribe",
  "symbols": ["NSE:RELIANCE"]
}
```

**Server streams (every tick):**
```json
{
  "type": "quote",
  "data": {
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "ltp": 2955.40,
    "volume": 4521000,
    "day_change_pct": 1.24,
    "ts": "2026-03-29T10:42:33.124Z"
  }
}
```

**Implementation:**
```python
# api/v1/ws/market_feed.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from infrastructure.cache.quote_cache import QuoteCache
from infrastructure.dhan.market_feed import MarketFeedService
import asyncio, json

router = APIRouter()

@router.websocket("/ws/market-feed")
async def market_feed_ws(
    websocket: WebSocket,
    token: str = Query(...),
):
    # Validate JWT
    user = await validate_ws_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    subscribed: set[str] = set()
    push_task: asyncio.Task | None = None

    async def push_quotes():
        """Push latest quotes for subscribed symbols every 500ms."""
        while True:
            if subscribed:
                quotes = await quote_cache.get_bulk(list(subscribed))
                for symbol, q in quotes.items():
                    if q:
                        await websocket.send_json({"type": "quote", "data": {**q, "symbol": symbol}})
            await asyncio.sleep(0.5)

    try:
        push_task = asyncio.create_task(push_quotes())
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            if data["action"] == "subscribe":
                new_symbols = set(data["symbols"])
                subscribed.update(new_symbols)
                # Register with market feed service
                market_feed.subscribe([s.split(":")[1] for s in new_symbols])
            elif data["action"] == "unsubscribe":
                subscribed.difference_update(set(data["symbols"]))
    except WebSocketDisconnect:
        pass
    finally:
        if push_task:
            push_task.cancel()
```

### WS /ws/cockpit

The unified cockpit data feed. Pushes:
- Position updates (on poll changes)
- Signal alerts (on new signal from candle evaluator)
- Risk bar updates (daily P&L, limit consumption)
- CSL trigger alerts
- Order fill notifications
- Token renewal alerts

**Connection:** `WS /ws/cockpit?token=<jwt>`

**Server messages (typed):**

```json
// Position update
{
  "type": "position_update",
  "data": {
    "symbol": "TATASTEEL",
    "unrealized_pnl": 920.0,
    "current_price": 150.35,
    "qty": 500
  }
}

// New intraday signal
{
  "type": "signal_alert",
  "data": {
    "symbol": "HDFCBANK",
    "direction": "LONG",
    "grade": "A",
    "score": 82,
    "interval": "15",
    "entry_price": 1725.0,
    "sl_price": 1700.0,
    "target_price": 1800.0,
    "message": "Grade A LONG setup on 15-min chart"
  }
}

// Risk bar update (sent every 10s)
{
  "type": "risk_bar",
  "data": {
    "daily_loss_limit": 5000.0,
    "consumed_loss": 850.0,
    "utilization_pct": 17.0,
    "realized_pnl": -850.0,
    "unrealized_pnl": 2600.0,
    "net_pnl": 1750.0,
    "can_trade": true
  }
}

// CSL triggered
{
  "type": "csl_alert",
  "severity": "critical",
  "data": {
    "strategy_id": "uuid",
    "strategy_type": "BULL_CALL_SPREAD",
    "combined_pnl": -5050.0,
    "csl_amount": 5000.0,
    "reason": "MONITOR_AUTO",
    "message": "CSL triggered on BULL_CALL_SPREAD — flattening all legs"
  }
}

// Order fill
{
  "type": "order_fill",
  "data": {
    "dhan_order_id": "1234567890",
    "symbol": "TATASTEEL",
    "side": "BUY",
    "filled_qty": 500,
    "fill_price": 148.55,
    "product_type": "INTRADAY"
  }
}
```

**Implementation:**
```python
# api/v1/ws/cockpit_feed.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from collections import defaultdict
import asyncio, json

router = APIRouter()

class CockpitBroadcaster:
    """
    Manages connected cockpit WebSocket clients.
    Application event handlers call broadcast_* methods to push data.
    """
    def __init__(self):
        self._clients: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.append(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.remove(ws)

    async def broadcast(self, message: dict) -> None:
        dead = []
        for client in self._clients:
            try:
                await client.send_json(message)
            except Exception:
                dead.append(client)
        for d in dead:
            await self.disconnect(d)

    async def broadcast_position_update(self, symbol: str, data: dict) -> None:
        await self.broadcast({"type": "position_update", "data": {"symbol": symbol, **data}})

    async def broadcast_signal_alert(self, signal_data: dict) -> None:
        await self.broadcast({"type": "signal_alert", "data": signal_data})

    async def broadcast_csl_alert(self, csl_data: dict) -> None:
        await self.broadcast({"type": "csl_alert", "severity": "critical", "data": csl_data})

    async def broadcast_order_fill(self, order_data: dict) -> None:
        await self.broadcast({"type": "order_fill", "data": order_data})

# App-level singleton, injected via Depends()
cockpit_broadcaster = CockpitBroadcaster()

@router.websocket("/ws/cockpit")
async def cockpit_ws(
    websocket: WebSocket,
    token: str = Query(...),
):
    user = await validate_ws_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    await cockpit_broadcaster.connect(websocket)

    # Send initial state snapshot
    await websocket.send_json({"type": "connected", "data": {"user_id": user.id}})

    try:
        while True:
            # Keep connection alive; frontend sends periodic pings
            msg = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            if msg == "ping":
                await websocket.send_text("pong")
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        await cockpit_broadcaster.disconnect(websocket)
```

---

## Error Response Format

All error responses use RFC 7807 Problem Details format.

```python
# config/errors.py
from fastapi import Request
from fastapi.responses import JSONResponse

async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://trader-cockpit.app/errors/domain-error",
            "title": "Business Rule Violation",
            "status": 422,
            "detail": str(exc),
            "instance": str(request.url),
        }
    )

async def broker_error_handler(request: Request, exc: DhanBrokerError) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "type": "https://trader-cockpit.app/errors/broker-error",
            "title": "Broker API Error",
            "status": 502,
            "detail": str(exc),
            "dhan_code": exc.dhan_code,
            "instance": str(request.url),
        }
    )

async def validation_error_handler(request: Request, exc) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "type": "https://trader-cockpit.app/errors/validation-error",
            "title": "Request Validation Error",
            "status": 422,
            "detail": exc.errors(),
            "instance": str(request.url),
        }
    )
```

**HTTP status code conventions:**

| Status | When |
|---|---|
| 200 OK | Successful GET / command |
| 201 Created | Resource created (order placed, position opened) |
| 400 Bad Request | Malformed request (missing fields, wrong types) |
| 401 Unauthorized | Missing or invalid JWT |
| 422 Unprocessable Entity | Business rule violation (not a validation error) |
| 429 Too Many Requests | Rate limit hit |
| 500 Internal Server Error | Unexpected server error (with correlation ID) |
| 502 Bad Gateway | Dhan API error |
| 503 Service Unavailable | DB or Redis connection failure |

---

## Rate Limiting

Frontend rate limiting prevents hammering the backend and the Dhan API.

```python
# Using slowapi (starlette-compatible rate limiting)
# config/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Applied per-endpoint:
@router.get("/signals/watchlist")
@limiter.limit("30/minute")
async def get_watchlist(request: Request, ...):
    ...

@router.get("/risk/position-size")
@limiter.limit("60/minute")  # Calculator — frequent calls OK
async def get_position_size(request: Request, ...):
    ...

@router.post("/equity/convert")
@limiter.limit("10/minute")  # Mutation — strict limit
async def convert_to_delivery(request: Request, ...):
    ...

@router.post("/orders")
@limiter.limit("30/minute")  # Order placement
async def place_order(request: Request, ...):
    ...
```

**Rate limit headers returned:**
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1711711260
```

**Rate limit exceeded response:**
```json
{
  "type": "https://trader-cockpit.app/errors/rate-limit",
  "title": "Too Many Requests",
  "status": 429,
  "detail": "Rate limit exceeded: 30 requests per minute"
}
```

---

## Request/Response Schema Conventions

1. **All monetary values** — floats in INR (not paise). The API serializes `Decimal` to `float` with 2 decimal places.
2. **All timestamps** — ISO 8601 UTC strings (`2026-03-29T09:15:00Z`). IST conversion is the frontend's responsibility.
3. **Symbol format** in responses — `symbol` and `exchange` as separate fields, not combined.
4. **Enums** — returned as uppercase strings (`"LONG"`, `"BUY"`, `"INTRADAY"`).
5. **Nullable fields** — included in response with `null` (not omitted). Makes frontend null checks consistent.
6. **Pagination** — `GET /orders`, `GET /options/strategies` support `limit` and `offset` query params.
7. **Correlation IDs** — every response includes `X-Correlation-Id` header for log tracing.

---

## Main App Assembly

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from api.v1.market_data.router import router as market_data_router
from api.v1.signals.router import router as signals_router
from api.v1.equity.router import router as equity_router
from api.v1.orders.router import router as orders_router
from api.v1.risk.router import router as risk_router
from api.v1.options.router import router as options_router
from api.v1.portfolio.router import router as portfolio_router
from api.v1.ws.market_feed import router as market_feed_ws_router
from api.v1.ws.cockpit_feed import router as cockpit_ws_router
from config.rate_limit import limiter
from lifespan import app_lifespan

def create_app() -> FastAPI:
    app = FastAPI(
        title="Trader Cockpit API",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=app_lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS — allow only the frontend origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://cockpit.yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST routers
    api_prefix = "/api/v1"
    app.include_router(market_data_router, prefix=api_prefix)
    app.include_router(signals_router,     prefix=api_prefix)
    app.include_router(equity_router,      prefix=api_prefix)
    app.include_router(orders_router,      prefix=api_prefix)
    app.include_router(risk_router,        prefix=api_prefix)
    app.include_router(options_router,     prefix=api_prefix)
    app.include_router(portfolio_router,   prefix=api_prefix)

    # WebSocket routers (no prefix — registered at root)
    app.include_router(market_feed_ws_router)
    app.include_router(cockpit_ws_router)

    return app

app = create_app()
```

```python
# lifespan.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

log = structlog.get_logger(__name__)

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Startup: initialize DB, Redis, DhanClient, WebSocket services, APScheduler.
    Shutdown: gracefully close all connections and stop background tasks.
    """
    log.info("Application starting up")
    from config.database import init_db
    from infrastructure.dhan.client import DhanClient
    from infrastructure.dhan.market_feed import MarketFeedService
    from infrastructure.dhan.order_feed import OrderFeedService
    from infrastructure.dhan.position_poll import PositionPollService
    from infrastructure.jobs.eod_scan import EODScanJob
    from infrastructure.jobs.token_renewal import TokenRenewalJob
    from infrastructure.jobs.csl_monitor import CSLMonitorTask
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    import asyncio

    # 1. DB + Redis
    await init_db()

    # 2. Dhan client + WebSocket services
    dhan_client = DhanClient(...)
    await dhan_client.initialize()

    market_feed = MarketFeedService(...)
    order_feed  = OrderFeedService(...)
    pos_poll    = PositionPollService(...)
    csl_monitor = CSLMonitorTask(...)

    # 3. Background tasks (persistent asyncio Tasks)
    tasks = [
        asyncio.create_task(market_feed.run(),  name="market_feed"),
        asyncio.create_task(order_feed.run(),   name="order_feed"),
        asyncio.create_task(pos_poll.run(),     name="position_poll"),
        asyncio.create_task(csl_monitor.run(),  name="csl_monitor"),
    ]

    # 4. APScheduler (EOD scan, token renewal)
    scheduler = AsyncIOScheduler()
    EODScanJob(...).register()
    TokenRenewalJob(...).register()
    scheduler.start()

    log.info("Application startup complete — all services running")
    yield

    # Shutdown
    log.info("Application shutting down")
    scheduler.shutdown(wait=False)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await market_feed.stop()
    log.info("Application shutdown complete")
```
