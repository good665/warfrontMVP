# 인터넷 친구 테스트 서버

이번 구성은 이 PC에서 전용 테스트 API를 실행하고 Cloudflare Quick Tunnel의 임시 HTTPS 주소로 연결합니다. 별도 Cloudflare 계정·도메인이 필요하지 않습니다. PC와 서버를 켜둬야 하며, 서버를 다시 시작하면 공개 주소가 바뀝니다. 상시 운영 서버 배포는 별도 단계입니다.

## 친구가 게임에서 입력할 것

1. 최신 Unity 프로젝트 `C:\Users\good6\WarfrontMVP`를 실행하거나 해당 코드로 빌드한 게임을 실행합니다.
2. 로비 또는 접속 실패 화면에서 **서버 접속 설정**을 누릅니다.
3. `backend/.test-server/connection.json`의 `api_base_url`을 **서버 주소**, `test_access_key`를 **테스트 접속키**에 입력합니다.
4. **저장하고 연결**을 누른 뒤 **온라인 1:1 / 3:3 대전**에서 빠른 대전을 선택하거나 방 코드를 공유합니다.

게임 안에서 저장한 주소는 Inspector의 기본 주소보다 우선합니다. 로컬 개발 서버로 돌아가려면 같은 화면에서 주소를 `http://127.0.0.1:8000`으로 바꾸고 접속키를 비웁니다. 테스트 접속키는 JWT 서명 비밀값과 다르며, 초대한 친구에게만 전달합니다.

## 실행과 종료

아래 명령은 `backend/`에서 실행합니다.

```powershell
# 최초 한 번: 공식 릴리스의 SHA-256 확인 후 휴대용 클라이언트 설치
.\.venv\Scripts\python.exe tools/install_cloudflared.py

# 백그라운드 실행. 포트와 키는 자동 생성하며 개발 DB를 사용하지 않음
.\.venv\Scripts\python.exe tools/friend_server.py start

# status가 running, stage가 ready가 된 뒤 연결 정보 공유
.\.venv\Scripts\python.exe tools/friend_server.py status
.\.venv\Scripts\python.exe tools/friend_server.py probe

# 공개 HTTPS 경로로 전용 검증 계정의 1:1·3:3 검사 후 해당 계정만 정리
.\.venv\Scripts\python.exe tools/check_friend_server.py

# 공개 주소와 API를 정상 종료
.\.venv\Scripts\python.exe tools/friend_server.py stop
```

`start --local-only`는 터널 없이 같은 보안 설정을 로컬에서 검사하는 옵션입니다. `start`는 이미 실행 중인 서버를 중복 생성하지 않습니다. `stop`은 전용 로컬 제어 포트의 인증을 거쳐 자기 실행만 종료하며, 임의의 PID를 종료하지 않습니다.

## 보관 파일

| 경로 | 용도 | 공유 여부 |
| --- | --- | --- |
| `.test-server/connection.json` | 공개 주소와 초대 접속키 | 초대한 친구에게 필요한 두 값만 전달 |
| `.test-server/profile.json` | 서버 JWT 서명 비밀값과 접속키 | 공유하지 않음 |
| `.test-server/state.json` | 실행 상태와 종료 제어 비밀값 | 공유하지 않음 |
| `.test-server/warfront.db` | 테스트 전용 계정·결과 | 공유하지 않음 |
| `.test-server/public-check.json` | 공개 주소 검사 결과 | 접속키·JWT 없음 |
| `.test-server/supervisor.log`, `tunnel.log` | 서버·터널 오류 확인 | 필요할 때 검토 |

이 폴더와 `.tools/`는 Git에서 제외합니다. 기존 `backend/.env`와 개발 DB를 공개하지 않으며, 계정 데이터는 전용 테스트 DB에만 기록합니다. 재시작 시 DB와 키는 유지하고 게임 방은 초기화합니다.

## 적용한 접속 설정

- 공개 주소는 HTTPS이며, API는 로컬 루프백에만 바인딩합니다.
- 게임 API에는 `X-Warfront-Test-Key` 헤더와 기존 JWT 인증이 적용됩니다. 게임이 자동으로 헤더를 보냅니다.
- `/health`·`/ready`는 접속키 없이 상태만 확인할 수 있습니다. 공개 모드의 Swagger/OpenAPI 문서는 비활성화합니다.
- 한 개의 서버 프로세스에서 방을 계산합니다. 60초 단계 상승, 코드 대전과 자동 매칭은 기존과 같습니다.
- Cloudflare 공식 릴리스에서 제공한 SHA-256으로 휴대용 실행 파일을 확인합니다.

## 검증 범위와 한계

로컬 공개 모드 검사는 다음으로 재현할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tests/check_online_live.py --public-test
```

실제 공개 주소의 준비 상태·접속키 검사와 HTTP 클라이언트의 1:1·3:3을 별도로 검사합니다. 두 물리 기기에서 Unity 화면을 함께 조작하는 검증은 아직 별도로 필요합니다. 연결 주소가 바뀌면 친구들도 게임의 서버 접속 설정을 바꿔야 합니다.

근거: [Cloudflare Quick Tunnels 공식 안내](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/). 임시 터널은 개발·테스트용이며 상시 가동을 보장하지 않습니다.
