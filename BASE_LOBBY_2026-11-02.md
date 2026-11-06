# WARFRONT 군사 기지 로비 구현·검증

2026-11-02. 사용자 선택에 따라 픽셀 군사 기지 로비를 활성 Unity 프로젝트에 구현하고 Android 휴대폰에 설치했다. 서버 API와 경기 규칙은 변경하지 않았다.

## 화면과 기능

- 상단: 지휘관 이름, 서버에서 받은 체력·다이아·랭킹, 체력 회복 시간, 광고 보상 사용 횟수와 서버 설정.
- 중앙: 1:1 AI 훈련장, 온라인 지휘본부, 정비 격납고, 3:3 AI 분대 막사, 전적 게시판.
- 하단: 체력 10 소모를 표시한 돌격·폭탄·PvE 버튼과 온라인 대전 출격 버튼.
- 시작 연결 중·연결 실패 화면에도 같은 배경을 표시한다. 안전 영역 안의 기존 1280×720 조작 좌표를 유지하며, 넓은 여백에는 어두운 기지 배경을 채운다.

주요 코드: `C:/Users/good6/WarfrontMVP/Assets/script/LobbyView.cs`, 기존 `GameBootstrap.cs`의 로비·연결 화면. 배경: `Assets/Resources/BaseLobby.png`. 기존 GameBootstrap은 워크스페이스의 `.tools/base-lobby-backup-20261102/`에 백업했다. 이 저장소의 legacy Unity 사본은 변경하지 않았다.

배경은 built-in image_gen으로 생성했다. [전체 프롬프트와 저장 경로](docs/superpowers/specs/2026-11-02-base-art-prompt.md)를 보관했다. 그림에는 기능 문구를 넣지 않고 실제 Unity 버튼과 자원 값을 얹었다.

## 검증 결과

| 항목 | 결과 |
|---|---|
| 최종 Unity 컴파일·회귀 검사 | `60 arena checks passed`, 종료 코드 0 |
| 백엔드 전체 검사 | 64개 통과 |
| 최종 Android 빌드·업데이트 설치 | 성공, 오류 0, 경고 971. 기존 패키지 셰이더 경고 등이 남아 있음 |
| 1:1 훈련장·3:3 막사 | 기존 역할 선택 화면 진입·로비 복귀 통과. 출전 전 체력 소모 없음 |
| 정비 격납고·전적 게시판 | 정비소·실제 서버 랭킹 진입·복귀 통과. 강화·일일 보상은 누르지 않음 |
| 서버 설정·온라인 지휘본부 | 설정 취소·로비 복귀·온라인 메뉴 진입 통과 |
| 연결 실패·복구 | 경기 종료 후 USB 경로를 끊고 재실행해 배경·오류·재시도 표시 확인. USB 복구 후 로비 정상 진입 |
| 온라인 3:3 | 휴대폰 1대 + HTTP 참가자 5명, 세 역할과 여섯 캐릭터 상태·피해·처치·부활 수신 확인 |
| 3:3 3단계 HUD | 서버 122.1초의 화면에서 온라인 위험 구역 안내 확인 |
| 3:3 팀 정산 | 135.3초에 HTTP 상대 한 명을 계획적으로 퇴장. `forfeit`, 승리 팀 1, 정산 완료. HTTP 보상 `[0,5,0,5,0]`, 휴대폰 +5 |
| 임시 계정 정리 | 3:3 각 시도의 임시 HTTP 계정 5개만 정리. 사용자 계정·실제 경기 기록 유지 |
| 런타임 오류 확인 | 검사한 앱 프로세스의 최근 최대 1500개 로그에서 크래시·ANR·OOM·NullReference/MissingReference 패턴 0건 |

첫 3:3 시도는 약 119초에 기록 도구의 Windows 파일 교체 잠금 충돌로 조기 종료됐다. 게임 오류로 분류하지 않았으며, 기록 실패가 경기를 중단하지 않도록 재시도 처리를 추가한 뒤 재검증했다. 첫 시도도 상대 퇴장 승리로 정산되어, 두 3:3 테스트 합계 체력 20 소모·다이아 10 지급이 실제 테스트 계정에 반영됐다. 최종 로비는 체력 50·다이아 24·랭킹 1000으로 확인했다.

이번 3:3은 **상대 퇴장 종료** 검사다. 600점 자연 종료 또는 여섯 명 실사용자 대전으로 보고하지 않는다. 앞서 [별도 1:1 검증](DEVICE_PLAYTEST_2026-11-02.md)에서 420점 자연 종료를 확인했다. 이번 경로는 USB 역방향 포트를 통한 로컬 전용 서버이며 인터넷 HTTPS나 모바일 데이터 검증이 아니다.

한 시점의 메모리는 PSS 614,056KiB(약 600MiB)였다. 장시간 FPS·발열·배터리나 누수 합격 판정은 하지 않았다. 두 휴대폰 동시 플레이, 여섯 명 실플레이, 접기·펼치기와 모바일 데이터 전환은 남아 있다.

## 산출물과 캡처

최종 설치 APK: `C:/Users/good6/WarfrontMVP/Build/Android/WarfrontMVP-BaseLobby.apk` (79,804,654바이트, ARM64/IL2CPP 개발 빌드). `BaseLobbyTest.apk`는 첫 검토용 빌드이며 최종본과 구분한다. 휴대폰에는 최종 `BaseLobby.apk`를 설치했다.

- [최종 기지 로비](validation/base-lobby-2026-11-02/lobby.png)
- [1:1 역할 선택](validation/base-lobby-2026-11-02/ai1-setup.png), [3:3 AI 역할 선택](validation/base-lobby-2026-11-02/ai3-setup.png)
- [정비소](validation/base-lobby-2026-11-02/workshop.png), [랭킹](validation/base-lobby-2026-11-02/ranking.png)
- [온라인 3:3 시작](validation/base-lobby-2026-11-02/online3-start.png), [3단계 HUD](validation/base-lobby-2026-11-02/online3-stage3.png), [결과](validation/base-lobby-2026-11-02/online3-result.png)
- [연결 실패](validation/base-lobby-2026-11-02/connection-error.png), [복구 후 최종 로비](validation/base-lobby-2026-11-02/lobby-restored.png)
- [검증 요약](validation/base-lobby-2026-11-02/summary.json), [산출물 해시](validation/base-lobby-2026-11-02/artifacts.json)

종료 상태: 사용자 계정과 로비 유지, 임시 HTTP 참가자 정리 완료. 로컬 테스트 서버와 USB 포트 `18082` 연결은 유지했으므로 USB와 서버를 켜두면 계속 접속할 수 있다. 공개 HTTPS 터널은 열지 않았다.
