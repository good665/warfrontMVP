# Simple Online Match Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline.

**Goal:** 온라인 화면을 두 모드의 자동 매칭과 안전한 취소로 단순화한다.

**Architecture:** 기존 OnlineView partial에 요청·취소 의도를 추가하고 기존 API를 재사용한다. 매칭 UI는 별도 partial OnlineMatchView.cs에 둔다. 서버 규칙은 바꾸지 않는다.

**Tech Stack:** Unity 6000.3.23f1, C#, IMGUI, 기존 FastAPI quick-match API.

**Spec:** ../specs/2026-11-02-simple-online-match-design.md

- [x] 현재 활성 소스를 백업한다. LobbyView, OnlineView, GameBootstrap을 수정하고 OnlineMatchView를 추가한다.
- [x] 로비 설정 버튼 제거·개발 전용 오류 설정·두 모드 UI·취소 의도와 응답 유실 복구를 연결한다.
- [x] 기존 검사와 취소 경합 테스트를 실행하고 새 Android APK를 빌드한다.
- [x] 단말에서 대기 취소와 실제 자동 시작을 확인하고 한계와 캡처를 기록한다.

검토에서 대기 만료·영구 4xx 오류의 무한 대기 위험을 수정했다. 근거는 ../../../SIMPLE_MATCH_2026-11-02.md. 최종 Unity 60개·백엔드 64개 통과, Android 오류 0. 실제 단말과 로컬 지연·오류 주입으로 취소와 상태 복구를 확인했다.
