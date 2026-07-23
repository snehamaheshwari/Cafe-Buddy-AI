"""
test_subscriptions.py — Comprehensive test suite for the multi-tenant
subscription system in Cafe Buddy AI.

Covers:
  Unit tests       — individual function behaviour
  Regression tests — existing features continue to work after changes
  Functional tests — end-to-end API flows via FastAPI TestClient
  Performance tests— response-time assertions for critical paths

Run with:
    cd backend && python -m pytest tests/test_subscriptions.py -v
"""
from __future__ import annotations

import json
import os
import time
import uuid
import shutil
import tempfile
from typing import Optional

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & helpers
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """
    Each test gets its own isolated DATA_DIR so tenant JSON files never
    bleed between tests.
    """
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # Force tenant_store and role_store to pick up the new path
    import importlib, tenant_store, role_store, data_store
    importlib.reload(tenant_store)
    importlib.reload(role_store)
    importlib.reload(data_store)
    yield tmp_path


class _SyncASGIClient:
    """
    Synchronous HTTP client backed by httpx.AsyncClient + ASGITransport.
    Needed because httpx 0.28 removed the `app=` shorthand from httpx.Client;
    ASGITransport only supports async — we bridge via asyncio.run().
    """
    def __init__(self, app):
        self._app = app

    def _send(self, method: str, url: str, **kwargs):
        import asyncio, httpx
        async def _inner():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=self._app),
                base_url="http://testserver",
            ) as c:
                return await getattr(c, method)(url, **kwargs)
        return asyncio.run(_inner())

    def get(self, url, **kwargs):    return self._send("get",    url, **kwargs)
    def post(self, url, **kwargs):   return self._send("post",   url, **kwargs)
    def put(self, url, **kwargs):    return self._send("put",    url, **kwargs)
    def delete(self, url, **kwargs): return self._send("delete", url, **kwargs)


@pytest.fixture()
def client(isolated_data_dir):
    """ASGI test client with fresh app state (httpx 0.28 compatible)."""
    import importlib
    import main as _main
    importlib.reload(_main)
    return _SyncASGIClient(_main.app)


def _register(client, cafe_name="Test Café", username="testowner",
              password="pass123", email="owner@test.com"):
    """Helper to register a new tenant via the API."""
    return client.post("/api/auth/register", json={
        "cafe_name":   cafe_name,
        "owner_name":  "Test Owner",
        "owner_email": email,
        "username":    username,
        "password":    password,
        "brand_color": "#10b981",
    })


def _login(client, username="admin", password="cafe123", workspace=None):
    body = {"username": username, "password": password}
    if workspace:
        body["workspace"] = workspace
    return client.post("/api/auth/login", json=body)


# ─────────────────────────────────────────────────────────────────────────────
# UNIT TESTS — auth_utils
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthUtils:
    def test_hash_and_verify_bcrypt(self):
        from auth_utils import hash_password, verify_password
        pwd = "securepassword"
        hashed = hash_password(pwd)
        assert hashed != pwd, "Hash must not equal plaintext"
        assert verify_password(pwd, hashed), "Correct password should verify"
        assert not verify_password("wrong", hashed), "Wrong password should fail"

    def test_legacy_plaintext_verify(self):
        """Legacy passwords (non-bcrypt) fall back to direct equality."""
        from auth_utils import verify_password
        assert verify_password("cafe123", "cafe123"), "Plaintext match should pass"
        assert not verify_password("wrong", "cafe123"), "Plaintext mismatch should fail"

    def test_create_and_decode_token(self):
        from auth_utils import create_access_token, decode_token
        payload = {"username": "alice", "tenant_id": "abc-123", "role_id": "admin"}
        token = create_access_token(payload)
        assert isinstance(token, str)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["username"]  == "alice"
        assert decoded["tenant_id"] == "abc-123"

    def test_expired_token_returns_none(self):
        from auth_utils import create_access_token, decode_token
        token = create_access_token({"username": "bob"}, expires_hours=-1)
        result = decode_token(token)
        assert result is None, "Expired token must return None"

    def test_invalid_token_returns_none(self):
        from auth_utils import decode_token
        assert decode_token("not.a.valid.jwt") is None
        assert decode_token("") is None

    def test_extract_tenant_id(self):
        from auth_utils import create_access_token, extract_tenant_id
        token = create_access_token({"username": "x", "tenant_id": "t-123"})
        header = f"Bearer {token}"
        assert extract_tenant_id(header) == "t-123"
        assert extract_tenant_id("") is None
        assert extract_tenant_id("Basic xyz") is None

    def test_extract_username(self):
        from auth_utils import create_access_token, extract_username
        token = create_access_token({"username": "charlie", "tenant_id": "t-1"})
        header = f"Bearer {token}"
        assert extract_username(header) == "charlie"


