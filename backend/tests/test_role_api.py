"""
Integration tests for role/user management — FastAPI endpoints called directly.
Regression tests verify existing endpoints still function after RBAC was added.
(Uses direct function calls instead of TestClient due to httpx/starlette version mismatch.)
"""
import os
import sys
import tempfile
import pytest
from fastapi import HTTPException
from pydantic import BaseModel

# ── Temp data dir ─────────────────────────────────────────────────────────────
_TMPDIR = tempfile.mkdtemp()
os.environ["DATA_DIR"] = _TMPDIR

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import role_store as rs

# Import endpoint functions from main after env is set
from main import (
    login       as ep_login,
    get_roles   as ep_get_roles,
    create_role as ep_create_role,
    update_role as ep_update_role,
    delete_role as ep_delete_role,
    get_users   as ep_get_users,
    create_user as ep_create_user,
    update_user as ep_update_user,
    delete_user as ep_delete_user,
    # Existing endpoints
    health              as ep_health,
    dashboard_overview  as ep_dashboard_overview,
    layer1_summary      as ep_layer1_summary,
    forecast            as ep_forecast,
    get_decisions       as ep_get_decisions,
    kpis                as ep_kpis,
    get_peer_cities     as ep_get_peer_cities,
    logout              as ep_logout,
    upload_status       as ep_upload_status,
    layer5_model_status as ep_layer5_model_status,
)
from main import (
    LoginRequest, RoleCreateRequest, RoleUpdateRequest,
    UserCreateRequest, UserUpdateRequest,
)


@pytest.fixture(autouse=True)
def reset():
    store_file = os.path.join(_TMPDIR, "roles.json")
    if os.path.exists(store_file):
        os.remove(store_file)
    rs.reload()
    yield
    if os.path.exists(store_file):
        os.remove(store_file)


# ═══════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

class TestLoginEndpoint:
    def test_admin_login_succeeds(self):
        result = ep_login(LoginRequest(username="admin", password="cafe123"))
        assert result["success"] is True

    def test_login_response_contains_permissions(self):
        result = ep_login(LoginRequest(username="admin", password="cafe123"))
        assert "permissions" in result
        assert isinstance(result["permissions"], list)
        assert "role_management" in result["permissions"]

    def test_login_response_contains_role_id(self):
        result = ep_login(LoginRequest(username="admin", password="cafe123"))
        assert result["role_id"] == "admin"

    def test_login_response_contains_token(self):
        result = ep_login(LoginRequest(username="admin", password="cafe123"))
        assert "token" in result

    def test_wrong_password_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            ep_login(LoginRequest(username="admin", password="wrong"))
        assert exc.value.status_code == 401

    def test_unknown_user_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            ep_login(LoginRequest(username="nobody_xyz", password="x"))
        assert exc.value.status_code == 401

    def test_viewer_login_has_limited_permissions(self):
        rs.create_user("view_api", "pass123", "viewer")
        result = ep_login(LoginRequest(username="view_api", password="pass123"))
        perms = result["permissions"]
        assert "role_management" not in perms
        assert "upload_data" not in perms
        assert "dashboard" in perms

    def test_sub_admin_login_permissions(self):
        rs.create_user("sub_api", "pass123", "sub_admin")
        result = ep_login(LoginRequest(username="sub_api", password="pass123"))
        perms = result["permissions"]
        assert "upload_data" in perms
        assert "role_management" not in perms

    def test_owner_login_succeeds(self):
        result = ep_login(LoginRequest(username="owner", password="buddy@2024"))
        assert result["success"] is True
        assert "role_management" in result["permissions"]

    def test_inactive_user_raises_401(self):
        rs.create_user("inactive_api", "pass", "viewer")
        rs.update_user("inactive_api", is_active=False)
        with pytest.raises(HTTPException) as exc:
            ep_login(LoginRequest(username="inactive_api", password="pass"))
        assert exc.value.status_code == 401

    def test_login_returns_full_name(self):
        rs.create_user("full_api", "pass", "viewer", full_name="Full API User")
        result = ep_login(LoginRequest(username="full_api", password="pass"))
        assert result["full_name"] == "Full API User"


# ═══════════════════════════════════════════════════════════════════════════
# ROLES ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class TestGetRoles:
    def test_get_roles_returns_dict(self):
        result = ep_get_roles()
        assert "roles" in result

    def test_get_roles_contains_three_system_roles(self):
        result = ep_get_roles()
        ids = {r["id"] for r in result["roles"]}
        assert {"admin", "sub_admin", "viewer"}.issubset(ids)

    def test_get_roles_contains_all_permissions(self):
        result = ep_get_roles()
        assert "all_permissions" in result
        assert len(result["all_permissions"]) >= 10

    def test_get_roles_contains_permission_labels(self):
        result = ep_get_roles()
        assert "permission_labels" in result
        assert isinstance(result["permission_labels"], dict)


