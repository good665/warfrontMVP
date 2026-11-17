# 수동 타깃 고정

활성 프로젝트: `C:/Users/good6/WarfrontMVP/Assets` (Unity 6000.3.23f1).

- `Tab` 또는 하단 `타깃 고정` 버튼: 화면 중앙에 가까운 살아 있는 적을 선택. 다시 누르면 해제하며 다른 적으로 자동 전환하지 않음.
- 선택 대상에 금색 표식·이름 강조·상태 안내 표시. 카메라 수평 방향을 부드럽게 추적하고 서버에 보내는 조준 좌표를 대상의 현재 좌표로 보정.
- 좌우 이동·회피는 기존 시점 기준 유지. 고정 중에도 상하 시점과 휠 거리 조절 가능. `Esc`는 고정과 커서 잠금 해제.
- 선택 거리 600 서버 단위(12 Unity 단위), 유지 거리 800(16 Unity 단위). 벽 뒤·화면 밖·사망한 적은 선택하지 않음.
- 대상 사망·소실·거리 이탈·장애물 차단, 플레이어 사망, 지역/인스턴스 변경, 메뉴, 통신 끊김/오래된 응답, 포커스 상실 시 해제.

## 검증

- `red.log`: 구현 전 `Manual target lock missing`으로 실패 확인.
- `checks.log`: 타깃 선택/중앙 우선/고정 해제/시야/실시간 조준/카메라 회전/거리/사망/소실/지역/메뉴/통신/포커스 일시중단 검사 통과. 기존 `ThirdPersonChecks.Run` 및 연결된 캐릭터·애니메이션·UI·MMO·모션·성장 검사도 통과.
- `play-mode.log`, `hud.png`, `scene.png`: 별도 임시 프로젝트의 실제 Play Mode 렌더 확인. 배치 모드는 GUI 캡처를 생성하지 않아 일반 Game 뷰에서 검증함.
- 읽기 전용 독립 코드 검토: 수정 필수 이슈 없음.
- 활성 프로젝트에서 재컴파일 성공 후 실제 공동 사냥터 입장, 화면 버튼으로 고정·추적·해제, 마을 복귀 확인.
- `input.log`: 실제 Unity Input System에 Tab 키 누름·놓기·다시 누름 이벤트를 넣고 `UpdateDungeonLook`를 실행하여 해제·키 놓기 유지·재고정 경로 통과. 운영체제 자동화 도구의 `Tab` 전송은 활성 Editor에서 반응을 확인하지 못했으며 이와 구분하여 검증함.
- 모바일 실제 기기와 신규 Android APK 빌드는 이번 작업에서 수행하지 않음. 모바일용 버튼의 클릭 동작은 Editor에서 확인.

## 적용

수정: `Assets/script/MmoView.cs`, `Assets/script/DungeonFirstPersonView.cs`.
추가: `Assets/script/MmoTargetLock.cs`, `Assets/Editor/TargetLockChecks.cs` 및 새 파일의 `.meta`.

원본 백업: 작업 폴더 `.tools/target-lock/backup-20261108-073731/`.
검증본과 적용본의 SHA-256 일치 확인. 기존 `.meta`, 씬, 서버 규칙, 보상·전투 수치는 유지.

활성 Editor에는 기존 씬의 누락 스크립트 경고 및 Unity AI 구독/네트워크 오류가 관찰됨. 이번 C# 컴파일은 성공했고 플레이 흐름을 확인함.
