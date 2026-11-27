from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
import app.application.timer_service as timer_service_module
from app.application.timer_service import TimerService
from app.domain.entities import DailyNorm, SessionType, TimeSession, UserSettings
from tests.fakes import FakeSessionRepository, FakeSettingsRepository

class FixedDateTime(datetime):
  current_now = datetime(2026, 11, 27, 15, 0, 0, tzinfo=timezone.utc)

  @classmethod
  def now(cls, tz=None):
    base = cls.current_now
    if tz is not None:
      return base.astimezone(tz)
    return base

def set_now(monkeypatch, dt: datetime) -> None:
  FixedDateTime.current_now = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
  monkeypatch.setattr(timer_service_module, "datetime", FixedDateTime)

@pytest.mark.asyncio
async def test_heal_active_sessions_keeps_newest_and_closes_stale(monkeypatch):
  now = datetime(2026, 11, 27, 15, 0, 0, tzinfo=timezone.utc)
  set_now(monkeypatch, now)
  s_old = TimeSession(
    id=1,
    user_id=1,
    session_type=SessionType.WORK,
    start_time=now - timedelta(hours=3),
    end_time=None
  )
  s_new = TimeSession(
    id=2,
    user_id=1,
    session_type=SessionType.WORK,
    start_time=now - timedelta(minutes=20),
    end_time=None
  )
  s_future_start = TimeSession(
    id=3,
    user_id=1,
    session_type=SessionType.BREAK,
    start_time=now + timedelta(hours=1),
    end_time=None
  )
  repo = FakeSessionRepository([s_old, s_new, s_future_start])
  settings_repo = FakeSettingsRepository({1: UserSettings(user_id=1, timezone="UTC")})
  service = TimerService(repo, settings_repo)
  active = await service.get_status(1)
  assert active is not None
  assert active.id == 3
  assert active.end_time is None
  all_sessions = {s.id: s for s in await repo.get_user_sessions(1)}
  assert all_sessions[1].end_time == now
  assert all_sessions[2].end_time == now
  assert all_sessions[3].end_time is None

@pytest.mark.asyncio
async def test_split_overnight_active_session_in_user_timezone(monkeypatch):
  # Europe/Berlin in November is UTC+1; local midnight is 23:00 UTC previous day
  berlin = ZoneInfo("Europe/Berlin")
  start_utc = datetime(2026, 11, 26, 21, 0, 0, tzinfo=timezone.utc)  # 22:00 Berlin
  now_utc = datetime(2026, 11, 27, 0, 30, 0, tzinfo=timezone.utc)    # 01:30 Berlin next day
  set_now(monkeypatch, now_utc)
  session = TimeSession(
    id=10,
    user_id=1,
    session_type=SessionType.WORK,
    start_time=start_utc,
    end_time=None
  )
  repo = FakeSessionRepository([session])
  settings_repo = FakeSettingsRepository({
    1: UserSettings(
      user_id=1,
      default_work_minutes=480,
      default_break_minutes=40,
      timezone="Europe/Berlin",
      timezone_auto=False
    )
  })
  service = TimerService(repo, settings_repo)
  await service.get_status(1)
  sessions = await repo.get_user_sessions(1)
  sessions.sort(key=lambda s: s.start_time)
  assert len(sessions) == 2
  expected_midnight_utc = datetime(2026, 11, 26, 23, 0, 0, tzinfo=timezone.utc)
  assert sessions[0].start_time == start_utc
  assert sessions[0].end_time == expected_midnight_utc
  assert sessions[0].session_type == SessionType.WORK
  assert sessions[1].start_time == expected_midnight_utc
  assert sessions[1].end_time is None
  assert sessions[1].session_type == SessionType.WORK
  norms = {n.date_str: n for n in await settings_repo.get_daily_norms(1)}
  assert "2026-11-26" in norms
  assert norms["2026-11-26"].work_minutes == 480

@pytest.mark.asyncio
async def test_get_user_tz_fallback_on_invalid_timezone():
  repo = FakeSessionRepository()
  settings_repo = FakeSettingsRepository({
    1: UserSettings(user_id=1, timezone="Invalid/Timezone_Name")
  })
  service = TimerService(repo, settings_repo)
  tz = await service._get_user_tz(1)
  assert tz.key == "UTC"

@pytest.mark.asyncio
async def test_start_session_same_type_returns_existing_and_different_type_closes_previous(monkeypatch):
  t0 = datetime(2026, 11, 27, 10, 0, 0, tzinfo=timezone.utc)
  t1 = datetime(2026, 11, 27, 10, 30, 0, tzinfo=timezone.utc)
  t2 = datetime(2026, 11, 27, 11, 0, 0, tzinfo=timezone.utc)
  repo = FakeSessionRepository()
  settings_repo = FakeSettingsRepository({1: UserSettings(user_id=1, timezone="UTC")})
  service = TimerService(repo, settings_repo)
  set_now(monkeypatch, t0)
  work1 = await service.start_session(1, SessionType.WORK)
  set_now(monkeypatch, t1)
  same_work = await service.start_session(1, SessionType.WORK)
  assert same_work.id == work1.id
  assert same_work.end_time is None
  set_now(monkeypatch, t2)
  brk = await service.start_session(1, SessionType.BREAK)
  assert brk.id != work1.id
  assert brk.session_type == SessionType.BREAK
  assert brk.end_time is None
  closed_work = await repo.get_by_id(work1.id)
  assert closed_work is not None
  assert closed_work.end_time == t2

@pytest.mark.asyncio
async def test_get_today_summary_clips_to_day_start_and_sums_durations(monkeypatch):
  # Local day in Europe/Berlin for 2026-11-27 starts at 2026-11-26 23:00:00 UTC
  now_utc = datetime(2026, 11, 27, 12, 0, 0, tzinfo=timezone.utc)  # 13:00 Berlin
  set_now(monkeypatch, now_utc)
  day_start_utc = datetime(2026, 11, 26, 23, 0, 0, tzinfo=timezone.utc)
  # Yesterday-only session: 21:00..22:00 UTC -> ignored
  s_yesterday = TimeSession(
    id=1,
    user_id=1,
    session_type=SessionType.WORK,
    start_time=datetime(2026, 11, 26, 21, 0, 0, tzinfo=timezone.utc),
    end_time=datetime(2026, 11, 26, 22, 0, 0, tzinfo=timezone.utc)
  )
  # Cross-midnight work: 22:30 UTC yesterday .. 00:00 UTC today -> 3600s inside today
  s_cross = TimeSession(
    id=2,
    user_id=1,
    session_type=SessionType.WORK,
    start_time=datetime(2026, 11, 26, 22, 30, 0, tzinfo=timezone.utc),
    end_time=datetime(2026, 11, 27, 0, 0, 0, tzinfo=timezone.utc)
  )
  # Break today: 01:00..01:15 UTC -> 900s
  s_break = TimeSession(
    id=3,
    user_id=1,
    session_type=SessionType.BREAK,
    start_time=datetime(2026, 11, 27, 1, 0, 0, tzinfo=timezone.utc),
    end_time=datetime(2026, 11, 27, 1, 15, 0, tz