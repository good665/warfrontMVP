from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class Avatar(Base):
    __tablename__ = 'mmo_avatars'
    player_id: Mapped[str] = mapped_column(ForeignKey('players.id'), primary_key=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    gold: Mapped[int] = mapped_column(Integer, default=0)
    role: Mapped[int] = mapped_column(Integer, default=0)
    hp: Mapped[float] = mapped_column(Float, default=100)
    weapon_rank: Mapped[int] = mapped_column(Integer, default=0)
    armor_rank: Mapped[int] = mapped_column(Integer, default=0)
    helmet_rank: Mapped[int] = mapped_column(Integer, default=0)
    helmet: Mapped[str] = mapped_column(String(64), default='')
    active_loadout: Mapped[int] = mapped_column(Integer, default=0)
    loadouts: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)
    weapon: Mapped[str] = mapped_column(String(64), default='starter-weapon')
    armor: Mapped[str] = mapped_column(String(64), default='starter-armor')
    kills: Mapped[int] = mapped_column(Integer, default=0)
    quest_stage: Mapped[int] = mapped_column(Integer, default=1)
    quest_state: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    inventory: Mapped[list] = mapped_column(JSON, default=lambda: [
        dict(id='starter-weapon', name='야전 소총', slot='weapon', power=0, rarity=0),
        dict(id='starter-armor', name='야전 방어복', slot='armor', power=0, rarity=0)])
