# 08 — Paper Mode

Full cockpit simulation using real market data with order execution in PostgreSQL. Same code path as live trading.

---

## What Paper Mode Is

Paper mode replaces only the `IOrderBrokerPort` implementation with `PaperOrderBrokerAdapter`. Everything else — domain logic, signal engine, risk engine, candle aggregation, EOD scan — runs identically.

| Component | Live Mode | Paper Mode |
|-----------|-----------|-----------|
| Market data | Dhan WebSocket | Dhan WebSocket (same) |
| Signal engine | Domain logic | Identical |
| Risk engine | Domain logic | Identical |
| Order execution | DhanOrderBrokerAdapter | PaperOrderBrokerAdapter |
| Position storage | Dhan API + PostgreSQL | PostgreSQL only |
| Fill simulation | Exchange | PaperFillMonitor (tick-based) |
| State persistence | PostgreSQL | PostgreSQL (paper_* tables) |

> Paper mode does NOT use in-memory state. All orders, fills, and positions are persisted so analytics and session recovery work identically to live.

---

## PostgreSQL Schema

### paper_accounts
```sql
CREATE TABLE paper_accounts (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name              VARCHAR(100) NOT NULL,
    starting_capital  NUMERIC(15,2) NOT NULL,
    current_cash      NUMERIC(15,2) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active         BOOLEAN     NOT NULL DEFAULT true
);
```

### paper_orders
```sql
CREATE TABLE paper_orders (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id       UUID         NOT NULL REFERENCES paper_accounts(id),
    client_order_id  VARCHAR(50)  UNIQUE NOT NULL,
    symbol           VARCHAR(30)  NOT NULL,
    exchange         VARCHAR(10)  NOT NULL,
    side             VARCHAR(4)   NOT NULL CHECK (side IN ('BUY','SELL')),
    order_type       VARCHAR(10)  NOT NULL CHECK (order_type IN ('MARKET','LIMIT','SL','SL-M')),
    product_type     VARCHAR(10)  NOT NULL CHECK (product_type IN ('INTRADAY','CNC','MARGIN')),
    qty              INTEGER      NOT NULL,
    limit_price      NUMERIC(12,4),
    trigger_price    NUMERIC(12,4),
    status           VARCHAR(20)  NOT NULL DEFAULT 'PENDING'
                       CHECK (status IN ('PENDING','FILLED','PARTIALLY_FILLED','CANCELLED','REJECTED')),
    filled_qty       INTEGER      NOT NULL DEFAULT 0,
    avg_fill_price   NUMERIC(12,4),
    placed_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    filled_at        TIMESTAMPTZ,
    cancelled_at     TIMESTAMPTZ,
    reject_reason    TEXT
);

CREATE INDEX idx_paper_orders_pending
    ON paper_orders (account_id, status)
    WHERE status = 'PENDING';
```

### paper_positions
```sql
CREATE TABLE paper_positions (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id       UUID         NOT NULL REFERENCES paper_accounts(id),
    symbol           VARCHAR(30)  NOT NULL,
    exchange         VARCHAR(10)  NOT NULL,
    product_type     VARCHAR(10)  NOT NULL,
    qty              INTEGER      NOT NULL,          -- positive=long, negative=short
    avg_price        NUMERIC(12,4) NOT NULL,
    last_price       NUMERIC(12,4),
    realised_pnl     NUMERIC(15,2) NOT NULL DEFAULT 0,
    unrealised_pnl   NUMERIC(15,2) NOT NULL DEFAULT 0,
    day_buy_qty      INTEGER      NOT NULL DEFAULT 0,
    day_sell_qty     INTEGER      NOT NULL DEFAULT 0,
    opened_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (account_id, symbol, product_type)
);
```

### paper_fills
```sql
CREATE TABLE paper_fills (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id     UUID         NOT NULL REFERENCES paper_orders(id),
    account_id   UUID         NOT NULL REFERENCES paper_accounts(id),
    symbol       VARCHAR(30)  NOT NULL,
    side         VARCHAR(4)   NOT NULL,
    qty          INTEGER      NOT NULL,
    fill_price   NUMERIC(12,4) NOT NULL,
    fill_time    TIMESTAMPTZ  NOT NULL,
    triggered_by VARCHAR(20)  NOT NULL
                   CHECK (triggered_by IN ('TICK_PRICE','MARKET','SL_TRIGGER','AUTO_SQUARE_OFF'))
);
```

