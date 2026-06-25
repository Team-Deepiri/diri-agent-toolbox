from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.last_accessed is None:
            self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CacheEntry:
        return cls(
            key=data["key"],
            value=data["value"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"])
            if data.get("last_accessed")
            else None,
            tags=data.get("tags", []),
        )


class AdvancedCacheManager:
    def __init__(
        self,
        redis_client: Any = None,
        default_ttl: int = 3600,
        max_size: int = 10000,
        enable_lru: bool = True,
    ):
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.enable_lru = enable_lru
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.tag_index: Dict[str, List[str]] = {}

    def _key_prefix(self, namespace: str = "toolbox") -> str:
        return f"{namespace}:"

    def get(
        self,
        key: str,
        namespace: str = "toolbox",
        update_access: bool = True,
    ) -> Optional[Any]:
        full_key = f"{self._key_prefix(namespace)}{key}"

        if self.redis_client:
            try:
                cached = self.redis_client.get(full_key)
                if cached:
                    entry_data = json.loads(cached)
                    entry = CacheEntry.from_dict(entry_data)
                    if entry.is_expired():
                        self.delete(key, namespace)
                        return None
                    if update_access:
                        entry.access_count += 1
                        entry.last_accessed = datetime.now()
                        self._update_redis_entry(full_key, entry)
                    return entry.value
            except Exception:
                pass

        if full_key in self.memory_cache:
            entry = self.memory_cache[full_key]
            if entry.is_expired():
                del self.memory_cache[full_key]
                return None
            if update_access:
                entry.access_count += 1
                entry.last_accessed = datetime.now()
            return entry.value

        return None

    def set(
        self,
        key: str,
        value: Any,
        namespace: str = "toolbox",
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        full_key = f"{self._key_prefix(namespace)}{key}"
        if ttl is None:
            ttl = self.default_ttl
        tags = tags or []
        expires_at = datetime.now() + timedelta(seconds=ttl)
        entry = CacheEntry(
            key=full_key, value=value, created_at=datetime.now(), expires_at=expires_at, tags=tags
        )

        if self.redis_client:
            try:
                entry_data = json.dumps(entry.to_dict())
                self.redis_client.setex(full_key, ttl, entry_data)
                for tag in tags:
                    tag_key = f"{self._key_prefix(namespace)}tag:{tag}"
                    self.redis_client.sadd(tag_key, full_key)
                return True
            except Exception:
                pass

        if len(self.memory_cache) >= self.max_size:
            if self.enable_lru:
                self._evict_lru()
            else:
                oldest = min(
                    self.memory_cache.keys(), key=lambda k: self.memory_cache[k].created_at
                )
                del self.memory_cache[oldest]

        self.memory_cache[full_key] = entry
        for tag in tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            if full_key not in self.tag_index[tag]:
                self.tag_index[tag].append(full_key)

        return True

    def delete(self, key: str, namespace: str = "toolbox") -> bool:
        full_key = f"{self._key_prefix(namespace)}{key}"

        if self.redis_client:
            try:
                self.redis_client.delete(full_key)
                return True
            except Exception:
                pass

        if full_key in self.memory_cache:
            entry = self.memory_cache[full_key]
            for tag in entry.tags:
                if tag in self.tag_index and full_key in self.tag_index[tag]:
                    self.tag_index[tag].remove(full_key)
            del self.memory_cache[full_key]
            return True
        return False

    def invalidate_by_tag(self, tag: str, namespace: str = "toolbox") -> int:
        tag_key = f"{self._key_prefix(namespace)}tag:{tag}"
        keys_to_delete: List[str] = []

        if self.redis_client:
            try:
                keys_to_delete = list(self.redis_client.smembers(tag_key))
                self.redis_client.delete(tag_key)
            except Exception:
                pass

        if tag in self.tag_index:
            keys_to_delete.extend(self.tag_index[tag])
            del self.tag_index[tag]

        count = 0
        for k in keys_to_delete:
            bare = (
                k.replace(self._key_prefix(namespace), "", 1)
                if k.startswith(self._key_prefix(namespace))
                else k
            )
            if self.delete(bare, namespace):
                count += 1
        return count

    def invalidate_by_pattern(self, pattern: str, namespace: str = "toolbox") -> int:
        full_pattern = f"{self._key_prefix(namespace)}{pattern}"
        count = 0

        if self.redis_client:
            try:
                keys = self.redis_client.keys(full_pattern)
                if keys:
                    count = self.redis_client.delete(*keys)
            except Exception:
                pass

        bare_prefix = self._key_prefix(namespace)
        keys_to_delete = [
            k for k in self.memory_cache if fnmatch.fnmatch(k, f"{bare_prefix}{pattern}")
        ]
        for k in keys_to_delete:
            bare = k.replace(bare_prefix, "", 1) if k.startswith(bare_prefix) else k
            self.delete(bare, namespace)
            count += 1
        return count

    def get_stats(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "memory_cache_size": len(self.memory_cache),
            "max_size": self.max_size,
            "tag_index_size": len(self.tag_index),
            "redis_available": self.redis_client is not None,
        }
        if self.memory_cache:
            total_access = sum(e.access_count for e in self.memory_cache.values())
            stats["total_accesses"] = total_access
            stats["avg_access_per_entry"] = total_access / len(self.memory_cache)
        return stats

    def clear(self, namespace: str = "toolbox") -> int:
        return self.invalidate_by_pattern("*", namespace)

    def _evict_lru(self) -> None:
        if not self.memory_cache:
            return
        lru_key = min(
            self.memory_cache.keys(),
            key=lambda k: self.memory_cache[k].last_accessed or self.memory_cache[k].created_at,
        )
        del self.memory_cache[lru_key]

    def _update_redis_entry(self, key: str, entry: CacheEntry) -> None:
        if not self.redis_client:
            return
        try:
            entry_data = json.dumps(entry.to_dict())
            ttl = self.redis_client.ttl(key)
            if ttl > 0:
                self.redis_client.setex(key, ttl, entry_data)
        except Exception:
            pass


class EmbeddingCache:
    def __init__(self, cache_manager: AdvancedCacheManager):
        self.cache_manager = cache_manager
        self.namespace = "embeddings"

    def _key(self, text: str) -> str:
        return f"emb:{hashlib.md5(text.encode()).hexdigest()}"

    def get(self, text: str) -> Optional[Any]:
        return self.cache_manager.get(self._key(text), namespace=self.namespace)

    def set(self, text: str, embedding: Any, ttl: int = 86400) -> bool:
        return self.cache_manager.set(
            self._key(text), embedding, namespace=self.namespace, ttl=ttl, tags=["embedding"]
        )
