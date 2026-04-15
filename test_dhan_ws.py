"""
Quick smoke test: connect to Dhan WebSocket and print the first few ticks.

Instruments used (NSE cash):
  - 1333  HDFC Bank
  - 11536 TCS
  - 3045  Infosys

Run:
    python test_dhan_ws.py
"""

import asyncio
import logging
from dotenv import dotenv_values
from dhanhq import marketfeed as mf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger(__name__)

MAX_TICKS   = 10     # stop after this many ticks
TIMEOUT_S   = 30     # give up if no ticks arrive within this many seconds

cfg = dotenv_values("D:/Apps Workspace/trader-cockpit-app/.env")
CLIENT_ID    = cfg["DHAN_CLIENT_ID"]
ACCESS_TOKEN = cfg["DHAN_ACCESS_TOKEN"]

# (exchange_segment, security_id, subscription_type)
INSTRUMENTS = [
    (mf.NSE, "1333",  mf.Ticker),   # HDFC Bank
    (mf.NSE, "11536", mf.Ticker),   # TCS
    (mf.NSE, "3045",  mf.Ticker),   # Infosys
]


async def main() -> None:
    logger.info("Client ID : %s", CLIENT_ID)
    logger.info("Token     : %s…", ACCESS_TOKEN[:40])
    logger.info("Connecting to Dhan WebSocket…")

    feed = mf.DhanFeed(
        client_id=CLIENT_ID,
        access_token=ACCESS_TOKEN,
        instruments=INSTRUMENTS,
        version="v2",
    )

    await feed.connect()
    logger.info("Connected — waiting for ticks (max %d, timeout %ds)…",
                MAX_TICKS, TIMEOUT_S)

    received = 0
    deadline = asyncio.get_event_loop().time() + TIMEOUT_S

    while received < MAX_TICKS:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            logger.warning("Timeout reached — no more ticks.")
            break
        try:
            data = await asyncio.wait_for(feed.get_instrument_data(), timeout=remaining)
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for tick.")
            break

        if data:
            received += 1
            logger.info("[tick %d] %s", received, data)

    logger.info("Done — received %d tick(s).", received)


if __name__ == "__main__":
    asyncio.run(main())
