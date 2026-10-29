# Warfront FastAPI 서버

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
