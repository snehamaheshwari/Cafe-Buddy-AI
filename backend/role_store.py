"""
Role-Based Access Control (RBAC) store.
Manages roles (with permissions) and users, persisted to data/roles.json.

Roles:
  admin      — All permissions including role_management (system, non-deletable)
  sub_admin  — Operational set: no role_management (system, non-deletable)
  viewer     — Read-only dashboards (system, non-deletable)
  <custom>   — Any admin-defined role

Users:
  admin / owner — system users (non-deletable); all others are managed via admin UI
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

# ─── All feature permission keys ─────────────────────────────────────────────
ALL_PERMISSIONS: list[str] = [
    "dashboard",
    "upload_data",
    "reports",
    "analytics",
    "decision_engine",
    "auto_pilot",
    "chatbot",
    "market_radar",
    "whatsapp_alerts",
    "role_management",
    "audit_logs",
]

PERMISSION_LABELS: dict[str, str] = {
    "dashboard":       "Home / Dashboard",
    "upload_data":     "Upload My Data",
    "reports":         "Reports & Insights",
    "analytics":       "Smart Analytics",
    "decision_engine": "What To Do Next",
    "auto_pilot":      "Auto-Pilot Mode",
    "chatbot":         "Ask Cafe Buddy",
    "market_radar":    "Market Radar",
    "whatsapp_alerts": "WhatsApp Alerts",
    "role_management": "Role Management",
    "audit_logs":      "Audit Logs",
}

# ─── System roles (always present, cannot be deleted) ─────────────────────────
_DEFAULT_ROLES: dict[str, dict] = {
    "admin": {
        "id":          "admin",
        "name":        "Admin",
        "description": "Full access to all features including role management and audit logs",
        "is_system":   True,
        "permissions": list(ALL_PERMISSIONS),  # includes audit_logs
    },
    "sub_admin": {
        "id":          "sub_admin",
        "name":        "Sub-Admin",
        "description": "Operational access — upload data, view analytics, manage decisions. No role management.",
        "is_system":   True,
        "permissions": [
            "dashboard", "upload_data", "reports",
            "analytics", "decision_engine", "chatbot",
        ],
    },
    "viewer": {
        "id":          "viewer",
        "name":        "Viewer",
        "description": "Read-only access to dashboards and market data",
        "is_system":   True,
        "permissions": ["dashboard", "reports", "market_radar"],
    },
}

# ─── System users (always present, cannot be deleted) ────────────────────────
_DEFAULT_USERS: dict[str, dict] = {
    "admin": {
        "username":   "admin",
        "password":   "cafe123",
        "role_id":    "admin",
        "full_name":  "Admin User",
        "email":      "admin@cafebuddy.ai",
        "is_active":  True,
        "is_system":  True,
        "created_at": "2024-01-01 00:00:00",
    },
    "owner": {
        "username":   "owner",
        "password":   "buddy@2024",
        "role_id":    "admin",
        "full_name":  "Cafe Owner",
        "email":      "owner@cafebuddy.ai",
        "is_active":  True,
        "is_system":  True,
        "created_at": "2024-01-01 00:00:00",
    },
}

# ─── Persistence ──────────────────────────────────────────────────────────────
_DATA_DIR = os.environ.get(
    "DATA_DIR",
    os.path.join(os.path.dirname(__file__), "data"),
)
_STORE_FILE = os.path.join(_DATA_DIR, "roles.json")

# In-memory store
_roles: dict[str, dict] = {}
_users: dict[str, dict] = {}
_loaded: bool = False


def _load() -> None:
    """Load roles + users from disk; merge defaults on top of persisted data."""
    global _roles, _users, _loaded
    os.makedirs(_DATA_DIR, exist_ok=True)

    if os.path.exists(_STORE_FILE):
        try:
            with open(_STORE_FILE, "r", encoding="utf-8") as f:
                obj = json.load(f)
            _roles = obj.get("roles", {})
            _users = obj.get("users", {})
        except Exception:
            _roles, _users = {}, {}

    # Always guarantee system roles + users exist
    for rid, role in _DEFAULT_ROLES.items():
        _roles.setdefault(rid, dict(role))
    for uname, user in _DEFAULT_USERS.items():
        _users.setdefault(uname, dict(user))

    _loaded = True


def _save() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_STORE_FILE, "w", encoding="utf-8") as f:
        json.dump({"roles": _roles, "users": _users}, f, indent=2, ensure_ascii=False)


def _ensure() -> None:
    if not _loaded:
        _load()


def reload() -> None:
    """Force reload from disk (used in tests to reset state).
    Also re-reads DATA_DIR from env so tests that change the env var
    before calling reload() pick up the new path correctly.
    """
    global _loaded, _DATA_DIR, _STORE_FILE
    _DATA_DIR   = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
    _STORE_FILE = os.path.join(_DATA_DIR, "roles.json")
    _loaded = False
    _roles.clear()
    _users.clear()
    _load()


# ─── Role CRUD ────────────────────────────────────────────────────────────────

def list_roles() -> list[dict]:
    """Return all roles."""
    _ensure()
    return list(_roles.values())


def get_role(role_id: str) -> Optional[dict]:
    """Return role by ID, or None."""
    _ensure()
    return _roles.get(role_id)


def create_role(
    role_id: str,
    name: str,
    description: str,
    permissions: list[str],
) -> dict:
    """Create a new custom role."""
    _ensure()
    if not role_id or not role_id.strip():
        raise ValueError("Role ID cannot be empty")
    role_id = role_id.strip().lower().replace(" ", "_")
    if role_id in _roles:
        raise ValueError(f"Role '{role_id}' already exists")
    bad = [p for p in permissions if p not in ALL_PERMISSIONS]
    if bad:
        raise ValueError(f"Unknown permissions: {bad}")
    role: dict = {
        "id":          role_id,
        "name":        name.strip(),
        "description": description.strip(),
        "is_system":   False,
        "permissions": list(permissions),
    }
    _roles[role_id] = role
    _save()
    return role


def update_role(
    role_id: str,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    permissions: Optional[list[str]] = None,
) -> dict:
    """Update a role's name, description, or permissions."""
    _ensure()
    if role_id not in _roles:
        raise KeyError(f"Role '{role_id}' not found")
    role = _roles[role_id]
    if name is not None:
        role["name"] = name.strip()
    if description is not None:
        role["description"] = description.strip()
    if permissions is not None:
        bad = [p for p in permissions if p not in ALL_PERMISSIONS]
        if bad:
            raise ValueError(f"Unknown permissions: {bad}")
        # Admin role must always retain role_management and audit_logs
        if role_id == "admin":
            must_have = ["role_management", "audit_logs"]
            for perm in must_have:
                if perm not in permissions:
                    permissions = list(permissions) + [perm]
        role["permissions"] = list(permissions)
    _save()
    return role


