from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from sqlalchemy.orm import Session

from .database import get_db
from .models import Player
from .online_rooms import rooms
from .security import decode_access_token

router = APIRouter(prefix="/v1/rooms", tags=["Online friend matches"])
bearer = HTTPBearer(auto_error=False)


def online_player(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    player_id = decode_access_token(creds.credentials) if creds else None
    if not player_id or db.get(Player, player_id) is None:
        raise HTTPException(401, "unauthorized")
    return player_id


class RoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: int = Field(default=0, ge=0, le=2)


class ReadyRequest(RoleRequest):
    ready: bool


class CreateRequest(RoleRequest):
    team_size: Literal[1, 3] = 1


class LeaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    waiting_only: bool = False


class OnlineInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    sequence: int = Field(ge=0, le=2147483647)
    move_x: float = Field(default=0, ge=-1, le=1)
    move_y: float = Field(default=0, ge=-1, le=1)
    aim_x: float = Field(default=640, ge=-1000, le=3000)
    aim_y: float = Field(default=370, ge=-1000, le=2000)
    attack: bool = False
    dodge: bool = False
    skill1: bool = False
    skill2: bool = False


@router.post("")
def create_room(payload: CreateRequest, player_id: str = Depends(online_player)):
    return rooms.create(player_id, payload.role, payload.team_size)


@router.get("/current")
def current_room(player_id: str = Depends(online_player)):
    return rooms.current(player_id)


@router.post("/quick-match")
def quick_match(payload: CreateRequest, player_id: str = Depends(online_player)):
    return rooms.quick_match(player_id, payload.role, payload.team_size)


@router.post("/{code}/join")
def join_room(code: str, payload: RoleRequest, player_id: str = Depends(online_player)):
    return rooms.join(code.strip().upper(), player_id, payload.role)


@router.get("/{code}")
def room_state(code: str, player_id: str = Depends(online_player)):
    return rooms.state(code, player_id)


@router.post("/{code}/ready")
def ready_room(code: str, payload: ReadyRequest, player_id: str = Depends(online_player)):
    return rooms.ready(code, player_id, payload.ready, payload.role)


@router.post("/{code}/input")
def room_input(code: str, payload: OnlineInput, player_id: str = Depends(online_player)):
    return rooms.input(code, player_id, payload.model_dump())


@router.post("/{code}/leave")
def leave_room(code: str, payload: LeaveRequest | None = None, player_id: str = Depends(online_player)):
    return rooms.leave(code, player_id, payload.waiting_only if payload else False)
