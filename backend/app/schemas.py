from typing import Literal

from pydantic import BaseModel, Field

NAME_PATTERN = r"^[a-zA-Z0-9가-힣 _-]+$"
MatchMode = Literal["pvp", "pve", "rush", "bomb", "arena1", "arena3"]


class GuestLoginRequest(BaseModel):
    device_id: str = Field(min_length=16, max_length=64, pattern=r"^[a-zA-Z0-9-]+$")
    display_name: str = Field(min_length=2, max_length=24, pattern=NAME_PATTERN)


class StartMatchRequest(BaseModel):
    mode: MatchMode


class FinishMatchRequest(BaseModel):
    # pvp/pve/arena1/arena3: won 사용, rush/bomb: survival_seconds 사용
    won: bool = False
    survival_seconds: float = Field(default=0.0, ge=0.0, le=14400.0)


class PlayerResponse(BaseModel):
    id: str
    display_name: str
    diamonds: int
    stamina: int
    rating: int
    wins: int
    losses: int
    power: int
    pve_best_stage: int
    next_stamina_in_seconds: int  # 가득 찼으면 -1
    daily_ad_views: int
    daily_reward_claimed: bool


class AuthResponse(BaseModel):
    access_token: str
    player: PlayerResponse


class StartMatchResponse(BaseModel):
    match_id: str
    mode: MatchMode
    stage: int
    player: PlayerResponse


class FinishMatchResponse(BaseModel):
    mode: MatchMode
    won: bool
    stage: int
    rating_delta: int
    diamonds_gained: int
    survival_seconds: float
    player: PlayerResponse


class AdStaminaResponse(BaseModel):
    recovered: int
    player: PlayerResponse


class DailyRewardResponse(BaseModel):
    rank: int
    reward: int
    player: PlayerResponse


class LeaderboardEntry(BaseModel):
    rank: int
    display_name: str
    rating: int
    is_me: bool


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    my_rank: int
    my_rating: int
    my_reward: int  # 지금 순위 기준 일일 보상 미리보기
