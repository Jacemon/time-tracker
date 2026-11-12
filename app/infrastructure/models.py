from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from app.domain.entities import SessionType
from app.infrastructure.database import Base

class UserModel(Base):
  __tablename__ = "users"

  id = Column(Integer, primary_key=True, index=True)
  username = Column(String, unique=True, index=True, nullable=False)
  hashed_password = Column(String, nullable=False)

class TimeSessionModel(Base):
  __tablename__ = "time_sessions"

  id = Column(Integer, primary_key=True, index=True)
  user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
  session_type = Column(Enum(SessionType), nullable=False)
  start_time = Column(DateTime(timezone=True), nullable=False)
  end_time = Column(DateTime(timezone=True), nullable=True)