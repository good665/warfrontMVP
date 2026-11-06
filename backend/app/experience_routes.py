from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import case, select, update
from sqlalchemy.orm import Session
from .database import get_db
from .models import Player
from .security import decode_access_token
from .experience import CLIENT_KINDS, MODES, lock_account, record_event
from .experience_models import ExperienceState

router = APIRouter(prefix="/v1/experience", tags=["Experience"])
bearer = HTTPBearer(auto_error=False)


def account(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    pid = decode_access_token(creds.credentials) if creds else None
    if not pid or db.get(Player, pid) is None:
        raise HTTPException(401, "unauthorized")
    return pid


def state_for(db, pid):
    # Serialize account changes, including consent vs event ingestion, on PostgreSQL.
    lock_account(db, pid)
    state = db.get(ExperienceState, pid)
    if state is None:
        state = ExperienceState(player_id=pid)
        db.add(state)
        db.flush()
    return state


def dto(state):
    return {k: getattr(state, k) for k in ("version", "tutorial_step", "tutorial_status", "analytics_consent")}


class Change(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["start", "progress", "skip", "consent"]
    tutorial_step: int | None = Field(default=None, ge=1, le=3)
    analytics_consent: bool | None = None


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    event_id: str
    app_session: str
    run_id: str
    kind: str
    mode: str
    step: int = Field(ge=0, le=3)
    duration_ms: int = Field(ge=0, le=86400000)
    queued_ms: int = Field(ge=0, le=604800000)
    success: bool

    @field_validator("event_id", "app_session", "run_id")
    @classmethod
    def uuid_id(cls, value):
        return str(UUID(value))

    @field_validator("kind")
    @classmethod
    def kind_allowed(cls, value):
        if value not in CLIENT_KINDS:
            raise ValueError("invalid_client_kind")
        return value

    @field_validator("mode")
    @classmethod
    def mode_allowed(cls, value):
        if value not in MODES:
            raise ValueError("invalid_mode")
        return value


class Batch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[Event] = Field(max_length=50)


@router.get("")
def get_experience(pid=Depends(account), db: Session = Depends(get_db)):
    state = state_for(db, pid)
    db.commit()
    return dto(state)


@router.post("")
def change_experience(payload: Change, pid=Depends(account), db: Session = Depends(get_db)):
    state = state_for(db, pid)
    if payload.action == "consent":
        if payload.analytics_consent is None or payload.tutorial_step is not None:
            raise HTTPException(422, "consent_required")
        state.analytics_consent = payload.analytics_consent
    elif payload.analytics_consent is not None:
        raise HTTPException(422, "use_consent_action")
    elif payload.action == "progress":
        step = payload.tutorial_step
        if step is None:
            raise HTTPException(422, "step_required")
        if step > state.tutorial_step + 1:
            raise HTTPException(409, "tutorial_step_out_of_order")
        changed = db.execute(update(ExperienceState).where(ExperienceState.player_id == pid, ExperienceState.tutorial_step >= step - 1).values(
            tutorial_step=case((ExperienceState.tutorial_step >= step, ExperienceState.tutorial_step), else_=step),
            tutorial_status=case((ExperienceState.tutorial_step >= 3, "completed"), else_="completed" if step == 3 else "in_progress")))
        if changed.rowcount != 1:
            raise HTTPException(409, "tutorial_step_out_of_order")
    elif payload.tutorial_step is not None:
        raise HTTPException(422, "unexpected_step")
    elif state.tutorial_status != "completed":
        db.execute(update(ExperienceState).where(ExperienceState.player_id == pid, ExperienceState.tutorial_status != "completed").values(tutorial_status="skipped" if payload.action == "skip" else "in_progress"))
    db.commit()
    db.refresh(state)
    return dto(state)


@router.post("/events")
def events(payload: Batch, pid=Depends(account), db: Session = Depends(get_db)):
    state = state_for(db, pid)
    accepted = []
    if state.analytics_consent:
        for event in payload.events:
            if record_event(db, pid, source="client", **event.model_dump()):
                accepted.append(event.event_id)
    db.commit()
    return {"accepted": accepted, "consent": state.analytics_consent}
