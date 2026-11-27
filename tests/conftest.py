from datetime import datetime, timezone
import pytest
from app.domain.entities import SessionType, TimeSession, UserSettings
from tests.fakes import FakeSessionRepository, FakeSettingsRepository

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