import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.auth_service import ALGORITHM, AuthService, SECRET_KEY
from app.application.settings_service import SettingsService
from app.application.timer_service import TimerService
from app.infrastructure.database import get_db
from app.infrastructure.repositories import PostgresSessionRepository, PostgresSettingsRepository, PostgresUserRepository

security = HTTPBearer()

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
  user_repo = PostgresUserRepository(db)
  return AuthService(user_repo)

def get_timer_service(db: AsyncSession = Depends(get_db)) -> TimerService:
  session_repo = PostgresSessionRepository(db)
  settings_repo = PostgresSettingsRepository(db)
  return TimerService(session_repo, settings_repo)

def get_settings_service(db: AsyncSession = Depends(get_db)) -> SettingsService:
  settings_repo = PostgresSettingsRepository(db)
  return SettingsService(settings_repo)

async def get_current_user_id(
  credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
  try:
    payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    user_id = payload.get("sub")
    if not user_id:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token payload"
      )
    return int(user_id)
  except jwt.PyJWTError:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid or expired token"
    )