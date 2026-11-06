# 성장 기능 스키마 적용과 복원

`AUTO_CREATE_TABLES=false`인 서버에서도 아래 명시적 도구로 적용한다. 서버 코드 배포 전에 API 쓰기 작업을 중지하고 백업을 확인한다. 도구는 기존 `players`와 `matches`가 있는 DB만 허용하며 해당 테이블을 만들거나 수정하지 않는다.

## SQLite

`backend/`에서 실행한다. 실제 파일 경로를 지정하고, 백업 디렉터리는 공개 정적 파일 경로 밖에 둔다.

```powershell
python -m tools.apply_growth_schema --database-url "sqlite:///C:/private/warfront.db" --backup-dir "C:/private/backups"
```

`--database-url`을 생략하면 기존 설정의 `DATABASE_URL`을 사용한다. 명령 출력은 적용된 테이블 이름, 백업 파일 경로, `status: ok`를 포함한다. SQLite 백업은 기존 `tools.backup_sqlite`를 사용해 일관된 스냅샷과 무결성을 검사한다. 같은 명령을 다시 실행해도 기존 계정·전투·진행·훈련 기록을 지우지 않는다.

복원은 기존 DB를 덮어쓰지 않고 새 경로로 수행한다.

```powershell
python -m tools.backup_sqlite restore "C:/private/backups/warfront-SNAPSHOT.db" --destination "C:/private/warfront-restored.db"
```

복원 DB의 계정·전투 행 수와 표본 계정 잔액을 확인한 뒤 서버의 DB 경로를 전환한다. 적용 전 백업을 복원했다면 성장 기능 코드가 그 DB에 접근하기 전에 스키마를 다시 적용하거나 서버 코드도 이전 버전으로 되돌려야 한다. 실행 중인 서버의 DB 파일을 직접 교체하지 않는다.

## PostgreSQL

기존 운영 절차로 `pg_dump` 백업을 만들고 별도 DB에 복원이 가능한지 먼저 확인한다. `--backup-dir`은 SQLite 전용이다. 연결 문자열을 명령행에 기록할 필요 없이 기존 환경 설정을 사용한다.

```powershell
python -m tools.apply_growth_schema
```

이 환경에서는 PostgreSQL 데몬을 사용할 수 없어서 실제 PostgreSQL 적용·동시성 테스트는 수행하지 않았다. SQLite 검증 결과를 PostgreSQL 실측 검증으로 간주하지 않는다.

## 적용 내용

- 2026-11-06 게임별 주간 순위: PostgreSQL의 `training_seasons.id`, `training_runs.season_id`, `training_bests.season_id`, `training_claims.season_id`를 `VARCHAR(16)`으로 확장한다. SQLite는 기존 VARCHAR 길이를 강제하지 않아 별도 테이블 재생성이 필요 없다. 기존 주간 ID·시드·기록·수령 내역을 보존하며, 추가 종목은 주차 뒤에 게임 코드를 붙인 독립 리그로 저장한다. PostgreSQL 실제 적용은 별도 환경에서 검증해야 한다.

- `experience_states`, `experience_events` 및 해당 인덱스.
- `experience_states`에 없는 `first_session_at`, `first_guide_exit_at` 두 nullable 타임스탬프와 `first_session_censored`, `first_guide_exit_censored` 두 boolean 필드를 추가한다. 기존 값은 보존한다. 앵커가 없는 과거 live client 이벤트만 해당 censor flag로 표시하며, 과거 날짜를 새 날짜로 추정하지 않는다.
- `training_seasons`: 주간 종목, 규칙 버전, 공통 seed와 시작·종료·정산·수령 만료 시각.
- `training_runs`: 계정에 귀속된 실행, 유효기간, 상태, 요청 fingerprint 및 검증된 결과. nullable unique `active_player_id`로 계정당 활성 실행 하나를 강제한다.
- `training_bests`: 계정·시즌 복합 기본키와 양수 최고 점수.
- `training_claims`: 계정·시즌 unique 수령 기록. 다이아 SQL 증가와 같은 트랜잭션에서 저장한다.

SQLite에서는 변경 전 `BEGIN IMMEDIATE`, PostgreSQL에서는 시즌 행 다음 계정 행의 `FOR UPDATE` 순서로 직렬화한다. 완료와 보상 요청 모두 잠금을 획득한 뒤 서버 시간을 검사한다. 시즌 정산은 KST 월요일 00:10, 수령 마감은 정산 시각에서 28일 뒤이며 마감 시각 자체는 포함하지 않는다.

## 검증 명령과 범위

```powershell
python -m pytest tests/test_training_league.py -q
python -m pytest -q
```

테스트는 별도 임시 SQLite DB를 사용한다. 기존 Player/Match 데이터가 있는 DB의 반복 적용, 이전 cohort 스키마의 추가 필드, 백업/새 경로 복원, `AUTO_CREATE_TABLES=false`, 별도 Python 프로세스 재시작, 실제 DB 잠금과 중복 수령을 포함한다. 운영 DB나 실제 계정에 보상을 지급하지 않으며, 운영 서버의 시간을 바꾸는 API·환경 변수는 추가하지 않는다.
