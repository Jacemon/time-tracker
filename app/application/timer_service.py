from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.domain.entities import SessionType, TimeSession
from app.domain.repositories import ISessionRepository

class TimerService:
  def __init__(self, session_repo: ISessionRepository):
    self.session_repo = session_repo

  async def start_session(self, user_id: int, session_type: SessionType) -> TimeSession:
    now = datetime.now(timezone.utc)
    active = await self.session_repo.get_active_session(user_id)
    if active:
      if active.session_type == session_type:
        return active
      active.end_time = now
      await self.session_repo.update(active)
    new_session = TimeSession(
      id=None,
      user_id=user_id,
      session_type=session_type,
      start_time=now
    )
    return await self.session_repo.create(new_session)

  async def stop_timer(self, user_id: int) -> Optional[TimeSession]:
    active = await self.session_repo.get_active_session(user_id)
    if not active:
      return None
    active.end_time = datetime.now(timezone.utc)
    return await self.session_repo.update(active)

  async def get_status(self, user_id: int) -> Optional[TimeSession]:
    return await self.session_repo.get_active_session(user_id)

  async def get_history(self, user_id: int) -> List[TimeSession]:
    return await self.session_repo.get_user_sessions(user_id)

  async def get_today_summary(self, user_id: int) -> Dict[str, int]:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sessions = await self.session_repo.get_user_sessions(user_id)
    work_seconds = 0
    break_seconds = 0
    for s in sessions:
      end = s.end_time if s.end_time else now
      if end <= day_start:
        continue
      effective_start = max(s.start_time, day_start)
      duration = int((end - effective_start).total_seconds())
      if duration > 0:
        if s.session_type == SessionType.WORK:
          work_seconds += duration
        elif s.session_type == SessionType.BREAK:
          break_seconds += duration
    return {
      "work_seconds": work_seconds,
      "break_seconds": break_seconds,
      "total_seconds": work_seconds + break_seconds
    }

  async def create_manual_session(
    self,
    user_id: int,
    session_type: SessionType,
    start_time: datetime,
    end_time: datetime
  ) -> TimeSession:
    if end_time <= start_time:
      raise ValueError("End time must be after start time")
    new_session = TimeSession(
      id=None,
      user_id=user_id,
      session_type=session_type,
      start_time=start_time,
      end_time=end_time
    )
    return await self.session_repo.create(new_session)

  async def update_session(
    self,
    user_id: int,
    session_id: int,
    session_type: Optional[SessionType] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
  ) -> TimeSession:
    session = await self.session_repo.get_by_id(session_id)
    if not session or session.user_id != user_id:
      raise ValueError("Session not found")
    if session_type is not None:
      session.session_type = session_type
    if start_time is not None:
      session.start_time = start_time
    if end_time is not None:
      session.end_time = end_time
    if session.end_time and session.end_time < session.start_time:
      raise ValueError("End time cannot be before start time")
    return await self.session_repo.update(session)

  async def delete_session(self, user_id: int, session_id: int) -> None:
    session = await self.session_repo.get_by_id(session_id)
    if not session or session.user_id != user_id:
      raise ValueError("Session not found")
    await self.session_repo.delete(session_id)