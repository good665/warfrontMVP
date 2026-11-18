# 분대전 맵: 골목 + 실내 건물 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 분대전(1:1/2:2) 평지 맵을 골목·물길·건물이 있는 대칭 맵으로 바꾸고, 영웅만 들어갈 수 있는 실내 층(보급 상자, 지름길)을 추가한다.

**Architecture:** 정적 맵은 서버 `rts_map.py`가 단일 원천이다. 통행 불가 칸 집합을 층별로 계산하고, `rts_path.py`의 A*·시야선으로 이동/전투를 막는다. 실내는 판 밖 좌표(x ≥ 6800)에 놓고 `floor`로 구분한다. 클라이언트는 `GET /v1/squad/map`을 한 번 받아 형상을 그린다.

**Tech Stack:** FastAPI, pytest(백엔드) / Unity 6000.3, C#(`C:\Users\good6\WarfrontMVP\Assets\script`)

**Spec:** `docs/superpowers/specs/2026-11-18-squad-map-interiors-design.md`

## Global Constraints

- 1칸 = 50 서버 단위, 바깥 128×128칸(`EXTENT = 6400`), 바깥 경계 `35..EXTENT-35`
- 바깥 floor = 1, 사분면 집 floor 2~5, 지름길 건물 floor 6~7
- 실내 원점 x ≥ 6800. 모든 실내 좌표 < 8400
- 영웅만 문 통과, 재진입 대기 1초
- 상자: 60초 재생성, 보상 = 체력 전부 회복 / `speed_left = 20` / 공격 +30% 30초
- 맵은 x축, y축 두 축 모두에 대해 대칭
- 기존 `backend/tests` 전부 통과

## Review Focus

1. 문 바로 앞에 유닛이 몰려 문 칸이 막힘 → `separate_units`는 영웅을 벽 안으로 밀지 않는다(Task 3 테스트)
2. 문 칸을 목표로 찍은 일반 유닛 → 가장 가까운 열린 칸에서 멈추고 진동하지 않는다(Task 3)
3. 실내에서 죽은 영웅 → 바깥 본진에서 floor 1로 부활한다(Task 4)
4. 실내 영웅의 조준(aim)이 판 밖 좌표 → 입력 검증이 거부하지 않는다(Task 4, `SquadInput` 범위 8400)
5. 스킬 돌진(`dash`/`charge`)으로 벽 통과 → `move()`를 거치므로 막힌다(Task 3)

---

### Task 1: 정적 맵 데이터 (`rts_map.py`)

**Files:** Modify `backend/app/rts_map.py` · Test `backend/tests/test_rts_map.py`

**Produces:**
- `OUTDOOR = 1`
- `cell(x: float, y: float) -> tuple[int, int]` (50 단위 칸)
- `blocked(floor: int, cx: int, cy: int) -> bool` (경계 밖도 True)
- `sight_blocked(floor, cx, cy) -> bool` (물은 False, 벽·경계 밖은 True)
- `bounds(floor) -> tuple[float, float, float, float]` (x0, y0, x1, y1 서버 단위)
- `DOORS: list[dict]` — `dict(floor, cx, cy, to_floor, to_x, to_y)` 양방향 각각 한 항목
- `CHESTS: list[dict]` — `dict(id, floor, x, y)`
- `map_payload() -> dict` — `dict(version, outdoor=[dict(kind, x, y, width, height)], buildings=[...], interiors=[dict(floor, x, y, rows: list[str])], doors=DOORS, chests=CHESTS)`