class TestCreateRoleEndpoint:
    def test_create_role_succeeds(self):
        result = ep_create_role(RoleCreateRequest(
            id="api_test", name="API Test", description="test",
            permissions=["dashboard", "chatbot"],
        ))
        assert result["success"] is True
        assert result["role"]["id"] == "api_test"

    def test_created_role_appears_in_list(self):
        ep_create_role(RoleCreateRequest(id="new_r", name="New", permissions=["dashboard"]))
        ids = {r["id"] for r in ep_get_roles()["roles"]}
        assert "new_r" in ids

    def test_create_duplicate_role_raises_400(self):
        ep_create_role(RoleCreateRequest(id="dup_r", name="Dup", permissions=["dashboard"]))
        with pytest.raises(HTTPException) as exc:
            ep_create_role(RoleCreateRequest(id="dup_r", name="Dup2", permissions=["reports"]))
        assert exc.value.status_code == 400

    def test_create_role_bad_permission_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            ep_create_role(RoleCreateRequest(id="bad_r", name="Bad", permissions=["nonexistent_perm"]))
        assert exc.value.status_code == 400


class TestUpdateRoleEndpoint:
    def test_update_role_name(self):
        ep_create_role(RoleCreateRequest(id="upd_r", name="Old", permissions=["dashboard"]))
        result = ep_update_role("upd_r", RoleUpdateRequest(name="New Name"))
        assert result["role"]["name"] == "New Name"

    def test_update_role_permissions(self):
        ep_create_role(RoleCreateRequest(id="perm_r", name="P", permissions=["dashboard"]))
        result = ep_update_role("perm_r", RoleUpdateRequest(permissions=["dashboard", "reports"]))
        assert "reports" in result["role"]["permissions"]

    def test_update_nonexistent_role_raises_404(self):
        with pytest.raises(HTTPException) as exc:
            ep_update_role("nonexistent_xyz", RoleUpdateRequest(name="X"))
        assert exc.value.status_code == 404

    def test_update_invalid_permission_raises_400(self):
        ep_create_role(RoleCreateRequest(id="inv_r", name="I", permissions=["dashboard"]))
        with pytest.raises(HTTPException) as exc:
            ep_update_role("inv_r", RoleUpdateRequest(permissions=["bad_perm"]))
        assert exc.value.status_code == 400


class TestDeleteRoleEndpoint:
    def test_delete_custom_role_succeeds(self):
        ep_create_role(RoleCreateRequest(id="del_r", name="Del", permissions=["dashboard"]))
        result = ep_delete_role("del_r")
        assert result["success"] is True

    def test_delete_custom_role_not_in_list_after_delete(self):
        ep_create_role(RoleCreateRequest(id="del_list_r", name="DL", permissions=["dashboard"]))
        ep_delete_role("del_list_r")
        ids = {r["id"] for r in ep_get_roles()["roles"]}
        assert "del_list_r" not in ids

    def test_delete_system_role_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            ep_delete_role("admin")
        assert exc.value.status_code == 400

    def test_delete_nonexistent_role_raises_404(self):
        with pytest.raises(HTTPException) as exc:
            ep_delete_role("nonexistent_xyz")
        assert exc.value.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# USERS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class TestGetUsersEndpoint:
    def test_get_users_returns_dict(self):
        result = ep_get_users()
        assert "users" in result

    def test_get_users_includes_admin(self):
        result = ep_get_users()
        names = {u["username"] for u in result["users"]}
        assert "admin" in names

    def test_get_users_no_passwords(self):
        result = ep_get_users()
        for u in result["users"]:
            assert "password" not in u


class TestCreateUserEndpoint:
    def test_create_user_succeeds(self):
        result = ep_create_user(UserCreateRequest(
            username="api_newuser", password="pass123",
            role_id="viewer", full_name="API User", email="api@test.com",
        ))
        assert result["success"] is True
        assert result["user"]["username"] == "api_newuser"

    def test_created_user_appears_in_list(self):
        ep_create_user(UserCreateRequest(username="list_u", password="p", role_id="viewer"))
        names = {u["username"] for u in ep_get_users()["users"]}
        assert "list_u" in names

    def test_created_user_can_login(self):
        ep_create_user(UserCreateRequest(username="loginable", password="mypass", role_id="viewer"))
        result = ep_login(LoginRequest(username="loginable", password="mypass"))
        assert result["success"] is True

    def test_create_duplicate_user_raises_400(self):
        ep_create_user(UserCreateRequest(username="dup_u", password="p", role_id="viewer"))
        with pytest.raises(HTTPException) as exc:
            ep_create_user(UserCreateRequest(username="dup_u", password="p2", role_id="viewer"))
        assert exc.value.status_code == 400

    def test_create_user_invalid_role_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            ep_create_user(UserCreateRequest(username="bad_role_u", password="p", role_id="nonexistent_xyz"))
        assert exc.value.status_code == 400

    def test_create_user_empty_username_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            ep_create_user(UserCreateRequest(username="", password="p", role_id="viewer"))
        assert exc.value.status_code == 400


