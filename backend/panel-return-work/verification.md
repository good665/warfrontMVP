# 닫기·취소 시 마을 복귀 개선

- 활성 프로젝트 `C:/Users/good6/WarfrontMVP/Assets/script`의 `MmoView.cs`, `MmoEquipmentPanel.cs`, `MmoControlSettings.cs` 수정.
- 장비·소지품, 캐릭터·퀘스트, 3인칭 안내의 닫기 버튼을 공통 `CloseMmoPanel()`에 연결.
- 마을에서 열린 창은 닫을 때 화면을 Lobby로 전환하고 기존 캐릭터/장비 프로필을 보존.
- 진행 중인 저장·조회는 기존 요청 큐로 완료 후 복귀. 전장에서 열었던 창은 서버 퇴장 경로로 마을 복귀.
- 마을 계열 화면에서 연 조작 설정의 취소도 마을로 복귀. 전투 중 조작 설정 취소는 기존대로 전투 유지.
- Unity 컴파일 성공. `TownPanelReturnChecks`: 기존 미구현 실패를 확인한 후 수정 적용, PASS (2026-11-13 10:19 KST).
- 실제 Unity Play 모드에서 장비·소지품 → 닫기 → 마을, 캐릭터·퀘스트 → 닫기 → 마을, 3인칭 조작 안내 → 닫기 → 마을을 모두 확인.
- 원본은 `original/`, 설치 전 백업은 `backup-*`에 보존. 기존 `.meta`, 서버와 DB는 변경하지 않음.
