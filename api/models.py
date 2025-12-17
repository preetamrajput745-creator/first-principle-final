
from pydantic import BaseModel

class SignalConfirmRequest(BaseModel):
    otp_token: str
