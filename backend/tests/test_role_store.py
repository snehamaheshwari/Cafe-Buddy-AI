"""
Unit tests for role_store.py
Tests: role CRUD, user CRUD, authentication, permissions, system-role protection.
Uses a temp directory so tests never touch the real data/roles.json.
"""
import json
import os
import sys
import tempfile
import pytest

# ─── Patch DATA_DIR before importing role_store ───────────────────────────────
_TMPDIR = tempfile.mkdtemp()
os.environ["DATA_DIR"] = _TMPDIR

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import role_store as rs

# ─── Auto-reset store between tests ──────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_store():
    """Remove roles.json and reload defaults before each test.
    Sets DATA_DIR each time so reload() picks up the correct tmpdir
    even when test_role_api.py has previously set a different DATA_DIR.
    """
    os.environ["DATA_DIR"] = _TMPDIR
    store_file = os.path.join(_TMPDIR, "roles.json")
    if os.path.exists(store_file):
        os.remove(store_file)
    rs.reload()   # reload() now re-reads DATA_DIR from env
    yield
    # Cleanup after test
    if os.path.exists(store_file):
        os.remove(store_file)


# ═════════════════════════════════════════════════════════════════════════════
# PERMISSIONS CONSTANTS
# ═════════════════════════════════════════════════════════════════════════════

class TestPermissionConstants:
    def test_all_permissions_is_non_empty_list(self):
        assert isinstance(rs.ALL_PERMISSIONS, list)
        assert len(rs.ALL_PERMISSIONS) >= 10

    def test_all_permissions_contains_required_keys(self):
        required = {
            "dashboard", "upload_data", "reports", "analytics",
            "decision_engine", "auto_pilot", "chatbot",
            "market_radar", "whatsapp_alerts", "role_management",
        }
        assert required.issubset(set(rs.ALL_PERMISSIONS))

    def test_permission_labels_covers_all_permissions(self):
        for perm in rs.ALL_PERMISSIONS:
            assert perm in rs.PERMISSION_LABELS, f"Missing label for '{perm}'"

    def test_permission_labels_are_strings(self):
        for key, label in rs.PERMISSION_LABELS.items():
            assert isinstance(label, str) and label.strip(), f"Empty label for '{key}'"


# ═════════════════════════════════════════════════════════════════════════════
# DEFAULT ROLES
# ═════════════════════════════════════════════════════════════════════════════

class TestDefaultRoles:
    def test_three_system_roles_present(self):
        roles = rs.list_roles()
        ids   = {r["id"] for r in roles}
        assert {"admin", "sub_admin", "viewer"}.issubset(ids)

    def test_admin_has_all_permissions(self):
        admin = rs.get_role("admin")
        assert admin is not None
        assert set(rs.ALL_PERMISSIONS).issubset(set(admin["permissions"]))

    def test_admin_has_role_management_permission(self):
        admin = rs.get_role("admin")
        assert "role_management" in admin["permissions"]

    def test_sub_admin_does_not_have_role_management(self):
        sub = rs.get_role("sub_admin")
        assert sub is not None
        assert "role_management" not in sub["permissions"]

    def test_sub_admin_has_operational_permissions(self):
        sub = rs.get_role("sub_admin")
        for perm in ["dashboard", "upload_data", "reports", "analytics", "decision_engine", "chatbot"]:
            assert perm in sub["permissions"], f"sub_admin missing '{perm}'"

    def test_viewer_has_limited_permissions(self):
        viewer = rs.get_role("viewer")
        assert viewer is not None
        for perm in ["dashboard", "reports", "market_radar"]:
            assert perm in viewer["permissions"]
        # Viewer must NOT have admin capabilities
        for perm in ["role_management", "upload_data", "auto_pilot"]:
            assert perm not in viewer["permissions"]

    def test_all_system_roles_are_marked_system(self):
        for rid in ["admin", "sub_admin", "viewer"]:
            role = rs.get_role(rid)
            assert role["is_system"] is True

    def test_get_role_returns_none_for_unknown(self):
        assert rs.get_role("nonexistent_xyz") is None


# ═════════════════════════════════════════════════════════════════════════════
# ROLE CREATE
# ═════════════════════════════════════════════════════════════════════════════

