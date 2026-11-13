from typing import List, Optional
from zoneinfo import available_timezones
from app.domain.entities import DailyNorm, UserSettings
from app.domain.repositories import ISettingsRepository

class SettingsService:
  def __init__(self, settings_repo: ISettingsRepository):
    self.settings_repo = settings_repo

  async def get_settings(self, user_id: int) -> UserSettings:
    return await self.settings_repo.get_settings(user_id)

  async def update_settings(
    self,
    user_id: int,
    default_work_minutes: int,
    default_break_minutes: int,
    weekend_days: List[int],
    timezone: Optional[str] = None
  ) -> UserSettings:
    if default_work_minutes < 0 or default_break_minutes < 0:
      raise ValueError("Minutes cannot be negative")
    if timezone is not None and timezone not in available_timezones():
      raise ValueError("Unknown timezone")
    valid_days = sorted({d for d in weekend_days if 0 <= d <= 6})
    weekend_str = ",".join(str(d) for d in valid_days)
    current = await self.settings_repo.get_settings(user_id)
    settings = UserSettings(
      user_id=user_id,
      default_work_minutes=default_work_minutes,
      default_break_minutes=default_break_minutes,
      weekend_days=weekend_str,
      timezone=timezone if timezone is not None else current.timezone
    )
    return await self.settings_repo.save_settings(settings)

  async def get_daily_norms(self, user_id: int) -> List[DailyNorm]:
    return await self.settings_repo.get_daily_norms(user_id)

  async def set_daily_norm(
    self,
    user_id: int,
    date_str: str,
    work_minutes: int,
    break_minutes: int
  ) -> DailyNorm:
    if work_minutes < 0 or break_minutes < 0:
      raise ValueError("Minutes cannot be negative")
    norm = DailyNorm(
      id=None,
      user_id=user_id,
      date_str=date_str,
      work_minutes=work_minutes,
      break_minutes=break_minutes
    )
    return await self.settings_repo.save_daily_norm(norm)