- [ ] 테스트 작성: `test_map_is_symmetric`(바깥 `blocked`가 `(cx,cy)`, `(127-cx,cy)`, `(cx,127-cy)`에서 같음), `test_starts_and_center_open`(각 `STARTS` 주변 반경 8칸과 중앙 3×3이 열려 있음), `test_outdoor_connected`(BFS: STARTS[0]에서 다른 STARTS, 중앙, 모든 바깥 문 칸에 도달), `test_interiors_connected`(실내마다 모든 문·상자에 도달), `test_doors_pair_up`(각 문의 to 좌표가 목적 층에서 열린 칸이고, 그 근처에 반대 방향 문이 있음), `test_interiors_off_board`(실내 bounds x0 ≥ 6800, x1 ≤ 8400)
- [ ] 실패 확인: `python -m pytest tests/test_rts_map.py -v`
- [ ] 구현: 사분면(0..63칸) 직사각형 목록을 x·y 대칭으로 4배 복제한다. 집은 `wall`, 물길은 `water`, 다리는 물 위 열린 칸. 문은 건물 벽에서 1칸 비워 둔 칸이며 바깥에서 그 칸을 밟으면 실내로 이동한다. 실내는 ASCII(`#` 벽, `.` 바닥, `D` 문, `C` 상자) 2종(집, 지름길)이고 floor별로 y를 띄워 배치한다.
- [ ] 통과 확인, 커밋 `backend: add squad map layout with interiors`

### Task 2: 길찾기·시야선 (`rts_path.py`)

**Files:** Create `backend/app/rts_path.py` · Test `backend/tests/test_rts_path.py`

**Consumes:** Task 1 `blocked`, `sight_blocked`, `cell`
**Produces:**
- `nearest_open(floor, x, y) -> tuple[float, float]` (칸 중심 좌표)
- `find_path(floor, sx, sy, gx, gy) -> list[dict]` — 시작 칸 제외, 칸 중심 `dict(x,y)` 목록. 마지막 점은 원래 목표(열린 칸이면) 또는 `nearest_open`. 같은 칸이면 `[]`
- `line_clear(floor, ax, ay, bx, by) -> bool` — 25 단위 간격으로 샘플링해 `sight_blocked` 검사

- [ ] 테스트: 벽을 사이에 둔 두 점의 경로가 벽 칸을 지나지 않고 목표에 도달, 대각선 모서리 통과 없음, 막힌 목표는 가장 가까운 열린 칸으로, `line_clear`가 벽에서 False·물 위에서 True
- [ ] 구현: 8방향 A*(heapq, 옥타일 휴리스틱), 대각 이동은 인접 두 직교 칸이 모두 열려야 함. 결과 경로는 시야선으로 웨이포인트를 줄인다(string pulling).
- [ ] 통과 확인, 커밋 `backend: add grid pathfinding and line of sight`

### Task 3: 이동·충돌·경로 따라가기

**Files:** Modify `backend/app/rts_game.py`(`move`, `input`, `command_tick`), `backend/app/rts_spacing.py`, `backend/app/rts_waves.py` · Test `backend/tests/test_rts_collision.py`

**Consumes:** Task 1·2
**Produces:** 유닛 필드 `_path: list[dict]`, `_path_goal: tuple`, `_repath_at: float`. 헬퍼 `RtsGame.walk(unit, gx, gy, speed, dt)` — 경로가 없거나 목표가 바뀌면(0.5초마다 재검사) `find_path`, 첫 웨이포인트로 `move`, 도착하면 pop

- [ ] 테스트: `test_move_slides_along_wall`, `test_move_never_enters_blocked`(무작위 1000회 `move` 후에도 막힌 칸 아님), `test_dash_stops_at_wall`, `test_ordered_unit_walks_around_building`(벽 너머 목표에 60초 안에 도달), `test_waves_reach_enemy_base`(1:1에서 첫 웨이브가 150초 안에 적 본진 반경 380 안에 들어감), `test_separation_keeps_out_of_walls`, `test_unit_ordered_onto_door_stops_nearby`
- [ ] 구현: `move()` 클램프를 `bounds(a['floor'])`로 바꾸고, 다음 칸이 막혔으면 x만→y만 시도. `command_tick`의 이동과 `wave_tick`의 웨이포인트 이동은 `walk` 사용. 일반 유닛에게 문 칸은 막힌 칸이다(Task 1 `blocked`는 문을 열린 칸으로 두고, `move`에서 `kind != 'hero'`이면 문 칸도 막힘으로 판정). `separate_units`/`avoid_heroes`는 결과 칸이 막혔으면 적용하지 않는다. `input()`의 `order_x/y` 클램프는 그대로 둔다(바깥 전용 명령).
- [ ] `python -m pytest` 전체 통과, 커밋 `backend: collide squad units with map walls`

