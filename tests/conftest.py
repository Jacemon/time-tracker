import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from datetime import datetime, timezone
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.domain.entities import SessionType, TimeSession, UserSettings
from app.infrastructure.models import Base
from tests.fakes import FakeSessionRepository, FakeSettingsRepository


@pytest_asyncio.fixture
async def db_session():
  db_url = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
  engine = create_async_engine(db_url)
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
  session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
  async with session_factory() as session:
    yield session
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.drop_all)
  await engine.dispose()


@pytest.fixture
def fixed_now() -> datetime:
  return datetime(2026, 11, 27, 15, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def default_settings() -> UserSettings:
  return UserSettings(
    user_id=1,
    default_work_minutes=480,
    default_break_minutes=40,
    weekend_days="5,6",
    timezone="Europe/Berlin",
    timezone_auto=False
  )


@pytest.fixture
def session_repo() -> FakeSessionRepository:
  return FakeSessionRepository()


@pytest.fixture
def settings_repo(default_settings: UserSettings) -> FakeSettingsRepository:
  return FakeSettingsRepository(settings_by_user={1: default_settings})


@pytest.fixture
def sample_work_session(fixed_now: datetime) -> TimeSession:
  return TimeSession(
    id=1,
    user_id=1,
    session_type=SessionType.WORK,
    start_time=fixed_now,
    end_time=None
  )