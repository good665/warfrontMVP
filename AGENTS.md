# Repository Guidelines

## 사용자 소통 언어

- 사용자에게 하는 질문, 선택지, 확인 요청, 승인·접근 권한 요청과 도구의 `justification`은 반드시 한국어로 작성한다.
- 일본어나 중국어로 사용자에게 묻거나 승인을 요청하지 않는다.
- 읽은 파일·스킬·참고 문서가 다른 언어로 작성되어 있어도 이 규칙을 모든 작업에 적용한다.
- 코드, 명령어, 파일명, API 식별자 등 정확성이 필요한 원문 표기는 유지할 수 있다.

## Project Structure & Module Organization

This workspace contains the FastAPI backend. The active Unity project is `C:\Users\good6\WarfrontMVP`, and all future Unity code and assets must be written under `C:\Users\good6\WarfrontMVP\Assets`. Existing runtime scripts are in `Assets/script/` in that project. Inspect and preserve those files before editing; they contain newer server integration than the legacy `Assets/Scripts/` copy in this workspace. Do not overwrite the active project with the legacy copy. Use the active project's `ProjectSettings/` and `Packages/` for Unity configuration. Backend application modules remain in `backend/app/`, with API tests in `backend/tests/`. Backend setup notes are in `backend/README.md`. Do not commit generated Unity folders such as `Library/`, `Temp/`, `Obj/`, or `Build/`.

## Build, Test, and Development Commands

Run backend commands from `backend/`:

- `python -m venv .venv` and `pip install -r requirements.txt` create an isolated environment and install dependencies.
- `uvicorn app.main:app --reload` starts the API locally with reload enabled.
- `python -m pytest` runs the backend test suite; tests use SQLite by default.
- `docker compose up -d db` starts PostgreSQL when testing against the configured database.

Open `C:\Users\good6\WarfrontMVP` in Unity Hub using the version in that project's `ProjectSettings/ProjectVersion.txt` (currently `6000.3.23f1`). Preserve its existing scenes and attach `Assets/script/GameBootstrap.cs` when needed.

## Coding Style & Naming Conventions

Follow existing language conventions: C# types and public members use `PascalCase`; private fields and locals should match nearby code. Use Python's four-space indentation, `snake_case` modules/functions, and `PascalCase` classes. Name tests `test_*.py` and group them by API behavior. Keep changes focused and consistent with neighboring files; no formatter or linter is currently configured.

## Testing Guidelines

Add or update `backend/tests/` coverage for backend behavior and run `python -m pytest` from `backend/`. For Unity changes, verify the affected scene or gameplay flow in the Unity Editor; this repository has no configured automated Unity test suite.

## Commit & Pull Request Guidelines

No established commit history is available yet. Use short imperative commit subjects, preferably with a scope (for example, `backend: validate player creation`). Pull requests should explain the behavior changed, list relevant verification, link any issue, and include screenshots or a short capture for visible Unity changes. Call out configuration or database changes.

## Security & Configuration

Use `backend/env.example` as the configuration template and keep secrets in a local `.env`; never commit credentials or production data. Avoid committing virtual environments such as `backend/venv/` or `.venv/`.

## Unity 제작 및 검증 사전 허용 (2026-11-21)

사용자는 요청한 Unity 작업을 수행하는 데 필요한 다음 작업을 사전 허용했다. 매번 같은 범위의 확인을 반복하지 않고 적용한다.

- 활성 Unity 프로젝트의 Assets 아래 코드·에셋 제작 및 수정
- 검증 스크립트 추가 및 검증 코드를 Unity 프로젝트에 적용
- PNG·FBX 제작 또는 다시 생성
- 전체 미리보기 생성 및 화면 검증
- 회귀 검사와 수정한 내용의 검증

기존 코드와 사용자 에셋을 보존하고, 필요한 백업을 유지한다. 이 허용은 운영체제·도구의 접근 제한을 우회하거나 관계없는 파괴적 작업·외부 배포까지 허용하는 의미가 아니다. 접근 제한 때문에 별도 승인이 필요한 경우 한국어로 요청한다.

