import jwt
import pytest
from app.application.auth_service import ALGORITHM, SECRET_KEY, AuthService
from app.application.settings_service import SettingsService
from app.domain.entities import UserSettings
from tests.fakes import FakeSettingsRepository, FakeUserRepository


@pytest.mark.asyncio
async def test_settings_service_update_normalizes_weekend_days_and_keeps_existing_tz():
  repo = FakeSettingsRepository({
    1: UserSettings(
      user_id=1,
      default_work_minutes=480,
      default_break_minutes=40,
      weekend_days="5,6",
      timezone="Europe/Berlin",
      timezone_auto=False
    )
  })
  service = SettingsService(repo)

  updated = await service.update_settings(
    user_id=1,
    default_work_minutes=360,
    default_break_minutes=30,
    weekend_days=[6, -1, 5, 5, 9, 0]
  )
  assert updated.default_work_minutes == 360
  assert updated.default_break_minutes == 30
  assert updated.weekend_days == "0,5,6"
  assert updated.timezone == "Europe/Berlin"
  assert updated.timezone_auto is False


@pytest.mark.asyncio
async def test_settings_service_rejects_invalid_values():
  repo = FakeSettingsRepository()
  service = SettingsService(repo)

  with pytest.raises(ValueError):
    await service.update_settings(
      user_id=1,
      default_work_minutes=-10,
      default_break_minutes=30,
      weekend_days=[5, 6]
    )

  with pytest.raises(ValueError):
    await service.update_settings(
      user_id=1,
      default_work_minutes=480,
      default_break_minutes=40,
      weekend_days=[5, 6],
      timezone="Mars/Olympus_Mons"
    )

  with pytest.raises(ValueError):
    await service.set_daily_norm(
      user_id=1,
      date_str="2026-11-27",
      work_minutes=480,
      break_minutes=-1
    )


@pytest.mark.asyncio
async def test_settings_service_set_and_get_daily_norm():
  repo = FakeSettingsRepository()
  service = SettingsService(repo)

  norm = await service.set_daily_norm(
    user_id=1,
    date_str="2026-11-27",
    work_minutes=420,
    break_minutes=45
  )
  assert norm.id is not None
  assert norm.work_minutes == 420

  norms = await service.get_daily_norms(1)
  assert len(norms) == 1
  assert norms[0].date_str == "2026-11-27"


@pytest.mark.asyncio
async def test_auth_service_register_duplicate_and_authenticate():
  repo = FakeUserRepository()
  service = AuthService(repo)

  user = await service.register_user("evgeny", "strong_pass_123")
  assert user.id is not None
  assert user.username == "evgeny"
  assert user.hashed_password != "strong_pass_123"
  assert service.verify_password("strong_pass_123", user.hashed_password)

  with pytest.raises(ValueError):
    await service.register_user("evgeny", "another_pass")

  assert await service.authenticate_user("evgeny", "wrong_pass") is None
  assert await service.authenticate_user("unknown_user", "strong_pass_123") is None

  token = await service.authenticate_user("evgeny", "strong_pass_123")
  assert token is not None
  decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
  assert decoded["sub"] == str(user.id)
  assert decoded["username"] == "evgeny"