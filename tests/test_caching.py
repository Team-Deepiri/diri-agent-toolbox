from datetime import datetime, timedelta

from diri_agent_toolbox.caching import AdvancedCacheManager, CacheEntry, EmbeddingCache


def test_cache_entry_defaults():
    now = datetime.now()
    entry = CacheEntry(key="k", value="v", created_at=now, expires_at=None)
    assert entry.access_count == 0
    assert entry.last_accessed == now
    assert entry.is_expired() is False


def test_cache_entry_expired():
    now = datetime.now()
    past = now - timedelta(seconds=1)
    entry = CacheEntry(key="k", value="v", created_at=past, expires_at=past)
    assert entry.is_expired() is True


def test_cache_entry_roundtrip():
    now = datetime.now()
    entry = CacheEntry(
        key="k", value=[1, 2], created_at=now, expires_at=now + timedelta(seconds=60), tags=["a"]
    )
    d = entry.to_dict()
    restored = CacheEntry.from_dict(d)
    assert restored.key == "k"
    assert restored.value == [1, 2]
    assert restored.tags == ["a"]


class TestAdvancedCacheManager:
    def test_set_and_get(self):
        cache = AdvancedCacheManager(max_size=10)
        assert cache.set("x", 42) is True
        assert cache.get("x") == 42

    def test_get_missing(self):
        cache = AdvancedCacheManager()
        assert cache.get("nonexistent") is None

    def test_expiration(self):
        cache = AdvancedCacheManager(max_size=10, default_ttl=0)
        cache.set("exp", "val")
        import time

        time.sleep(0.01)
        assert cache.get("exp") is None

    def test_delete(self):
        cache = AdvancedCacheManager(max_size=10)
        cache.set("d", "v")
        assert cache.delete("d") is True
        assert cache.get("d") is None

    def test_delete_missing(self):
        cache = AdvancedCacheManager()
        assert cache.delete("nope") is False

    def test_tags(self):
        cache = AdvancedCacheManager(max_size=10)
        cache.set("a", 1, tags=["x"])
        cache.set("b", 2, tags=["x"])
        cache.set("c", 3, tags=["y"])
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        count = cache.invalidate_by_tag("x")
        assert count == 2
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.get("c") == 3

    def test_clear(self):
        cache = AdvancedCacheManager(max_size=10)
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.clear() == 2
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_lru_eviction(self):
        cache = AdvancedCacheManager(max_size=3, enable_lru=True)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.get("a")
        cache.get("b")
        cache.set("d", 4)
        assert cache.get("c") is None
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("d") == 4

    def test_invalidate_by_pattern(self):
        cache = AdvancedCacheManager(max_size=10)
        cache.set("user:1", "a")
        cache.set("user:2", "b")
        cache.set("config:x", "c")
        count = cache.invalidate_by_pattern("user:*")
        assert count == 2
        assert cache.get("user:1") is None
        assert cache.get("config:x") == "c"

    def test_get_stats(self):
        cache = AdvancedCacheManager(max_size=100)
        cache.set("a", 1)
        cache.get("a")
        cache.get("a")
        stats = cache.get_stats()
        assert stats["memory_cache_size"] == 1
        assert stats["max_size"] == 100
        assert stats["total_accesses"] == 2

    def test_namespace_isolation(self):
        cache = AdvancedCacheManager(max_size=10)
        cache.set("k", "ns1", namespace="ns1")
        cache.set("k", "ns2", namespace="ns2")
        assert cache.get("k", namespace="ns1") == "ns1"
        assert cache.get("k", namespace="ns2") == "ns2"

    def test_update_access(self):
        cache = AdvancedCacheManager(max_size=10)
        cache.set("u", "v")
        assert cache.get("u", update_access=False) == "v"


class TestEmbeddingCache:
    def test_set_and_get(self):
        inner = AdvancedCacheManager(max_size=10)
        ec = EmbeddingCache(inner)
        ec.set("hello world", [0.1, 0.2])
        result = ec.get("hello world")
        assert result == [0.1, 0.2]

    def test_missing(self):
        inner = AdvancedCacheManager(max_size=10)
        ec = EmbeddingCache(inner)
        assert ec.get("missing") is None
