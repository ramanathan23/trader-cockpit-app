from pydantic import BaseModel


class TokenUpdate(BaseModel):
    access_token: str
