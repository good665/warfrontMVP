from contextlib import asynccontextmanager
import secrets

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import game_rules as rules
from .config import settings
from .database import Base, engine, get_db
from .models import Match, Player
from .online_rooms import rooms
from .online_routes import router as online_router
from .schemas import (
    AdStaminaResponse,
    AuthResponse,
    DailyRewardResponse,
    FinishMatchRequest,
    FinishMatchResponse,
    GuestLoginRequest,
    LeaderboardEntry,
    LeaderboardResponse,
    PlayerResponse,
    StartMatchRequest,
    StartMatchResponse,
)
from .security import create_access_token, decode_access_token


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    rooms.start()
    try:
        yield
    finally:
        await rooms.stop()


app = FastAPI(title="Warfront API", version="0.3.0", lifespan=lifespan,
              docs_url=None if settings.public_test_mode else "/docs",
              redoc_url=None if settings.public_test_mode else "/redoc",
              openapi_url=None if settings.public_test_mode else "/openapi.json")
app.include_router(online_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

bearer = HTTPBearer(auto_error=False)


@app.middleware("http")
async def public_test_access(request: Request, call_next):
    if settings.public_test_mode and request.url.path not in ("/health", "/ready") and request.method != "OPTIONS":
        supplied = request.headers.get("X-Warfront-Test-Key", "")
        if not secrets.compare_digest(supplied.encode(), settings.test_access_key.encode()):
            return JSONResponse(status_code=403, content={"detail": "test_access_required"})
    return await call_next(request)


def err(code: int, detail: str) -> HTTPException:
    """detail 은 Unity 클라이언트가 분기하기 쉬운 에러 코드 문자열."""
    return HTTPException(status_code=code, detail=detail)


# ---------- 인증 / 의존성 ----------

def current_player_id(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    player_id = decode_access_token(creds.credentials) if creds else None
    if player_id is None:
        raise err(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    return player_id


def _load_player(db: Session, player_id: str, lock: bool) -> Player:
    stmt = select(Player).where(Player.id == player_id)
    if lock:
        stmt = stmt.with_for_update()  # PostgreSQL 행 잠금: 동시 요청으로 재화가 이중 지급되는 것을 방지
    player = db.scalar(stmt)
    if player is None:
        raise err(status.HTTP_401_UNAUTHORIZED, "unauthorized")
    rules.recover_stamina(player)
    return player


def get_player(player_id: str = Depends(current_player_id), db: Session = Depends(get_db)) -> Player:
    return _load_player(db, player_id, lock=False)


def get_player_locked(player_id: str = Depends(current_player_id), db: Session = Depends(get_db)) -> Player:
    return _load_player(db, player_id, lock=True)


def serialize(player: Player) -> PlayerResponse:
    return PlayerResponse(
        id=player.id,
        display_name=player.display_name,
        diamonds=player.diamonds,
        stamina=player.stamina,
        rating=player.rating,
        wins=player.wins,
        losses=player.losses,
        power=player.power,
        pve_best_stage=player.pve_best_stage,
        next_stamina_in_seconds=rules.seconds_to_next_stamina(player),
        daily_ad_views=rules.daily_ad_views(player),
        daily_reward_claimed=player.daily_reward_date == rules.today_key(),
    )


def rank_of(db: Session, player: Player) -> int:
    """정렬 기준(rating desc, created_at asc)과 동일한 규칙으로 순위를 계산."""
    ahead = db.scalar(
        select(func.count())
        .select_from(Player)
        .where((Player.rating > player.rating) | ((Player.rating == player.rating) & ((Player.created_at < player.created_at) | ((Player.created_at == player.created_at) & (Player.id < player.id)))))
    )
    return int(ahead or 0) + 1


# ---------- 기본 ----------

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise err(status.HTTP_503_SERVICE_UNAVAILABLE, "database_unavailable")
    if rooms.task is None or rooms.task.done():
        raise err(status.HTTP_503_SERVICE_UNAVAILABLE, "room_loop_unavailable")
    return {"status": "ready", "version": app.version, "stage_seconds": 60, "room_sizes": [1, 3]}


@app.post("/v1/auth/guest", response_model=AuthResponse)
def guest_login(payload: GuestLoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    player = db.scalar(select(Player).where(Player.device_id == payload.device_id))
    if player is None:
        if db.scalar(select(Player.id).where(Player.display_name == payload.display_name)):
            raise err(status.HTTP_409_CONFLICT, "display_name_taken")
        player = Player(device_id=payload.device_id, display_name=payload.display_name)
        db.add(player)
        try:
            db.commit()
        except IntegrityError:  # 동시 가입으로 이름/기기 중복
            db.rollback()
            raise err(status.HTTP_409_CONFLICT, "display_name_taken")
    else:
        rules.recover_stamina(player)
        db.commit()
    return AuthResponse(access_token=create_access_token(player.id), player=serialize(player))


@app.get("/v1/me", response_model=PlayerResponse)
def me(player: Player = Depends(get_player), db: Session = Depends(get_db)) -> PlayerResponse:
    db.commit()  # recover_stamina 결과 저장
    return serialize(player)


# ---------- 전투 ----------

@app.post("/v1/matches", response_model=StartMatchResponse, status_code=status.HTTP_201_CREATED)
def start_match(payload: StartMatchRequest, player: Player = Depends(get_player_locked), db: Session = Depends(get_db)) -> StartMatchResponse:
    if db.scalar(select(Match.id).where(Match.player_id == player.id, Match.mode.in_(("online1", "online3")), Match.status == "active")):
        raise err(status.HTTP_409_CONFLICT, "online_match_active")
    if player.stamina < rules.GAME_COST:
        raise err(status.HTTP_400_BAD_REQUEST, "not_enough_stamina")
    rules.spend_stamina(player, rules.GAME_COST)

    # 이전에 끝내지 않은 전투는 포기 처리 (체력은 환불하지 않음)
    db.execute(update(Match).where(Match.player_id == player.id, Match.status == "active").values(status="abandoned"))

    stage = player.pve_best_stage + 1 if payload.mode == "pve" else 0
    match = Match(player_id=player.id, mode=payload.mode, stage=stage)
    db.add(match)
    db.commit()
    return StartMatchResponse(match_id=match.id, mode=payload.mode, stage=stage, player=serialize(player))


@app.post("/v1/matches/{match_id}/finish", response_model=FinishMatchResponse)
def finish_match(
    match_id: str,
    payload: FinishMatchRequest,
    player: Player = Depends(get_player_locked),
    db: Session = Depends(get_db),
) -> FinishMatchResponse:
    match = db.scalar(select(Match).where(Match.id == match_id, Match.player_id == player.id).with_for_update())
    if match is None:
        raise err(status.HTTP_404_NOT_FOUND, "match_not_found")
    if match.mode in ("online1", "online3"):
        raise err(status.HTTP_403_FORBIDDEN, "server_owned_match")
    if match.status != "active":
        raise err(status.HTTP_409_CONFLICT, "match_already_finished")

    now = rules.utcnow()
    elapsed = (now - rules.as_utc(match.started_at)).total_seconds()
    ttl = rules.SURVIVAL_TTL_SECONDS if match.mode in ("rush", "bomb") else rules.MATCH_TTL_SECONDS
    if elapsed > ttl:
        match.status = "abandoned"
        db.commit()
        raise err(status.HTTP_409_CONFLICT, "match_expired")

    rating_delta = 0
    diamonds = 0
    won = False
    survival = 0.0

    if match.mode in rules.ARENA_WIN_DIAMONDS:
        # AI arena practice has its own rewards and does not alter ranked PvP.
        won = payload.won
        if won and elapsed < rules.ARENA_MIN_WIN_SECONDS:
            raise err(status.HTTP_400_BAD_REQUEST, "finish_too_early")
        diamonds = rules.ARENA_WIN_DIAMONDS[match.mode] if won else 0
    elif match.mode == "pvp":
        won = payload.won
        if won and elapsed < rules.MIN_WIN_SECONDS["pvp"]:
            raise err(status.HTTP_400_BAD_REQUEST, "finish_too_early")
        before = player.rating
        if won:
            player.wins += 1
            player.rating += rules.PVP_RATING_DELTA
            diamonds = rules.PVP_WIN_DIAMONDS
        else:
            player.losses += 1
            player.rating = max(0, player.rating - rules.PVP_RATING_DELTA)
        rating_delta = player.rating - before
    elif match.mode == "pve":
        won = payload.won
        if won and elapsed < rules.MIN_WIN_SECONDS["pve"]:
            raise err(status.HTTP_400_BAD_REQUEST, "finish_too_early")
        if won:
            player.pve_best_stage = max(player.pve_best_stage, match.stage)
            diamonds = 2 + match.stage
    else:  # rush / bomb : 서버가 잰 경과 시간을 상한으로 사용 (+1초 네트워크 여유)
        survival = min(payload.survival_seconds, elapsed + 1.0)
        diamonds = rules.survival_reward(survival)

    player.diamonds += diamonds
    match.status = "finished"
    match.won = won if match.mode in ("pvp", "pve", "arena1", "arena3") else None
    match.survival_seconds = survival if match.mode in ("rush", "bomb") else None
    match.finished_at = now
    db.commit()

    return FinishMatchResponse(
        mode=match.mode,
        won=won,
        stage=match.stage,
        rating_delta=rating_delta,
        diamonds_gained=diamonds,
        survival_seconds=round(survival, 1),
        player=serialize(player),
    )


# ---------- 경제 ----------

@app.post("/v1/me/upgrade", response_model=PlayerResponse)
def upgrade(player: Player = Depends(get_player_locked), db: Session = Depends(get_db)) -> PlayerResponse:
    cost = rules.upgrade_cost(player.power)
    if player.diamonds < cost:
        raise err(status.HTTP_400_BAD_REQUEST, "not_enough_diamonds")
    player.diamonds -= cost
    player.power += 1
    db.commit()
    return serialize(player)


@app.post("/v1/me/ad-stamina", response_model=AdStaminaResponse)
def ad_stamina(player: Player = Depends(get_player_locked), db: Session = Depends(get_db)) -> AdStaminaResponse:
    # TODO(운영): 클라이언트 신고만 믿지 말고 광고 SDK 의 서버측 검증(SSV) 콜백으로 교체할 것.
    rules.reset_daily_ad_views(player)
    if player.stamina >= rules.MAX_STAMINA:
        raise err(status.HTTP_400_BAD_REQUEST, "stamina_full")
    if player.daily_ad_views >= rules.AD_DAILY_LIMIT:
        raise err(status.HTTP_400_BAD_REQUEST, "ad_limit_reached")
    before = player.stamina
    player.stamina = min(rules.MAX_STAMINA, player.stamina + rules.AD_STAMINA)
    player.daily_ad_views += 1
    db.commit()
    return AdStaminaResponse(recovered=player.stamina - before, player=serialize(player))


@app.get("/v1/leaderboard", response_model=LeaderboardResponse)
def leaderboard(limit: int = Query(20, ge=1, le=100), player: Player = Depends(get_player), db: Session = Depends(get_db)) -> LeaderboardResponse:
    rows = db.scalars(select(Player).order_by(Player.rating.desc(), Player.created_at.asc(), Player.id.asc()).limit(limit)).all()
    entries = [
        LeaderboardEntry(rank=i + 1, display_name=row.display_name, rating=row.rating, is_me=row.id == player.id)
        for i, row in enumerate(rows)
    ]
    my_rank = rank_of(db, player)
    db.commit()
    return LeaderboardResponse(
        entries=entries,
        my_rank=my_rank,
        my_rating=player.rating,
        my_reward=rules.daily_reward_for_rank(my_rank),
    )


@app.post("/v1/me/daily-reward", response_model=DailyRewardResponse)
def claim_daily_reward(player: Player = Depends(get_player_locked), db: Session = Depends(get_db)) -> DailyRewardResponse:
    # TODO: 현재는 "수령 시점 순위" 기준. 어뷰징 방지를 위해 일 단위 정산 배치(스냅샷)로 바꿀 것.
    today = rules.today_key()
    if player.daily_reward_date == today:
        raise err(status.HTTP_409_CONFLICT, "reward_already_claimed")
    rank = rank_of(db, player)
    reward = rules.daily_reward_for_rank(rank)
    if reward == 0:
        raise err(status.HTTP_400_BAD_REQUEST, "no_reward_for_rank")
    player.daily_reward_date = today
    player.diamonds += reward
    db.commit()
    return DailyRewardResponse(rank=rank, reward=reward, player=serialize(player))