class TestUpdateUserEndpoint:
    def test_update_user_role(self):
        ep_create_user(UserCreateRequest(username="role_u", password="p", role_id="viewer"))
        result = ep_update_user("role_u", UserUpdateRequest(role_id="sub_admin"))
        assert result["user"]["role_id"] == "sub_admin"

    def test_update_user_full_name(self):
        ep_create_user(UserCreateRequest(username="name_u", password="p", role_id="viewer"))
        result = ep_update_user("name_u", UserUpdateRequest(full_name="Updated Name"))
        assert result["user"]["full_name"] == "Updated Name"

    def test_deactivate_user(self):
        ep_create_user(UserCreateRequest(username="deact_u", password="p", role_id="viewer"))
        result = ep_update_user("deact_u", UserUpdateRequest(is_active=False))
        assert result["user"]["is_active"] is False

    def test_update_nonexistent_user_raises_404(self):
        with pytest.raises(HTTPException) as exc:
            ep_update_user("nobody_xyz", UserUpdateRequest(full_name="X"))
        assert exc.value.status_code == 404

    def test_update_invalid_role_raises_400(self):
        ep_create_user(UserCreateRequest(username="bad_r_u", password="p", role_id="viewer"))
        with pytest.raises(HTTPException) as exc:
            ep_update_user("bad_r_u", UserUpdateRequest(role_id="nonexistent_xyz"))
        assert exc.value.status_code == 400


class TestDeleteUserEndpoint:
    def test_delete_custom_user_succeeds(self):
        ep_create_user(UserCreateRequest(username="del_u", password="p", role_id="viewer"))
        result = ep_delete_user("del_u")
        assert result["success"] is True

    def test_deleted_user_cannot_login(self):
        ep_create_user(UserCreateRequest(username="del_login_u", password="p", role_id="viewer"))
        ep_delete_user("del_login_u")
        with pytest.raises(HTTPException) as exc:
            ep_login(LoginRequest(username="del_login_u", password="p"))
        assert exc.value.status_code == 401

    def test_delete_system_user_raises_400(self):
        with pytest.raises(HTTPException) as exc:
            ep_delete_user("admin")
        assert exc.value.status_code == 400

    def test_delete_nonexistent_user_raises_404(self):
        with pytest.raises(HTTPException) as exc:
            ep_delete_user("nobody_xyz")
        assert exc.value.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# REGRESSION TESTS — existing endpoints must still function
# ═══════════════════════════════════════════════════════════════════════════

class TestRegressionExistingEndpoints:
    def test_health_endpoint_still_works(self):
        result = ep_health()
        assert result["status"] == "ok"

    def test_dashboard_overview_still_works(self):
        result = ep_dashboard_overview()
        assert "revenue_today" in result

    def test_layer1_summary_still_works(self):
        result = ep_layer1_summary()
        assert "total_records" in result

    def test_layer3_forecast_still_works(self):
        result = ep_forecast()
        assert "forecast" in result

    def test_layer4_decisions_still_works(self):
        result = ep_get_decisions()
        assert "decisions" in result

    def test_layer5_kpis_still_works(self):
        result = ep_kpis()
        assert "kpis" in result

    def test_peer_cities_still_works(self):
        result = ep_get_peer_cities()
        assert "cities" in result

    def test_logout_still_works(self):
        result = ep_logout()
        assert result["success"] is True

    def test_upload_status_still_works(self):
        result = ep_upload_status()
        assert "uploaded" in result

    def test_layer5_model_status_still_works(self):
        result = ep_layer5_model_status()
        assert "models" in result

    def test_full_workflow_create_role_user_login_verify(self):
        """Create custom role → create user → login → verify permissions match role."""
        ep_create_role(RoleCreateRequest(
            id="workflow_r", name="Workflow Role",
            permissions=["dashboard", "reports"],
        ))
        ep_create_user(UserCreateRequest(
            username="workflow_u", password="wf_pass",
            role_id="workflow_r", full_name="Workflow User",
        ))
        result = ep_login(LoginRequest(username="workflow_u", password="wf_pass"))
        assert result["success"] is True
        assert "reports" in result["permissions"]
        assert "auto_pilot" not in result["permissions"]
        assert "role_management" not in result["permissions"]

    def test_delete_role_then_user_downgraded_to_viewer(self):
        """After custom role is deleted, affected user is downgraded to viewer."""
        ep_create_role(RoleCreateRequest(id="tmp_r", name="Tmp", permissions=["dashboard", "analytics"]))
        ep_create_user(UserCreateRequest(username="tmp_u", password="pass", role_id="tmp_r"))
        ep_delete_role("tmp_r")
        result = ep_login(LoginRequest(username="tmp_u", password="pass"))
        assert result["role_id"] == "viewer"
        assert "analytics" not in result["permissions"]

    def test_permission_change_in_role_reflected_on_next_login(self):
        ep_create_role(RoleCreateRequest(id="flex_r", name="Flex", permissions=["dashboard"]))
        ep_create_user(UserCreateRequest(username="flex_u", password="pass", role_id="flex_r"))
        r1 = ep_login(LoginRequest(username="flex_u", password="pass"))
        assert "reports" not in r1["permissions"]
        # Admin upgrades the role
        ep_update_role("flex_r", RoleUpdateRequest(permissions=["dashboard", "reports"]))
        r2 = ep_login(LoginRequest(username="flex_u", password="pass"))
        assert "reports" in r2["permissions"]
