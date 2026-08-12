from pydantic import BaseModel


class ReferralCodeOut(BaseModel):
    code: str
    count: int = 0
