"""Server-owned weekly training calendar, changing Monday at midnight in Korea."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
ROTATION = ("range", "drone", "cipher")
ANCHOR = datetime(2026, 11, 2, tzinfo=KST)


def season_at(now: datetime | None = None) -> dict:
    """Return the current season; naive input follows the app's UTC convention."""
    now = now if now is not None else datetime.now(timezone.utc)
    now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    local_now = now.astimezone(KST)
    start = local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=local_now.weekday())
    end = start + timedelta(weeks=1)
    index = ((start.date() - ANCHOR.date()).days // 7) % len(ROTATION)
    iso_year, iso_week, _ = start.isocalendar()
    return {
        "season_id": f"{iso_year}-W{iso_week:02d}",
        "active_game": ROTATION[index],
        "active_games": list(ROTATION),
        "next_game": ROTATION[(index + 1) % len(ROTATION)],
        "starts_at": start.astimezone(timezone.utc).isoformat(),
        "ends_at": end.astimezone(timezone.utc).isoformat(),
        "server_now": now.isoformat(),
        "duration_seconds": 45,
        "timezone": "Asia/Seoul",
        "rotation": list(ROTATION),
    }
