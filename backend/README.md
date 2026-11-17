# Warfront FastAPI 서버

## 단일 전장 RTS 및 거점 웨이브

현재 분대 대전은 6400 × 6400 단일 전장에서 1:1 또는 2:2로 진행한다. 사람 대전은 `/v1/squad/create` + `/join` 코드 초대 또는 `/queue` 빠른 매칭으로 참가하고 정원이 모여야 시작한다. `/v1/squad/computer`는 같은 규칙으로 컴퓨터와 대전한다.

- 각 플레이어의 살아 있는 거점에서 경기 시작 30초 후, 이후 30초마다 수호병 3명·궁수 2명이 자동 생성된다. 게임 시작 시에는 영웅과 거점만 배치하며, 미니언은 첫 웨이브부터 생성한다.
- 자동 병력은 거점 앞 → 중앙 → 적 거점 앞 → 적 거점을 순서대로 이동한다. 주변 적과 교전한 뒤 경로 이동을 재개한다. 목표 거점 파괴 시 가장 가까운 생존 적 거점으로 재지정하며, 경기 종료 후에는 생성하지 않는다.
- 선택한 병력에 내리는 직접 명령과 G 집결은 자동 이동보다 우선한다. G 집결은 선택 여부와 관계없이 내 미니언 전체에 적용하고, 이후 생성되는 웨이브도 마지막으로 지정한 집결 지점으로 이동한다. 집결 이동 중이나 도착 후 주변 적을 만나면 자동으로 교전하고, 적이 사라지면 집결 지점으로 복귀한다. 이동·집결·교전 중 미니언끼리 약 80 서버 단위(1.6 Unity 단위)의 간격을 유지하고, 영웅을 밀어내지 않고 돌아서 이동한다. 컴퓨터의 일반 호위병 명령은 웨이브 병력의 경로를 덮어쓰지 않는다.
- 좌클릭/드래그로 선택, 우클릭으로 이동·집중 공격, Ctrl+1~9 부대 지정, Tab 시점 전환, G 집결을 사용한다. 캐릭터의 Q/E 능력, 1인칭 좌클릭 공격·Shift 회피, Space 연출 점프를 유지한다.
- `battle.next_wave`가 다음 생성까지 남은 초를 제공한다. 일시정지 중 서버 경기 시간과 웨이브 타이머도 정지한다.
- 5층 전투와 일반 분대 본진전의 실행 코드·전용 UI·전용 테스트를 삭제했다. RTS가 사용하던 배우 상태·피해·12간지 능력은 `app/rts_combat.py`, 웨이브는 `app/rts_waves.py`로 분리했다. 포털·경기 아이템·구 생산/연구 입력은 더 이상 받지 않는다.

검증: `python -m pytest`. Unity 메뉴 `Warfront > RTS > Run Integration Checks`, `Check Waves And Retired Mode Cleanup`으로 서버 스냅샷의 소유권·미니언 표시·이동·일시정지 입력 초기화를 확인한다. `python tools/generate_rts_wave_fixtures.py`로 테스트 자료를 생성한다. 후자는 임시 폴더의 `warfront-rts-wave-before.json`, `warfront-rts-wave-after.json` 테스트 스냅샷을 사용한다. 12간지 캐릭터 모델과 능력 시각 효과를 유지하며 기존 에셋·장면·설정은 보존한다.

인터넷 친구 테스트는 [FRIEND_TEST_SERVER.md](../FRIEND_TEST_SERVER.md)를 참조하세요. `tools/friend_server.py`는 전용 DB·생성된 비밀값·초대 접속키를 사용하며, 기존 개발 DB와 별개로 실행합니다.

플레이어 상태를 저장하고 JWT로 인증하는 API 서버입니다. 활성 Unity 프로젝트는 `C:\Users\good6\WarfrontMVP`이며, 로그인·전투·보상·랭킹을 이 API에 연결합니다. 이 워크스페이스의 `Assets/Scripts/`는 이전 MVP 사본입니다.

## 실행

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

