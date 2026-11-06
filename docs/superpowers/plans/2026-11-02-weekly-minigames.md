# Weekly Minigames Implementation Plan

**Goal:** 세 개의 터치 미니게임을 만들고 매주 월요일 00:00 KST에 한 종씩 순환한다.

**Spec:** ../specs/2026-11-02-weekly-minigames-design.md

**Architecture:** 서버는 읽기 전용 주간 일정을 제공한다. Unity의 순수 C# 규칙과 UI·입력을 분리한다. 게임 기록은 서버·계정·주차·종목별 기기 저장소에 보관하고 재화는 바꾸지 않는다.

**Tech Stack:** FastAPI/Python, Unity 6000.3.23f1/C#, IMGUI/New Input System, Android ARM64.

## 독립 작업 경계

- backend: app/training_seasons.py, app/main.py 일정 엔드포인트, tests/test_training_seasons.py.
- 게임 규칙: 활성 Assets/script/TrainingSimulation.cs와 Assets/Editor/TrainingChecks.cs. 범위 1000×400, TrainingKind Range/Drone/Cipher, TrainingSession.Tick/Tap/MoveDrone/PressSignal.
- 통합: 활성 Assets/script/TrainingView.cs·TrainingApiClient.cs, GameBootstrap.cs·LobbyView.cs·GameData.cs. 주간 확인·남은 시간·잠금·입력·결과·일시정지·최고 기록.

## 실행

- [x] 날짜 경계 테스트를 먼저 실패시키고 서버 주간 일정 API를 구현한다.
- [x] 명중·오사·배달·충돌·암호·종료 검사를 먼저 실패시키고 순수 게임 규칙을 구현한다.
- [x] 기존 로비·온라인 출격을 보존하면서 훈련본부·세 게임 UI와 계정별 기록을 연결한다.
- [x] 전체 backend 및 Unity 검사를 실행하고 Android APK를 빌드한다.
- [x] 현재 주 게임의 실제 터치 플레이와 일시정지·결과·복귀를 확인한다. 나머지 주간 종목은 테스트 전용 서버 일정 주입으로 검증하고 실제 달력 전환과 구분한다.
- [x] 캡처·검증 범위·운영 상태를 기록한다.

새 DB 스키마와 재화 보상은 추가하지 않는다. 실제 iOS 빌드·단말 성능과 운영 서버 배포는 이번 범위에 포함하지 않는다.
