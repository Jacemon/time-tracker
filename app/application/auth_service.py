import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from passlib.context import CryptContext
from app.domain.entities import User
from app.domain.repositories import IUserRepository

SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_local_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

class AuthService:
  def __init__(self, user_repo: IUserRepository):
    self.user_repo = user_repo

  def verify_password(self, plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

  def get_password_hash(self, password: str) -> str:
    return pwd_context.hash(password)

  def create_access_token(self, user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
      "sub": str(user_id),
      "username": username,
      "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

  async def register_user(self, username: str, password: str) -> User:
    existing_user = await self.user_repo.get_by_username(username)
    if existing_user:
      raise ValueError("Username already exists")
    hashed = self.get_password_hash(password)
    new_user = User(id=None, username=username, hashed_password=hashed)
    return await self.user_repo.create(new_user)

  async def authenticate_user(self, username: str, password: str) -> Optional[str]:
    user = await self.user_repo.get_by_username(username)
    if not user or not self.verify_password(password, user.hashed_password):
      return None
    return self.create_access_token(user.id, user.username)