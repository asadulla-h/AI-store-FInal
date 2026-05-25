import json
import os
from typing import Any

import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "86400"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "20"))

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client


def _session_key(session_id: str) -> str:
    return f"chat:session:{session_id}"


def get_history(session_id: str) -> list[dict[str, Any]]:
    raw = get_redis().get(_session_key(session_id))
    if not raw:
        return []
    return json.loads(raw)


def append_turn(session_id: str, user_message: str, model_reply: str) -> list[dict[str, Any]]:
    history = get_history(session_id)
    history.append({"role": "user", "parts": [{"text": user_message}]})
    history.append({"role": "model", "parts": [{"text": model_reply}]})
    max_messages = MAX_HISTORY_TURNS * 2
    if len(history) > max_messages:
        history = history[-max_messages:]
    get_redis().set(
        _session_key(session_id),
        json.dumps(history),
        ex=SESSION_TTL_SECONDS,
    )
    return history


def history_for_gemini(session_id: str, new_user_message: str) -> list[dict[str, Any]]:
    """Return prior turns plus the new user message (not yet persisted)."""
    history = get_history(session_id)
    return history + [{"role": "user", "parts": [{"text": new_user_message}]}]
