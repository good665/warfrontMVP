# 3인칭 전투 시점 적용

활성 프로젝트: `C:/Users/good6/WarfrontMVP/Assets/script`.

- 캐릭터가 보이는 후방 추적 카메라, 기본 거리 5.6, 시야각 60도.
- 마우스/터치 회전, 시점 기준 이동과 전방 공격을 유지. 휠로 거리 3.5–8 조절.
- 서버 장애물과 외곽 벽의 확장된 경계를 검사하여 카메라를 즉시 당기고, 공간이 생기면 부드럽게 복원.
- 1인칭 화면용 무기를 숨기고 기존 캐릭터 이동·공격·회피 애니메이션 표시.
- 필드·마을 안내를 3인칭으로 변경.

변경 파일: `RetroFantasyScene.cs`, `DungeonFirstPersonView.cs`, `FantasyTownView.cs`, `MmoView.cs`. 기존 `.meta`와 씬 유지. 공유 이동 계산 클래스 이름과 이전 검사용 FirstPerson 메서드는 호환성을 위해 유지.

검증:

- 변경 전 검사: `Third person follow camera missing`로 실패 확인.
- 변경 후 Unity 6000.3.23f1 배치 검사 통과: 캐릭터 표시, 4방향 구도, 전방 조준 정렬, 벽 회피, 마을 카메라 복원.
- MiniDungeonChecks.All에서 호출하는 기존 캐릭터 리그·애니메이션·UI·MMO·모션·시뮬레이션 검사 통과.
- 별도 임시 프로젝트의 실제 Play Mode 렌더 검사 통과. `third-person.png`는 생성된 실제 렌더.
- 활성 Unity Editor에서 마을과 공동 사냥터의 변경된 표시 확인. 키 입력 자동화로 Esc 메뉴 복귀는 확실히 확인하지 못했으며, 카메라 마을 복원은 네이티브 검사로 확인.
- 모바일 실제 기기 조작은 미검증.

원본 백업: 작업 폴더 `.tools/third-person/backup-20261108-055807/`.
서버 규칙, 전투 밸런스, 스킬 로직 변경 없음.

## 위쪽 시점 제한 수정

사용자 제보: 사냥터에서 마우스로 위를 볼 수 없음.
원인: 마우스, 터치, 카메라 렌더 단계 모두 pitch를 8~48도로 제한하여 수평 및 위쪽 시야가 막힘.
수정: 세 경로를 -35~48도로 변경. 올려다볼 때 궤도 카메라가 지면 아래로 내려가지 않도록 최소 높이 0.3을 기준으로 카메라 거리를 줄임.
회귀 검사: -35/-15/0/48도 × 거리 3.5/5.6/8 조합에서 요청한 실제 카메라 각도와 지면 높이를 확인. 수정 전 `requested -35, actual 8`로 실패했고 수정 후 기존 검사와 함께 통과.
수정 파일: `DungeonFirstPersonView.cs`, `RetroFantasyScene.cs`, `Assets/Editor/ThirdPersonChecks.cs`.
