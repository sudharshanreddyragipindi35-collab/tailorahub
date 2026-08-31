from __future__ import annotations

import asyncio
import base64
import hashlib
import ipaddress
import json
import logging
import time
from urllib.parse import parse_qsl, urlencode

import jwt
from redis.asyncio import Redis

from app.settings import settings


logger = logging.getLogger(__name__)

RATE_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


class MemoryTrafficStore:
    """Process-local development store. Production is guarded to require Redis."""

    def __init__(self) -> None:
        self._rates: dict[str, tuple[int, float]] = {}
        self._cache: dict[str, tuple[str, float]] = {}
        self._generation = 1
        self._lock = asyncio.Lock()

    async def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        now = time.monotonic()
        async with self._lock:
            count, expires = self._rates.get(key, (0, now + window_seconds))
            if expires <= now:
                count, expires = 0, now + window_seconds
            count += 1
            self._rates[key] = (count, expires)
            return count, max(1, int(expires - now))

    async def generation(self) -> int:
        return self._generation

    async def invalidate(self) -> None:
        async with self._lock:
            self._generation += 1
            self._cache.clear()

    async def cache_get(self, key: str) -> str | None:
        now = time.monotonic()
        value = self._cache.get(key)
        if not value:
            return None
        payload, expires = value
        if expires <= now:
            self._cache.pop(key, None)
            return None
        return payload

    async def cache_set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._cache[key] = (value, time.monotonic() + ttl_seconds)


class RedisTrafficStore:
    def __init__(self, redis_url: str) -> None:
        self.redis = Redis.from_url(redis_url, decode_responses=True)

    async def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        count, ttl = await self.redis.eval(RATE_SCRIPT, 1, key, window_seconds)
        return int(count), max(1, int(ttl))

    async def generation(self) -> int:
        await self.redis.setnx("tailorahub:public-cache:generation", 1)
        value = await self.redis.get("tailorahub:public-cache:generation")
        return int(value or 1)

    async def invalidate(self) -> None:
        await self.redis.setnx("tailorahub:public-cache:generation", 1)
        await self.redis.incr("tailorahub:public-cache:generation")

    async def cache_get(self, key: str) -> str | None:
        return await self.redis.get(key)

    async def cache_set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self.redis.set(key, value, ex=ttl_seconds)


def build_store():
    if settings.traffic_store_backend == "redis":
        return RedisTrafficStore(settings.redis_url)
    if settings.traffic_store_backend == "memory":
        return MemoryTrafficStore()
    raise RuntimeError("TRAFFIC_STORE_BACKEND must be 'memory' or 'redis'")


def _header_map(scope: dict) -> dict[str, str]:
    return {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}


def _trusted_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks = []
    for value in settings.client_ip_trusted_proxy_networks:
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError as exc:
            raise RuntimeError(f"Invalid CLIENT_IP_TRUSTED_PROXY_NETWORKS entry: {value}") from exc
    return networks


TRUSTED_PROXY_NETWORKS = _trusted_networks()


def _in_networks(value: str, networks: list) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return any(address.version == network.version and address in network for network in networks)


def request_client_ip(scope: dict, headers: dict[str, str]) -> str:
    peer = str((scope.get("client") or ("unknown", 0))[0])
    if not _in_networks(peer, TRUSTED_PROXY_NETWORKS):
        return peer
    forwarded = [part.strip() for part in headers.get("x-forwarded-for", "").split(",") if part.strip()]
    for candidate in reversed(forwarded):
        if not _in_networks(candidate, TRUSTED_PROXY_NETWORKS):
            return candidate
    return peer


