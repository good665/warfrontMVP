# Military Base Lobby Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement inline.

**Goal:** 건물 중심의 픽셀 군사 기지 로비와 시작 화면을 구현하고 단말에서 확인한다.

**Architecture:** 기존 GameBootstrap partial 구조에 LobbyView를 추가한다. 건물 클릭은 기존 메서드로 연결하며 데이터는 GameData 서버 캐시를 읽는다. 생성 배경은 Resources에서 한 번 로드한다.

**Tech Stack:** Unity 6000.3.23f1, C#, IMGUI, Android ARM64/IL2CPP.

**Spec:** ../specs/2026-11-02-military-base-lobby-design.md

## Constraints and review

- 활성 프로젝트 C:/Users/good6/WarfrontMVP/Assets만 수정. legacy Assets/Scripts는 사용하지 않는다.
- 자원은 서버 값으로 표시하고, 기능 진입 자체로 체력을 소모하지 않는다.
- 긴 프로필명, 안전 영역, 버튼 겹침, 연결 실패, 기존 메뉴 복귀를 단말에서 확인한다.

## Tasks

- [x] 픽셀 기지 배경 생성·저장·확인. Assets/Resources/BaseLobby.png로 복사한다.
- [x] Assets/script/LobbyView.cs 구현. DrawBaseLobby(), DrawBaseBackdrop()으로 배경과 UI를 분리한다.
- [x] GameBootstrap.DrawLobby()를 연결하고 DrawConnecting()에도 배경을 표시한다.
- [x] Unity 기존 검사 실행 후 새 이름의 Android 테스트 APK를 빌드한다.
- [x] 단말에서 주요 건물 버튼·온라인 메뉴·로비 자원을 검증하고 캡처와 한계를 기록한다.

완료 근거: ../../../BASE_LOBBY_2026-11-02.md. 검토에서 즉시 출전의 체력 소모 문구와 보상 횟수 표시 누락을 찾아 복원했다. 최종 소스 검사 60개·백엔드 64개 통과. 최종 APK 오류 0, 경고 971. UI 변경에는 구현을 그대로 복제하는 테스트를 추가하지 않고 기존 검사와 실제 기기 흐름으로 확인했다.
