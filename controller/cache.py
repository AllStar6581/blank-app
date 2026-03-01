"""Dual-cache layer (L2) for resume report generation.

Architecture:
    Request -> L1: @st.cache_data (in-memory, per-process)
                -> MISS -> L2: FallbackCache
                   -> Redis HIT: return (also warm local file)
                   -> Local file HIT: return
                   -> MISS: generate -> store in both -> return

Cache key: ``resume_report:<language>:<sha256_hex[:16]>``
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(".cache")
DEFAULT_TTL_SECONDS = 24 * 60 * 60 # 


# ---------------------------------------------------------------------------
# Backend protocol
# ---------------------------------------------------------------------------

class CacheBackend(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, value: bytes) -> None: ...


# ---------------------------------------------------------------------------
# Local file backend
# ---------------------------------------------------------------------------

class LocalFileCache:
    """Stores blobs in ``.cache/`` directory with optional TTL."""

    def __init__(
        self,
        base_dir: Path = _CACHE_DIR,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._base_dir = base_dir
        self._ttl_seconds = ttl_seconds

    def _path_for(self, key: str) -> Path:
        safe_name = key.replace(":", "_")
        return self._base_dir / safe_name

    def get(self, key: str) -> bytes | None:
        path = self._path_for(key)
        if path.exists():
            import time

            age = time.time() - path.stat().st_mtime
            if age > self._ttl_seconds:
                logger.debug("LocalFileCache EXPIRED (%ds old): %s", int(age), key)
                path.unlink(missing_ok=True)
                return None
            logger.debug("LocalFileCache HIT: %s", key)
            return path.read_bytes()
        logger.debug("LocalFileCache MISS: %s", key)
        return None

    def set(self, key: str, value: bytes) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._path_for(key).write_bytes(value)
        logger.debug("LocalFileCache SET: %s", key)


# ---------------------------------------------------------------------------
# Redis backend
# ---------------------------------------------------------------------------

class RedisCache:
    """Lazy connection from ``st.secrets["REDIS_URL"]`` or ``os.environ["REDIS_URL"]``.

    7-day TTL.  All errors are caught so Redis unavailability never breaks the app.
    """

    def __init__(self) -> None:
        self._client: Any | None = None
        self._unavailable = False

    def _connect(self) -> Any | None:
        if self._unavailable:
            return None
        if self._client is not None:
            return self._client

        url = self._resolve_url()
        if url is None:
            self._unavailable = True
            return None

        try:
            import redis as redis_lib

            self._client = redis_lib.from_url(
                url,
                decode_responses=False,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._client.ping()
            logger.info("RedisCache connected")
            return self._client
        except Exception:
            # logger.warning(ex)
            logger.warning("RedisCache connection failed — falling back", exc_info=True)
            self._unavailable = True
            return None

    @staticmethod
    def _resolve_url() -> str | None:
        # Prefer env var (no side-effects), then Streamlit secrets
        url = os.environ.get("REDIS_URL")
        if url:
            return url

        # Only touch st.secrets when a secrets.toml actually exists,
        # otherwise Streamlit displays a warning banner on the page.
        _secrets_paths = (
            Path(".streamlit/secrets.toml"),
            Path.home() / ".streamlit" / "secrets.toml",
        )
        if not any(p.exists() for p in _secrets_paths):
            logger.debug("No secrets.toml found, skipping st.secrets")
            return None

        try:
            import streamlit as st

            return st.secrets["REDIS_URL"]
        except Exception:
            pass
        return None

    def get(self, key: str) -> bytes | None:
        client = self._connect()
        if client is None:
            return None
        try:
            data = client.get(key)
            if data is not None:
                logger.debug("RedisCache HIT: %s", key)
            else:
                logger.debug("RedisCache MISS: %s", key)
            return data
        except Exception:
            logger.warning("RedisCache GET failed", exc_info=True)
            return None

    def set(self, key: str, value: bytes) -> None:
        client = self._connect()
        if client is None:
            return
        try:
            client.set(key, value, ex=DEFAULT_TTL_SECONDS)
            logger.debug("RedisCache SET: %s", key)
        except Exception:
            logger.warning("RedisCache SET failed", exc_info=True)


# ---------------------------------------------------------------------------
# Fallback composite backend
# ---------------------------------------------------------------------------

class FallbackCache:
    """Tries Redis first, falls back to local file."""

    def __init__(self) -> None:
        self._redis = RedisCache()
        self._local = LocalFileCache()

    def get(self, key: str) -> bytes | None:
        # Try Redis first
        data = self._redis.get(key)
        if data is not None:
            # Warm the local file cache
            self._local.set(key, data)
            return data

        # Try local file
        data = self._local.get(key)
        return data

    def set(self, key: str, value: bytes) -> None:
        self._redis.set(key, value)
        self._local.set(key, value)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_cache = FallbackCache()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def make_cache_key(language: str, data: dict) -> str:
    """Build a cache key from language and a SHA-256 of the data dict."""
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"resume_report:{language}:{digest}"


def get_cached(key: str) -> bytes | None:
    """Retrieve bytes from the L2 cache, or *None* on miss."""
    return _cache.get(key)


def set_cached(key: str, value: bytes) -> None:
    """Store bytes in the L2 cache (both Redis and local file)."""
    _cache.set(key, value)


def _image_cache_key(url: str) -> str:
    return f"image:{hashlib.sha256(url.encode()).hexdigest()[:16]}"


def get_image_from_cache(url: str) -> bytes | None:
    """Return cached image bytes without any network I/O.

    Returns *None* on miss **and** on cached failure (``b""``).
    """
    data = _cache.get(_image_cache_key(url))
    if data:
        return data
    return None


def fetch_image_cached(url: str) -> bytes | None:
    """Download an image URL, caching the result in L2.

    Returns the raw image bytes, or *None* if the download fails.
    Failed downloads are cached as ``b""`` to avoid repeated timeouts.
    """
    import urllib.request

    key = _image_cache_key(url)
    data = _cache.get(key)
    if data is not None:
        return data if data else None

    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = resp.read()
        _cache.set(key, data)
        return data
    except Exception:
        logger.warning("fetch_image_cached failed for %s", url, exc_info=True)
        _cache.set(key, b"")
        return None
