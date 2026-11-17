# 포물선 화살과 느린 걷기

- 활성 Unity 프로젝트: `C:/Users/good6/WarfrontMVP`.
- 화살 표현은 시작점/끝점을 유지하면서 `4 * height * t * (1-t)` 높이를 더한다. 화살촉은 곡선의 접선 방향을 따른다. 서버의 평면 명중 판정과 피해 타이밍은 유지한다.
- 일반 영웅 이동 235 → 175, 활 발사/당기기 이동 110, 동료/일반 분대 210 → 155, 정찰병 285 → 210.
- 걷기 애니메이션 재생 속도 0.65, 전환 시간 0.20초. 위치/방향은 지수 보간한다. 신규 생성, 큰 위치 보정, 회피는 즉시 위치를 반영한다.
- Bow는 torso 하위에만 적용하는 상체 레이어를 사용한다. 하체 Walk/Idle을 함께 샘플링하며 발사 종료 시 Bow를 중지한다.
- 변경한 Unity 파일: `Assets/script/RetroFantasyScene.cs`, `RetroSquadCompanions.cs`, `RetroSquadCombat.cs`, 신규 `GentleArcheryMotion.cs`, `Assets/Editor/GentleArcheryChecks.cs`.
- 기존 Unity 스크립트 백업: `%TEMP%/warfront-gentle-archery/backup`.

## 검증

- Unity 스크립트 컴파일 성공. `GentleArcheryChecks` 에디터 검사 PASS: 포물선 시작/정점/착지, 상승/하강 방향, 렌더링 객체의 중간 높이, 발사 중 걷기 레이어 유지, 종료 시 상체 해제.
- 백엔드 이동/발사/충돌 43개 통과. 봇/분대/이동 26개 통과(이동 테스트 2개 중복).
- 전체 백엔드: 324 passed, 13 failed. 남은 실패는 기존 경로 탐색용 불완전 actor fixture 8개, 대형 유지 1개, 동료 전투 좌표 기대값 4개다. 이전 비교 실행에서도 실패한 항목이다.
- 실제 플레이에서 장시간 조작감 평가 및 모바일 기기 검증은 수행하지 않았다.
