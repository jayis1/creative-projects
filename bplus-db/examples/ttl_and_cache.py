#!/usr/bin/env python3
"""Example: TTL (time-to-live) keys and LRU cache.

Demonstrates key expiration and the read-through cache.
"""

import time
from bplus_db import Database

# ── TTL Example ──────────────────────────────────────────────

print("=== TTL (Time-To-Live) ===\n")

db = Database(order=16)

# Store temporary keys with TTL
db.put("session:abc123", {"user": "alice"}, ttl=3600)   # Expires in 1 hour
db.put("cache:weather", "sunny, 72°F", ttl=60)          # Expires in 1 minute
db.put("otp:1234", "verification code", ttl=0.05)       # Expires in 50ms

print("Session key:", db.get("session:abc123"))
print("Remaining TTL:", round(db.get_ttl("session:abc123"), 1), "seconds")
print()

# Short-lived key
print("OTP before expiry:", db.get("otp:1234"))
time.sleep(0.06)
print("OTP after expiry:", db.get("otp:1234"))  # Returns None
print()

# Eagerly clean up all expired keys
db.put("temp1", "data", ttl=0.01)
db.put("temp2", "data2", ttl=0.01)
time.sleep(0.02)
evicted = db.cleanup_expired()
print(f"Cleaned up {evicted} expired keys")

# ── LRU Cache Example ────────────────────────────────────────

print("\n=== LRU Cache ===\n")

from bplus_db import DatabaseConfig, CacheConfig, TreeConfig

# Create a database with a 100-entry LRU cache
config = DatabaseConfig(
    tree=TreeConfig(order=16),
    cache=CacheConfig(enabled=True, max_size=100),
)
db_cached = Database(config=config)

# Populate with data
for i in range(200):
    db_cached.put(f"key:{i}", f"value_{i}")

# Read all keys twice — second pass should be cache hits
for i in range(200):
    db_cached.get(f"key:{i}")
for i in range(200):
    db_cached.get(f"key:{i}")

# Check cache statistics
cache_stats = db_cached.cache_stats()
print(f"Cache size: {cache_stats['cache_size']}")
print(f"Cache hits: {cache_stats['hits']}")
print(f"Cache misses: {cache_stats['misses']}")
print(f"Hit rate: {cache_stats['hit_rate']:.2%}")
print()

# Cache is invalidated on write
db_cached.put("key:0", "new_value")
result = db_cached.get("key:0")
print(f"After update: key:0 = {result}")
cache_stats = db_cached.cache_stats()
print(f"Cache misses after invalidation: {cache_stats['misses']}")

# Clear the cache
db_cached.clear_cache()
cache_stats = db_cached.cache_stats()
print(f"Cache size after clear: {cache_stats['cache_size']}")