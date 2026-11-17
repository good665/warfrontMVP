# RTS Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 기존 5층 전투를 1:1·2:2 단일 격자 전장으로 교체한다.
**Architecture:** 서버가 명시적 팀·소유권과 전투를 판정하고 Unity는 선택·명령 및 표현을 담당한다. 기존 로그인·방 API를 확장하며 활성 Unity 프로젝트에 적용한다.
**Tech Stack:** FastAPI/Python, Unity 6000.3.23f1/C#, Input System.
**Spec:** backend/docs/superpowers/specs/2026-11-15-rts-replacement-design.md

## Global Constraints
- Unity 변경은 C:/Users/good6/WarfrontMVP/Assets 아래에서 수행한다. 기존 .meta와 서버 연동을 보존한다.
- 128×128 전장, 1:1 및 2:2, 초기 근접 3명·원거리 2명, 자동 충원 없음.
- 기존 12종 모델·기술을 재사용하고 서버가 명령 권한을 검증한다.

## Review Focus
- 동맹·적 유닛 ID 위조 명령 거절: Task 1.
- 네 번째 참가 전 시작 또는 1:1·2:2 큐 혼합 방지: Task 2.
- 팀원 한 명 이탈과 팀 전체 이탈 구분: Task 2.
- 삭제·교체된 유닛 선택 및 부대 참조 정리: Task 4.
- UI 위 클릭·해상도 변경·시점 전환으로 선택 좌표 또는 입력이 어긋나지 않음: Task 4.

### Task 1: 서버 전장 및 유닛 지휘
Files: create backend/app/rts_game.py, backend/app/rts_map.py, backend/tests/test_rts_game.py.
Interfaces: RtsGame(ids, team_size=1, seed=None), tick(dt), input(pid, data), snapshot(pid, code, now), battle_snapshot(pid). 기존 방에서 호출하는 인터페이스를 유지한다.
- [ ] 테스트: 2명/4명 팀과 본진 배치 대칭, 플레이어당 초기 병력 5명, 60초 후 자동 증원 없음, 적·동맹 명령 거절, 본진 승패 및 영웅 부활.
- [ ] python -m pytest tests/test_rts_game.py 실행으로 실패 확인.
- [ ] 기존 전투·12종 기술을 재사용하되 층·포탈·몬스터 성장 의존성을 제거한 단일 전장 구현. 타일당 서버 50단위, Unity 1단위로 6400×6400 서버 좌표를 사용한다. 동시 양 팀 본진 파괴는 무승부, 지휘할 생존 유닛이 없는 플레이어는 관전한다.
- [ ] 위 테스트 통과 확인.

### Task 2: 방·팀·봇 및 API
Files: modify backend/app/squad_rooms.py, backend/app/squad_routes.py, backend/app/squad_bot.py; create backend/tests/test_rts_rooms.py.
Interfaces: 요청 team_size=1|2, 응답 team_size/capacity/members(owner_id,team,base_id), 입력 unit_ids/command/order_x/order_y. 기존 요청은 team_size=1로 처리한다.
- [ ] 테스트: 2인/4인 정원, 모드별 큐 분리, 참가 중복·초과 거절, 명시적 팀 배정, 30초 이탈 유예와 팀 전체 이탈 판정, 봇 충원.
- [ ] 실패 확인 후 방 생성·입장·상태·이탈·봇 처리에 새 전투 연결.
- [ ] 해당 테스트 및 python -m pytest 전체 실행.

### Task 3: Unity 맵 및 로비 연결
Files under active Assets/script: new RtsMapView.cs, RtsBattleView.cs; modify SquadModels.cs, SquadApi.cs, SquadView.cs, FantasyTownView.cs, FiveFloorBattle.cs.
Interfaces: 응답 RTS 판별 필드와 team_size/members/unit owner_id, 128×128 논리 격자와 16×16칸 청크 메시.
- [ ] Editor 검사: 맵 경계·본진 대칭·서버 좌표 변환, 청크 개수와 전체 조망 카메라.
- [ ] 실패 확인 후 본진·자원 표시, 탑뷰 카메라, 1:1·2:2 로비 선택, 기존 포탈·층 UI 교체.
- [ ] 컴파일과 서버 연결·전투 진입 검사.

### Task 4: 선택·부대·카메라·집결
Files under active Assets/script: new RtsSelection.cs, RtsUnitIdentity.cs, RtsCommandInput.cs; modify StrategicBattleView.cs, SquadStrategyView.cs, SquadLifecycle.cs.
Interfaces: 선택 ID 목록을 unit_ids로 전송. RenderTexture 화면 영역과 전투 카메라로 Raycast/화면 좌표 변환. 유닛 식별은 owner_id/team/kind 사용.
- [ ] 검사: 클릭·Shift·박스·동종 선택, 적 정보 확인, 1~9 부대 저장·호출·연속 호출, 제거된 유닛 정리, UI 차단과 화면 크기 변경.
- [ ] 선택용 Collider, Canvas 선택 박스(Raycast Target=false), 선택 링 구현.
- [ ] RTS 우클릭 이동·공격, Tab 시점 전환, G 핑과 자신의 AI 집결 구현. RTS 영웅 우클릭 이동 지원, WASD 입력 시 해당 이동 명령 취소.
- [ ] Editor에서 실제 입력·카메라·핑 반응 및 콘솔 오류 확인.

### Task 5: 통합 검증 및 인계
- [ ] 1:1 두 클라이언트, 2:2 네 클라이언트로 팀·소유권·명령·승패 일치 검증.
- [ ] Unity 컴파일 및 캐릭터 교체·죽음·재시작 회귀 검사.
- [ ] 변경 범위 검토 후 검사 결과와 재현 절차를 validation/rts-replacement-2026-11-15에 기록.
- [ ] 실제 게임 화면을 확인하고 완료 범위·남은 제한을 보고한다.