class TestRoleCreate:
    def test_create_custom_role_succeeds(self):
        role = rs.create_role("kitchen", "Kitchen Staff", "Ops only", ["dashboard", "chatbot"])
        assert role["id"] == "kitchen"
        assert role["name"] == "Kitchen Staff"
        assert "dashboard" in role["permissions"]
        assert role["is_system"] is False

    def test_created_role_is_persisted(self):
        rs.create_role("cashier", "Cashier", "", ["dashboard"])
        rs.reload()
        assert rs.get_role("cashier") is not None

    def test_create_role_with_empty_id_raises(self):
        with pytest.raises(ValueError, match="empty"):
            rs.create_role("", "Empty ID", "", ["dashboard"])

    def test_create_duplicate_role_raises(self):
        rs.create_role("dup", "Dup", "", ["dashboard"])
        with pytest.raises(ValueError, match="already exists"):
            rs.create_role("dup", "Dup2", "", ["reports"])

    def test_create_role_with_invalid_permissions_raises(self):
        with pytest.raises(ValueError, match="Unknown permissions"):
            rs.create_role("bad", "Bad", "", ["nonexistent_perm"])

    def test_create_role_normalises_id_to_lowercase(self):
        role = rs.create_role("MyRole", "My Role", "", ["dashboard"])
        assert role["id"] == "myrole"

    def test_create_role_replaces_spaces_in_id(self):
        role = rs.create_role("my role", "My Role", "", ["dashboard"])
        assert " " not in role["id"]

    def test_list_roles_includes_new_custom_role(self):
        rs.create_role("tester", "Tester", "", ["analytics"])
        ids = {r["id"] for r in rs.list_roles()}
        assert "tester" in ids


# ═════════════════════════════════════════════════════════════════════════════
# ROLE UPDATE
# ═════════════════════════════════════════════════════════════════════════════

class TestRoleUpdate:
    def test_update_role_name(self):
        rs.create_role("upd", "Old Name", "", ["dashboard"])
        role = rs.update_role("upd", name="New Name")
        assert role["name"] == "New Name"

    def test_update_role_permissions(self):
        rs.create_role("upd2", "R2", "", ["dashboard"])
        role = rs.update_role("upd2", permissions=["dashboard", "reports"])
        assert "reports" in role["permissions"]

    def test_update_persists_to_disk(self):
        rs.create_role("persist_upd", "P", "", ["dashboard"])
        rs.update_role("persist_upd", name="Updated Name")
        rs.reload()
        assert rs.get_role("persist_upd")["name"] == "Updated Name"

    def test_update_nonexistent_role_raises(self):
        with pytest.raises(KeyError):
            rs.update_role("ghost_role_xyz", name="X")

    def test_update_role_invalid_permission_raises(self):
        rs.create_role("upd3", "R3", "", ["dashboard"])
        with pytest.raises(ValueError, match="Unknown permissions"):
            rs.update_role("upd3", permissions=["bad_perm"])

    def test_admin_role_always_keeps_role_management(self):
        """Removing role_management from admin should auto-add it back."""
        rs.update_role("admin", permissions=["dashboard"])
        admin = rs.get_role("admin")
        assert "role_management" in admin["permissions"]

    def test_update_system_role_description(self):
        role = rs.update_role("viewer", description="Updated desc")
        assert role["description"] == "Updated desc"


# ═════════════════════════════════════════════════════════════════════════════
# ROLE DELETE
# ═════════════════════════════════════════════════════════════════════════════

class TestRoleDelete:
    def test_delete_custom_role_succeeds(self):
        rs.create_role("del_me", "Del", "", ["dashboard"])
        rs.delete_role("del_me")
        assert rs.get_role("del_me") is None

    def test_delete_custom_role_is_persisted(self):
        rs.create_role("del_persist", "D", "", ["dashboard"])
        rs.delete_role("del_persist")
        rs.reload()
        assert rs.get_role("del_persist") is None

    def test_delete_system_role_raises(self):
        with pytest.raises(ValueError, match="system role"):
            rs.delete_role("admin")

    def test_delete_system_viewer_raises(self):
        with pytest.raises(ValueError, match="system role"):
            rs.delete_role("viewer")

    def test_delete_nonexistent_role_raises(self):
        with pytest.raises(KeyError):
            rs.delete_role("ghost_xyz")

    def test_delete_role_downgrades_affected_users(self):
        rs.create_role("temp_role", "Temp", "", ["dashboard"])
        rs.create_user("temp_user", "pass123", "temp_role")
        rs.delete_role("temp_role")
        user = rs.get_user("temp_user")
        assert user["role_id"] == "viewer"


