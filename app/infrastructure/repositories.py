from typing import List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import DailyNorm, TimeSession, User, UserSettings
from app.domain.repositories import ISessionRepository, ISettingsRepository, IUserRepository
from app.infrastructure.models import DailyNormModel, TimeSessionModel, UserModel, UserSettingsModel

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

  async def get_by_id(self, session_id: int) -> Optional[TimeSession]:
    result = await self.db.execute(select(TimeSessionModel).where(TimeSessionModel.id == session_id))
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
    model.session_type = session.session_type
    model.start_time = session.start_time
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

  async def delete(self, session_id: int) -> None:
    await self.db.execute(delete(TimeSessionModel).where(TimeSessionModel.id == session_id))
    await self.db.commit()

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

class PostgresSettingsRepository(ISettingsRepository):
  def __init__(self, db: AsyncSession):
    self.db = db

  async def get_settings(self, user_id: int) -> UserSettings:
    result = await self.db.execute(select(UserSettingsModel).where(UserSettingsModel.user_id == user_id))
    model = result.scalar_one_or_none()
    if not model:
      return UserSettings(user_id=user_id)
    return UserSettings(
      user_id=model.user_id,
      default_work_minutes=model.default_work_minutes,
      default_break_minutes=model.default_break_minutes,
      weekend_days=model.weekend_days,
      timezone=model.timezone,
      timezone_auto=model.timezone_auto
    )

  async def save_settings(self, settings: UserSettings) -> UserSettings:
    result = await self.db.execute(select(UserSettingsModel).where(UserSettingsModel.user_id == settings.user_id))
    model = result.scalar_one_or_none()
    if not model:
      model = UserSettingsModel(
        user_id=settings.user_id,
        default_work_minutes=settings.default_work_minutes,
        default_break_minutes=settings.default_break_minutes,
        weekend_days=settings.weekend_days,
        timezone=settings.timezone,
        timezone_auto=settings.timezone_auto
      )
      self.db.add(model)
    else:
      model.default_work_minutes = settings.default_work_minutes
      model.default_break_minutes = settings.default_break_minutes
      model.weekend_days = settings.weekend_days
      model.timezone = settings.timezone
      model.timezone_auto = settings.timezone_auto
    await self.db.commit()
    await self.db.refresh(model)
    return UserSettings(
      user_id=model.user_id,
      default_work_minutes=model.default_work_minutes,
      default_break_minutes=model.default_break_minutes,
      weekend_days=model.weekend_days,
      timezone=model.timezone,
      timezone_auto=model.timezone_auto
    )

  async def get_daily_norms(self, user_id: int) -> List[DailyNorm]:
    result = await self.db.execute(select(DailyNormModel).where(DailyNormModel.user_id == user_id))
    models = result.scalars().all()
    return [
      DailyNorm(
        id=m.id,
        user_id=m.user_id,
        date_str=m.date_str,
        work_minutes=m.work_minutes,
        break_minutes=m.break_minutes
      )
      for m in models
    ]

  async def save_daily_norm(self, norm: DailyNorm) -> DailyNorm:
    query = select(DailyNormModel).where(
      DailyNormModel.user_id == norm.user_id,
      DailyNormModel.date_str == norm.date_str
    )
    result = await self.db.execute(query)
    model = result.scalar_one_or_none()
    if not model:
      model = DailyNormModel(
        user_id=norm.user_id,
        date_str=norm.date_str,
        work_minutes=norm.work_minutes,
        break_minutes=norm.break_minutes
      )
      self.db.add(model)
    else:
      model.work_minutes = norm.work_minutes
      model.break_minutes = norm.break_minutes
    await self.db.commit()
    await self.db.refresh(model)
    return DailyNorm(
      id=model.id,
      user_id=model.user_id,
      date_str=model.date_str,
      work_minutes=model.work_minutes,
      break_minutes=model.break_minutes
    )