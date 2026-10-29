# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Unity 6 game client and a FastAPI backend. Unity code lives in `Assets/Scripts/` (`GameBootstrap.cs`, `GameData.cs`); editor and project settings are in `ProjectSettings/`. Backend application modules are in `backend/app/`, with API tests in `backend/tests/`. Backend setup notes are in `backend/README.md`. Keep new Unity assets under `Assets/` and backend code or tests under their corresponding `backend/` folders. Do not commit generated Unity folders such as `Library/`, `Temp/`, `Obj/`, or `Build/`.

## Build, Test, and Development Commands

Run backend commands from `backend/`:

- `python -m venv .venv` and `pip install -r requirements.txt` create an isolated environment and install dependencies.
- `uvicorn app.main:app --reload` starts the API locally with reload enabled.
- `python -m pytest` runs the backend test suite; tests use SQLite by default.
- `docker compose up -d db` starts PostgreSQL when testing against the configured database.

Open the repository in Unity Hub using the Unity version recorded in `ProjectSettings/ProjectVersion.txt` (Unity 6.0.0f1). Create a scene, add a `GameBootstrap` GameObject, attach `Assets/Scripts/GameBootstrap.cs`, and press Play.

## Coding Style & Naming Conventions

Follow existing language conventions: C# types and public members use `PascalCase`; private fields and locals should match nearby code. Use Python's four-space indentation, `snake_case` modules/functions, and `PascalCase` classes. Name tests `test_*.py` and group them by API behavior. Keep changes focused and consistent with neighboring files; no formatter or linter is currently configured.

## Testing Guidelines

Add or update `backend/tests/` coverage for backend behavior and run `python -m pytest` from `backend/`. For Unity changes, verify the affected scene or gameplay flow in the Unity Editor; this repository has no configured automated Unity test suite.

## Commit & Pull Request Guidelines

No established commit history is available yet. Use short imperative commit subjects, preferably with a scope (for example, `backend: validate player creation`). Pull requests should explain the behavior changed, list relevant verification, link any issue, and include screenshots or a short capture for visible Unity changes. Call out configuration or database changes.

## Security & Configuration

Use `backend/env.example` as the configuration template and keep secrets in a local `.env`; never commit credentials or production data. Avoid committing virtual environments such as `backend/venv/` or `.venv/`.
