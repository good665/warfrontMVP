"""Authenticated, bounded training inputs; score/rank/reward are server-owned."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from sqlalchemy.orm import Session
from .database import get_db
from .security import decode_access_token
from . import training_service as service


class LimitedTrainingRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def limited(request: Request):
            if request.method == 'POST':
                # Enforce streaming bytes too: Content-Length is client-controlled.
                body = bytearray()
                async for chunk in request.stream():
                    if len(body) + len(chunk) > 512 * 1024:
                        raise HTTPException(413, 'training_body_too_large')
                    body.extend(chunk)
                request._body = bytes(body)
            return await original(request)
        return limited


router = APIRouter(prefix='/v1/training', tags=['Training'], route_class=LimitedTrainingRoute)
bearer = HTTPBearer(auto_error=False)


def account(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    pid = decode_access_token(creds.credentials) if creds else None
    if not pid:
        raise HTTPException(401, 'unauthorized')
    return pid


class Empty(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Start(Empty):
    game: Literal['range', 'drone', 'cipher'] = Field(default=None)


class TrainingInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    tick: int = Field(ge=0, le=4500)
    action: int = Field(ge=0, le=2)
    x: int = Field(ge=0, le=100000)
    y: int = Field(ge=0, le=40000)
    index: int = Field(ge=0, le=3)


class Finish(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    total_ticks: int = Field(ge=0, le=4500)
    events: list[TrainingInput] = Field(max_length=4501)


@router.post('/runs', status_code=201)
def start(payload: Start, pid=Depends(account), db: Session = Depends(get_db)):
    return service.start_run(db, pid, payload.game)


@router.post('/runs/{run_id}/finish')
def finish(run_id: str, payload: Finish, pid=Depends(account), db: Session = Depends(get_db)):
    return service.finish_run(db, pid, run_id, payload.model_dump())


@router.post('/runs/{run_id}/cancel')
def cancel(run_id: str, payload: Empty, pid=Depends(account), db: Session = Depends(get_db)):
    return service.cancel_run(db, pid, run_id)


@router.get('/leaderboard')
def leaderboard(season_id: str | None = None, game: Literal['range', 'drone', 'cipher'] | None = None,
                pid=Depends(account), db: Session = Depends(get_db)):
    return service.leaderboard(db, pid, season_id, game)


@router.get('/rewards')
def rewards(pid=Depends(account), db: Session = Depends(get_db)):
    return service.rewards(db, pid)


@router.post('/rewards/{season_id}/claim')
def claim(season_id: str, payload: Empty, pid=Depends(account), db: Session = Depends(get_db)):
    return service.claim_reward(db, pid, season_id)
