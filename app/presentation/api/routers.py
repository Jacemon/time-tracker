from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from app.application.auth_service import AuthService
from app.application.timer_service import TimerService
from app.domain.entities import SessionType
from app.presentation.api.dependencies import get_auth_service, get_current_user_id, get_timer_service
from app.presentation.api.schemas import SessionResponse, SessionUpdateRequest, StatusResponse, SummaryResponse, TokenResponse, UserAuthRequest

auth_router = APIRouter(prefix="/auth", tags=["Auth"])
timer_router = APIRouter(prefix="/timer", tags=["Timer"])

@auth_router.post("/register", response_model=TokenResponse)
async def register(data: UserAuthRequest, auth_service: AuthService = Depends(get_auth_service)):
  try:
    user = await auth_service.register_user(data.username, data.password)
    token = auth_service.create_access_token(user.id, user.username)
    return TokenResponse(access_token=token)
  except ValueError as e:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@auth_router.post("/login", response_model=TokenResponse)
async def login(data: UserAuthRequest, auth_service: AuthService = Depends(get_auth_service)):
  token = await auth_service.authenticate_user(data.username, data.password)
  if not token:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
  return TokenResponse(access_token=token)

@timer_router.post("/work", response_model=SessionResponse)
async def start_work(
  user_id: int = Depends(get_current_user_id),
  timer_service: TimerService = Depends(get_timer_service)
):
  return await timer_service.start_session(user_id, SessionType.WORK)

@timer_router.post("/break", response_model=SessionResponse)
async def start_break(
  user_id: int = Depends(get_current_user_id),
  timer_service: TimerService = Depends(get_timer_service)
):
  return await timer_service.start_session(user_id, SessionType.BREAK)

@timer_router.post("/stop", response_model=StatusResponse)
async def stop_timer(
  user_id: int = Depends(get_current_user_id),
  timer_service: TimerService = Depends(get_timer_service)
):
  await timer_service.stop_timer(user_id)
  return StatusResponse(active_session=None)

@timer_router.get("/status", response_model=StatusResponse)
async def get_status(
  user_id: int = Depends(get_current_user_id),
  timer_service: TimerService = Depends(get_timer_service)
):
  session = await timer_service.get_status(user_id)
  return StatusResponse(active_session=session)

@timer_router.get("/history", response_model=List[SessionResponse])
async def get_history(
  user_id: int = Depends(get_current_user_id),
  timer_service: TimerService = Depends(get_timer_service)
):
  return await timer_service.get_history(user_id)

@timer_router.get("/summary", response_model=SummaryResponse)
async def get_summary(
  user_id: int = Depends(get_current_user_id),
  timer_service: TimerService = Depends(get_timer_service)
):
  return await timer_service.get_today_summary(user_id)

@timer_router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
  session_id: int,
  data: SessionUpdateRequest,
  user_id: int = Depends(get_current_user_id),
  timer_service: TimerService = Depends(get_timer_service)
):
  try:
    return await timer_service.update_session(
      user_id=user_id,
      session_id=session_id,
      session_type=data.session_type,
      start_time=data.start_time,
      end_time=data.end_time
    )
  except ValueError as e:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@timer_router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
  session_id: int,
  user_id: int = Depends(get_current_user_id),
  timer_service: TimerService = Depends(get_timer_service)
):
  try:
    await timer_service.delete_session(user_id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
  except ValueError as e:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))