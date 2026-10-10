"""Thin WHOOP v2 API client with pagination."""
from datetime import datetime, timedelta, timezone

import httpx

from .auth import get_access_token

BASE = "https://api.prod.whoop.com/developer"


def _get(path: str, params: dict | None = None) -> dict:
    r = httpx.get(
        BASE + path,
        params=params,
        headers={"Authorization": f"Bearer {get_access_token()}"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def collection(path: str, days: int, max_records: int = 200) -> list[dict]:
    """Fetch all records from a v2 collection endpoint for the last `days` days."""
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    params = {"start": start, "limit": 25}
    records: list[dict] = []
    while len(records) < max_records:
        data = _get(path, params)
        records.extend(data.get("records", []))
        token = data.get("next_token")
        if not token:
            break
        params["nextToken"] = token
    return records[:max_records]


def profile() -> dict:
    return _get("/v2/user/profile/basic")


def body() -> dict:
    return _get("/v2/user/measurement/body")


def recovery(days: int) -> list[dict]:
    return collection("/v2/recovery", days)


def sleep(days: int) -> list[dict]:
    return collection("/v2/activity/sleep", days)


def workouts(days: int) -> list[dict]:
    return collection("/v2/activity/workout", days)


def cycles(days: int) -> list[dict]:
    return collection("/v2/cycle", days)
