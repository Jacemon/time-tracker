from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.infrastructure.database import Base, engine
from app.infrastructure import models
from app.presentation.api.routers import auth_router, settings_router, timer_router

@asynccontextmanager
async def lifespan(app: FastAPI):
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
    if engine.dialect.name == "postgresql":
      await conn.execute(text(
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) NOT NULL DEFAULT 'UTC'"
      ))
      await conn.execute(text(
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS timezone_auto BOOLEAN NOT NULL DEFAULT TRUE"
      ))
  yield

app = FastAPI(title="Time Tracker API", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(timer_router)
app.include_router(settings_router)

app.mount("/static", StaticFiles(directory="app/presentation/web"), name="static")

@app.get("/sw.js")
async def serve_sw():
  return FileResponse("app/presentation/web/sw.js", media_type="application/javascript")

@app.get("/")
async def serve_web():
  return FileResponse("app/presentation/web/index.html")

@app.get("/health")
async def health_check():
  return {"status": "ok", "message": "Backend is running"}