### paper_sl_monitors
```sql
CREATE TABLE paper_sl_monitors (
    id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id       UUID         NOT NULL REFERENCES paper_orders(id),
    account_id     UUID         NOT NULL REFERENCES paper_accounts(id),
    symbol         VARCHAR(30)  NOT NULL,
    trigger_price  NUMERIC(12,4) NOT NULL,
    side           VARCHAR(4)   NOT NULL,    -- BUY (close short) | SELL (close long)
    qty            INTEGER      NOT NULL,
    is_active      BOOLEAN      NOT NULL DEFAULT true,
    triggered_at   TIMESTAMPTZ
);

CREATE INDEX idx_paper_sl_monitors_active
    ON paper_sl_monitors (symbol, is_active)
    WHERE is_active = true;
```

### paper_conversions
```sql
CREATE TABLE paper_conversions (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id        UUID         NOT NULL REFERENCES paper_accounts(id),
    symbol            VARCHAR(30)  NOT NULL,
    from_product_type VARCHAR(10)  NOT NULL,
    to_product_type   VARCHAR(10)  NOT NULL,
    qty               INTEGER      NOT NULL,
    avg_price         NUMERIC(12,4) NOT NULL,
    converted_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

---

## PaperFillMonitor — Fill Simulation Engine

Runs as a background task. Subscribes to real ticks (same subscription as live candle aggregator). On each tick, checks pending orders and active SL monitors for that symbol.

```python
class PaperFillMonitor:
    """
    Simulates order fills from real tick stream.
    Registered as a tick handler in the market data subscription.
    """

    def __init__(
        self,
        repo: PaperOrderRepository,
        account_id: UUID,
        event_bus: EventBus,
    ) -> None:
        self._repo = repo
        self._account_id = account_id
        self._event_bus = event_bus

    async def on_tick(self, tick: Tick) -> None:
        # Check pending orders
        pending = await self._repo.get_pending_orders(
            account_id=self._account_id, symbol=tick.symbol
        )
        for order in pending:
            if self._should_fill(order, tick):
                price = self._fill_price(order, tick)
                await self._execute_fill(order, tick, fill_price=price)

        # Check SL monitors
        active_sls = await self._repo.get_active_sl_monitors(
            account_id=self._account_id, symbol=tick.symbol
        )
        for sl in active_sls:
            if self._sl_triggered(sl, tick):
                await self._trigger_sl_fill(sl, tick)

    def _should_fill(self, order: PaperOrder, tick: Tick) -> bool:
        match order.order_type:
            case "MARKET":
                return True
            case "LIMIT":
                if order.side == "BUY":
                    return tick.price <= order.limit_price
                return tick.price >= order.limit_price
            case "SL" | "SL-M":
                if order.side == "BUY":
                    return tick.price >= order.trigger_price
                return tick.price <= order.trigger_price
        return False

    def _fill_price(self, order: PaperOrder, tick: Tick) -> Decimal:
        """Conservative fill — no price improvement."""
        match order.order_type:
            case "MARKET" | "SL-M":
                return tick.price
            case "LIMIT":
                return order.limit_price
            case "SL":
                return order.trigger_price
        return tick.price

    def _sl_triggered(self, sl: PaperSLMonitor, tick: Tick) -> bool:
        if sl.side == "SELL":   # stop for long position
            return tick.price <= sl.trigger_price
        return tick.price >= sl.trigger_price   # stop for short

    async def _execute_fill(
        self, order: PaperOrder, tick: Tick, fill_price: Decimal
    ) -> None:
        async with self._repo.transaction():
            # Record fill
            fill = PaperFill(
                order_id=order.id,
                account_id=self._account_id,
                symbol=order.symbol,
                side=order.side,
                qty=order.qty,
                fill_price=fill_price,
                fill_time=tick.timestamp,
                triggered_by="MARKET" if order.order_type == "MARKET" else "TICK_PRICE",
            )
            await self._repo.insert_fill(fill)

            # Update order status
            await self._repo.update_order_filled(
                order_id=order.id,
                avg_fill_price=fill_price,
                filled_at=tick.timestamp,
            )

            # Update position (FIFO P&L)
            await self._update_position(order, fill_price, tick.timestamp)

        # Publish to cockpit event bus → triggers POSITION_UPDATE on WS
        await self._event_bus.publish(PaperFillEvent(
            account_id=self._account_id,
            symbol=order.symbol,
            side=order.side,
            qty=order.qty,
            fill_price=fill_price,
        ))