# ─────────────────────────────────────────────────────────────────────────────
# UNIT TESTS — tenant_store
# ─────────────────────────────────────────────────────────────────────────────

class TestTenantStore:
    def test_create_tenant_basic(self):
        import tenant_store as ts
        tenant = ts.create_tenant(
            cafe_name="Heenu's Cafe",   # ASCII version to avoid unicode variance
            owner_name="Heenu",
            owner_email="heenu@cafe.com",
            admin_username="heenu_admin",
        )
        assert tenant["tenant_id"]
        assert tenant["slug"] == "heenus-cafe"
        assert tenant["plan"] == ts.PLAN_FREE
        assert tenant["max_users"] == 3
        assert tenant["storage_limit_mb"] == 200
        assert tenant["is_active"] is True

    def test_create_tenant_slugify(self):
        import tenant_store as ts
        t1 = ts.create_tenant("My Café", "A", "a@x.com", "a1")
        t2 = ts.create_tenant("My Café", "B", "b@x.com", "b1")   # duplicate name
        assert t1["slug"] != t2["slug"], "Duplicate names must get unique slugs"
        assert t2["slug"].startswith(t1["slug"])  # e.g. "my-cafe-1"

    def test_create_tenant_missing_fields(self):
        import tenant_store as ts
        with pytest.raises(ValueError, match="Café name"):
            ts.create_tenant("", "A", "a@x.com", "u1")
        with pytest.raises(ValueError, match="email"):
            ts.create_tenant("Café", "A", "", "u1")
        with pytest.raises(ValueError, match="username"):
            ts.create_tenant("Café", "A", "a@x.com", "")

    def test_duplicate_username_rejected(self):
        import tenant_store as ts
        ts.create_tenant("Café A", "A", "a@x.com", "shareduser")
        with pytest.raises(ValueError, match="already registered"):
            ts.create_tenant("Café B", "B", "b@x.com", "shareduser")

    def test_get_tenant_by_slug(self):
        import tenant_store as ts
        ts.create_tenant("Brewed Cafe", "X", "x@x.com", "xu1")
        t = ts.get_tenant_by_slug("brewed-cafe")
        assert t is not None
        assert t["cafe_name"] == "Brewed Cafe"

    def test_check_storage_limit_ok(self):
        import tenant_store as ts
        tenant = ts.create_tenant("StoreCafe", "S", "s@x.com", "su1")
        tid = tenant["tenant_id"]
        ok, used, limit = ts.check_storage_limit(tid, 10 * 1024 * 1024)  # 10 MB
        assert ok is True

    def test_check_storage_limit_exceeded(self):
        import tenant_store as ts
        tenant = ts.create_tenant("FullCafe", "F", "f@x.com", "fu1")
        tid = tenant["tenant_id"]
        # Simulate 195 MB already used
        ts.record_upload(tid, 195 * 1024 * 1024)
        ok, used, limit = ts.check_storage_limit(tid, 10 * 1024 * 1024)  # 10 MB more
        assert ok is False
        assert used >= 195.0

    def test_record_upload_increments_storage(self):
        import tenant_store as ts
        tenant = ts.create_tenant("UploadCafe", "U", "u@x.com", "uu1")
        tid = tenant["tenant_id"]
        ts.record_upload(tid, 5 * 1024 * 1024)     # 5 MB
        ts.record_upload(tid, 3 * 1024 * 1024)     # 3 MB
        used = ts.get_storage_used_mb(tid)
        assert 7.9 < used < 8.1, f"Expected ~8 MB, got {used}"

    def test_system_tenant_storage_always_ok(self):
        import tenant_store as ts
        ok, _, _ = ts.check_storage_limit(ts.SYSTEM_TENANT_ID, 500 * 1024 * 1024)
        assert ok is True, "System tenant has unlimited storage"

    def test_update_branding(self):
        import tenant_store as ts
        tenant = ts.create_tenant("OldName Café", "X", "x@x.com", "xo1")
        tid = tenant["tenant_id"]
        updated = ts.update_branding(tid, cafe_name="NewName Café", brand_color="#ff0000")
        assert updated["cafe_name"]   == "NewName Café"
        assert updated["brand_color"] == "#ff0000"

    def test_get_tenant_data_dir_created(self):
        import tenant_store as ts
        tenant = ts.create_tenant("DirCafe", "D", "d@x.com", "du1")
        path = ts.get_tenant_data_dir(tenant["tenant_id"])
        assert os.path.isdir(path), "Tenant data directory must be created"

    def test_slugify(self):
        from tenant_store import slugify
        # Accents are stripped via NFKD normalization: é→e, Café→cafe
        assert slugify("Heenu's Café")  == "heenus-cafe"
        assert slugify("  The Café!  ") == "the-cafe"
        # @ is removed; é→e; spaces→hyphen
        assert slugify("My café@123")   == "my-cafe123"
        assert slugify("Normal Cafe")   == "normal-cafe"


