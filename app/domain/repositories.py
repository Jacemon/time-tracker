from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities import DailyNorm, TimeSession, User, UserSettings

class IUserRepository(ABC):
  @abstractmethod
  async def get_by_username(self, username: str) -> Optional[User]:
    pass

  @abstractmethod
  async def create(self, user: User) -> User:
    pass

class ISessionRepository(ABC):
  @abstractmethod
  async def get_by_id(self, session_id: int) -> Optional[TimeSession]:
    pass

  @abstractmethod
  async def get_active_session(self, user_id: int) -> Optional[TimeSession]:
    pass

  @abstractmethod
  async def create(self, session: TimeSession) -> TimeSession:
    pass

  @abstractmethod
  async def update(self, session: TimeSession) -> TimeSession:
    pass

  @abstractmethod
  async def delete(self, session_id: int) -> None:
    pass

  @abstractmethod
  async def get_user_sessions(self, user_id: int) -> List[TimeSession]:
    pass

class ISettingsRepository(ABC):
  @abstractmethod
  async def get_settings(self, user_id: int) -> UserSettings:
    pass

  @abstractmethod
  async def save_settings(self, settings: UserSettings) -> UserSettings:
    pass

  @abstractmethod
  async def get_daily_norms(self, user_id: int) -> List[DailyNorm]:
    pass

  @abstractmethod
  async def save_daily_norm(self, norm: DailyNorm) -> DailyNorm:
    pass