# 상시 친구 테스트 서버

한 대의 Linux 서버에 Docker Compose로 API와 Caddy를 실행하는 소규모 초대 테스트 구성이다. 이 PC의 Quick Tunnel과 별개이며 아직 외부 서버에는 배포하지 않았다. 현재 방은 프로세스 메모리에 있으므로 API 워커와 복제본은 각각 **1개**만 사용한다.

## 첫 배포

1. 사용할 서버에 Docker Engine과 Compose 플러그인을 설치한다. 고정 도메인의 DNS A/AAAA를 서버에 연결하고 외부 80·443 포트가 도달하도록 준비한다. 8000 포트는 외부에 공개하지 않는다.
2. 저장소의 `backend/`를 서버에 배치한다. 아래 명령은 `backend/deploy/`에서 실행한다.

```sh
cp .env.example .env
chmod 600 .env
python3 -c 'import secrets; print(secrets.token_urlsafe(64)); print(secrets.token_urlsafe(32))'
```

출력한 두 값을 각각 `.env`의 `JWT_SECRET`, `TEST_ACCESS_KEY`에 넣고 `WARFRONT_DOMAIN`, `ACME_EMAIL`을 실제 값으로 변경한다. 키는 문서·APK·Git에 넣지 않는다. 기존 임시 서버의 비밀값이나 개발 DB는 가져오지 않는다. WebGL을 쓴다면 `ALLOWED_ORIGINS`에 실제 웹 주소를 지정한다.

```sh
docker compose config --quiet
docker compose up -d --build --wait
docker compose ps
docker compose exec -T api python tools/check_readiness.py
python3 ../tools/check_readiness.py --url https://사용할-도메인
```

Caddy가 인증서 발급과 갱신, HTTP → HTTPS 이동을 처리한다. 실제 도메인·DNS·외부 포트 조건이 필요하다. [공식 HTTPS 조건](https://caddyserver.com/docs/automatic-https)

게임의 서버 접속 설정에는 `https://사용할-도메인`과 초대용 `TEST_ACCESS_KEY`만 입력한다. JWT 서명 비밀값은 서버에만 둔다. `/health`, `/ready`를 제외한 API에는 초대 키와 기존 로그인 인증이 적용된다.

## 상태와 로그

```sh
docker compose ps
docker compose logs --tail 100 api
docker compose logs --tail 100 caddy
docker compose exec -T api python tools/check_readiness.py
```

`/ready`는 DB 연결, 경기 루프 존재 여부와 최근 5초 이내 정상 반복 여부를 검사한다. 외부 모니터에 HTTPS `/ready`를 등록하여 HTTP 200 여부를 확인할 수 있다. 컨테이너별 로그는 10MB × 3개로 제한한다. API가 비정상 종료하면 재시작하지만 `unhealthy` 표시 자체는 자동 재시작을 일으키지 않는다. 건강 상태 실패 알림은 운영 모니터에서 연결해야 한다.

API 데이터·백업·인증서는 각각 Docker 볼륨에 보존한다. Compose의 건강 상태 의존성으로 API 준비 후 프록시를 시작한다. [Compose 시작 순서](https://docs.docker.com/compose/how-tos/startup-order/)

## 백업과 복구

```sh
# 실행 중에도 일관된 SQLite 백업과 SHA-256 기록을 생성한다.
sh backup.sh
docker compose run --rm maintenance backup /data/warfront.db --output-dir /backups

# 호스트 장애에 대비해 백업을 별도 저장소로 복사한다.
mkdir -p ./exported-backups
docker compose cp api:/backups/. ./exported-backups/
```

백업은 SQLite backup API와 무결성 검사로 만든다. DB 원본 파일을 단순 복사하지 않으며 기존 복구 대상 파일을 덮어쓰지 않는다. [Python SQLite backup API](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup)

일일 예약 예시: 서버의 crontab에 `0 3 * * * /bin/sh /srv/warfront/backend/deploy/backup.sh`를 등록한다. 실제 설치 경로에 맞게 바꾼다. 이 저장소는 예약 등록이나 외부 백업 전송을 자동으로 수행하지 않는다. 볼륨 내부의 백업만으로는 서버 자체의 장애에 대비할 수 없다. 보관 기간은 운영자가 정하고, 복구 검증 후 만료 백업을 관리한다.

복구는 사용자가 없는 점검 시간에 진행한다.

```sh
docker compose stop api
# 실제 백업 파일명으로 변경한다. 새 경로만 허용한다.
docker compose run --rm maintenance restore /backups/warfront-실제파일명.db --destination /data/recovered.db
# .env에서 DATABASE_URL=sqlite:////data/recovered.db 로 변경한다.
docker compose up -d --wait api
docker compose exec -T api python tools/check_readiness.py
```

복구 후에는 백업 명령의 원본도 `/data/recovered.db`로 바꾼다. `backup.sh`는 `WARFRONT_BACKUP_DB=/data/recovered.db sh backup.sh`로 실행할 수 있다. 과거 백업으로 복구하면 백업 이후의 계정·보상도 과거 시점으로 돌아간다. 이 도구는 이 구성의 SQLite 전용이며 PostgreSQL 백업을 대신하지 않는다.

업데이트 전 백업을 만들고 참가자가 없는 시간에 `docker compose up -d --build --wait`를 실행한다. 서버 재시작 시 진행 중 방은 종료되고 미정산 경기 체력은 기존 복구 규칙에 따라 환급된다. `docker compose down`은 종료용이며, 데이터 보존이 필요할 때 `-v`를 붙이지 않는다.

## 검증 기록

2026-10-30: Linux Docker 이미지 빌드, Compose 문법, API 건강 상태, 실행 중 DB 백업, 별도 DB 파일로 복구, API 재시작 후 준비 상태, Caddy 설정 검증 통과. 실제 외부 도메인의 인증서 발급과 상시 가동은 서버·도메인 선정 후 확인해야 한다.
