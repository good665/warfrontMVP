# 2026-11-13 구현·검증 기록

## 적용 내용

- 활성 Unity: `C:/Users/good6/WarfrontMVP/Assets/script` 및 `Assets/Editor`.
- HP 0: 0.65초 동안 쓰러지며, 0.45초부터 투명도를 낮춰 1.25초에 완전 소멸. 부활 시 기존 재질과 애니메이션 복구. 반복 스냅샷은 연출을 재시작하지 않음.
- 서버가 전멸한 생산 분대를 즉시 삭제해도 아군 시체는 연출 종료까지 유지. 적 시야 이탈의 기존 fog 처리 보존.
- 사망 중에도 마우스·터치 시점 회전 허용. 이동·공격·명령은 서버와 클라이언트에서 차단 유지.
- 전투 상단 제목/캐릭터·본진 HP 문구 제거. 전투 필드 높이 572, 중앙 하단 스킬, 화면 오른쪽 끝 하단 3×3 지휘 패널. 조작 설정에서 지휘 패널과 고정 메뉴 영역을 침범하지 못하도록 검증.
- 장비: 투구/방어구/주무기 삼각형 배치, 실시간 캐릭터 프리뷰, 가방 종류 필터, 아이템 비교·장착·강화, 장비 세트 3개 서버 저장·전환.
- 기존 장비는 처음 접근할 때 세 세트에 복제하여 보존. 투구는 세 번째 처치부터 전리품 순환에 포함. 강화 수치는 슬롯별로 세 세트 공통.
- 스타일: 돌/목재 프레임, 보라색 룬·금속 외형, 픽셀 지형 텍스처를 마을·전투·장비 화면에 적용. 기존 스킨 메시·리그·클립 기반이며 새 비트맵 외부 의존성 없음. 전달 형식은 C# 소스와 런타임 생성 Mesh/Texture2D/Material.
- 검증 중 발견한 실제 동료 이동 정체와 좌표 탐색 호환 문제도 수정.

## 검증 결과

1. `backend`에서 `python -m pytest -q`: **355 passed in 55.20s**.
2. 실제 Unity 6000.3.23f1에서 런타임/Editor 어셈블리 컴파일 성공.
3. `NovemberCombatChecks`: **PASS**, 마지막 결과 2026-11-13 09:55:34 KST.
   - 사망 중간 자세, 최종 비표시, 반복 사망의 멱등성, 부활 복원.
   - 삭제된 아군의 시체 유지, 사망 시 카메라 허용.
   - 스킬/지휘 영역, 메뉴 위 커스텀 버튼 거부, 마을 장비 프리뷰 유지.
   - 기존 `ThirdPersonChecks`, `SquadCursorChecks`, `HeroBowChecks`, `CornerCommandChecks` 함께 통과. ThirdPersonChecks를 통한 MiniDungeon/MMO/GameMotion 검사도 통과.
4. `NovemberNetworkChecks`: **PASS**.
   - 기존 서버와 분리한 127.0.0.1:58741 + 별도 SQLite에서 실제 Unity ApiClient/JsonUtility 사용.
   - 로그인, 투구 장착·강화, 세 세트 전환, 전투 중 능력치 갱신·무료 회복 방지, 재접속 저장 유지 확인.
   - 검증 서버는 종료함. 테스트 전용 DB는 이 작업 폴더의 `e2e-*.db`.
5. Unity 화면에서 장비 배치, 하단 HUD, 쓰러지는 중간 모습과 완전 소멸을 육안 확인.
6. 설치한 C# 소스가 작업용 사본과 일치함을 SHA256으로 확인. 기존 `.meta`와 원본 씬/Packages/ProjectSettings는 수정하지 않음.
7. 별도 코드 검토에서 발견한 버튼 겹침과 분대 소멸 문제를 수정하고 재검토함.

## 백업과 실행

- 최초 원본: `original/`, 첫 설치 직전 사본: `installed-backup-20261113-093515/`. 이후 설치별 백업도 보존.
- Unity에서 `Warfront > November > Preview Equipment And Battle`로 화면 확인 가능. Play 모드 진입 시 미리보기의 임시 오브젝트와 카메라는 정리됨.
- 검사 메뉴: `Warfront > November > Check Combat And Equipment`.
- 네트워크 검사는 작업 폴더의 `run_e2e.py`로 독립 검증 서버를 먼저 실행해야 함.

## 기존 서버에 적용할 때

공개 테스트 서버와 기존 PostgreSQL에는 배포·마이그레이션하지 않았다. 기존 서버의 쓰기 작업을 정지한 뒤, 그 서버와 같은 DATABASE_URL 환경에서 `python -m app.mmo_schema`를 실행하고 서버를 재시작해야 새 장비 API를 사용할 수 있다. 추가 마이그레이션은 기존 캐릭터/골드/인벤토리를 삭제하지 않으며 반복 실행 가능하다.

Android 실기기/새 APK 빌드는 이번 검증 범위에 포함하지 않았다.

## 인벤토리 SQL 오류 현장 복구 (2026-11-13 10:04 KST)

- 사용 중인 PostgreSQL에서 신규 열 4개 누락을 실제 확인.
- 임시 폴더 `warfront-inventory-backups`에 pg_dump 형식으로 캐릭터 테이블을 백업한 뒤 additive migration 적용.
- 기존 열의 모든 값이 적용 전후 동일함을 확인. 캐릭터 1개와 보유 장비 100개 보존.
- 실행 중인 localhost:8000의 해당 캐릭터 `/v1/mmo/profile`: HTTP 200, 인벤토리 100개와 장비 세트 3개 반환 확인. 서버 재시작 없이 정상 조회됨.
- 관련 MMO 회귀 테스트 24 passed.
- 위의 '기존 PostgreSQL에는 마이그레이션하지 않았다'는 최초 구현 완료 시점의 기록이며, 이번 복구에서 현재 개발 PostgreSQL에 적용 완료. 별도의 공개 SQLite 테스트 서버는 변경하지 않음.
