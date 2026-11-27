import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.entities import DailyNorm, User, UserSettings
from app.infrastructure.repositories import PostgresSettingsRepository, PostgresUserRepository


@pytest.mark.asyncio
async def test_user_repository_create_and_get_by_username(db_session: AsyncSession):
  repo = PostgresUserRepository(db_session)
  assert await repo.get_by_username("missing_user") is None

  created = await repo.create(User(
    id=None,
    username="alice",
    hashed_password="hashed_secret_password"
  ))
  assert created.id is not None
  assert created.username == "alice"
  assert created.hashed_password == "hashed_secret_password"

  fetched = await repo.get_by_username("alice")
  assert fetched is not None
  assert fetched.id == created.id
  assert fetched.hashed_password == "hashed_secret_password"


@pytest.mark.asyncio
async def test_settings_repository_defaults_save_and_update(db_session: AsyncSession):
  repo = PostgresSettingsRepository(db_session)
  defaults = await repo.get_settings(42)
  assert defaults.user_id == 42
  assert defaults.default_work_minutes == 480
  assert defaults.default_break_minutes == 40
  assert defaults.weekend_days == "5,6"
  assert defaults.timezone == "UTC"
  assert defaults.timezone_auto is True

  saved = await repo.save_settings(UserSettings(
    user_id=42,
    default_work_minutes=360,
    default_break_minutes=30,
    weekend_days="6",
    timezone="Europe/Berlin",
    timezone_auto=False
  ))
  assert saved.default_work_minutes == 360
  assert saved.timezone == "Europe/Berlin"
  assert saved.timezone_auto is False

  updated = await repo.save_settings(UserSettings(
    user_id=42,
    default_work_minutes=420,
    default_break_minutes=45,
    weekend_days="5,6",
    timezone="UTC",
    timezone_auto=True
  ))
  assert updated.default_work_minutes == 420
  fetched = await repo.get_settings(42)
  assert fetched.default_work_minutes == 420
  assert fetched.default_break_minutes == 45
  assert fetched.timezone == "UTC"


@pytest.mark.asyncio
async def test_settings_repository_daily_norms_upsert_and_isolation(db_session: AsyncSession):
  repo = PostgresSettingsRepository(db_session)
  n1 = await repo.save_daily_norm(DailyNorm(
    id=None,
    user_id=1,
    date_str="2026-11-27",
    work_minutes=480,
    break_minutes=40
  ))
  assert n1.id is not None

  # Обновление нормы за ту же дату и пользователя не должно создавать дубль
  n1_updated = await repo.save_daily_norm(DailyNorm(
    id=None,
    user_id=1,
    date_str="2026-11-27",
    work_minutes=240,
    break_minutes=20
  ))
  assert n1_updated.id == n1.id
  assert n1_updated.work_minutes == 240
  assert n1_updated.break_minutes == 20

  # Другой пользователь и другая дата
  await repo.save_daily_norm(DailyNorm(
    id=None,
    user_id=1,
    date_str="2026-11-28",
    work_minutes=300,
    break_minutes=30
  ))
  await repo.save_daily_norm(DailyNorm(
    id=None,
    user_id=2,
    date_str="2026-11-27",
    work_minutes=600,
    break_minutes=60
  ))

  user1_norms = await repo.get_daily_norms(1)
  assert len(user1_norms) == 2
  by_date = {n.date_str: n for n in user1_norms}
  assert by_date["2026-11-27"].work_minutes == 240
  assert by_date["2026-11-28"].work_minutes == 300

  user2_norms = await repo.get_daily_norms(2)
  assert len(user2_norms) == 1
  assert user2_norms[0].work_minutes == 600