"""
tenant_store.py — Multi-tenant registry for Cafe Buddy AI.

Each tenant (café workspace) is an isolated environment with:
  • Own data directory  → data/{tenant_id}/
  • Own role/user file  → data/{tenant_id}/roles.json
  • Own branding        → cafe_name, logo_url, brand_color
  • Plan limits         → max_users (3), storage_limit_mb (200)
  • Storage tracking    → storage_used_mb (tracked per upload)

The "system" tenant (SYSTEM_TENANT_ID) is the legacy demo environment —
existing admin/owner accounts live there with no data isolation needed.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
import uuid
from datetime import datetime
from typing import Optional

# ─── Constants ────────────────────────────────────────────────────────────────
SYSTEM_TENANT_ID = "system"     # legacy demo workspace (no isolation)

PLAN_FREE = "free"              # initial plan: 3 users, 200 MB

PLAN_LIMITS: dict[str, dict] = {
    PLAN_FREE: {"max_users": 3, "storage_limit_mb": 200},
}

_DATA_DIR = os.environ.get("DATA_DIR",
                            os.path.join(os.path.dirname(__file__), "data"))
_TENANTS_FILE = os.path.join(_DATA_DIR, "tenants.json")


# ─── Disk I/O ─────────────────────────────────────────────────────────────────

def _load() -> dict:
    os.makedirs(_DATA_DIR, exist_ok=True)
    if os.path.exists(_TENANTS_FILE):
        try:
            with open(_TENANTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"tenants": {}}


def _save(data: dict) -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_TENANTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ─── Slug utilities ───────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    """Convert a café name to a URL-safe ASCII workspace slug (max 50 chars).

    Handles unicode: é→e, ñ→n, etc. via NFKD normalization.
    """
    # Normalize unicode (NFKD decomposes accented chars into base + combining)
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = ascii_str.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)   # remove non-word chars (except space/-)
    slug = re.sub(r"[\s_]+", "-", slug)     # spaces/underscores → hyphen
    slug = slug.strip("-")
    return slug[:50] or "cafe"


def _unique_slug(base: str, existing: set[str]) -> str:
    slug = base
    counter = 1
    while slug in existing:
        slug = f"{base}-{counter}"
        counter += 1
    return slug


# ─── Tenant CRUD ──────────────────────────────────────────────────────────────

def create_tenant(
    cafe_name: str,
    owner_name: str,
    owner_email: str,
    admin_username: str,
    brand_color: str = "#6366f1",
    logo_url: str = "",
    plan: str = PLAN_FREE,
) -> dict:
    """
    Register a new tenant workspace.

    Returns the created tenant dict.
    Raises ValueError if cafe_name / admin_username / owner_email is empty.
    """
    cafe_name      = cafe_name.strip()
    owner_name     = owner_name.strip()
    owner_email    = owner_email.strip()
    admin_username = admin_username.strip()

    if not cafe_name:
        raise ValueError("Café name is required")
    if not owner_email:
        raise ValueError("Owner email is required")
    if not admin_username:
        raise ValueError("Admin username is required")

    data = _load()
    existing_slugs    = {t["slug"] for t in data["tenants"].values()}
    existing_usernames = {t["admin_username"] for t in data["tenants"].values()}

    if admin_username in existing_usernames:
        raise ValueError(f"Username '{admin_username}' is already registered")

    limits     = PLAN_LIMITS.get(plan, PLAN_LIMITS[PLAN_FREE])
    tenant_id  = str(uuid.uuid4())
    slug       = _unique_slug(slugify(cafe_name), existing_slugs)

    tenant: dict = {
        "tenant_id":        tenant_id,
        "slug":             slug,
        "cafe_name":        cafe_name,
        "owner_name":       owner_name,
        "owner_email":      owner_email,
        "brand_color":      brand_color if brand_color else "#6366f1",
        "logo_url":         logo_url or "",
        "plan":             plan,
        "max_users":        limits["max_users"],
        "storage_limit_mb": limits["storage_limit_mb"],
        "storage_used_mb":  0.0,
        "is_active":        True,
        "admin_username":   admin_username,
        "created_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    data["tenants"][tenant_id] = tenant
    _save(data)

    # Create tenant data directory
    get_tenant_data_dir(tenant_id)
    return tenant


def get_tenant(tenant_id: str) -> Optional[dict]:
    """Return tenant dict by ID, or None."""
    return _load()["tenants"].get(tenant_id)


def get_tenant_by_slug(slug: str) -> Optional[dict]:
    """Return tenant dict by workspace slug, or None."""
    for t in _load()["tenants"].values():
        if t.get("slug") == slug:
            return t
    return None


def list_tenants() -> list[dict]:
    return list(_load()["tenants"].values())


def slug_available(slug: str) -> bool:
    return all(t.get("slug") != slug for t in _load()["tenants"].values())


def update_branding(
    tenant_id: str,
    *,
    cafe_name:   Optional[str] = None,
    brand_color: Optional[str] = None,
    logo_url:    Optional[str] = None,
) -> dict:
    """Update branding fields. Returns updated tenant dict."""
    data = _load()
    if tenant_id not in data["tenants"]:
        raise KeyError(f"Tenant '{tenant_id}' not found")
    t = data["tenants"][tenant_id]
    if cafe_name   is not None: t["cafe_name"]   = cafe_name.strip()
    if brand_color is not None: t["brand_color"] = brand_color
    if logo_url    is not None: t["logo_url"]    = logo_url
    _save(data)
    return t


# ─── Storage tracking ─────────────────────────────────────────────────────────

def get_storage_used_mb(tenant_id: str) -> float:
    t = get_tenant(tenant_id)
    return t["storage_used_mb"] if t else 0.0


def get_storage_limit_mb(tenant_id: str) -> float:
    t = get_tenant(tenant_id)
    return float(t["storage_limit_mb"]) if t else 200.0


def check_storage_limit(tenant_id: str, file_bytes: int) -> tuple[bool, float, float]:
    """
    Check whether uploading `file_bytes` would exceed the tenant's storage limit.

    Returns (ok: bool, used_mb: float, limit_mb: float).
    `ok` is True if the upload is within quota.
    """
    if tenant_id == SYSTEM_TENANT_ID:
        return True, 0.0, float("inf")
    t = get_tenant(tenant_id)
    if not t:
        return True, 0.0, 200.0   # unknown tenant — allow, don't crash
    used_mb  = float(t.get("storage_used_mb", 0.0))
    limit_mb = float(t.get("storage_limit_mb", 200.0))
    new_mb   = used_mb + file_bytes / (1024 * 1024)
    return new_mb <= limit_mb, used_mb, limit_mb


def record_upload(tenant_id: str, file_bytes: int) -> None:
    """Increment storage_used_mb for a tenant after a successful upload."""
    if tenant_id == SYSTEM_TENANT_ID:
        return
    data = _load()
    if tenant_id in data["tenants"]:
        current = float(data["tenants"][tenant_id].get("storage_used_mb", 0.0))
        data["tenants"][tenant_id]["storage_used_mb"] = round(
            current + file_bytes / (1024 * 1024), 3
        )
        _save(data)


# ─── User-count helpers ───────────────────────────────────────────────────────

def delete_tenant(tenant_id: str) -> None:
    """
    Permanently delete a tenant workspace.

    Removes the tenant record from tenants.json and wipes their data directory.
    Raises ValueError for the system tenant, KeyError if tenant_id is unknown.
    """
    import shutil
    if tenant_id == SYSTEM_TENANT_ID:
        raise ValueError("Cannot delete the system workspace")
    data = _load()
    if tenant_id not in data["tenants"]:
        raise KeyError(f"Workspace '{tenant_id}' not found")
    del data["tenants"][tenant_id]
    _save(data)
    # Remove tenant data directory (roles.json + uploaded datasets)
    tenant_dir = os.path.join(_DATA_DIR, tenant_id)
    if os.path.exists(tenant_dir):
        shutil.rmtree(tenant_dir, ignore_errors=True)


def get_max_users(tenant_id: str) -> int:
    if tenant_id == SYSTEM_TENANT_ID:
        return 999   # no limit for demo
    t = get_tenant(tenant_id)
    return int(t["max_users"]) if t else 3


# ─── Data-directory helpers ───────────────────────────────────────────────────

def get_tenant_data_dir(tenant_id: str) -> str:
    """Return (and create if missing) the data directory for this tenant."""
    if tenant_id == SYSTEM_TENANT_ID:
        return _DATA_DIR
    path = os.path.join(_DATA_DIR, tenant_id)
    os.makedirs(path, exist_ok=True)
    return path