def classify_rate_limit(path: str) -> tuple[str, int]:
    normalized = path.lower()
    if "/webhooks/" in normalized:
        return "webhook", settings.rate_limit_webhook_per_minute
    if "/otp" in normalized or "forgot-password" in normalized or "reset-password" in normalized:
        return "otp", settings.rate_limit_otp_per_minute
    if any(value in normalized for value in ("/login", "/register", "check-availability", "/auth/refresh")):
        return "auth", settings.rate_limit_auth_per_minute
    if any(value in normalized for value in ("/payment", "/payments", "/pay", "/razorpay")):
        return "payment", settings.rate_limit_payment_per_minute
    if any(value in normalized for value in ("/media", "profile-image", "/presign", "/uploads", "/disputes", "/offers")):
        return "upload", settings.rate_limit_upload_per_minute
    return "general", settings.rate_limit_general_per_minute


def is_public_cache_path(path: str) -> bool:
    parts = [part for part in path.rstrip("/").split("/") if part]
    if path.rstrip("/") in {"/api/reference", "/api/tailors"}:
        return True
    return (
        len(parts) == 4 and parts[:2] == ["api", "tailors"] and parts[3] == "services"
    ) or (
        len(parts) == 5 and parts[:3] == ["api", "v1", "tailors"] and parts[4] == "services"
    )


def should_cache(scope: dict, headers: dict[str, str]) -> bool:
    return (
        scope.get("method") == "GET"
        and is_public_cache_path(scope.get("path", ""))
        and "authorization" not in headers
        and "cookie" not in headers
    )


def should_invalidate_public_cache(method: str, path: str) -> bool:
    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    return any(
        marker in path
        for marker in (
            "/tailor/", "/tailors/", "/admin/tailors", "/admin/reviews",
            "/booking", "/orders", "/review", "/offers",
        )
    )


def _cache_key(scope: dict, generation: int) -> str:
    query = urlencode(sorted(parse_qsl(scope.get("query_string", b"").decode("latin-1"), keep_blank_values=True)))
    raw = f"{scope.get('path')}?{query}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"tailorahub:public-cache:v{generation}:{digest}"


def _rate_identity(headers: dict[str, str], client_ip: str) -> list[str]:
    identities = ["ip:" + hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:24]]
    authorization = headers.get("authorization", "")
    if authorization:
        raw_token = authorization.split(" ", 1)[1] if " " in authorization else authorization
        try:
            subject = str(jwt.decode(raw_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])["sub"])
        except Exception:
            subject = authorization
        identities.append("user:" + hashlib.sha256(subject.encode("utf-8")).hexdigest()[:24])
    return identities


def _replace_header(headers: list[tuple[bytes, bytes]], name: bytes, value: bytes) -> list[tuple[bytes, bytes]]:
    lowered = name.lower()
    return [(key, item) for key, item in headers if key.lower() != lowered] + [(name, value)]


async def _json_response(send, status: int, detail: str, headers: list[tuple[bytes, bytes]] | None = None) -> None:
    body = json.dumps({"detail": detail}, separators=(",", ":")).encode("utf-8")
    response_headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    response_headers.extend(headers or [])
    await send({"type": "http.response.start", "status": status, "headers": response_headers})
    await send({"type": "http.response.body", "body": body})


