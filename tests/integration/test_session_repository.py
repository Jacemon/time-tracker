import os
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.domain.entities import SessionType, TimeSession
from app.infrastructure.models import Base
from app.infrastructure.repositories import PostgresSessionRepository

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

@pytest.mark.asyncio
async def test_get_active_session_returns_latest_when_multiple_open(db_session: AsyncSession):
  repo = PostgresSessionRepository(db_session)
  base = datetime(2026, 11, 27, 10, 0, 0, tzinfo=timezone.utc)
  s1 = await repo.create(TimeSession(
    id=None,
    user_id=1,
    session_type=SessionType.WORK,
    start_time=base,
    end_time=None
  ))
  s2 = await repo.create(TimeSession(
    id=None,
    user_id=1,
    session_type=SessionType.BREAK,
    start_time=base + timedelta(minutes=30),
    end_time=None
  ))
  active = await repo.get_active_session(1)
  assert active is not None
  assert active.id == s2.id
  active_list = await repo.get_active_sessions(1)
  assert [s.id for s in active_list] == [s2.id, s1.id]

@pytest.mark.asyncio
async def test_crud_and_user_isolation(db_session: AsyncSession):
  repo = PostgresSessionRepository(db_session)
  t0 = datetime(2026, 11, 27, 9, 0, 0, tzinfo=timezone.utc)
  t1 = datetime(2026, 11, 27, 11, 0, 0, tzinfo=timezone.utc)
  created = await repo.create(TimeSession(
    id=None,
    user_id=1,
    session_type=SessionType.WORK,
    start_time=t0,
    end_time=None
  ))
  await repo.create(TimeSession(
    id=None,
    user_id=2,
    session_type=SessionType.WORK,
    start_time=t0,
    end_time=None
  ))
  created.end_time = t1
  updated = await repo.update(created)
  assert updated.end_time == t1
  fetched = await repo.get_by_id(created.id)
  assert fetched is not None
  assert fetched.end_time == t1
  user1_sessions = await repo.get_user_sessions(1)
  assert len(user1_sessions) == 1
  assert user1_sessions[0].id == created.id
  await repo.delete(created.id)
  assert await repo.get_by_id(created.id) is None