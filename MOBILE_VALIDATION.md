# Android 출시 및 두 기기 검증

## 실기기 검증 추가 결과

2026-10-30에 SM-F966N / Android 16 한 대를 연결해 최신 APK를 설치하고 검증했다. 실제 휴대폰의 로그인·터치 이동·공격·스킬·피격·부활·단계 상승·4초 백그라운드 복귀·결과/보상 및 Wi-Fi 공개 HTTPS 대전이 통과했다. 상대는 PC의 독립 HTTP 참가자이며 두 물리 기기 또는 3:3 실기기 검증은 아니다. 표시 문제 2건과 미검증 항목은 [휴대폰 플레이 검증 결과](DEVICE_PLAYTEST.md)에 캡처와 함께 정리했다.

## 최신 네트워크 테스트 APK (2026-10-30)

- `C:\Users\good6\WarfrontMVP\Build\Android\WarfrontMVP-NetworkTest.apk` — 56,282,521바이트. 연결 복구·안전 영역·모바일 버튼·피격 피드백 변경 반영.
- Unity 빌드 성공, 오류 0. 경고 971개가 기록됐으며 기존 `com.unity.ai.inference`의 Sentis 셰이더 변형·성능 관련 경고 등이 포함되어 있다. 패키지를 임의로 제거하지 않았다. 실제 Android 실행 영향은 실기기에서 확인해야 한다.
- ARM64/IL2CPP, 대상 API 36, 개발용 디버그 서명. `apksigner verify`의 v2 검증과 `zipalign -c -P 16 4` 통과. 네이티브 라이브러리 7개의 ELF 16KB 정렬 검사 통과.
- Unity Play 모드와 별도 HTTP 참가자로 60초 단계 상승, 피격·부활, 8초 통신 실패 후 같은 경기 복귀를 확인했다. Android 실기기 실행 결과는 아니다.
- 상세: [개발 검증 기록](DEVELOPMENT_STATUS.md), [상시 테스트 서버 준비](backend/deploy/README.md).

검증일: 2026-10-30. 실제 Unity 프로젝트: `C:\Users\good6\WarfrontMVP` (Unity 6000.3.23f1).

## 완료한 검증

Unity Editor의 실제 `ApiClient`, `UnityWebRequest`, `JsonUtility`를 사용하여 공개 HTTPS 테스트 서버에서 다음 항목을 통과했다.

| 항목 | 1:1 (2클라이언트) | 3:3 (6클라이언트) |
|---|---|---|
| 게스트 로그인, 방 생성·입장·준비 | 통과 | 통과 |
| 자기 플레이어 식별 및 상대 시점 | 통과 | 통과 |
| 상대 클라이언트에서 이동 수신 | 통과 | 통과 |
| 서버 경기 종료, 체력 차감 및 승리 보상 | 통과 | 통과 |
| 난이도 단계 설정 60초 | 통과 | 통과 |

실제 오류도 수정했다. `RoomReadyRequest`의 불필요한 `team` 필드는 서버의 추가 필드 거부 정책에 걸려 준비 요청이 HTTP 422로 실패했다. 해당 필드를 제거한 뒤 위 흐름이 통과했다.

실행: Unity 메뉴 `Warfront > Run Native Online API Check`, 테스트 서버의 `connection.json` 선택.
결과: Unity 프로젝트 `Build/Validation/unity-native-check.json`.
테스트 계정 정리: 저장소에서 `python backend/tools/cleanup_native_check.py C:\Users\good6\WarfrontMVP\Build\Validation\unity-native-check.json`.

이는 한 Unity Editor 프로세스에서 수행한 통신 검증이다. 휴대폰 두 대의 플레이 화면, 터치 조작, 프레임 속도 또는 서로 다른 이동통신망 검증 결과가 아니다.

## 실제 기기에서 남은 검증

초기에는 ADB 연결 기기가 0대였으며, 이후 한 대를 연결해 위 실기기 검증을 수행했다. 두 휴대폰 동시 플레이를 검증하려면 두 번째 독립 기기가 필요하다.

## 이전 테스트 APK