개발 중 PostgreSQL이 없으면 기본 SQLite 데이터베이스로 실행됩니다. PostgreSQL을 사용하려면 `env.example`을 `.env`로 복사한 뒤 `docker compose up -d`를 실행합니다.

## 현재 API

- `GET /health` — 서버 상태
- `POST /v1/auth/guest` — 게스트 가입 또는 로그인 (`device_id`, `display_name`)
- `GET /v1/me` — 인증된 플레이어 상태
- `POST /v1/matches` — 체력 소모 및 전투 시작
- `POST /v1/matches/{match_id}/finish` — 전투 결과 반영
- `POST /v1/me/upgrade` — 다이아를 사용한 강화
- `POST /v1/me/ad-stamina` — 테스트 광고 체력 회복
- `POST /v1/me/daily-reward` — 일일 랭킹 보상
- `GET /v1/leaderboard` — 점수 순위

로그인 이외의 `/v1` API는 `Authorization: Bearer <access_token>` 헤더가 필요합니다. 게스트 식별자는 계정 접근에 사용되므로 공개하지 않습니다. 전투 결과는 현재 MVP용 클라이언트 보고 방식으로, 실제 출시 전 서버 권한 검증이 필요합니다.

전투 모드는 기존 `pvp`, `pve`, `rush`, `bomb` 외에 AI 연습용 `arena1`(1:1), `arena3`(3:3)을 지원합니다. AI 연습은 승리 시 각각 다이아 3개/5개를 지급하며 랭킹 점수와 PvP 전적을 변경하지 않습니다. 승리는 최소 서버 경과 시간 60초 후에만 보고할 수 있고, 전투 만료 시간은 30분입니다. 종료 요청의 `won`을 사용하며, 생존 시간 기반 보상은 지급하지 않습니다. 기존 데이터베이스 컬럼을 그대로 사용합니다.

## 온라인 친선전 API

서버 전투 계산을 사용하는 사람 간 1:1·3:3입니다. 상세 접속 안내는 [ONLINE_PLAY.md](../ONLINE_PLAY.md)에 있습니다. 전투 단계는 서버 시간 60초마다 상승하며, 방은 메모리에 있으므로 `--workers 1`로 실행합니다.

- `POST /v1/rooms` — `{ "role": 0, "team_size": 1 }`로 방 생성. `team_size`는 1 또는 3.
- `GET /v1/rooms/current` — 자기 방 복구.
- `POST /v1/rooms/quick-match` — `{ "role": 0, "team_size": 1 }`로 경기 크기별 자동 대기열 참가. 실제 인원이 모이면 자동 시작.
- `POST /v1/rooms/{code}/join` — `{ "role": 0 }`로 코드 입장.
- `GET /v1/rooms/{code}` — 참가자에게만 상태·전투 스냅샷 제공.
- `POST /v1/rooms/{code}/ready` — `{ "ready": true, "role": 0 }`. 전원 준비 시 체력을 한 번 차감하고 시작.
- `POST /v1/rooms/{code}/input` — `sequence`, `move_x/y`, `aim_x/y`, `attack`, `dodge`, `skill1/2`만 허용.
- `POST /v1/rooms/{code}/leave` — 대기실 나가기 또는 경기 중 팀 포기. `{ "waiting_only": true }`는 대기 취소와 경기 시작이 겹쳐도 포기하지 않고 현재 상태를 반환.

이 API도 Bearer 토큰이 필요합니다. 역할 번호는 돌격 0, 수호 1, 지원 2입니다. 위치·체력·결과를 입력에 넣으면 422로 거부합니다. 온라인 기록의 내부 모드 `online1`/`online3`는 일반 `/v1/matches` 시작·결과 제출로 조작할 수 없습니다. 친선전 승리 팀 각자에게 다이아 3개/5개를 한 번 지급하고 랭킹·기존 PvP 승패는 변경하지 않습니다. 서버가 종료·재시작되면 방은 사라지고 미정산 경기의 체력을 환급합니다.