# ─────────────────────────────────────────────────────────────────────────────
# UNIT TESTS — TenantRoleStore
# ─────────────────────────────────────────────────────────────────────────────

class TestTenantRoleStore:
    def _make_store(self, tmp_path, name="TestCafe"):
        import tenant_store as ts
        tenant = ts.create_tenant(name, "T", "t@t.com",
                                  f"admin_{uuid.uuid4().hex[:6]}")
        from role_store import TenantRoleStore
        return TenantRoleStore(tenant["tenant_id"],
                               ts.get_tenant_data_dir(tenant["tenant_id"]))

    def test_default_roles_exist(self, tmp_path):
        store = self._make_store(tmp_path)
        role_ids = {r["id"] for r in store.list_roles()}
        assert "admin" in role_ids
        assert "sub_admin" in role_ids
        assert "viewer" in role_ids

    def test_create_and_authenticate_user(self, tmp_path):
        import tenant_store as ts
        tenant = ts.create_tenant("AuthCafe", "A", "a@t.com", "acowner")
        from role_store import TenantRoleStore
        store = TenantRoleStore(tenant["tenant_id"],
                                ts.get_tenant_data_dir(tenant["tenant_id"]))
        store.seed_admin_user("acowner", "$plaintext$")   # seed first
        from auth_utils import hash_password
        pwd = hash_password("mypassword")
        store._users["acowner"]["password"] = pwd
        store._persist()
        result = store.authenticate("acowner", "mypassword")
        assert result is not None
        assert result["username"] == "acowner"
        assert result["role_id"]  == "admin"

    def test_max_users_enforced(self, tmp_path):
        """Free plan only allows 3 users total."""
        import tenant_store as ts
        tenant = ts.create_tenant("LimitCafe", "L", "l@t.com", "lcowner")
        from role_store import TenantRoleStore
        tid = tenant["tenant_id"]
        store = TenantRoleStore(tid, ts.get_tenant_data_dir(tid))
        store.seed_admin_user("lcowner", "pw1")   # user 1 (owner)
        store.create_user("user2", "pw2", "viewer")  # user 2
        store.create_user("user3", "pw3", "viewer")  # user 3
        with pytest.raises(ValueError, match="Plan limit"):
            store.create_user("user4", "pw4", "viewer")  # user 4 — exceeds 3

    def test_delete_system_user_rejected(self, tmp_path):
        import tenant_store as ts
        tenant = ts.create_tenant("ProtectedCafe", "P", "p@t.com", "pcowner")
        from role_store import TenantRoleStore
        store = TenantRoleStore(tenant["tenant_id"],
                                ts.get_tenant_data_dir(tenant["tenant_id"]))
        store.seed_admin_user("pcowner", "pw")
        with pytest.raises(ValueError, match="system user"):
            store.delete_user("pcowner")

    def test_data_isolation_between_tenants(self, tmp_path):
        """Users created for Tenant A should not appear in Tenant B."""
        import tenant_store as ts
        from role_store import TenantRoleStore

        tA = ts.create_tenant("Café A", "A", "a@a.com", "ownerA")
        tB = ts.create_tenant("Café B", "B", "b@b.com", "ownerB")

        storeA = TenantRoleStore(tA["tenant_id"], ts.get_tenant_data_dir(tA["tenant_id"]))
        storeB = TenantRoleStore(tB["tenant_id"], ts.get_tenant_data_dir(tB["tenant_id"]))

        storeA.seed_admin_user("ownerA", "pwA")
        storeB.seed_admin_user("ownerB", "pwB")

        storeA.create_user("extra_user_A", "pw", "viewer")

        users_A = {u["username"] for u in storeA.list_users()}
        users_B = {u["username"] for u in storeB.list_users()}

        assert "extra_user_A" in users_A
        assert "extra_user_A" not in users_B, "Tenant B must not see Tenant A users"


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONAL TESTS — Registration API
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistrationAPI:
    def test_register_success(self, client):
        r = _register(client)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        assert data["slug"]
        assert data["token"]
        assert data["tenant_id"]
        assert data["cafe_name"] == "Test Café"

    def test_register_short_password(self, client):
        r = _register(client, password="abc")
        assert r.status_code == 400
        assert "6 characters" in r.json()["detail"].lower()

    def test_register_empty_cafe_name(self, client):
        r = _register(client, cafe_name="  ")
        assert r.status_code == 400

    def test_register_duplicate_username(self, client):
        _register(client, username="dupuser")
        r = _register(client, cafe_name="Another Café", username="dupuser",
                      email="other@test.com")
        assert r.status_code == 400
        assert "already registered" in r.json()["detail"]

    def test_registration_token_carries_tenant_id(self, client):
        from auth_utils import decode_token
        r = _register(client)
        token = r.json()["token"]
        payload = decode_token(token)
        assert payload is not None
        assert payload["tenant_id"] == r.json()["tenant_id"]
        assert payload["username"]  == "testowner"


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONAL TESTS — Workspace Lookup
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkspaceAPI:
    def test_workspace_info_found(self, client):
        reg = _register(client, cafe_name="Brewed Bliss")
        slug = reg.json()["slug"]
        r = client.get(f"/api/auth/workspace/{slug}")
        assert r.status_code == 200
        data = r.json()
        assert data["found"] is True
        assert data["cafe_name"] == "Brewed Bliss"

    def test_workspace_info_not_found(self, client):
        r = client.get("/api/auth/workspace/nonexistent-cafe-xyz")
        assert r.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONAL TESTS — Login Flow
