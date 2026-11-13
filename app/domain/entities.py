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

@dataclass
class UserSettings:
  user_id: int
  default_work_minutes: int = 480
  default_break_minutes: int = 40
  weekend_days: str = "5,6"
  timezone: str = "UTC"

@dataclass
class DailyNorm:
  id: Optional[int]
  user_id: int
  date_str: str
  work_minutes: int
  break_minutes: int