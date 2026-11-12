from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities import TimeSession, User

class IUserRepository(ABC):
  @abstractmethod
  async def get_by_username(self, username: str) -> Optional[User]:
    pass

  @abstractmethod
  async def create(self, user: User) -> User:
    pass

class ISessionRepository(ABC):
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
  async def get_user_sessions(self, user_id: int) -> List[TimeSession]:
    pass