```

---

## Position Update — FIFO P&L

```python
async def _update_position(
    self, order: PaperOrder, fill_price: Decimal, ts: datetime
) -> None:
    pos = await self._repo.get_position(
        self._account_id, order.symbol, order.product_type
    )

    if pos is None:
        # Opening new position
        await self._repo.insert_position(PaperPosition(
            account_id=self._account_id,
            symbol=order.symbol,
            product_type=order.product_type,
            qty=order.qty if order.side == "BUY" else -order.qty,
            avg_price=fill_price,
        ))
        return

    if order.side == "BUY":
        new_qty = pos.qty + order.qty
        if pos.qty >= 0:
            # Adding to long — weighted avg
            new_avg = (pos.avg_price * pos.qty + fill_price * order.qty) / new_qty
        else:
            # Covering short — realise P&L on covered qty
            covered = min(abs(pos.qty), order.qty)
            realised = (pos.avg_price - fill_price) * covered
            new_avg = fill_price if new_qty > 0 else pos.avg_price
            pos.realised_pnl += realised
    else:  # SELL
        new_qty = pos.qty - order.qty
        if pos.qty > 0:
            # Reducing long — realise P&L
            sold = min(pos.qty, order.qty)
            realised = (fill_price - pos.avg_price) * sold
            pos.realised_pnl += realised
            new_avg = pos.avg_price
        else:
            # Adding to short
            new_avg = (pos.avg_price * abs(pos.qty) + fill_price * order.qty) / abs(new_qty)

    await self._repo.update_position(
        position_id=pos.id,
        qty=new_qty,
        avg_price=new_avg,
        realised_pnl=pos.realised_pnl,
        updated_at=ts,
    )
```

---

## Auto Square-Off at 3:20 PM

Mimics Dhan INTRADAY auto square-off. Scheduled by the market session job.

```python
async def auto_square_off_paper_intraday(
    account_id: UUID,
    repo: PaperOrderRepository,
    adapter: PaperOrderBrokerAdapter,
) -> None:
    positions = await repo.get_positions(account_id, product_type="INTRADAY")
    for pos in positions:
        if pos.qty == 0:
            continue
        side = "SELL" if pos.qty > 0 else "BUY"
        await adapter.place_order(PlaceOrderCommand(
            symbol=Symbol(pos.symbol),
            side=Side(side),
            qty=abs(pos.qty),
            order_type=OrderType.MARKET,
            product_type=ProductType.INTRADAY,
            note="AUTO_SQUARE_OFF_3_20PM",
        ))
```

---

## Unrealised P&L Updates

Every tick for open positions updates `unrealised_pnl` in paper_positions. Batched per symbol, not per tick:

```python
async def update_unrealised_pnl(self, tick: Tick) -> None:
    positions = await self._repo.get_positions_by_symbol(
        self._account_id, tick.symbol
    )
    for pos in positions:
        if pos.qty == 0:
            continue
        unrealised = (tick.price - pos.avg_price) * pos.qty
        await self._repo.update_unrealised_pnl(
            position_id=pos.id,
            last_price=tick.price,
            unrealised_pnl=unrealised,
        )
```

---

## Paper vs Live Analytics

```sql
-- 30-day performance comparison
SELECT
    'live'  AS mode,
    COUNT(*) AS trades,
    ROUND(AVG(realised_pnl), 2) AS avg_pnl,
    ROUND(SUM(realised_pnl), 2) AS total_pnl,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE realised_pnl > 0) / NULLIF(COUNT(*), 0),
        1
    ) AS win_rate_pct
FROM trade_journal
WHERE closed_at >= CURRENT_DATE - INTERVAL '30 days'

UNION ALL

SELECT
    'paper' AS mode,
    COUNT(DISTINCT f.id) AS trades,
    ROUND(AVG(pp.realised_pnl), 2) AS avg_pnl,
    ROUND(SUM(pp.realised_pnl), 2) AS total_pnl,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE pp.realised_pnl > 0) / NULLIF(COUNT(*), 0),
        1
    ) AS win_rate_pct
FROM paper_fills f
JOIN paper_orders o  ON f.order_id = o.id
JOIN paper_positions pp ON pp.account_id = o.account_id AND pp.symbol = o.symbol
WHERE o.account_id = :paper_account_id
  AND f.fill_time >= CURRENT_DATE - INTERVAL '30 days'
  AND o.side = 'SELL';
```

---

## UI Indicators

| Location | Paper Mode Indicator |
|----------|---------------------|
| Risk bar | `[PAPER]` badge — amber, always visible |
| Order confirm dialog | No countdown; immediate fill on next tick |
| Positions strip | Italic row style; `PAPER` tag in product column |
| Analytics page | Toggle: Live / Paper / Side-by-side |

---

## Switching Modes

```bash
# .env
ACTIVE_ORDER_BROKER=paper
PAPER_STARTING_CAPITAL=1000000
```

No code change. No restart required if using dynamic settings. The DI container resolves `IOrderBrokerPort` to `PaperOrderBrokerAdapter` at request time.

```
ACTIVE_ORDER_BROKER=dhan   → DhanOrderBrokerAdapter
ACTIVE_ORDER_BROKER=paper  → PaperOrderBrokerAdapter
```

Market data is always real (Dhan WebSocket) in both modes. Paper mode only simulates fills.
