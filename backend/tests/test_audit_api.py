"""
Integration tests for the audit API endpoints (via direct function calls),
plus regression tests to verify existing endpoints still work after adding
audit logging.

Same pattern as test_role_api.py — calls FastAPI endpoint functions directly
to avoid httpx / starlette TestClient version incompatibilities.
"""
from __future__ import annotations

import os
import sys
import tempfile
import pytest

# ─── Path setup ──────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set temp DATA_DIR before importing main (so audit_store and role_store pick it up)
_TMPDIR = tempfile.mkdtemp(prefix="audit_api_test_")
os.environ["DATA_DIR"] = _TMPDIR

import audit_store as _audit
import role_store as _rs

# Import endpoint functions from main
from main import (
    login, logout,
    get_audit_logs, get_audit_stats, get_audit_modules,
    get_roles, create_role, delete_role,
    get_users, create_user, delete_user,
    upload_status, health,
)
from main import LoginRequest, RoleCreateRequest, UserCreateRequest


# ─── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def reset_state():
    """Each test gets a clean audit log and fresh role store."""
    _audit.reset_for_tests()
    _rs.reload()
    yield
    _audit.reset_for_tests()


class FakeRequest:
    """Minimal request stub that satisfies endpoint signatures."""
    def __init__(self, username: str = "admin", role: str = "Admin"):
        self.headers = {"X-Username": username, "X-Role": role}
        self.client  = type("C", (), {"host": "127.0.0.1"})()
        self.url     = type("U", (), {"path": "/api/test"})()
        self.method  = "GET"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Login audit
# ═══════════════════════════════════════════════════════════════════════════════
class TestLoginAudit:
    def test_successful_login_creates_audit(self):
        req = FakeRequest()
        login(LoginRequest(username="admin", password="cafe123"), request=req)
        entries, total = _audit.get_logs(username="admin", action="LOGIN")
        assert total >= 1
        entry = entries[0]
        assert entry["status"] == "success"
        assert "logged in" in entry["description"].lower()

    def test_failed_login_creates_audit(self):
        from fastapi import HTTPException
        req = FakeRequest()
        try:
            login(LoginRequest(username="admin", password="wrongpass"), request=req)
        except HTTPException:
            pass
        entries, total = _audit.get_logs(username="admin", action="LOGIN", status="error")
        assert total >= 1

    def test_login_audit_has_role(self):
        req = FakeRequest()
        login(LoginRequest(username="admin", password="cafe123"), request=req)
        entries, _ = _audit.get_logs(username="admin", action="LOGIN", status="success")
        assert entries[0]["role"] != ""

    def test_login_audit_module_is_auth(self):
        req = FakeRequest()
        login(LoginRequest(username="owner", password="buddy@2024"), request=req)
        entries, _ = _audit.get_logs(username="owner", action="LOGIN")
        assert entries[0]["module"] == "auth"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Logout audit
# ═══════════════════════════════════════════════════════════════════════════════
class TestLogoutAudit:
    def test_logout_creates_audit(self):
        req = FakeRequest(username="admin")
        logout(request=req)
        entries, total = _audit.get_logs(action="LOGOUT")
        assert total >= 1

    def test_logout_audit_has_correct_username(self):
        req = FakeRequest(username="owner")
        logout(request=req)
        entries, _ = _audit.get_logs(username="owner", action="LOGOUT")
        assert len(entries) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Role CRUD audit
# ═══════════════════════════════════════════════════════════════════════════════
class TestRoleCrudAudit:
    def test_create_role_creates_audit(self):
        req = FakeRequest(username="admin")
        create_role(RoleCreateRequest(id="test_role", name="Test Role",
                                       description="desc", permissions=["dashboard"]),
                    request=req)
        entries, total = _audit.get_logs(action="ROLE_CREATE")
        assert total >= 1
        assert "test_role" in entries[0]["description"].lower() or "Test Role" in entries[0]["description"]

    def test_delete_role_creates_audit(self):
        req = FakeRequest(username="admin")
        create_role(RoleCreateRequest(id="tmp_role", name="Tmp", permissions=[]), request=req)
        _audit.reset_for_tests()  # clear so we only see delete
        delete_role("tmp_role", request=req)
        entries, total = _audit.get_logs(action="ROLE_DELETE")
        assert total >= 1

    def test_create_user_creates_audit(self):
        req = FakeRequest(username="admin")
        create_user(UserCreateRequest(username="newtest", password="pass123",
                                       role_id="viewer", full_name="New Test"),
                    request=req)
        entries, total = _audit.get_logs(action="USER_CREATE")
        assert total >= 1

    def test_delete_user_creates_audit(self):
        from main import delete_user
        req = FakeRequest(username="admin")
        create_user(UserCreateRequest(username="todelete", password="x",
                                       role_id="viewer"), request=req)
        _audit.reset_for_tests()
        delete_user("todelete", request=req)
        entries, total = _audit.get_logs(action="USER_DELETE")
        assert total >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 4. GET /api/audit/logs
