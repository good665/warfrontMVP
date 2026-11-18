from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from .online_routes import online_player
from .squad_rooms import squad_rooms
from .rts_map import map_payload
from .database import get_db
from .models import Player
from sqlalchemy.orm import Session

router = APIRouter(prefix='/v1/squad', tags=['Squad headquarters PvP'])


class EmptyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')


class MatchRequest(EmptyRequest):
    team_size: Literal[1, 2] = 1


class JoinRequest(EmptyRequest):
    code: str = Field(min_length=1, max_length=12)


class PauseRequest(EmptyRequest):
    paused: bool = Field(strict=True)


class SquadInput(EmptyRequest):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    unit_ids: list[str] = Field(default_factory=list, max_length=128)
    sequence: int = Field(ge=0, le=2147483647)
    character: Literal['', 'rat', 'ox', 'tiger', 'rabbit', 'dragon', 'snake', 'horse', 'goat', 'monkey', 'rooster', 'dog', 'pig'] = ''
    jump: bool = False
    move_x: float = Field(default=0, ge=-1, le=1)
    move_y: float = Field(default=0, ge=-1, le=1)
    aim_x: float = Field(default=0, ge=-1000, le=8400)  # interiors sit at x 6800..8400
    aim_y: float = Field(default=0, ge=-1000, le=8400)
    attack: bool = False
    dodge: bool = False
    skill1: bool = False
    skill2: bool = False
    command: Literal['none', 'gather', 'focus', 'hold', 'retreat', 'move', 'attack_move'] = 'none'
    target_id: str = Field(default='', max_length=128)
    order_x: float = Field(default=0, ge=0, le=6400)
    order_y: float = Field(default=0, ge=0, le=6400)


@router.get('/current')
def current(pid: str = Depends(online_player)):
    return squad_rooms.current(pid)


@router.post('/queue')
def queue(payload: MatchRequest, pid: str = Depends(online_player), db: Session = Depends(get_db)):
    return squad_rooms.create(pid, queue=True, name=db.get(Player, pid).display_name, team_size=payload.team_size)


@router.post('/create')
def create(payload: MatchRequest, pid: str = Depends(online_player), db: Session = Depends(get_db)):
    return squad_rooms.create(pid, name=db.get(Player, pid).display_name, team_size=payload.team_size)


@router.post('/computer')
def computer(payload: MatchRequest, pid: str = Depends(online_player), db: Session = Depends(get_db)):
    return squad_rooms.computer(pid, name=db.get(Player, pid).display_name, team_size=payload.team_size)


@router.post('/join')
def join(payload: JoinRequest, pid: str = Depends(online_player), db: Session = Depends(get_db)):
    return squad_rooms.join(payload.code, pid, name=db.get(Player, pid).display_name)


@router.post('/leave')
def leave(payload: EmptyRequest, pid: str = Depends(online_player)):
    return squad_rooms.leave(pid)


# Static layout; registered before '/{code}' so 'map' is not taken as a room code.
@router.get('/map')
def squad_map():
    return map_payload()


@router.get('/{code}')
def state(code: str, pid: str = Depends(online_player)):
    return squad_rooms.state(code, pid)


@router.post('/{code}/input')
def control(code: str, payload: SquadInput, pid: str = Depends(online_player)):
    return squad_rooms.input(code, pid, payload.model_dump())


@router.post('/{code}/pause')
def pause(code: str, payload: PauseRequest, pid: str = Depends(online_player)):
    return squad_rooms.pause(code, pid, payload.paused)
