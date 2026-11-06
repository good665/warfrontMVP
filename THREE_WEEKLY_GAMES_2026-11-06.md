# 주간 미니게임 3종 동시 공개

사용자 결정: 지휘관 사격장(range), 드론 보급 작전(drone), 통신 암호 해독(cipher)을 매주 모두 공개하고 게임별 공용 순위와 주간 보상을 독립 운영한다.

## 동작

- 훈련본부의 카드 3개에서 종목을 고르고 공용 경쟁 또는 개인 연습을 시작한다.
- 순위 화면에는 종목별 탭을 제공한다. 각 게임 점수는 해당 게임의 순위에만 반영한다.
- 보상 목록에 게임 이름을 표시하고 계정·게임·주차별 한 번씩 수령한다.
- 각 게임 보상은 기존과 동일하다: 1위 30, 2~3위 20, 4~10위 10, 나머지 양수 기록 참가자 3 다이아.
- 한국 시간 월요일 00:00 새 시즌, 00:10 이후 순위 확정, 확정 후 28일 수령.
- 무료 플레이, 45초 진행, 서버 입력 검증, 계정당 활성 실행 하나, 재전송·중복 수령 방지를 유지한다.

## 기존 데이터 호환

기존 주간 순환 게임은 주차 ID와 seed를 그대로 사용한다. 추가 두 게임은 `2026-W45-drone` 같은 독립 ID를 사용한다. 기존 게임의 접미사 별칭은 기존 ID로 정규화하여 보상을 다시 받지 못하게 한다. 기존 실행·기록·청구 내역은 이동하거나 삭제하지 않는다.

`active_games`는 모든 공개 종목이다. 구버전용 `active_game`·`next_game` 필드는 기본 종목과 기존 기록 식별용으로 유지한다. 새로운 클라이언트는 시작 요청의 `game`과 순위 조회의 `game`을 전달한다.

PostgreSQL은 `python -m tools.apply_growth_schema`로 시즌 키 네 컬럼을 VARCHAR(16)으로 확장해야 한다. SQLite에는 기존 길이 제한이 없어 별도 테이블 재생성이 없다. 테스트 서버에는 검증된 SQLite 백업을 만든 뒤 스키마 도구를 적용했다. PostgreSQL 데몬 검증은 미실시다.

## 변경 위치와 검증

활성 Unity 변경은 `C:/Users/good6/WarfrontMVP/Assets/script/`의 TrainingView, TrainingLeagueView, TrainingApiClient, TrainingRewardValidation에 적용했다. Editor/TrainingLeagueChecks도 보상 30개를 검사하도록 확장했다. 이전의 돌격·폭탄 난이도 30초 설정을 보존했다.

- 백엔드 전체 pytest: 171개 통과. 새 API 검사는 종목별 리플레이·순위 격리·세 보상 독립 지급·재청구·기존 별칭 호환·30개 보상 창을 포함한다.
- 활성 런타임 C# 컴파일: 오류 0, 기존 미사용 필드 경고 1.
- 실제 Unity 6000.3.23f1 격리 실행: 픽셀 에셋 검사 5 + 성장 기능 검사 184(League 39) = 189개 통과, 종료 코드 0.
- 공개 HTTPS 서버에서 실제 게스트 로그인, 달력 3종 공개, 각 게임 시작·취소·분리된 순위 조회 확인. 검증 계정만 정리했다. `.tools/three-weekly-games-20261106/live-check.json`에 비밀값 없는 결과가 있다.
- 독립 코드 검토: 차단할 결함 없음. PostgreSQL 실제 적용과 Unity 화면 조작은 검토 범위 밖이다.

검증용 격리 프로젝트는 누락된 Input System을 활성 프로젝트의 기존 패키지 캐시로 연결했다. 활성 프로젝트의 Packages 설정은 변경하지 않았다. 원본 Unity 수정 전 백업은 `.tools/three-weekly-games-20261106/before/`에 보관했다.

실제 휴대폰 설치·화면 조작 검증과 PostgreSQL 실행 검증은 별도로 남아 있다. 임시 테스트 서버 재시작으로 접속 주소가 바뀌었으므로 `backend/.test-server/connection.json`의 최신 주소와 기존 테스트 접속키를 사용한다. 접속키는 APK에 포함하지 않는다.

## Android APK

[새 개발용 APK](validation/three-weekly-games-2026-11-06/WarfrontMVP-ThreeWeeklyGames.apk): ARM64 / IL2CPP, API 36, 개발용 서명. 빌드 성공(오류 0, 경고 2), 실제 파일 48,733,596바이트, ZIP CRC 검사 통과. 활성 C# 소스 전체가 빌드 프로젝트의 소스와 일치하고 두 생존 모드의 난이도 주기가 30초임을 확인했다. [검증 보고서](validation/three-weekly-games-2026-11-06/verification.json).

테스트 서버 주소는 `https://receiver-spin-creation-noon.trycloudflare.com`이다. Unity와 APK의 저장된 접속 주소는 자동 변경하지 않았으므로 오류 화면의 서버 접속 설정에서 최신 주소를 저장한다. 임시 서버는 PC와 서버 프로세스가 켜져 있어야 접속할 수 있다.