class TrafficProtectionMiddleware:
    """Distributed rate limits, bounded request bodies, and allowlisted public caching."""

    def __init__(self, app, store=None) -> None:
        self.app = app
        self.store = store or build_store()

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = _header_map(scope)
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        rate_headers: list[tuple[bytes, bytes]] = []
        if settings.rate_limit_enabled:
            bucket, limit = classify_rate_limit(path)
            minute = int(time.time()) // 60
            try:
                results = []
                identities = _rate_identity(headers, request_client_ip(scope, headers))
                for identity in identities:
                    identity_limit = limit * 5 if len(identities) > 1 and identity.startswith("ip:") else limit
                    count, retry_after = await self.store.increment(f"tailorahub:rate:{bucket}:{identity}:{minute}", 60)
                    results.append((count, retry_after, identity_limit))
                exceeded = next((result for result in results if result[0] > result[2]), None)
                count, retry_after, applied_limit = exceeded or max(results, key=lambda item: item[0] / item[2])
                remaining = max(0, applied_limit - count)
                rate_headers = [
                    (b"x-ratelimit-limit", str(applied_limit).encode()),
                    (b"x-ratelimit-remaining", str(remaining).encode()),
                ]
                if exceeded:
                    await _json_response(
                        send, 429, "Too many requests. Please try again shortly.",
                        rate_headers + [(b"retry-after", str(retry_after).encode())],
                    )
                    return
            except Exception:
                logger.exception("Traffic rate-limit store unavailable; allowing request")

        if method in {"POST", "PUT", "PATCH"}:
            is_upload = classify_rate_limit(path)[0] == "upload"
            body_limit = settings.max_upload_request_bytes if is_upload else settings.max_request_body_bytes
            try:
                declared = int(headers.get("content-length", "0"))
            except ValueError:
                declared = 0
            if declared > body_limit:
                await _json_response(send, 413, "Request body is too large.")
                return
            messages = []
            total = 0
            while True:
                message = await receive()
                messages.append(message)
                if message.get("type") == "http.disconnect":
                    break
                total += len(message.get("body", b""))
                if total > body_limit:
                    await _json_response(send, 413, "Request body is too large.")
                    return
                if not message.get("more_body", False):
                    break

            async def replay_receive():
                return messages.pop(0) if messages else {"type": "http.request", "body": b"", "more_body": False}

            receive = replay_receive

        cacheable = should_cache(scope, headers)
        cache_key = None
        if cacheable:
            try:
                cache_key = _cache_key(scope, await self.store.generation())
                cached = await self.store.cache_get(cache_key)
                if cached:
                    item = json.loads(cached)
                    cached_headers = [(key.encode("latin-1"), value.encode("latin-1")) for key, value in item["headers"]]
                    for key, value in rate_headers:
                        cached_headers = _replace_header(cached_headers, key, value)
                    cached_headers = _replace_header(cached_headers, b"x-cache", b"HIT")
                    await send({"type": "http.response.start", "status": item["status"], "headers": cached_headers})
                    await send({"type": "http.response.body", "body": base64.b64decode(item["body"])})
                    return
            except Exception:
                logger.exception("Public response cache unavailable; loading from application")

        captured: list[dict] = []
        response_status = 500

        async def protected_send(message: dict) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = list(message.get("headers", [])) + rate_headers
                if cacheable:
                    response_headers = _replace_header(response_headers, b"cache-control", f"public, max-age={settings.public_cache_ttl_seconds}".encode())
                    response_headers = _replace_header(response_headers, b"x-cache", b"MISS")
                elif "authorization" in headers or "cookie" in headers or path.startswith(("/api/admin", "/api/tailor", "/api/customer", "/api/v1/admin")):
                    response_headers = _replace_header(response_headers, b"cache-control", b"private, no-store")
                message = {**message, "headers": response_headers}
            if cacheable:
                captured.append(message)
            else:
                await send(message)

        await self.app(scope, receive, protected_send)

        if cacheable:
            for message in captured:
                await send(message)
            try:
                starts = [message for message in captured if message["type"] == "http.response.start"]
                bodies = [message.get("body", b"") for message in captured if message["type"] == "http.response.body"]
                body = b"".join(bodies)
                if starts and response_status == 200 and len(body) <= 2 * 1024 * 1024 and cache_key:
                    safe_headers = [
                        (key.decode("latin-1"), value.decode("latin-1"))
                        for key, value in starts[0].get("headers", [])
                        if key.lower() not in {
                            b"set-cookie", b"content-length", b"x-cache",
                            b"x-ratelimit-limit", b"x-ratelimit-remaining", b"retry-after",
                        }
                    ]
                    payload = json.dumps({"status": 200, "headers": safe_headers, "body": base64.b64encode(body).decode("ascii")})
                    await self.store.cache_set(cache_key, payload, settings.public_cache_ttl_seconds)
            except Exception:
                logger.exception("Could not store public response cache entry")

        if 200 <= response_status < 400 and should_invalidate_public_cache(method, path):
            try:
                await self.store.invalidate()
            except Exception:
                logger.exception("Could not invalidate public response cache")
