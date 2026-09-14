"""Redis-backed realtime plumbing: conversation pub/sub + visitor rate limiting."""

import json
from typing import AsyncIterator

import redis.asyncio as aioredis

from .config import settings

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def conversation_channel(conversation_id: str) -> str:
    return f"perch:conv:{conversation_id}"


async def publish(conversation_id: str, event: dict) -> None:
    await get_redis().publish(conversation_channel(conversation_id), json.dumps(event))


async def subscribe(conversation_id: str) -> AsyncIterator[dict]:
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(conversation_channel(conversation_id))
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(conversation_channel(conversation_id))
        await pubsub.aclose()


async def allow_message(site_key: str, visitor_id: str, limit: int = 30, window_s: int = 60) -> bool:
    """Sliding-window-ish fixed counter: limit messages per visitor per site."""
    r = get_redis()
    key = f"perch:rl:{site_key}:{visitor_id}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window_s)
    return count <= limit