# ═══════════════════════════════════════════════════════════════════════════════
class TestGetAuditLogs:
    def setup_method(self):
        for i in range(5):
            _audit.log_action(f"user{i}", "auth", "LOGIN", f"entry {i}")

    def test_returns_logs_and_total(self):
        req = FakeRequest()
        result = get_audit_logs(request=req)
        assert "logs" in result
        assert "total" in result

    def test_default_limit(self):
        req = FakeRequest()
        result = get_audit_logs(request=req)
        assert result["total"] >= 5

    def test_limit_applied(self):
        req = FakeRequest()
        result = get_audit_logs(request=req, limit=2)
        assert len(result["logs"]) == 2

    def test_offset_applied(self):
        # Seed enough entries so offset works reliably regardless of AUDIT_VIEW self-logging
        for i in range(10):
            _audit.log_action(f"seed{i}", "auth", "LOGIN", f"seed entry {i}")
        req = FakeRequest()
        r1 = get_audit_logs(request=req, limit=3, offset=0)
        r2 = get_audit_logs(request=req, limit=3, offset=6)
        assert len(r1["logs"]) == 3
        assert len(r2["logs"]) == 3

    def test_filter_by_action(self):
        _audit.log_action("alice", "upload_data", "FILE_UPLOAD", "upload")
        req = FakeRequest()
        result = get_audit_logs(request=req, action="FILE_UPLOAD")
        assert all(e["action"] == "FILE_UPLOAD" for e in result["logs"])

    def test_filter_by_username(self):
        req = FakeRequest()
        result = get_audit_logs(request=req, username="user0")
        assert all(e["username"] == "user0" for e in result["logs"])

    def test_viewing_audit_creates_its_own_entry(self):
        _audit.reset_for_tests()
        req = FakeRequest(username="admin")
        get_audit_logs(request=req)
        entries, _ = _audit.get_logs(action="AUDIT_VIEW")
        assert len(entries) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 5. GET /api/audit/stats
# ═══════════════════════════════════════════════════════════════════════════════
class TestGetAuditStats:
    def test_returns_dict(self):
        _audit.log_action("alice", "auth", "LOGIN", "x")
        result = get_audit_stats()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = get_audit_stats()
        for key in ("total_today", "total_all", "active_users_today", "error_rate_pct"):
            assert key in result

    def test_totals_accurate(self):
        _audit.clear_logs()  # removes disk file too so reload is clean
        for _ in range(3):
            _audit.log_action("u", "auth", "LOGIN", "x")
        result = get_audit_stats()
        assert result["total_all"] == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 6. GET /api/audit/modules
# ═══════════════════════════════════════════════════════════════════════════════
class TestGetAuditModules:
    def test_returns_modules_and_labels(self):
        result = get_audit_modules()
        assert "modules"  in result
        assert "labels"   in result
        assert "action_types" in result

    def test_modules_is_list(self):
        result = get_audit_modules()
        assert isinstance(result["modules"], list)
        assert len(result["modules"]) >= 5

    def test_action_types_is_list(self):
        result = get_audit_modules()
        assert isinstance(result["action_types"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Regression — existing endpoints still work
# ═══════════════════════════════════════════════════════════════════════════════
class TestRegressionExistingEndpoints:
    def test_health_still_works(self):
        result = health()
        assert result["status"] == "ok"

    def test_get_roles_still_works(self):
        result = get_roles()
        assert "roles" in result
        assert len(result["roles"]) >= 3

    def test_get_users_still_works(self):
        result = get_users()
        assert "users" in result
        assert len(result["users"]) >= 2

    def test_upload_status_still_works(self):
        result = upload_status()
        assert "uploaded" in result

    def test_login_still_works(self):
        req = FakeRequest()
        result = login(LoginRequest(username="admin", password="cafe123"), request=req)
        assert result["success"] is True
        assert result["username"] == "admin"

    def test_login_invalid_creds_still_raises_401(self):
        from fastapi import HTTPException
        req = FakeRequest()
        with pytest.raises(HTTPException) as exc:
            login(LoginRequest(username="admin", password="wrong"), request=req)
        assert exc.value.status_code == 401

    def test_default_roles_still_present(self):
        result = get_roles()
        role_ids = [r["id"] for r in result["roles"]]
        assert "admin"     in role_ids
        assert "sub_admin" in role_ids
        assert "viewer"    in role_ids

    def test_audit_permission_in_all_permissions(self):
        result = get_roles()
        assert "audit_logs" in result["all_permissions"]

    def test_admin_role_has_audit_permission(self):
        result = get_roles()
        admin = next(r for r in result["roles"] if r["id"] == "admin")
        assert "audit_logs" in admin["permissions"]

    def test_create_and_retrieve_role(self):
        req = FakeRequest()
        create_role(RoleCreateRequest(
            id="audit_tester", name="Audit Tester",
            permissions=["dashboard", "audit_logs"]
        ), request=req)
        result = get_roles()
        ids = [r["id"] for r in result["roles"]]
        assert "audit_tester" in ids

    def test_logout_still_works(self):
        req = FakeRequest()
        result = logout(request=req)
        assert result["success"] is True
