import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.application.auth_service import ALGORITHM, SECRET_KEY, AuthService
from app.application.timer_service import TimerService
from app.infrastructure.database import get_db
from app.infrastructure.repositories import PostgresSessionRepository, PostgresUserRepository

security = HTTPBearer()

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
  return AuthService(PostgresUserRepository(db))

def get_timer_service(db: AsyncSession = Depends(get_db)) -> TimerService:
  return TimerService(PostgresSessionRepository(db))

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
  token = credentials.credentials
  try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_id = payload.get("sub")
    if user_id is None:
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return int(user_id)
  except jwt.PyJWTError:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")