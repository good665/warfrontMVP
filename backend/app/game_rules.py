"""게임 규칙(상수/계산)을 한 곳에 모아 서버가 유일한 진실 공급원이 되도록 한다."""
import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .models import Player

KST = ZoneInfo("Asia/Seoul")  # 일일 리셋 기준 (한국 서비스)

MAX_STAMINA = 100
GAME_COST = 10
RECOVERY_SECONDS = 60 * 60
RECOVERY_AMOUNT = 5

AD_STAMINA = 10
AD_DAILY_LIMIT = 5

PVP_RATING_DELTA = 100
PVP_WIN_DIAMONDS = 3
MIN_WIN_SECONDS = {"pvp": 3.0, "pve": 2.0}  # 이보다 빨리 "승리" 보고하면 거부
ARENA_WIN_DIAMONDS = {"arena1": 3, "arena3": 5}
ARENA_MIN_WIN_SECONDS = 60.0
MATCH_TTL_SECONDS = 30 * 60            # pvp / pve
SURVIVAL_TTL_SECONDS = 4 * 60 * 60     # rush / bomb (무한 스테이지)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def today_key(now: datetime | None = None) -> str:
    return (now or utcnow()).astimezone(KST).strftime("%Y-%m-%d")


def recover_stamina(player: Player, now: datetime | None = None) -> None:
    now = now or utcnow()
    if player.stamina >= MAX_STAMINA:
        player.last_stamina_at = now  # 가득 차 있는 동안은 타이머를 흘려보내지 않는다
        return
    last = as_utc(player.last_stamina_at)
    intervals = int((now - last).total_seconds() // RECOVERY_SECONDS)
    if intervals <= 0:
        return
    player.stamina = min(MAX_STAMINA, player.stamina + intervals * RECOVERY_AMOUNT)
    # 남은 시간(나머지)을 버리지 않도록 intervals 만큼만 전진
    player.last_stamina_at = now if player.stamina >= MAX_STAMINA else last + timedelta(seconds=intervals * RECOVERY_SECONDS)


def spend_stamina(player: Player, amount: int, now: datetime | None = None) -> None:
    now = now or utcnow()
    if player.stamina >= MAX_STAMINA:
        player.last_stamina_at = now  # 가득 찬 상태에서 소모하면 이 시점부터 회복 시작
    player.stamina -= amount


def seconds_to_next_stamina(player: Player, now: datetime | None = None) -> int:
    """가득 찼으면 -1."""
    if player.stamina >= MAX_STAMINA:
        return -1
    now = now or utcnow()
    elapsed = (now - as_utc(player.last_stamina_at)).total_seconds()
    return max(0, math.ceil(RECOVERY_SECONDS - elapsed))


def daily_ad_views(player: Player, now: datetime | None = None) -> int:
    return player.daily_ad_views if player.daily_ad_date == today_key(now) else 0


def reset_daily_ad_views(player: Player, now: datetime | None = None) -> None:
    today = today_key(now)
    if player.daily_ad_date != today:
        player.daily_ad_date = today
        player.daily_ad_views = 0


def upgrade_cost(power: int) -> int:
    return 10 + power * 5


def survival_reward(seconds: float) -> int:
    return max(1, int(seconds // 15))


def daily_reward_for_rank(rank: int) -> int:
    if rank == 1:
        return 100
    if rank == 2:
        return 50
    if rank == 3:
        return 20
    if rank <= 10:
        return 10
    if rank <= 20:
        return 5
    return 0
