from pydantic import BaseModel


class OptionChainRequest(BaseModel):
    symbol: str
    expiry: str | None = None
