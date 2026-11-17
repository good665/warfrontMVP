# Five-floor headquarters battle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 사람이 실제로 참가하는 1:1 및 컴퓨터 본진 대전에 동일한 5층 전장을 제공한다.

**Architecture:** 기존 인증·방·고정 20Hz 루프를 유지하고 새 `FiveFloorGame`을 연결한다. 이전 시뮬레이션은 회귀 검증용으로 보존한다. Unity는 현재 층만 렌더링하며 서버 층·포탈 전환 상태에 따라 등장 연출을 재생한다. 모델·점프에는 판정이나 루트 이동 권한이 없다.

**Tech Stack:** FastAPI, Python, pytest, Unity 6000.3.23f1, C# / URP.

**Spec:** ../specs/2026-11-14.md 및 사용자의 후속 확정 답변.

## Global Constraints
- 활성 Unity의 Assets/script를 먼저 읽고 패치하며 레거시 사본을 덮어쓰지 않는다.
- 계정·영구 장비 데이터는 삭제하지 않고 폐기 모드의 진입을 종료한다.
- 5층, 양방향 포탈, 층당 캠프 3개(쫄병 2+중간보스 1), 캠프 재생성 없음.
- 3층 용은 처치 180초 후 재생성, 개인 랜덤 버프 90초(공격 10%, 체력 10%, 속도 8% 중 하나), 중첩 없음.
- 미니언은 기존 외형으로 본진 중앙·양끝에서 30초마다 출격한다.
- 아이템 9칸, 경기 한정, 서버 누적 유효 피해량 1위에게 1회 지급. 동률은 먼저 기여한 개인.
- 12간지 동물 캐릭터, Q 일반 스킬 / E 필살기 / 좌클릭 기본공격 / Space 연출 점프.
- 사용자가 세부 판단을 위임하고 즉시 실행을 요청했으므로 추가 설계 승인 대기는 생략한다.

## Review Focus
- 다른 층 공격·회복·전리품 가로채기 차단.
- 입력 재전송·포탈 왕복·보상 중복 방지.
- 포탈 반대편 도착 직후 자동 재진입 방지.
- 인벤토리가 가득 찬 개인의 교체 선택은 서버가 검증.
- 두 실제 인증 클라이언트의 입장·상태 공유·승패 및 연결 종료.

### Task 1: Authoritative battle
**Files:** create app/five_floor_game.py, app/zodiac_rules.py, tests/test_five_floor.py; modify app/squad_rooms.py, app/squad_bot.py, app/squad_routes.py.
**Interfaces:** game exposes heroes, units, bases, camps, input(pid,data), tick(dt), snapshot(pid,code,now), strategy_snapshot(team); compatible with existing room lifecycle.
- [ ] Write and run failing tests for floor isolation, bidirectional portal cooldown, 15 finite camps, damage ownership, inventory replacement, dragon timer, 30-second waves, 12 skills, replay rejection.
- [ ] Implement deterministic clocked game and schema fields. Connect both human and computer room creation.
- [ ] Run targeted pytest then full pytest; update only obsolete expectations where requested new behavior replaces old behavior.

### Task 2: Unity flow and art
**Files:** active Assets/script/{SquadView,SquadModels,MmoModels,MmoView,FantasyTownView,NovemberBattleHud,RetroFantasyScene}.cs; new FiveFloor UI/scene files; new Editor/ZodiacAssetBuilder.cs and generated Resources/Zodiac assets.
**Interfaces:** snapshot five_floor metadata, floor/character/jump/transition actor fields, inventory and pending drop; input character, portal_delta, jump, replace_slot.
- [ ] Stage precise changes from active sources and retain file hashes for conflict protection.
- [ ] Add character selector, live skill labels, 9-slot inventory, floor/dragon/wave HUD and portal up/down controls.
- [ ] Remove retired mode menu/landmark entries and guard old entry points; keep saved account data.
- [ ] Generate 12 distinctive low-poly skinned animal meshes, UV palette, native material, rig, clips and prefabs plus dragon model. Animate from server state.
- [ ] Install active Assets edits with required filesystem approval, compile in Editor, inspect scene and capture evidence.

### Task 3: End-to-end verification
**Files:** tests/test_five_floor_online.py, README.md; progress.md alongside plan.
- [ ] Verify two real HTTP clients create/join, choose animals, share server floor state, play and settle victory; computer uses ordinary input.
- [ ] Run full backend suite and Unity compilation; review complete change once independently.
- [ ] Record results and limitations, no deployment or account data removal.