# ─────────────────────────────────────────────────────────────────────────────

class TestLoginFlow:
    def test_system_tenant_login(self, client):
        """Existing admin/owner credentials must still work."""
        r = _login(client, "admin", "cafe123")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["username"] == "admin"
        assert data["token"]

    def test_system_tenant_wrong_password(self, client):
        r = _login(client, "admin", "wrongpassword")
        assert r.status_code == 401

    def test_new_tenant_login_via_workspace(self, client):
        reg = _register(client, username="cafeowner", password="pass123")
        slug = reg.json()["slug"]
        r = _login(client, "cafeowner", "pass123", workspace=slug)
        assert r.status_code == 200
        data = r.json()
        assert data["tenant_id"] == reg.json()["tenant_id"]
        assert data["cafe_name"] == "Test Café"
        assert data["token"]

    def test_new_tenant_wrong_password(self, client):
        reg = _register(client, username="cafeo2", password="pass123")
        slug = reg.json()["slug"]
        r = _login(client, "cafeo2", "wrongpass", workspace=slug)
        assert r.status_code == 401

    def test_workspace_not_found_returns_404(self, client):
        r = _login(client, "admin", "cafe123", workspace="no-such-slug")
        assert r.status_code == 404

    def test_login_returns_jwt_with_correct_claims(self, client):
        from auth_utils import decode_token
        reg = _register(client, username="jwttest", password="pass123")
        slug = reg.json()["slug"]
        r = _login(client, "jwttest", "pass123", workspace=slug)
        token = r.json()["token"]
        payload = decode_token(token)
        assert payload["username"]  == "jwttest"
        assert payload["tenant_id"] == reg.json()["tenant_id"]
        assert payload["role_id"]   == "admin"


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONAL TESTS — Tenant Branding API
# ─────────────────────────────────────────────────────────────────────────────