def delete_role(role_id: str) -> None:
    """Delete a custom role. System roles cannot be deleted."""
    _ensure()
    if role_id not in _roles:
        raise KeyError(f"Role '{role_id}' not found")
    if _roles[role_id].get("is_system"):
        raise ValueError(f"Cannot delete system role '{role_id}'")
    # Downgrade affected users to viewer
    for user in _users.values():
        if user.get("role_id") == role_id:
            user["role_id"] = "viewer"
    del _roles[role_id]
    _save()


# ─── User CRUD ────────────────────────────────────────────────────────────────

def _user_safe(user: dict) -> dict:
    """Return user without password field."""
    return {k: v for k, v in user.items() if k != "password"}


def list_users() -> list[dict]:
    """Return all users (without passwords)."""
    _ensure()
    return [_user_safe(u) for u in _users.values()]


def get_user(username: str) -> Optional[dict]:
    """Return user by username (without password), or None."""
    _ensure()
    u = _users.get(username)
    return _user_safe(u) if u else None


def authenticate(username: str, password: str) -> Optional[dict]:
    """
    Validate credentials. On success returns:
      { username, full_name, role_id, role_name, permissions }
    Returns None on failure.
    """
    _ensure()
    u = _users.get(username)
    if not u or not u.get("is_active", True):
        return None
    if u.get("password") != password:
        return None
    role = _roles.get(u.get("role_id", "viewer"), _roles.get("viewer", {}))
    return {
        "username":    u["username"],
        "full_name":   u.get("full_name", u["username"]),
        "role_id":     role.get("id", "viewer"),
        "role_name":   role.get("name", "Viewer"),
        "permissions": list(role.get("permissions", [])),
    }


def create_user(
    username: str,
    password: str,
    role_id: str,
    full_name: str = "",
    email: str = "",
) -> dict:
    """Create a new user. Returns safe user dict."""
    _ensure()
    username = username.strip()
    if not username:
        raise ValueError("Username cannot be empty")
    if not password:
        raise ValueError("Password cannot be empty")
    if username in _users:
        raise ValueError(f"User '{username}' already exists")
    if role_id not in _roles:
        raise ValueError(f"Role '{role_id}' not found")
    user: dict = {
        "username":   username,
        "password":   password,
        "role_id":    role_id,
        "full_name":  full_name.strip() or username,
        "email":      email.strip(),
        "is_active":  True,
        "is_system":  False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _users[username] = user
    _save()
    return _user_safe(user)


def update_user(
    username: str,
    *,
    role_id: Optional[str] = None,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    is_active: Optional[bool] = None,
    password: Optional[str] = None,
) -> dict:
    """Update user fields. Returns safe user dict."""
    _ensure()
    if username not in _users:
        raise KeyError(f"User '{username}' not found")
    user = _users[username]
    if role_id is not None:
        if role_id not in _roles:
            raise ValueError(f"Role '{role_id}' not found")
        user["role_id"] = role_id
    if full_name is not None:
        user["full_name"] = full_name.strip()
    if email is not None:
        user["email"] = email.strip()
    if is_active is not None:
        user["is_active"] = is_active
    if password is not None:
        if not password:
            raise ValueError("Password cannot be empty")
        user["password"] = password
    _save()
    return _user_safe(user)


def delete_user(username: str) -> None:
    """Delete a non-system user."""
    _ensure()
    if username not in _users:
        raise KeyError(f"User '{username}' not found")
    if _users[username].get("is_system"):
        raise ValueError(f"Cannot delete system user '{username}'")
    del _users[username]
    _save()


def get_permissions(username: str) -> list[str]:
    """Return permission list for a user (empty list if user not found)."""
    _ensure()
    u = _users.get(username)
    if not u:
        return []
    role = _roles.get(u.get("role_id", "viewer"), {})
    return list(role.get("permissions", []))
