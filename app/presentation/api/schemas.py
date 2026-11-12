from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.domain.entities import SessionType

class UserAuthRequest(BaseModel):
  username: str
  password: str

class TokenResponse(BaseModel):
  access_token: str
  token_type: str = "bearer"

class SessionResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)
  id: int
  session_type: SessionType
  start_time: datetime
  end_time: Optional[datetime] = None

class StatusResponse(BaseModel):
  active_session: Optional[SessionResponse] = None

class SummaryResponse(BaseModel):
  work_seconds: int
  break_seconds: int
  total_seconds: int