- 파일: `C:\Users\good6\WarfrontMVP\Build\Android\WarfrontMVP-DeviceTest.apk` (56,282,633바이트).
- Unity 빌드 성공: 오류 0, 경고 1. 보고서: 같은 폴더 `device-build-report.json`.
- Manifest 확인: 패키지 `com.good665.warfrontmvp.dev`, 최소 API 25, 대상 API 36, `arm64-v8a`, `INTERNET` 권한 포함.
- `apksigner verify --verbose`: 검증 성공, v2 서명. 디버그 서명이며 Play 업로드용 서명이 아니다.
- `zipalign -c -P 16 4`: 종료 코드 0.
- 포함된 ARM64 네이티브 라이브러리 7개의 ELF LOAD 세그먼트가 16KB 정렬 조건 통과. 검사 도구: `backend/tools/check_apk_pages.py`.
- 위 정렬 검사는 16KB 페이지 크기의 실제 Android 기기 실행을 대체하지 않는다.
- 별도 `Assets/Scenes/WarfrontDeviceTest.unity`만 빌드했다. 첫 설치는 서버 설정 화면에서 시작하며 공개 서버 주소만 안내하고 초대 키는 APK에 넣지 않는다.
- 설치 SDK의 Build Tools 폴더명이 잘못돼 사용자 임시 폴더 `%TEMP%\warfront-android-sdk`에 도구를 준비했다. 한글 경로에서는 CMake 실행이 실패하여 영문 임시 경로로 옮긴 뒤 성공했다. 빌드 함수는 `-warfrontSdk <SDK 경로>`를 지원하며 종료 시 기존 SDK 선택과 앱 설정을 복원한다.

아래는 전체 실기기 검증 절차다. 한 대에서 완료한 부분과 남은 부분은 최신 [실기기 보고서](DEVICE_PLAYTEST.md)를 기준으로 구분한다.

1. 두 기기에 테스트 APK를 설치한다. 각 기기에 서버 URL과 초대 키를 입력한다. 초대 키는 APK에 포함하지 않는다.
2. A에서 1:1 방을 생성하고 B에서 코드로 입장한다. 양쪽 준비 후 이동·공격·피격·스킬·점수·종료 화면이 서로 일치하는지 확인한다.
3. 한 기기는 Wi-Fi, 다른 기기는 모바일 데이터로 바꿔 인터넷 대전을 확인한다.
4. 홈 화면 전환, 복귀, 화면 잠금, 네트워크 끊김 및 재연결 시 동작과 서버의 이탈 판정을 확인한다.
5. 화면 비율과 안전 영역, 두 손가락 동시 입력, 발열·프레임 속도를 확인한다.
6. 60초를 넘겨 단계 상승을 직접 확인한다. 현재 자동 검증은 설정값 확인이며 60초 실시간 플레이 검증은 아니다.
7. 3:3 전체 실기기 플레이에는 6개의 독립 플레이어 클라이언트가 필요하다. 휴대폰 두 대만으로 6명의 화면·조작을 모두 검증할 수 없다.

## Play Store 준비

실기기 검증과 Play Console의 배포 요구사항은 별도로 확인한다.

- [대상 API 정책](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en): 2026-08-31부터 일반 Android 신규 앱·업데이트는 API 36 이상을 대상으로 해야 한다. 제출 시점에 정책을 다시 확인한다.
- [신규 개인 계정 테스트 요건](https://support.google.com/googleplay/android-developer/answer/14151465?hl=en): 해당 계정은 최소 12명의 테스터가 연속 14일 참여하는 비공개 테스트 및 프로덕션 접근 신청이 필요하다.
- [16KB 페이지 크기 지원](https://developer.android.com/guide/practices/page-sizes): Unity와 포함된 네이티브 라이브러리의 호환성을 확인한다.
- 출시용 고유 패키지 ID, 업로드 키와 서명된 AAB, 개인정보처리방침, 데이터 보안 설문, 콘텐츠 등급 및 스토어 등록정보를 준비한다.
- 현재 임시 테스트 서버는 PC가 켜져 있어야 한다. 정식 출시 전 지속 운영 서버와 계정 복구·운영 정책을 마련해야 한다.

테스트 APK는 `com.good665.warfrontmvp.dev`, ARM64/IL2CPP, API 36, 개발 빌드와 디버그 서명을 사용하도록 준비했다. 이는 출시용 패키지 ID나 업로드 키를 확정한 것이 아니다. 빌드 결과와 실기기 결과는 각각 확인해야 한다.
