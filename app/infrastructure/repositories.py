from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import TimeSession, User
from app.domain.repositories import ISessionRepository, IUserRepository
from app.infrastructure.models import TimeSessionModel, UserModel

class PostgresUserRepository(IUserRepository):
  def __init__(self, db: AsyncSession):
    self.db = db

  async def get_by_username(self, username: str) -> Optional[User]:
    result = await self.db.execute(select(UserModel).where(UserModel.username == username))
    model = result.scalar_one_or_none()
    if not model:
      return None
    return User(id=model.id, username=model.username, hashed_password=model.hashed_password)

  async def create(self, user: User) -> User:
    model = UserModel(username=user.username, hashed_password=user.hashed_password)
    self.db.add(model)
    await self.db.commit()
    await self.db.refresh(model)
    return User(id=model.id, username=model.username, hashed_password=model.hashed_password)

class PostgresSessionRepository(ISessionRepository):
  def __init__(self, db: AsyncSession):
    self.db = db

  async def get_active_session(self, user_id: int) -> Optional[TimeSession]:
    query = select(TimeSessionModel).where(
      TimeSessionModel.user_id == user_id,
      TimeSessionModel.end_time.is_(None)
    )
    result = await self.db.execute(query)
    model = result.scalar_one_or_none()
    if not model:
      return None
    return TimeSession(
      id=model.id,
      user_id=model.user_id,
      session_type=model.session_type,
      start_time=model.start_time,
      end_time=model.end_time
    )

  async def create(self, session: TimeSession) -> TimeSession:
    model = TimeSessionModel(
      user_id=session.user_id,
      session_type=session.session_type,
      start_time=session.start_time,
      end_time=session.end_time
    )
    self.db.add(model)
    await self.db.commit()
    await self.db.refresh(model)
    return TimeSession(
      id=model.id,
      user_id=model.user_id,
      session_type=model.session_type,
      start_time=model.start_time,
      end_time=model.end_time
    )

  async def update(self, session: TimeSession) -> TimeSession:
    result = await self.db.execute(select(TimeSessionModel).where(TimeSessionModel.id == session.id))
    model = result.scalar_one()
    model.end_time = session.end_time
    await self.db.commit()
    await self.db.refresh(model)
    return TimeSession(
      id=model.id,
      user_id=model.user_id,
      session_type=model.session_type,
      start_time=model.start_time,
      end_time=model.end_time
    )

  async def get_user_sessions(self, user_id: int) -> List[TimeSession]:
    query = select(TimeSessionModel).where(TimeSessionModel.user_id == user_id).order_by(TimeSessionModel.start_time.desc())
    result = await self.db.execute(query)
    models = result.scalars().all()
    return [
      TimeSession(
        id=m.id,
        user_id=m.user_id,
        session_type=m.session_type,
        start_time=m.start_time,
        end_time=m.end_time
      )
      for m in models
    ]