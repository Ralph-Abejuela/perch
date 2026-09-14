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


def tenant_channel(tenant_id: str) -> str:
    return f"perch:tenant:{tenant_id}"


async def publish_tenant(tenant_id: str, event: dict) -> None:
    await get_redis().publish(tenant_channel(tenant_id), json.dumps(event))


async def publish_event(tenant_id: str, conversation_id: str, event: dict) -> None:
    """Conversation-scoped events go to the conversation channel (visitor)
    and the tenant channel (all connected agents of the tenant)."""
    payload = json.dumps(event)
    r = get_redis()
    await r.publish(conversation_channel(conversation_id), payload)
    await r.publish(tenant_channel(tenant_id), payload)


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


async def subscribe_tenant(tenant_id: str) -> AsyncIterator[dict]:
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(tenant_channel(tenant_id))
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(tenant_channel(tenant_id))
        await pubsub.aclose()


async def allow_message(
    site_key: str,
    visitor_id: str,
    limit: int | None = None,
    window_s: int = 60,
) -> bool:
    """Fixed-window counter: limit messages per visitor per site."""
    limit = limit or settings.rate_limit_per_minute
    r = get_redis()
    key = f"perch:rl:{site_key}:{visitor_id}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, window_s)
    return count <= limit


# --- agent presence -------------------------------------------------------

PRESENCE_TTL_S = 90


def presence_key(tenant_id: str, agent_id: str) -> str:
    return f"perch:presence:{tenant_id}:{agent_id}"


async def touch_presence(tenant_id: str, agent_id: str) -> None:
    await get_redis().set(presence_key(tenant_id, agent_id), "1", ex=PRESENCE_TTL_S)


async def clear_presence(tenant_id: str, agent_id: str) -> None:
    await get_redis().delete(presence_key(tenant_id, agent_id))


async def online_agents(tenant_id: str) -> int:
    r = get_redis()
    count = 0
    async for _ in r.scan_iter(match=f"perch:presence:{tenant_id}:*", count=100):
        count += 1
    return count