# ═════════════════════════════════════════════════════════════════════════════
# DEFAULT USERS
# ═════════════════════════════════════════════════════════════════════════════

class TestDefaultUsers:
    def test_admin_and_owner_users_present(self):
        names = {u["username"] for u in rs.list_users()}
        assert "admin" in names
        assert "owner" in names

    def test_system_users_marked_system(self):
        for uname in ["admin", "owner"]:
            u = rs.get_user(uname)
            assert u is not None
            assert u["is_system"] is True

    def test_user_safe_hides_password(self):
        u = rs.get_user("admin")
        assert "password" not in u

    def test_admin_user_has_admin_role(self):
        u = rs.get_user("admin")
        assert u["role_id"] == "admin"


# ═════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ═════════════════════════════════════════════════════════════════════════════

class TestAuthenticate:
    def test_valid_admin_login(self):
        result = rs.authenticate("admin", "cafe123")
        assert result is not None
        assert result["username"] == "admin"
        assert result["role_id"] == "admin"
        assert "role_management" in result["permissions"]

    def test_valid_owner_login(self):
        result = rs.authenticate("owner", "buddy@2024")
        assert result is not None
        assert result["role_id"] == "admin"

    def test_wrong_password_returns_none(self):
        assert rs.authenticate("admin", "wrongpass") is None

    def test_nonexistent_user_returns_none(self):
        assert rs.authenticate("nobody_xyz", "pass") is None

    def test_returns_permissions_list(self):
        result = rs.authenticate("admin", "cafe123")
        assert isinstance(result["permissions"], list)
        assert len(result["permissions"]) > 0

    def test_viewer_login_has_limited_permissions(self):
        rs.create_user("viewtest", "pass123", "viewer")
        result = rs.authenticate("viewtest", "pass123")
        assert result is not None
        assert "role_management" not in result["permissions"]
        assert "upload_data" not in result["permissions"]
        assert "dashboard" in result["permissions"]

    def test_sub_admin_login_has_correct_permissions(self):
        rs.create_user("subtest", "pass123", "sub_admin")
        result = rs.authenticate("subtest", "pass123")
        assert "upload_data" in result["permissions"]
        assert "role_management" not in result["permissions"]

    def test_inactive_user_cannot_login(self):
        rs.create_user("inactive_u", "pass123", "viewer")
        rs.update_user("inactive_u", is_active=False)
        assert rs.authenticate("inactive_u", "pass123") is None

    def test_returns_full_name_in_result(self):
        rs.create_user("fulltest", "pass123", "viewer", full_name="Full Person")
        result = rs.authenticate("fulltest", "pass123")
        assert result["full_name"] == "Full Person"

    def test_returns_role_name_display(self):
        result = rs.authenticate("admin", "cafe123")
        assert result["role_name"] == "Admin"


# ═════════════════════════════════════════════════════════════════════════════
# USER CREATE
# ═════════════════════════════════════════════════════════════════════════════

class TestUserCreate:
    def test_create_user_succeeds(self):
        u = rs.create_user("newuser", "pass123", "viewer")
        assert u["username"] == "newuser"
        assert u["role_id"] == "viewer"
        assert u["is_active"] is True
        assert u["is_system"] is False

    def test_create_user_password_not_in_return(self):
        u = rs.create_user("secuser", "secret", "viewer")
        assert "password" not in u

    def test_create_user_persists(self):
        rs.create_user("persist_u", "pass", "viewer")
        rs.reload()
        assert rs.get_user("persist_u") is not None

    def test_create_user_empty_username_raises(self):
        with pytest.raises(ValueError, match="empty"):
            rs.create_user("", "pass", "viewer")

    def test_create_user_empty_password_raises(self):
        with pytest.raises(ValueError, match="empty"):
            rs.create_user("ok_user", "", "viewer")

    def test_create_user_duplicate_raises(self):
        rs.create_user("dupuser", "pass", "viewer")
        with pytest.raises(ValueError, match="already exists"):
            rs.create_user("dupuser", "pass2", "viewer")

    def test_create_user_invalid_role_raises(self):
        with pytest.raises(ValueError, match="not found"):
            rs.create_user("baduser", "pass", "nonexistent_role")

    def test_create_user_stores_full_name(self):
        rs.create_user("named", "pass", "viewer", full_name="Jane Doe")
        u = rs.get_user("named")
        assert u["full_name"] == "Jane Doe"

    def test_create_user_stores_email(self):
        rs.create_user("emailed", "pass", "viewer", email="test@cafe.com")
        u = rs.get_user("emailed")
        assert u["email"] == "test@cafe.com"

    def test_create_user_sets_created_at(self):
        rs.create_user("timestamped", "pass", "viewer")
        u = rs.get_user("timestamped")
        assert "created_at" in u and u["created_at"]


