from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.entities import SessionType
from app.infrastructure.database import Base

class UserModel(Base):
  __tablename__ = "users"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
  username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
  hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

class TimeSessionModel(Base):
  __tablename__ = "time_sessions"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
  session_type: Mapped[SessionType] = mapped_column(SQLEnum(SessionType), nullable=False)
  start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
  end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class UserSettingsModel(Base):
  __tablename__ = "user_settings"

  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
  default_work_minutes: Mapped[int] = mapped_column(Integer, default=480, nullable=False)
  default_break_minutes: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
  weekend_days: Mapped[str] = mapped_column(String(20), default="5,6", nullable=False)
  timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
  timezone_auto: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

class DailyNormModel(Base):
  __tablename__ = "daily_norms"
  __table_args__ = (UniqueConstraint("user_id", "date_str", name="uq_user_date_norm"),)

  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
  date_str: Mapped[str] = mapped_column(String(10), nullable=False)
  work_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
  break_minutes: Mapped[int] = mapped_column(Integer, nullable=False)