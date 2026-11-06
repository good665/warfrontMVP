"""Persistent server-issued runs and once-only weekly training rewards."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base
from .models import _uuid


class TrainingSeason(Base):
    __tablename__ = 'training_seasons'
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    game: Mapped[str] = mapped_column(String(12))
    rules_version: Mapped[int] = mapped_column(Integer)
    seed: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    settles_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    claim_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TrainingRun(Base):
    __tablename__ = 'training_runs'
    __table_args__ = (Index('ix_training_runs_player_started', 'player_id', 'starts_at'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'))
    season_id: Mapped[str] = mapped_column(ForeignKey('training_seasons.id'), index=True)
    # NULL after finish/cancel/expiry; UNIQUE is portable across SQLite/PostgreSQL.
    active_player_id: Mapped[str | None] = mapped_column(ForeignKey('players.id'), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default='active')
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class TrainingBest(Base):
    __tablename__ = 'training_bests'
    __table_args__ = (Index('ix_training_bests_season_score', 'season_id', 'score'),)
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), primary_key=True)
    season_id: Mapped[str] = mapped_column(ForeignKey('training_seasons.id'), primary_key=True)
    score: Mapped[int] = mapped_column(Integer)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    run_id: Mapped[str] = mapped_column(ForeignKey('training_runs.id'))


class TrainingClaim(Base):
    __tablename__ = 'training_claims'
    __table_args__ = (UniqueConstraint('player_id', 'season_id', name='uq_training_claim_player_season'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), index=True)
    season_id: Mapped[str] = mapped_column(ForeignKey('training_seasons.id'))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    reward: Mapped[int] = mapped_column(Integer)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