# ═════════════════════════════════════════════════════════════════════════════
# USER UPDATE
# ═════════════════════════════════════════════════════════════════════════════

class TestUserUpdate:
    def test_update_user_role(self):
        rs.create_user("roleusr", "pass", "viewer")
        rs.update_user("roleusr", role_id="sub_admin")
        assert rs.get_user("roleusr")["role_id"] == "sub_admin"

    def test_update_user_full_name(self):
        rs.create_user("nameusr", "pass", "viewer")
        rs.update_user("nameusr", full_name="Updated Name")
        assert rs.get_user("nameusr")["full_name"] == "Updated Name"

    def test_update_user_email(self):
        rs.create_user("mailusr", "pass", "viewer")
        rs.update_user("mailusr", email="new@cafe.com")
        assert rs.get_user("mailusr")["email"] == "new@cafe.com"

    def test_deactivate_user(self):
        rs.create_user("activeusr", "pass", "viewer")
        rs.update_user("activeusr", is_active=False)
        assert rs.get_user("activeusr")["is_active"] is False

    def test_reactivate_user(self):
        rs.create_user("inactiveusr", "pass", "viewer")
        rs.update_user("inactiveusr", is_active=False)
        rs.update_user("inactiveusr", is_active=True)
        assert rs.get_user("inactiveusr")["is_active"] is True

    def test_update_password_allows_new_login(self):
        rs.create_user("pwdusr", "oldpass", "viewer")
        rs.update_user("pwdusr", password="newpass")
        assert rs.authenticate("pwdusr", "newpass") is not None
        assert rs.authenticate("pwdusr", "oldpass") is None

    def test_update_empty_password_raises(self):
        rs.create_user("epwdusr", "pass", "viewer")
        with pytest.raises(ValueError, match="empty"):
            rs.update_user("epwdusr", password="")

    def test_update_nonexistent_user_raises(self):
        with pytest.raises(KeyError):
            rs.update_user("nobody_xyz", full_name="X")

    def test_update_invalid_role_raises(self):
        rs.create_user("badrole_u", "pass", "viewer")
        with pytest.raises(ValueError, match="not found"):
            rs.update_user("badrole_u", role_id="bad_role_xyz")

    def test_update_persists(self):
        rs.create_user("persist_upd_u", "pass", "viewer")
        rs.update_user("persist_upd_u", full_name="Saved")
        rs.reload()
        assert rs.get_user("persist_upd_u")["full_name"] == "Saved"


# ═════════════════════════════════════════════════════════════════════════════
# USER DELETE
# ═════════════════════════════════════════════════════════════════════════════

class TestUserDelete:
    def test_delete_custom_user_succeeds(self):
        rs.create_user("del_u", "pass", "viewer")
        rs.delete_user("del_u")
        assert rs.get_user("del_u") is None

    def test_delete_system_user_raises(self):
        with pytest.raises(ValueError, match="system user"):
            rs.delete_user("admin")

    def test_delete_nonexistent_user_raises(self):
        with pytest.raises(KeyError):
            rs.delete_user("nobody_xyz")

    def test_delete_persists(self):
        rs.create_user("del_persist_u", "pass", "viewer")
        rs.delete_user("del_persist_u")
        rs.reload()
        assert rs.get_user("del_persist_u") is None


# ═════════════════════════════════════════════════════════════════════════════
# GET PERMISSIONS
# ═════════════════════════════════════════════════════════════════════════════

