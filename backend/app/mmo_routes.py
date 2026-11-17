from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from .online_routes import online_player
from .mmo_world import world

router = APIRouter(prefix='/v1/mmo', tags=['MMO'])


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Enter(Strict):
    zone: Literal['frontier', 'minefield', 'ruins']
    role: int = Field(default=0, ge=0, le=2)


class Input(Strict):
    sequence: int = Field(ge=0, le=2147483647)
    move_x: float = Field(default=0, ge=-1, le=1)
    move_y: float = Field(default=0, ge=-1, le=1)
    aim_x: float = Field(default=0, ge=-10000, le=10000)
    aim_y: float = Field(default=0, ge=-10000, le=10000)
    attack: bool = False
    dodge: bool = False
    skill1: bool = False
    skill2: bool = False


class Equip(Strict):
    item_id: str = Field(min_length=1, max_length=64)
    loadout: int | None = Field(default=None, ge=0, le=2, strict=True)


class Loadout(Strict):
    index: int = Field(ge=0, le=2, strict=True)


class Upgrade(Strict):
    slot: Literal['weapon', 'armor', 'helmet']


class Party(Strict):
    action: Literal['create', 'join', 'leave']
    code: str = Field(default='', max_length=16)


@router.get('/profile')
def profile(pid: str = Depends(online_player)):
    return world.profile(pid)


@router.post('/enter')
def enter(body: Enter, pid: str = Depends(online_player)):
    return world.enter(pid, body.zone, body.role)


@router.get('/state')
def state(pid: str = Depends(online_player)):
    return world.state(pid)


@router.post('/input')
def input(body: Input, pid: str = Depends(online_player)):
    return world.input(pid, body.model_dump())


@router.post('/leave')
def leave(body: Strict, pid: str = Depends(online_player)):
    return world.leave(pid)


@router.post('/equip')
def equip(body: Equip, pid: str = Depends(online_player)):
    return world.equip(pid, body.item_id, body.loadout)


@router.post('/loadout')
def loadout(body: Loadout, pid: str = Depends(online_player)):
    return world.loadout(pid, body.index)


@router.post('/upgrade')
def upgrade(body: Upgrade, pid: str = Depends(online_player)):
    return world.upgrade(pid, body.slot)


@router.post('/quest/claim')
def claim(body: Strict, pid: str = Depends(online_player)):
    return world.claim(pid)


@router.post('/party')
def party(body: Party, pid: str = Depends(online_player)):
    return world.party(pid, body.action, body.code)