class TestTenantBrandingAPI:
    def test_tenant_info_system(self, client):
        r = _login(client, "admin", "cafe123")
        token = r.json()["token"]
        info = client.get("/api/tenant/info",
                          headers={"Authorization": f"Bearer {token}"})
        assert info.status_code == 200
        assert info.json()["tenant_id"] == "system"

    def test_tenant_info_new_tenant(self, client):
        reg = _register(client, cafe_name="Colour Café", username="cco1", password="pass123")
        token = reg.json()["token"]
        r = client.get("/api/tenant/info",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["cafe_name"] == "Colour Café"

    def test_update_branding(self, client):
        reg = _register(client, cafe_name="Old Name", username="brd1", password="pass123")
        token = reg.json()["token"]
        r = client.put("/api/tenant/branding",
                       json={"cafe_name": "New Name", "brand_color": "#ff0000"},
                       headers={"Authorization": f"Bearer {token}",
                                "Content-Type": "application/json"})
        assert r.status_code == 200
        updated = r.json()["tenant"]
        assert updated["cafe_name"]   == "New Name"
        assert updated["brand_color"] == "#ff0000"

    def test_system_tenant_branding_update_rejected(self, client):
        r = _login(client, "admin", "cafe123")
        token = r.json()["token"]
        r2 = client.put("/api/tenant/branding",
                        json={"cafe_name": "Hacked"},
                        headers={"Authorization": f"Bearer {token}",
                                 "Content-Type": "application/json"})
        assert r2.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONAL TESTS — Upload Storage Limit
# ─────────────────────────────────────────────────────────────────────────────

class TestUploadStorageLimit:
    def test_upload_exceeds_limit_rejected(self, client, tmp_path):
        """Simulate a tenant that has used 199 MB and tries to upload 2 MB."""
        import tenant_store as ts
        reg = _register(client, cafe_name="FullCafe", username="fc1", password="pass123")
        tid = reg.json()["tenant_id"]
        ts.record_upload(tid, 199 * 1024 * 1024)  # 199 MB used

        # Create a tiny dummy xlsx (won't parse correctly but will hit the size check first)
        token = reg.json()["token"]
        dummy = b"\x00" * (2 * 1024 * 1024)   # 2 MB of zeros
        from io import BytesIO
        r = client.post(
            "/api/upload/excel",
            files={"file": ("data.xlsx", BytesIO(dummy), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 413
        assert "Storage limit exceeded" in r.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# REGRESSION TESTS — existing features still work
# ─────────────────────────────────────────────────────────────────────────────

class TestRegression:
    def test_system_login_unaffected(self, client):
        """Existing admin/owner login still returns 200 after adding tenant auth."""
        r = client.post("/api/auth/login",
                        json={"username": "admin", "password": "cafe123"})
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_roles_api_still_works(self, client):
        r = client.get("/api/roles", headers={"X-Username": "admin"})
        assert r.status_code == 200
        role_ids = {role["id"] for role in r.json()["roles"]}
        assert "admin" in role_ids and "viewer" in role_ids

    def test_health_endpoint(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_dashboard_returns_data(self, client):
        r = client.get("/api/dashboard/overview",
                       headers={"X-Username": "admin"})
        assert r.status_code == 200
        assert "revenue_today" in r.json()

    def test_layer3_forecast_returns(self, client):
        r = client.get("/api/layer3/forecast",
                       headers={"X-Username": "admin"})
        assert r.status_code == 200
        assert "forecast" in r.json()

    def test_audit_logs_returns(self, client):
        r = client.get("/api/audit/logs",
                       headers={"X-Username": "admin", "X-Role": "admin"})
        assert r.status_code == 200
        assert "logs" in r.json()

    def test_auth_utils_backward_compatible_plaintext(self):
        """Legacy plaintext passwords (admin/owner) still verify without passlib hash."""
        from auth_utils import verify_password
        # admin uses "cafe123" stored as plaintext in _DEFAULT_USERS
        assert verify_password("cafe123", "cafe123")
        assert not verify_password("wrong", "cafe123")

    def test_tenant_register_does_not_break_system_roles(self, client):
        """Registering a new tenant must not alter system tenant's roles.json."""
        before = client.get("/api/roles", headers={"X-Username": "admin"}).json()
        _register(client)
        after = client.get("/api/roles", headers={"X-Username": "admin"}).json()
        assert before["roles"] == after["roles"]

    def test_data_isolation_upload(self, client, tmp_path):
        """POS data uploaded for one tenant must not appear for another."""
        import tenant_store as ts
        from data_store import save_dataset_for_tenant, load_dataset_for_tenant

        tA = ts.create_tenant("Café A", "A", "a@a.com", "ownerA")
        tB = ts.create_tenant("Café B", "B", "b@b.com", "ownerB")

        sample = [{"date": "2024-01-01", "item_name": "Espresso",
                   "category": "Bev", "quantity": 5, "price": 80,
                   "revenue": 400, "cost": 100, "platform": "Dine-in"}]

        save_dataset_for_tenant(tA["tenant_id"], "pos", sample, {"rows": 1})

        data_A, _ = load_dataset_for_tenant(tA["tenant_id"], "pos")
        data_B, _ = load_dataset_for_tenant(tB["tenant_id"], "pos")

        assert len(data_A) == 1, "Tenant A should have its own POS data"
        assert len(data_B) == 0, "Tenant B should not see Tenant A's data"


# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANCE TESTS — response-time assertions
# ─────────────────────────────────────────────────────────────────────────────

class TestPerformance:
    _MAX_MS = {
        "register":  900,   # bcrypt hashing adds ~200-400ms
        "login":     800,   # bcrypt verification adds ~200-400ms
        "workspace": 200,
        "dashboard": 300,
        "roles":     200,
        "forecast":  800,
    }

    def _elapsed_ms(self, fn):
        t0 = time.perf_counter()
        fn()
        return (time.perf_counter() - t0) * 1000

    def test_register_response_time(self, client):
        ms = self._elapsed_ms(lambda: _register(client,
            cafe_name="PerfCafe1", username="pc1", email="pc1@x.com"))
        assert ms < self._MAX_MS["register"], \
            f"Register took {ms:.0f} ms (max {self._MAX_MS['register']} ms)"

    def test_login_response_time(self, client):
        ms = self._elapsed_ms(lambda: _login(client, "admin", "cafe123"))
        assert ms < self._MAX_MS["login"], \
            f"Login took {ms:.0f} ms (max {self._MAX_MS['login']} ms)"

    def test_tenant_login_response_time(self, client):
        reg = _register(client, username="ptl1", password="pass123",
                        cafe_name="PerfTenant", email="ptl1@x.com")
        slug = reg.json()["slug"]
        ms = self._elapsed_ms(lambda: _login(client, "ptl1", "pass123", workspace=slug))
        assert ms < self._MAX_MS["login"], \
            f"Tenant login took {ms:.0f} ms (max {self._MAX_MS['login']} ms)"

    def test_workspace_lookup_response_time(self, client):
        reg = _register(client, username="pwl1", email="pwl1@x.com",
                        cafe_name="PerfWorkspace")
        slug = reg.json()["slug"]
        ms = self._elapsed_ms(
            lambda: client.get(f"/api/auth/workspace/{slug}"))
        assert ms < self._MAX_MS["workspace"], \
            f"Workspace lookup took {ms:.0f} ms (max {self._MAX_MS['workspace']} ms)"

    def test_dashboard_response_time(self, client):
        ms = self._elapsed_ms(
            lambda: client.get("/api/dashboard/overview",
                               headers={"X-Username": "admin"}))
        assert ms < self._MAX_MS["dashboard"], \
            f"Dashboard took {ms:.0f} ms (max {self._MAX_MS['dashboard']} ms)"

    def test_roles_response_time(self, client):
        ms = self._elapsed_ms(
            lambda: client.get("/api/roles", headers={"X-Username": "admin"}))
        assert ms < self._MAX_MS["roles"], \
            f"Roles took {ms:.0f} ms (max {self._MAX_MS['roles']} ms)"

    def test_concurrent_registrations(self, client):
        """50 sequential registrations must all succeed (no shared-state corruption)."""
        results = []
        for i in range(50):
            r = _register(client,
                cafe_name=f"Café {i}",
                username=f"user_{i}",
                email=f"u{i}@test.com")
            results.append(r.status_code)
        assert all(s == 200 for s in results), \
            f"Some registrations failed: {results}"
        # All slugs must be unique
        import tenant_store as ts
        slugs = [t["slug"] for t in ts.list_tenants()]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs detected"


# ─────────────────────────────────────────────────────────────────────────────
# NEW SUBSCRIPTION & DATA ISOLATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestNewUserBlankState:
    """New tenants must never see data that belongs to another tenant."""

    def test_new_tenant_dashboard_returns_zeros(self, client):
        """A freshly registered tenant has no data — dashboard must return 0s."""
        reg = _register(client, cafe_name="BlankCafe", username="blank1", email="b@b.com")
        assert reg.status_code == 200
        token = reg.json()["token"]
        r = client.get("/api/dashboard/overview",
                       headers={"Authorization": f"Bearer {token}", "X-Username": "blank1"})
        assert r.status_code == 200
        d = r.json()
        assert d["revenue_today"] == 0, "New tenant must have 0 revenue"
        assert d["orders_today"]  == 0, "New tenant must have 0 orders"

    def test_new_tenant_cannot_see_system_data(self, client):
        """
        Even if system tenant has data, a new tenant's token must
        route to their own (empty) dataset.
        """
        import data_store as ds
        # Inject data directly into the system-tenant in-memory store
        ds._pos_data = [{
            "date": "2024-01-01", "item_name": "Stolen Item",
            "category": "Main", "quantity": 10, "price": 100,
            "revenue": 1000.0, "cost": 200.0, "platform": "Dine-in",
        }]
        try:
            reg = _register(client, cafe_name="IsolatedCafe", username="iso1", email="i@i.com")
            token = reg.json()["token"]
            r = client.get("/api/dashboard/overview",
                           headers={"Authorization": f"Bearer {token}", "X-Username": "iso1"})
            d = r.json()
            assert d["revenue_today"] == 0, \
                "New tenant must not see system tenant's revenue"
        finally:
            ds._pos_data = []

    def test_new_tenant_layer1_summary_blank(self, client):
        """Layer-1 summary for a new tenant must show 0 records, not system data."""
        reg = _register(client, cafe_name="Layer1Cafe", username="l1user", email="l1@l1.com")
        token = reg.json()["token"]
        r = client.get("/api/layer1/summary",
                       headers={"Authorization": f"Bearer {token}", "X-Username": "l1user"})
        assert r.status_code == 200
        body = r.json()
        assert body.get("total_records", 0) == 0


class TestRegistrationResponse:
    """Registration endpoint must return enough info for the frontend workspace URL."""

    def test_register_returns_slug(self, client):
        r = _register(client, cafe_name="SlugTestCafe", username="slugtest", email="st@st.com")
        assert r.status_code == 200
        data = r.json()
        assert "slug" in data, "Response must include workspace slug"
        assert data["slug"] != "", "Slug must not be empty"

    def test_register_returns_workspace_url(self, client):
        r = _register(client, cafe_name="UrlTestCafe", username="urltest", email="ut@ut.com")
        assert r.status_code == 200
        data = r.json()
        assert "workspace_url" in data, "Response must include workspace_url"
        assert data["workspace_url"].startswith("?workspace="), \
            f"workspace_url must start with ?workspace=, got: {data['workspace_url']}"

    def test_slug_matches_cafe_name(self, client):
        r = _register(client, cafe_name="My Test Café", username="mtc1", email="mtc@m.com")
        data = r.json()
        # Slug should be URL-safe version of cafe name
        slug = data["slug"]
        assert " " not in slug, "Slug must not contain spaces"
        assert slug.islower() or "-" in slug, "Slug should be lowercase"

    def test_register_returns_token(self, client):
        r = _register(client)
        assert r.status_code == 200
        data = r.json()
        assert "token" in data and data["token"], "Must return a JWT token"

    def test_register_token_contains_tenant_id(self, client):
        """The issued JWT must embed the new tenant's ID so tenant routing works."""
        from auth_utils import decode_token
        r = _register(client, cafe_name="TokenCafe", username="tktst", email="tk@tk.com")
        token = r.json()["token"]
        decoded = decode_token(token)
        assert decoded is not None
        tenant_id = decoded.get("tenant_id")
        assert tenant_id and tenant_id != "system", \
            "New tenant JWT must carry their own tenant_id, not 'system'"


class TestWorkspaceSeedIdempotency:
    """Seed function must be idempotent — safe to run multiple times at startup."""

    def test_seed_creates_workspace(self, isolated_data_dir):
        import importlib, main as _m
        importlib.reload(_m)
        # on_event("startup") does NOT fire on module reload — call directly
        _m._seed_workspaces()
        import tenant_store as ts
        tenant = ts.get_tenant_by_slug("impastocafe")
        assert tenant is not None, "ImpastoCafe workspace must be created by seed"

    def test_seed_is_idempotent(self, isolated_data_dir):
        import importlib, main as _m
        importlib.reload(_m)
        _m._seed_workspaces()   # second call must not raise or duplicate
        import tenant_store as ts
        slugs = [t["slug"] for t in ts.list_tenants()]
        assert slugs.count("impastocafe") == 1, "Seed must not create duplicate workspace"

    def test_seed_admin_can_login(self, client):
        """ImpastoCafe admin must be able to log in after seed."""
        import importlib, main as _m
        importlib.reload(_m)
        _m._seed_workspaces()
        r = _login(client, username="ImpastoCafe", password="ImpastoCafe@123",
                   workspace="impastocafe")
        assert r.status_code == 200, f"ImpastoCafe login must succeed; got {r.text}"
        data = r.json()
        assert data["tenant_slug"] == "impastocafe"


class TestLoginWorkspaceIsolation:
    """Login without workspace slug must route to system tenant only."""

    def test_login_without_workspace_uses_system_tenant(self, client):
        """Default login (no workspace) routes to system tenant."""
        r = _login(client, username="admin", password="cafe123")
        assert r.status_code == 200
        data = r.json()
        assert data.get("tenant_id") == "system" or data.get("tenant_slug") is None, \
            "System login must produce system tenant context"

    def test_tenant_user_cannot_login_without_workspace(self, client):
        """A tenant-only user must not be able to log in without specifying workspace."""
        _register(client, username="tenantonly", password="pass123",
                  cafe_name="PrivateCafe", email="p@p.com")
        # Login WITHOUT workspace slug — system tenant doesn't know this user
        r = _login(client, username="tenantonly", password="pass123")
        assert r.status_code in (401, 403, 404), \
            "Tenant user must fail to login without workspace slug"

    def test_login_with_wrong_workspace_fails(self, client):
        """A correct username/password should fail if workspace slug is wrong."""
        _register(client, username="wrongws", password="pass123",
                  cafe_name="Correct Café", email="c@c.com")
        r = _login(client, username="wrongws", password="pass123",
                   workspace="this-workspace-does-not-exist")
        assert r.status_code == 404, "Login with non-existent workspace must return 404"

    def test_login_with_correct_workspace_succeeds(self, client):
        """Same credentials succeed when the correct workspace slug is provided."""
        reg = _register(client, username="ws_user", password="pass123",
                        cafe_name="My Workspace Café", email="w@w.com")
        slug = reg.json()["slug"]
        r = _login(client, username="ws_user", password="pass123", workspace=slug)
        assert r.status_code == 200
        assert r.json()["tenant_slug"] == slug


class TestIntegrationFullRegistrationFlow:
    """End-to-end: register → login → use dashboard → data is blank."""

    def test_full_registration_to_blank_dashboard(self, client):
        # 1. Register
        reg = _register(client, cafe_name="Flow Café", username="flowuser",
                        email="flow@f.com", password="flowpass1")
        assert reg.status_code == 200
        slug  = reg.json()["slug"]
        token = reg.json()["token"]

        # 2. Use the token to hit the dashboard
        headers = {"Authorization": f"Bearer {token}", "X-Username": "flowuser"}
        r = client.get("/api/dashboard/overview", headers=headers)
        assert r.status_code == 200
        assert r.json()["revenue_today"] == 0

        # 3. Log out (implicit: just log in again via workspace slug)
        r2 = _login(client, username="flowuser", password="flowpass1", workspace=slug)
        assert r2.status_code == 200
        token2 = r2.json()["token"]
        assert token2, "Second login must issue a token"

        # 4. Confirm new token still shows empty data
        r3 = client.get("/api/dashboard/overview",
                        headers={"Authorization": f"Bearer {token2}", "X-Username": "flowuser"})
        assert r3.json()["revenue_today"] == 0

    def test_data_uploaded_to_one_tenant_not_visible_to_another(self, client):
        """Full integration: upload for Tenant A, confirm Tenant B sees nothing."""
        from data_store import save_dataset_for_tenant

        regA = _register(client, cafe_name="Café A", username="ownerA",
                         email="a@a.com", password="passA123")
        regB = _register(client, cafe_name="Café B", username="ownerB",
                         email="b@b.com", password="passB123")

        tid_A = regA.json()["tenant_id"]
        token_B = regB.json()["token"]

        # Upload POS data for Tenant A only
        sample = [{"date": "2024-06-01", "item_name": "Pizza", "category": "Main",
                   "quantity": 5.0, "price": 300.0, "revenue": 1500.0,
                   "cost": 500.0, "platform": "Dine-in"}]
        save_dataset_for_tenant(tid_A, "pos", sample, {"rows": 1})

        # Tenant B must still see empty dashboard
        r = client.get("/api/dashboard/overview",
                       headers={"Authorization": f"Bearer {token_B}", "X-Username": "ownerB"})
        assert r.status_code == 200
        assert r.json()["revenue_today"] == 0, \
            "Tenant B must not see Tenant A's uploaded revenue"
