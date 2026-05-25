import json
import os
from typing import Any

import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "86400"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "20"))
# Set SESSION_BACKEND=memory to skip Redis entirely (e.g. quick Render deploy)
SESSION_BACKEND = os.getenv("SESSION_BACKEND", "redis").lower()

_redis_client: redis.Redis | None = None
_redis_available: bool | None = None
_memory_store: dict[str, list[dict[str, Any]]] = {}


def _session_key(session_id: str) -> str:
    return f"chat:session:{session_id}"


def _use_memory_only() -> bool:
    return SESSION_BACKEND == "memory"


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
    return _redis_client


def _redis_read(session_id: str) -> str | None:
    global _redis_available
    if _use_memory_only():
        return None
    if _redis_available is False:
        return None
    try:
        return get_redis().get(_session_key(session_id))
    except (redis.RedisError, OSError) as exc:
        _redis_available = False
        print(f"Redis unavailable, falling back to in-memory sessions: {exc}")
        return None


def _redis_write(session_id: str, payload: str) -> bool:
    global _redis_available
    if _use_memory_only():
        return False
    if _redis_available is False:
        return False
    try:
        get_redis().set(
            _session_key(session_id),
            payload,
            ex=SESSION_TTL_SECONDS,
        )
        return True
    except (redis.RedisError, OSError) as exc:
        _redis_available = False
        print(f"Redis write failed, falling back to in-memory sessions: {exc}")
        return False


def get_history(session_id: str) -> list[dict[str, Any]]:
    raw = _redis_read(session_id)
    if raw:
        return json.loads(raw)
    return list(_memory_store.get(session_id, []))


def append_turn(session_id: str, user_message: str, model_reply: str) -> list[dict[str, Any]]:
    history = get_history(session_id)
    history.append({"role": "user", "parts": [{"text": user_message}]})
    history.append({"role": "model", "parts": [{"text": model_reply}]})
    max_messages = MAX_HISTORY_TURNS * 2
    if len(history) > max_messages:
        history = history[-max_messages:]

    if not _redis_write(session_id, json.dumps(history)):
        _memory_store[session_id] = history
    return history


def history_for_gemini(session_id: str, new_user_message: str) -> list[dict[str, Any]]:
    history = get_history(session_id)
    return history + [{"role": "user", "parts": [{"text": new_user_message}]}]
