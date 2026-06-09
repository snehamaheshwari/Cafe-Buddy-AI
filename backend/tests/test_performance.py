"""
Performance & Load Tests — Cafe Buddy API

Tests simulate concurrent load in-process using asyncio + httpx.ASGITransport.
All tests run inside the same event loop against the live FastAPI app.

Targets:
  - P50 response time   < 100 ms
  - P95 response time   < 500 ms
  - Error rate          < 1 %
  - 1000-user burst     completes in < 60 s

Note: These tests are marked with @pytest.mark.slow and are excluded from
normal test runs. Execute explicitly with:
    pytest tests/test_performance.py -v -s
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
import statistics
from typing import Any

import pytest

# ─── Path + env setup ────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_TMPDIR = tempfile.mkdtemp(prefix="perf_test_")
os.environ.setdefault("DATA_DIR", _TMPDIR)

import httpx

# Lazily import the FastAPI app so the env var is already set
from main import app

# ─── Transport ────────────────────────────────────────────────────────────────
_transport = httpx.ASGITransport(app=app)


async def _get(path: str, username: str = "admin") -> tuple[int, float]:
    """Perform one GET request; returns (status_code, elapsed_ms)."""
    start = time.monotonic()
    async with httpx.AsyncClient(transport=_transport, base_url="http://test") as client:
        resp = await client.get(path, headers={"X-Username": username})
    elapsed = (time.monotonic() - start) * 1000
    return resp.status_code, elapsed


async def _post(path: str, payload: dict, username: str = "admin") -> tuple[int, float]:
    """Perform one POST request; returns (status_code, elapsed_ms)."""
    start = time.monotonic()
    async with httpx.AsyncClient(transport=_transport, base_url="http://test") as client:
        resp = await client.post(
            path, json=payload,
            headers={"Content-Type": "application/json", "X-Username": username},
        )
    elapsed = (time.monotonic() - start) * 1000
    return resp.status_code, elapsed


def _stats(times: list[float]) -> dict:
    if not times:
        return {}
    times_s = sorted(times)
    n = len(times_s)
    return {
        "n":   n,
        "min": round(times_s[0],  1),
        "p50": round(times_s[n // 2], 1),
        "p95": round(times_s[int(n * 0.95)], 1),
        "p99": round(times_s[int(n * 0.99)], 1),
        "max": round(times_s[-1], 1),
        "avg": round(statistics.mean(times),  1),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Sanity — single requests
# ═══════════════════════════════════════════════════════════════════════════════
class TestSingleRequests:
    def test_health_responds(self):
        status, ms = asyncio.get_event_loop().run_until_complete(_get("/health"))
        assert status == 200
        assert ms < 500

    def test_roles_responds(self):
        status, ms = asyncio.get_event_loop().run_until_complete(_get("/api/roles"))
        assert status == 200

    def test_audit_stats_responds(self):
        status, ms = asyncio.get_event_loop().run_until_complete(_get("/api/audit/stats"))
        assert status == 200

    def test_login_responds(self):
        status, ms = asyncio.get_event_loop().run_until_complete(
            _post("/api/auth/login", {"username": "admin", "password": "cafe123"})
        )
        assert status == 200

    def test_audit_logs_responds(self):
        status, ms = asyncio.get_event_loop().run_until_complete(
            _get("/api/audit/logs?limit=10")
        )
        assert status == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Concurrent load — 100 users
# ═══════════════════════════════════════════════════════════════════════════════
class TestConcurrent100:
    @pytest.fixture(scope="class")
    def results(self):
        """Run 100 concurrent health checks and collect timings."""
        async def run():
            tasks = [_get("/health", username=f"user{i%10}") for i in range(100)]
            return await asyncio.gather(*tasks)
        return asyncio.get_event_loop().run_until_complete(run())

    def test_all_succeed(self, results):
        statuses = [r[0] for r in results]
        errors = sum(1 for s in statuses if s >= 400)
        error_rate = errors / len(statuses)
        assert error_rate < 0.01, f"Error rate {error_rate:.1%} ≥ 1%"

    def test_p95_under_500ms(self, results):
        times = [r[1] for r in results]
        st = _stats(times)
        print(f"\n[100 users / health] {st}")
        assert st["p95"] < 500, f"P95 = {st['p95']} ms ≥ 500 ms"

    def test_average_under_200ms(self, results):
        times = [r[1] for r in results]
        st = _stats(times)
        assert st["avg"] < 200, f"Avg = {st['avg']} ms ≥ 200 ms"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Concurrent load — 100 login requests
# ═══════════════════════════════════════════════════════════════════════════════
class TestConcurrentLogin100:
    @pytest.fixture(scope="class")
    def results(self):
        async def run():
            tasks = [
                _post("/api/auth/login",
                      {"username": "admin", "password": "cafe123"},
                      username="admin")
                for _ in range(100)
            ]
            return await asyncio.gather(*tasks)
        return asyncio.get_event_loop().run_until_complete(run())

    def test_all_succeed(self, results):
        errors = sum(1 for s, _ in results if s >= 400)
        assert errors / len(results) < 0.01

    def test_p95_under_500ms(self, results):
        times = [ms for _, ms in results]
        st = _stats(times)
        print(f"\n[100 logins] {st}")
        assert st["p95"] < 500


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Audit log write performance — 500 concurrent writes
# ═══════════════════════════════════════════════════════════════════════════════
class TestAuditWritePerformance:
    def test_500_concurrent_audit_writes(self):
        import audit_store as _audit
        _audit.clear_logs()  # start from clean slate

        async def run():
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(None, lambda i=i: _audit.log_action(
                    f"user{i % 10}", "auth", "LOGIN", f"entry {i}"
                ))
                for i in range(500)
            ]
            return await asyncio.gather(*tasks)

        start = time.monotonic()
        asyncio.get_event_loop().run_until_complete(run())
        elapsed = time.monotonic() - start

        _, total = _audit.get_logs(limit=600)
        print(f"\n[500 audit writes] {elapsed:.2f}s total, {total} entries stored")
        assert total == 500
        assert elapsed < 10  # 500 writes must complete in <10s


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Mixed endpoint load — 500 users, various endpoints
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.slow
class TestMixedLoad500:
    def test_mixed_500_concurrent(self):
        async def run():
            endpoints = [
                "/health",
                "/api/roles",
                "/api/audit/stats",
                "/api/audit/logs?limit=10",
                "/api/upload/status",
            ]
            tasks = [
                _get(endpoints[i % len(endpoints)], username=f"user{i % 20}")
                for i in range(500)
            ]
            return await asyncio.gather(*tasks, return_exceptions=True)

        start = time.monotonic()
        results = asyncio.get_event_loop().run_until_complete(run())
        elapsed = time.monotonic() - start

        # Filter out exceptions (network errors)
        valid = [(s, ms) for r in results if isinstance(r, tuple)
                 for s, ms in [r]]
        errors = sum(1 for s, _ in valid if s >= 500)
        times  = [ms for _, ms in valid]
        st     = _stats(times)

        print(f"\n[500 mixed users] {st} | elapsed={elapsed:.1f}s | errors={errors}")
        assert errors / max(len(valid), 1) < 0.01, f"Server error rate > 1%"
        assert st["p95"] < 1000, f"P95 {st['p95']} ms too high for mixed load"


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Burst — 1000 users
# ═══════════════════════════════════════════════════════════════════════════════
@pytest.mark.slow
class TestBurst1000:
    def test_1000_concurrent_health(self):
        async def run():
            tasks = [_get("/health", username=f"u{i%50}") for i in range(1000)]
            return await asyncio.gather(*tasks, return_exceptions=True)

        start = time.monotonic()
        results = asyncio.get_event_loop().run_until_complete(run())
        elapsed = time.monotonic() - start

        valid  = [r for r in results if isinstance(r, tuple)]
        errors = sum(1 for s, _ in valid if s >= 500)
        times  = [ms for _, ms in valid]
        st     = _stats(times)

        print(f"\n[1000 burst / health] {st} | elapsed={elapsed:.1f}s | errors={errors}/{len(valid)}")
        error_rate = errors / max(len(valid), 1)
        assert error_rate < 0.01, f"Error rate {error_rate:.1%} ≥ 1%"
        assert elapsed < 60, f"1000 requests took {elapsed:.1f}s > 60s"
        assert st["p95"] < 1000, f"P95 {st['p95']} ms under 1000-user burst"

    def test_1000_login_burst(self):
        async def run():
            # Only admin/owner credentials are valid — we intentionally mix
            # valid and invalid to simulate realistic load
            tasks = []
            for i in range(1000):
                if i % 3 == 0:
                    tasks.append(_post("/api/auth/login",
                                       {"username": "admin", "password": "cafe123"}))
                elif i % 3 == 1:
                    tasks.append(_post("/api/auth/login",
                                       {"username": "owner", "password": "buddy@2024"}))
                else:
                    tasks.append(_post("/api/auth/login",
                                       {"username": f"user{i}", "password": "wrong"}))
            return await asyncio.gather(*tasks, return_exceptions=True)

        start = time.monotonic()
        results = asyncio.get_event_loop().run_until_complete(run())
        elapsed = time.monotonic() - start

        valid    = [r for r in results if isinstance(r, tuple)]
        failures = sum(1 for s, _ in valid if s >= 500)  # 401 is expected, 500 is not
        times    = [ms for _, ms in valid]
        st       = _stats(times)

        print(f"\n[1000 login burst] {st} | elapsed={elapsed:.1f}s | server_errors={failures}")
        assert failures / max(len(valid), 1) < 0.01  # no server errors > 1%
        assert elapsed < 60


# ═══════════════════════════════════════════════════════════════════════════════
# 7. audit_store throughput benchmark
# ═══════════════════════════════════════════════════════════════════════════════
class TestAuditStoreThroughput:
    def test_1000_sequential_writes_under_5s(self, tmp_path, monkeypatch):
        import audit_store as _audit
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        _audit.reset_for_tests()

        start = time.monotonic()
        for i in range(1000):
            _audit.log_action(f"user{i%10}", "auth", "LOGIN", f"entry {i}")
        elapsed = time.monotonic() - start

        print(f"\n[1000 sequential writes] {elapsed:.2f}s → {1000/elapsed:.0f} writes/s")
        assert elapsed < 5, f"1000 sequential writes took {elapsed:.2f}s > 5s"
        _, total = _audit.get_logs(limit=1100)
        assert total == 1000
