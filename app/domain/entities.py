from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class SessionType(str, Enum):
  WORK = "WORK"
  BREAK = "BREAK"

@dataclass
class User:
  id: Optional[int]
  username: str
  hashed_password: str

@dataclass
class TimeSession:
  id: Optional[int]
  user_id: int
  session_type: SessionType
  start_time: datetime
  end_time: Optional[datetime] = None