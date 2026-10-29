import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Player(Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # 게스트 로그인용 기기 식별자 (추후 Google/Apple 로그인 계정과 연결)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    diamonds: Mapped[int] = mapped_column(Integer, default=0)
    stamina: Mapped[int] = mapped_column(Integer, default=100)
    rating: Mapped[int] = mapped_column(Integer, default=1000, index=True)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    power: Mapped[int] = mapped_column(Integer, default=0)
    pve_best_stage: Mapped[int] = mapped_column(Integer, default=0)
    daily_ad_views: Mapped[int] = mapped_column(Integer, default=0)
    daily_ad_date: Mapped[str] = mapped_column(String(10), default="")
    daily_reward_date: Mapped[str] = mapped_column(String(10), default="")
    last_stamina_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Match(Base):
    """전투 1회 = 체력 소모 시점에 생성되고, 결과 보고 시 1회만 정산된다."""

    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.id"), index=True)
    mode: Mapped[str] = mapped_column(String(10))  # pvp | pve | rush | bomb | arena1 | arena3 | online1 | online3
    stage: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(10), default="active", index=True)  # active|finished|abandoned
    won: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    survival_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