### Task 4: 문·상자·시야선 전투·스냅샷·맵 엔드포인트

**Files:** Modify `backend/app/rts_game.py`, `backend/app/rts_combat.py`(`stats`), `backend/app/squad_routes.py` · Test `backend/tests/test_rts_interiors.py`

**Consumes:** Task 1~3
**Produces:** 영웅 필드 `door_cooldown`, `attack_left`; 게임 필드 `chests: dict[id, dict(ready_at)]`; 스냅샷 `floor = 영웅 floor`, 스냅샷 `chests=[dict(id, floor, x, y, ready)]`(보는 층 것만); 이펙트 kind `door`, `chest`; `GET /v1/squad/map` → `map_payload()`(`/{code}`보다 먼저 등록)

- [ ] 테스트: `test_hero_enters_and_exits_door`(floor·좌표 변경, 1초 안 재진입 없음), `test_minion_cannot_enter_door`, `test_passage_connects_two_sides`, `test_chest_reward_and_respawn`(열면 60초 동안 닫힘, 보상 3종 중 하나 적용, `attack_left` 시 `stats()['attack']` ×1.3), `test_walls_block_hero_attack`(벽 너머 적에게 피해 0), `test_dead_hero_respawns_outdoor`, `test_snapshot_floor_follows_hero`, `test_map_endpoint`(HTTP 200, `interiors` 6개), `test_input_accepts_interior_aim`(aim_x 8000 허용)
- [ ] 구현: `hero_tick` 끝에서 문/상자 검사. 공격 대상 필터에 `line_clear` 추가(영웅 기본 공격, `command_tick`, 웨이브 적 탐지, 본진 포탑). 부활 시 `floor=1`. `SquadInput.aim_x/aim_y` 상한 8400.
- [ ] `python -m pytest` 전체 통과, 커밋 `backend: add squad doors, chests and wall line of sight`

### Task 5: Unity 클라이언트

**Files:** Modify `SquadApi.cs`, `SquadModels.cs`, `MmoModels.cs`, `RtsBattleView.cs`, `FantasyTownView.cs`, `WorldFogVisibility.cs` · Create `SquadMapView.cs` (모두 `C:\Users\good6\WarfrontMVP\Assets\script`)

**Consumes:** Task 4 엔드포인트와 스냅샷 필드

- [ ] `SquadApi.SquadMapAsync()`과 `SquadMap` DTO(`map_payload` 구조 그대로, JsonUtility 호환 배열)
- [ ] `RtsBoard(SquadMap map)`: 칸 메쉬 색으로 잔디·길·물 구분, `wall`/건물 위치에 기존 `Model()` 키트(`wall`, `column`, `banner`, `barrel`, `chest`) 배치, 실내는 판 밖 좌표에 바닥·벽·문 표시
- [ ] 보는 층: 영웅 floor. 실내에서 Tab을 누르면 바깥 보기(카메라를 내 본진에 고정), G 집결은 화면 중앙에. 아군도 보는 층이 아니면 숨김. `RtsGround` 클램프를 보는 층의 bounds로 변경
- [ ] 실내에 있는 동안 바깥 본진이나 유닛 hp가 감소하면 상단 경고 표시
- [ ] 상자 열림/닫힘 표시, 문 표시
- [ ] Unity 에디터 확인: 1:1 컴퓨터 대전에서 진입·퇴장, 지름길, 상자, Tab, 골목 교전. 2:2 화면 확인
- [ ] 커밋(백엔드 저장소 아님. Unity 프로젝트에는 git이 있을 때만)