class TestGetPermissions:
    def test_admin_permissions_include_role_management(self):
        perms = rs.get_permissions("admin")
        assert "role_management" in perms

    def test_viewer_permissions_do_not_include_upload(self):
        rs.create_user("viewperm", "pass", "viewer")
        perms = rs.get_permissions("viewperm")
        assert "upload_data" not in perms

    def test_nonexistent_user_returns_empty(self):
        assert rs.get_permissions("nobody_xyz") == []

    def test_sub_admin_permissions_include_analytics(self):
        rs.create_user("subperm", "pass", "sub_admin")
        perms = rs.get_permissions("subperm")
        assert "analytics" in perms

    def test_custom_role_permissions_are_correct(self):
        rs.create_role("custom_r", "Custom", "", ["dashboard", "chatbot"])
        rs.create_user("custom_u", "pass", "custom_r")
        perms = rs.get_permissions("custom_u")
        assert "dashboard" in perms
        assert "chatbot" in perms
        assert "reports" not in perms


# ═════════════════════════════════════════════════════════════════════════════
# PERSISTENCE / RELOAD
# ═════════════════════════════════════════════════════════════════════════════

class TestPersistence:
    def test_roles_json_created_on_first_save(self):
        store_file = os.path.join(_TMPDIR, "roles.json")
        rs.create_role("persist_r", "P", "", ["dashboard"])
        assert os.path.exists(store_file)

    def test_custom_role_survives_reload(self):
        rs.create_role("survivor", "Survivor", "desc", ["dashboard", "reports"])
        rs.reload()
        role = rs.get_role("survivor")
        assert role is not None
        assert role["name"] == "Survivor"
        assert "reports" in role["permissions"]

    def test_custom_user_survives_reload(self):
        rs.create_user("surv_user", "pass123", "viewer", full_name="Survive Test")
        rs.reload()
        u = rs.get_user("surv_user")
        assert u is not None
        assert u["full_name"] == "Survive Test"

    def test_roles_json_is_valid_json(self):
        rs.create_role("json_r", "J", "", ["dashboard"])
        store_file = os.path.join(_TMPDIR, "roles.json")
        with open(store_file, "r") as f:
            obj = json.load(f)
        assert "roles" in obj
        assert "users" in obj

    def test_default_roles_always_restored_after_corrupt_file(self):
        """Even with a corrupt JSON file, defaults should load."""
        store_file = os.path.join(_TMPDIR, "roles.json")
        with open(store_file, "w") as f:
            f.write("INVALID JSON {{{{")
        rs.reload()
        # Defaults must still be present
        assert rs.get_role("admin") is not None
        assert rs.get_role("viewer") is not None


# ═════════════════════════════════════════════════════════════════════════════
# EDGE CASES / INTEGRATION
# ═════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_list_roles_returns_list(self):
        assert isinstance(rs.list_roles(), list)

    def test_list_users_returns_list(self):
        assert isinstance(rs.list_users(), list)

    def test_list_users_does_not_include_passwords(self):
        for u in rs.list_users():
            assert "password" not in u

    def test_multiple_users_same_role(self):
        rs.create_user("u1", "pass", "viewer")
        rs.create_user("u2", "pass", "viewer")
        rs.create_user("u3", "pass", "viewer")
        viewers = [u for u in rs.list_users() if u["role_id"] == "viewer"]
        assert len(viewers) >= 3

    def test_create_then_login_then_delete_workflow(self):
        rs.create_user("workflow_u", "wf_pass", "sub_admin", full_name="Workflow Test")
        result = rs.authenticate("workflow_u", "wf_pass")
        assert result is not None
        assert "upload_data" in result["permissions"]
        rs.delete_user("workflow_u")
        assert rs.authenticate("workflow_u", "wf_pass") is None

    def test_role_permission_change_affects_subsequent_logins(self):
        rs.create_role("flex_role", "Flex", "", ["dashboard"])
        rs.create_user("flex_u", "pass", "flex_role")
        result = rs.authenticate("flex_u", "pass")
        assert "reports" not in result["permissions"]
        # Admin adds reports permission to the role
        rs.update_role("flex_role", permissions=["dashboard", "reports"])
        result2 = rs.authenticate("flex_u", "pass")
        assert "reports" in result2["permissions"]

    def test_whitespace_stripped_from_names(self):
        role = rs.create_role("strip_r", "  Stripped Name  ", "  desc  ", ["dashboard"])
        assert role["name"] == "Stripped Name"
        assert role["description"] == "desc"

    def test_get_user_returns_none_for_unknown(self):
        assert rs.get_user("absolutely_nobody") is None