방 루프는 [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)에서 시작·정리합니다. 20Hz 서버 계산과 약 10Hz HTTP 입력·상태 교환을 사용하는 개발용 구현입니다. 빠른 대전은 비공개 방과 분리된 경기 크기별 대기열이며, 대기 취소·연결 종료 시 남은 참가자를 유지합니다. 공용 방 저장소, 다중 서버, 랭크 기반 매칭과 외부 배포는 별도 작업입니다. 추가 패키지나 데이터베이스 컬럼 변경은 없습니다.

실제 네트워크 검증: `python tests/check_online_live.py`. 임시 서버·DB와 2개/6개의 HTTP 클라이언트를 사용하며 기존 계정과 데이터를 건드리지 않습니다.

Warfront backend (FastAPI + PostgreSQL)
cd backend
cp env.example .env
docker compose up -d db
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
python -m pytest            # 테스트는 SQLite 로 실행됨

마이그레이션 (Alembic)
alembic init migrations
# migrations/env.py 에서 target_metadata = Base.metadata, sqlalchemy.url = settings.database_url 로 설정
alembic revision --autogenerate -m "init"
alembic upgrade head
# 이후 .env 의 AUTO_CREATE_TABLES=false

## Windows ??? ??

?? ??? `backend/.venv`? ?????. ???? ????:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q
.\.venv\Scripts\python.exe -m pytest
```

???? ?? SQLite DB? ??? ?? JWT ?? ?????. ?? DB? ???? ????.
Starlette ??? ?????? `httpx2`? ???? ?????.

## Weekly training calendar

Authenticated `GET /v1/training/season` returns all three available games in `active_games`: `range`, `drone`, `cipher`. All three open every week, each lasting 45 seconds, with independent rankings and weekly rewards. Seasons change Monday 00:00 Asia/Seoul and settle at 00:10. The legacy `active_game`, `next_game`, and `rotation` fields remain for older clients and legacy record identity; they no longer limit game availability. The calendar endpoint does not create matches, spend stamina, grant rewards, or store scores.

Send `{"game":"drone"}` (or `range` / `cipher`) to `POST /v1/training/runs`; an omitted game retains the old default. Query `GET /v1/training/leaderboard?game=drone` for that game's board. Run responses and reward items contain their canonical `season_id`; use it unchanged for results, historical boards and claims. Original weekly games preserve their existing week-only ID, seed, scores and claim markers; additional leagues use week-game IDs such as `2026-W45-drone`. Suffixed aliases of the original game resolve to the same claim marker, preventing duplicate credits. Historical board queries can include both `season_id` and `game`.

Each game's rewards remain 30 diamonds for first place, 20 for ranks 2–3, 10 for ranks 4–10 and 3 for other positive-score participants. Claims are once per account/game/week, valid for 28 days after settlement. The reward history can contain up to 30 entries. Existing single-active-run and replay validation rules still apply. Tests: `tests/test_training_seasons.py`, `tests/test_training_league.py`, `tests/test_training_three_games.py`.

## 첫 플레이·분석·공용 훈련 순위

기존 DB에는 먼저 백업 후 [성장 기능 스키마 적용](deploy/growth-schema.md)을 실행한다. 새 환경은 기존 `AUTO_CREATE_TABLES` 설정을 따른다. 운영 배포를 자동 실행하는 절차는 아니다.

- `GET/POST /v1/experience`: 안내 단계·완료/건너뛰기·분석 동의. 분석은 기본 비동의이며 안내 진행 저장과 독립적이다.
- `POST /v1/experience/events`: 동의 계정만 허용된 클라이언트 이벤트를 최대 50개씩 수집한다. 서버 경기 정산 이벤트와 출처를 분리한다.
- `POST /v1/training/runs`, `POST /v1/training/runs/{id}/finish`, `POST /v1/training/runs/{id}/cancel`: 서버 발급 시드·v2 입력 재계산·중복 제출 복구. 클라이언트 점수는 받지 않는다.
- `GET /v1/training/leaderboard`, `GET /v1/training/rewards`, `POST /v1/training/rewards/{season_id}/claim`: 상위 50명·내 순위·주간 보상 1회 지급. 시즌은 월요일 00:00 KST 교체, 00:10 이후 확정, 보상 수령 기한은 확정 후 28일이다.

최근 7일 운영 지표를 읽기만 하는 명령:

```powershell
.\.venv\Scripts\python.exe -m tools.player_metrics --days 7
```

분석은 동의 계정 중 관측된 표본이며 지연 이벤트는 전환·리텐션에서 제외한다. 일별 KST 코호트, 모드별 완료율, 첫 게임 전환·재도전·D1, 매칭 지표를 JSON으로 출력한다. `--prune`은 30일이 지난 원시 이벤트를 삭제하는 별도 운영 작업이므로 보관 정책에 따라 명시적으로 실행한다. 최초 관측 기준 시각은 최소 메타데이터로 유지한다.

전체 설계·검증 기록은 [플레이어 성장 기능](../PLAYER_GROWTH_2026-11-04.md)에 있다.

## Persistent action RPG (MMO v1)

The additive `/v1/mmo` API uses existing bearer tokens and keeps RPG progression
in `mmo_avatars`; legacy player balances, matches and training data are untouched.
The fixed client protocol is documented in `../docs/superpowers/specs/2026-11-07-mmo-api.md`.

Development `AUTO_CREATE_TABLES` registers the new table automatically. With
production automatic schema creation disabled, back up the database and run the
following explicit additive migration from `backend/` before starting the server:

```powershell
.\.venv\Scripts\python.exe -m app.mmo_schema
```

This command creates `mmo_avatars` if missing and adds the nullable quest state
column when needed; it never drops or resets tables. Back up existing data first.
Run exactly **one Uvicorn worker/process** for this API. Shared enemies, parties,
party dungeon instances and input/cooldown state are process-local. SQL stores
character HP, XP, level, gold, equipment, inventory, cumulative kill count and
quest stage and varied quest progress. A server restart preserves those SQL values but rebuilds world/party
sessions. Horizontal multiworker hosting requires a separate shared simulation
service and is not supported by this implementation.

Simulation ticks at 20 Hz. Inputs expire in 0.35 seconds, repeated input sequences
cannot refresh them, and request traffic cannot accelerate server time. A long
server stall drops elapsed time beyond two seconds rather than simulating a large
catch-up burst. No state/input heartbeat for 30 seconds releases the zone slot;
re-entering preserves in-process HP/cooldowns/sequence. Dead avatars revive after
five active world seconds. Re-entry, role changes and equipment changes do not
heal. Starter role currently changes avatar appearance; combat base stats and
skills are shared across roles.

Frontier and minefield each hold 32 active players. Ruins are scoped to solo
identity or an invite-code party of at most four. Party mutation moves that player
out of ruins immediately; re-enter to join the current party instance. Standard
enemies respawn after 12 seconds and the boss after 45 seconds. Damage contributors
still in the same zone receive server-issued rewards once per kill. Inventory is
bounded to 100 items; XP and gold continue when full. Equipment is account-owned,
upgrades cost `50 * (rank + 1)` gold, with rank capped at 20. Existing cumulative hunt
quests retain their `5 * stage` goal until claimed, then enter the varied quest
cycle described below. Each stage can be claimed once. All mutations are
serialized by the single world process lock, including simultaneous quest claims.

Validation: `python -m pytest tests/test_mmo_world.py` exercises shared state,
authoritative combat/loot, replay and silence protection, no re-entry healing,
SQL restart persistence, party isolation, authentication, request validation,
inventory ownership, and concurrent once-only quest claims. This is functional
validation, not a measured production load/capacity claim.


### MMO quest state additive migration

Before deploying the updated backend, stop writers and run `python -m app.mmo_schema`
from `backend/` against the intended database, then start the backend. This command
creates missing MMO tables and adds nullable `mmo_avatars.quest_state` (JSON) when
absent; it never resets players, kills, stages, inventory, or rewards. Back up the
database through the normal deployment process first. Re-running is safe.
Existing rows retain NULL quest state and continue their existing cumulative
`hunt-{quest_stage}` objective, including any earned progress and rewards. On its
next successful claim, that character enters the persisted hunt / elite / explore /
boss cycle. New quest progress is tracked on the server in the same transaction as
combat rewards and HP. No startup migration is implicit.

Quest snapshots retain id/title/progress/target/ready and add kind, zone,
description, x, y, reward_xp, reward_gold. Hunt and elite goals recommend frontier
while accepting qualifying kills from other zones. Explore goals require physically reaching
within 100 units of the indicated server waypoint (frontier 1200,1800 or minefield
3000,1900); elite goals require guard kills and boss goals require ruins boss kills.
Enemy snapshots add windup_left, windup_duration, attack_radius, attack_x, attack_y,
and stagger_left. A normal strike telegraphs for 0.7 seconds with radius 90; a boss
strike telegraphs for 1 second with radius 150. The strike center stays fixed and
dodging is immune. Effect kinds enemy_attack and player_damage report impact.

### Squad headquarters PvP

`/v1/squad` adds a separate, non-ranked real-human 1v1 mode. `GET /current`,
`POST /queue`, `POST /create`, `POST /join` (`code`), `GET /{code}`,
`POST /{code}/input`, and `POST /leave` use the existing bearer authentication.
Two humans are required; no bot replaces an absent opponent. Use one server
process, as with the existing in-memory online rooms. Server restarts end these
temporary sessions. No new database schema or RPG currency/gear mutations occur.

Each player starts alone. Their own camp at (800,1200) or (2800,1200) recruits a
guard, archer and healer within radius 120. Lost companions can be replenished at
the camp after 12 seconds; heroes respawn after 8 seconds. Commands are `gather`,
`focus`, `hold`, and `retreat` (or `none` for no new command). Inputs carry a
monotonically increasing sequence, expire after 0.35 seconds, and cannot modify
another room. Hold keeps its world anchor and formation; companions route around
the authoritative obstacles with a collision-padded visibility graph.

Headquarters have 2200 HP, defensive fire, and do not respawn. Destroy the enemy
headquarters to win; simultaneous destruction or the 15-minute time limit draws.
Leaving an active match forfeits, and 30 seconds without a participant heartbeat
causes a distinct disconnect outcome. Finished results remain recoverable briefly.
`GET /ready` also checks the squad simulation loop. Run `python -m pytest` for all
regressions, including actual-input headquarters victory, recruitment, formation,
pathfinding, commands, room isolation, replay handling, respawn and disconnect.

#### Computer opponent

`POST /v1/squad/computer` with `{}` starts an immediate match against the standard
server-controlled commander. Snapshots add `mode` (`computer` or `pvp`) and
`opponent_name`; `/current` recovers the same match. Repeated creation requests
reuse the existing waiting/active room rather than silently replacing it.

The computer starts alone, recruits at its own camp, attacks/defends headquarters,
retreats at low health, and replenishes companions through the same timers. It
submits ordinary expiring controls, with the same stats, cooldowns and damage
rules as humans. Its room-local `bot:` identifier is not a database player or
queue member; other players cannot join that room or authenticate as the bot.
Only the human heartbeat can cause a connection-loss result. Human matchmaking
continues to require two real players and never substitutes a computer.

This mode requires a running server and is not an offline Unity simulation.
No database migration, persistent computer account or RPG reward change is added.
# MMO equipment loadouts

Run `python -m app.mmo_schema` before starting an existing deployment to add
`helmet`, `helmet_rank`, `active_loadout`, and JSON `loadouts` columns without
resetting existing characters. On first access, existing equipment is copied into
all three saved sets; starter inventory stays at two items. Loot cycles through
weapon, armor, and helmet. Helmet power and helmet upgrades add maximum HP.

`POST /v1/mmo/equip` accepts `{"item_id":"...","loadout":0}`; omit `loadout`
to edit the active set. `POST /v1/mmo/loadout` with `{"index":0}` activates a set
(indices 0–2). `/v1/mmo/upgrade` accepts slot `helmet` as well as `weapon` and
`armor`; upgrade ranks belong to the character slot and apply across all sets.
Profiles include `equipped_helmet`, `helmet_rank`, `active_loadout`, and `loadouts`
containing weapon/armor/helmet item IDs. Empty helmet uses an empty string.
Changing active equipment updates live stats and clamps current HP downward;
switching sets never heals or revives the character.





