from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from app.domain.entities import SessionType, TimeSession
from app.domain.repositories import ISessionRepository, ISettingsRepository

class TimerService:
  def __init__(self, session_repo: ISessionRepository, settings_repo: ISettingsRepository):
    self.session_repo = session_repo
    self.settings_repo = settings_repo

  async def _get_user_tz(self, user_id: int) -> ZoneInfo:
    settings = await self.settings_repo.get_settings(user_id)
    try:
      return ZoneInfo(settings.timezone)
    except (ZoneInfoNotFoundError, ValueError):
      return ZoneInfo("UTC")

  @staticmethod
  def _next_midnight(moment: datetime, tz: ZoneInfo) -> datetime:
    local_moment = moment.astimezone(tz)
    local_day_start = local_moment.replace(hour=0, minute=0, second=0, microsecond=0)
    return (local_day_start + timedelta(days=1)).astimezone(timezone.utc)

  @classmethod
  def _day_start(cls, moment: datetime, tz: ZoneInfo) -> datetime:
    local_moment = moment.astimezone(tz)
    local_day_start = local_moment.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_day_start.astimezone(timezone.utc)

  @classmethod
  def _split_into_day_segments(cls, start_time: datetime, end_time: datetime, tz: ZoneInfo) -> List[tuple]:
    segments = []
    cursor = start_time
    while True:
      next_midnight = cls._next_midnight(cursor, tz)
      if next_midnight >= end_time:
        segments.append((cursor, end_time))
        break
      segments.append((cursor, next_midnight))
      cursor = next_midnight
    return segments

  async def _split_overnight_active_session(self, user_id: int) -> None:
    active = await self.session_repo.get_active_session(user_id)
    if not active:
      return
    tz = await self._get_user_tz(user_id)
    while active:
      now = datetime.now(timezone.utc)
      next_midnight = self._next_midnight(active.start_time, tz)
      if next_midnight > now:
        break
      active.end_time = next_midnight
      await self.session_repo.update(active)
      new_session = TimeSession(
        id=None,
        user_id=user_id,
        session_type=active.session_type,
        start_time=next_midnight
      )
      active = await self.session_repo.create(new_session)

  async def start_session(self, user_id: int, session_type: SessionType) -> TimeSession:
    await self._split_overnight_active_session(user_id)
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
    await self._split_overnight_active_session(user_id)
    active = await self.session_repo.get_active_session(user_id)
    if not active:
      return None
    active.end_time = datetime.now(timezone.utc)
    return await self.session_repo.update(active)

  async def get_status(self, user_id: int) -> Optional[TimeSession]:
    await self._split_overnight_active_session(user_id)
    return await self.session_repo.get_active_session(user_id)

  async def get_history(self, user_id: int) -> List[TimeSession]:
    await self._split_overnight_active_session(user_id)
    return await self.session_repo.get_user_sessions(user_id)

  async def get_today_summary(self, user_id: int) -> Dict[str, Union[int, Optional[datetime]]]:
    await self._split_overnight_active_session(user_id)
    tz = await self._get_user_tz(user_id)
    now = datetime.now(timezone.utc)
    day_start = self._day_start(now, tz)
    sessions = await self.session_repo.get_user_sessions(user_id)
    work_seconds = 0
    break_seconds = 0
    day_start_time: Optional[datetime] = None
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
      if day_start_time is None or effective_start < day_start_time:
        day_start_time = effective_start
    return {
      "work_seconds": work_seconds,
      "break_seconds": break_seconds,
      "total_seconds": work_seconds + break_seconds,
      "day_start_time": day_start_time
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
    tz = await self._get_user_tz(user_id)
    segments = self._split_into_day_segments(start_time, end_time, tz)
    first_session: Optional[TimeSession] = None
    for seg_start, seg_end in segments:
      created = await self.session_repo.create(TimeSession(
        id=None,
        user_id=user_id,
        session_type=session_type,
        start_time=seg_start,
        end_time=seg_end
      ))
      if first_session is None:
        first_session = created
    return first_session

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
    if session.end_time is None:
      return await self.session_repo.update(session)
    tz = await self._get_user_tz(user_id)
    segments = self._split_into_day_segments(session.start_time, session.end_time, tz)
    seg_start, seg_end = segments[0]
    session.start_time = seg_start
    session.end_time = seg_end
    updated = await self.session_repo.update(session)
    for seg_start, seg_end in segments[1:]:
      await self.session_repo.create(TimeSession(
        id=None,
        user_id=user_id,
        session_type=updated.session_type,
        start_time=seg_start,
        end_time=seg_end
      ))
    return updated

  async def delete_session(self, user_id: int, session_id: int) -> None:
    session = await self.session_repo.get_by_id(session_id)
    if not session or session.user_id != user_id:
      raise ValueError("Session not found")
    await self.session_repo.delete(session_id)
