from copy import deepcopy
from typing import Dict, List, Optional
from app.domain.entities import DailyNorm, TimeSession, User, UserSettings
from app.domain.repositories import ISessionRepository, ISettingsRepository, IUserRepository


class FakeUserRepository(IUserRepository):
  def __init__(self, users: Optional[List[User]] = None):
    self._users: Dict[int, User] = {}
    self._next_id = 1
    for u in users or []:
      item = deepcopy(u)
      if item.id is None:
        item.id = self._next_id
      self._next_id = max(self._next_id, item.id + 1)
      self._users[item.id] = item

  async def get_by_username(self, username: str) -> Optional[User]:
    for u in self._users.values():
      if u.username == username:
        return deepcopy(u)
    return None

  async def create(self, user: User) -> User:
    item = deepcopy(user)
    item.id = self._next_id
    self._next_id += 1
    self._users[item.id] = item
    return deepcopy(item)


class FakeSessionRepository(ISessionRepository):
  def __init__(self, sessions: Optional[List[TimeSession]] = None):
    self._sessions: Dict[int, TimeSession] = {}
    self._next_id = 1
    for s in sessions or []:
      item = deepcopy(s)
      if item.id is None:
        item.id = self._next_id
      self._next_id = max(self._next_id, item.id + 1)
      self._sessions[item.id] = item

  async def get_by_id(self, session_id: int) -> Optional[TimeSession]:
    item = self._sessions.get(session_id)
    return deepcopy(item) if item else None

  async def get_active_session(self, user_id: int) -> Optional[TimeSession]:
    active = await self.get_active_sessions(user_id)
    return active[0] if active else None

  async def get_active_sessions(self, user_id: int) -> List[TimeSession]:
    items = [
      deepcopy(s)
      for s in self._sessions.values()
      if s.user_id == user_id and s.end_time is None
    ]
    items.sort(key=lambda s: (s.start_time, s.id or 0), reverse=True)
    return items

  async def create(self, session: TimeSession) -> TimeSession:
    item = deepcopy(session)
    item.id = self._next_id
    self._next_id += 1
    self._sessions[item.id] = item
    return deepcopy(item)

  async def update(self, session: TimeSession) -> TimeSession:
    if session.id is None or session.id not in self._sessions:
      raise KeyError(f"Session {session.id} not found")
    item = deepcopy(session)
    self._sessions[item.id] = item
    return deepcopy(item)

  async def delete(self, session_id: int) -> None:
    self._sessions.pop(session_id, None)

  async def get_user_sessions(self, user_id: int) -> List[TimeSession]:
    items = [deepcopy(s) for s in self._sessions.values() if s.user_id == user_id]
    items.sort(key=lambda s: s.start_time, reverse=True)
    return items


class FakeSettingsRepository(ISettingsRepository):
  def __init__(
    self,
    settings_by_user: Optional[Dict[int, UserSettings]] = None,
    norms: Optional[List[DailyNorm]] = None
  ):
    self._settings: Dict[int, UserSettings] = {
      uid: deepcopy(cfg) for uid, cfg in (settings_by_user or {}).items()
    }
    self._norms: Dict[int, DailyNorm] = {}
    self._next_norm_id = 1
    for n in norms or []:
      item = deepcopy(n)
      if item.id is None:
        item.id = self._next_norm_id
      self._next_norm_id = max(self._next_norm_id, item.id + 1)
      self._norms[item.id] = item

  async def get_settings(self, user_id: int) -> UserSettings:
    if user_id not in self._settings:
      self.self_create(user_id)
    return deepcopy(self._settings[user_id])

  def self_create(self, user_id: int) -> None:
    self._settings[user_id] = UserSettings(user_id=user_id)

  async def save_settings(self, settings: UserSettings) -> UserSettings:
    self._settings[settings.user_id] = deepcopy(settings)
    return deepcopy(self._settings[settings.user_id])

  async def get_daily_norms(self, user_id: int) -> List[DailyNorm]:
    return [deepcopy(n) for n in self._norms.values() if n.user_id == user_id]

  async def save_daily_norm(self, norm: DailyNorm) -> DailyNorm:
    existing_id: Optional[int] = None
    for norm_id, existing in self._norms.items():
      if existing.user_id == norm.user_id and existing.date_str == norm.date_str:
        existing_id = norm_id
        break
    item = deepcopy(norm)
    if existing_id is not None:
      item.id = existing_id
      self._norms[existing_id] = item
    else:
      item.id = self._next_norm_id
      self._next_norm_id += 1
      self._norms[item.id] = item
    return deepcopy(item)