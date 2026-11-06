"""Account-scoped functional state and consent-gated, minimal analytics records."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base
from .models import _now


class ExperienceState(Base):
    __tablename__ = "experience_states"
    player_id: Mapped[str] = mapped_column(ForeignKey("players.id"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    tutorial_step: Mapped[int] = mapped_column(Integer, default=0)
    tutorial_status: Mapped[str] = mapped_column(String(16), default="new")
    analytics_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    # Consent-gated cohort identity survives raw-event retention. No device time.
    first_session_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_guide_exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_session_censored: Mapped[bool] = mapped_column(Boolean, default=False)
    first_guide_exit_censored: Mapped[bool] = mapped_column(Boolean, default=False)


class ExperienceEvent(Base):
    __tablename__ = "experience_events"
    __table_args__ = (UniqueConstraint("player_id", "event_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.id"), index=True)
    event_id: Mapped[str] = mapped_column(String(128))
    app_session: Mapped[str] = mapped_column(String(36), default="")
    run_id: Mapped[str] = mapped_column(String(64), default="")
    kind: Mapped[str] = mapped_column(String(32), index=True)
    mode: Mapped[str] = mapped_column(String(24), default="lobby")
    step: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    queued_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(8))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
