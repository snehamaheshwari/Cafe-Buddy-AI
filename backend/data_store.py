"""
Shared mutable state and analytics helpers.
Imported by both main.py and chatbot.py to avoid circular imports.
"""
from __future__ import annotations
import json
import os
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

# ─── Persistence helpers ─────────────────────────────────────────────────────
# DATA_DIR env var lets Railway volume path be overridden if needed.
# Default: <backend-dir>/data  →  /app/backend/data inside Docker.
# Railway volume must be mounted at the same path shown in startup logs.
_DATA_DIR = os.environ.get("DATA_DIR",
                            os.path.join(os.path.dirname(__file__), "data"))
print(f"[data_store] DATA_DIR = {_DATA_DIR}", flush=True)


def save_dataset(name: str, data: list, info: dict) -> None:
    """Persist a dataset to disk so it survives server restarts."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    path = os.path.join(_DATA_DIR, f"{name}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": data, "info": info}, f, ensure_ascii=False)
    except Exception:
        pass  # never crash an upload due to disk write failure


def load_dataset(name: str) -> tuple[list, dict]:
    """Load a persisted dataset from disk. Returns ([], {}) if not found."""
    path = os.path.join(_DATA_DIR, f"{name}.json")
    if not os.path.exists(path):
        return [], {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj.get("data", []), obj.get("info", {})
    except Exception:
        return [], {}


def clear_dataset(name: str) -> None:
    """Remove a persisted dataset file from disk."""
    path = os.path.join(_DATA_DIR, f"{name}.json")
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

# ─── Global state (mutated by main.py / multi_upload.py) ─────────────────────
_uploaded_data: list = []       # legacy single-file upload
_upload_info: dict   = {}
_decision_overrides: dict = {}

# Three typed datasets
_financial_data: list = []
_financial_info: dict = {}
_pos_data: list = []
_pos_info: dict  = {}
_customer_data: list = []
_customer_info: dict = {}

# Sentiment / Reviews dataset
_review_data: list = []
_review_info: dict = {}

# Menu dataset
_menu_data: list = []
_menu_info: dict = {}


def get_data() -> list:
    """Priority: POS upload → legacy upload → empty (no mock fallback)."""
    if _pos_data:
        return _pos_data
    if _uploaded_data:
        return _uploaded_data
    return []

# ─── Mock seed ───────────────────────────────────────────────────────────────
_MOCK_MENU = [
    {"id": 1,  "name": "Pasta Combo",      "category": "Main",     "price": 280, "cost": 120},
    {"id": 2,  "name": "Garlic Bread",     "category": "Starter",  "price": 80,  "cost": 25},
    {"id": 3,  "name": "Cappuccino",       "category": "Beverage", "price": 120, "cost": 35},
    {"id": 4,  "name": "Cold Coffee",      "category": "Beverage", "price": 150, "cost": 45},
    {"id": 5,  "name": "Mozzarella Pizza", "category": "Main",     "price": 320, "cost": 140},
    {"id": 6,  "name": "Caesar Salad",     "category": "Starter",  "price": 180, "cost": 70},
    {"id": 7,  "name": "Tiramisu",         "category": "Dessert",  "price": 160, "cost": 55},
    {"id": 8,  "name": "Espresso",         "category": "Beverage", "price": 80,  "cost": 20},
    {"id": 9,  "name": "Bruschetta",       "category": "Starter",  "price": 120, "cost": 40},
    {"id": 10, "name": "Penne Arrabbiata", "category": "Main",     "price": 240, "cost": 95},
]

def _make_mock() -> list:
    rows, rng = [], random.Random(42)
    base = datetime.now() - timedelta(days=30)
    for i in range(30):
        date = base + timedelta(days=i)
        mult = 1.3 if date.weekday() >= 5 else 1.0
        for item in _MOCK_MENU:
            qty = int(rng.randint(5, 25) * mult)
            rows.append({
                "date": date.strftime("%Y-%m-%d"),
                "item_name": item["name"], "category": item["category"],
                "quantity": float(qty), "price": float(item["price"]),
                "revenue": float(qty * item["price"]),
                "cost": float(qty * item["cost"]),
                "platform": rng.choice(["Dine-in", "Zomato", "Swiggy"]),
            })
    return rows

_MOCK_SALES: list = _make_mock()

# ─── Analytics helpers (shared) ──────────────────────────────────────────────

def item_stats(data: list) -> list:
    agg: dict = defaultdict(lambda: {"qty": 0.0, "revenue": 0.0, "cost": 0.0})
    for r in data:
        agg[r["item_name"]]["qty"]     += r.get("quantity", r.get("qty", 1))
        agg[r["item_name"]]["revenue"] += r["revenue"]
        agg[r["item_name"]]["cost"]    += r["cost"]
    out = []
    for name, v in agg.items():
        margin = (v["revenue"] - v["cost"]) / max(v["revenue"], 1) * 100
        out.append({"name": name, "qty": round(v["qty"], 1),
                    "revenue": round(v["revenue"], 2), "cost": round(v["cost"], 2),
                    "margin_pct": round(margin, 1)})
    return sorted(out, key=lambda x: x["revenue"], reverse=True)


def platform_breakdown(data: list) -> list:
    agg: dict = defaultdict(lambda: {"orders": 0, "revenue": 0.0})
    for r in data:
        agg[r["platform"]]["orders"]  += int(r["quantity"])
        agg[r["platform"]]["revenue"] += r["revenue"]
    return [{"platform": k, "orders": v["orders"], "revenue": round(v["revenue"], 2)}
            for k, v in agg.items()]


def category_breakdown(data: list) -> list:
    agg: dict = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "cost": 0.0})
    for r in data:
        agg[r["category"]]["revenue"] += r["revenue"]
        agg[r["category"]]["orders"]  += int(r["quantity"])
        agg[r["category"]]["cost"]    += r["cost"]
    return [{"category": k, "revenue": round(v["revenue"], 2),
             "orders": v["orders"], "cost": round(v["cost"], 2),
             "margin_pct": round((v["revenue"] - v["cost"]) / max(v["revenue"], 1) * 100, 1)}
            for k, v in agg.items()]


def daily_revenue(data: list, days: int = 14) -> list:
    agg: dict = defaultdict(lambda: {"revenue": 0.0, "orders": 0.0})
    for r in data:
        agg[r["date"]]["revenue"] += r["revenue"]
        agg[r["date"]]["orders"]  += r["quantity"]
    rows = sorted(agg.items())[-days:]
    return [{"date": d, "revenue": round(v["revenue"], 2), "orders": int(v["orders"]),
             "avg_order_value": round(v["revenue"] / max(v["orders"], 1), 2)}
            for d, v in rows]


def weekday_forecast(data: list, days: int = 7) -> list:
    wd_total: dict = defaultdict(float)
    wd_count: dict = defaultdict(int)
    for r in data:
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d")
            wd_total[d.weekday()] += r["revenue"]
            wd_count[d.weekday()] += 1
        except Exception:
            pass
    overall = sum(wd_total.values()) / max(sum(wd_count.values()), 1)
    wd_avg  = {wd: wd_total[wd] / wd_count[wd] for wd in wd_total}
    names   = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    result  = []
    for i in range(1, days + 1):
        date = datetime.now() + timedelta(days=i)
        wd   = date.weekday()
        base = wd_avg.get(wd, overall)
        rev  = int(base * random.uniform(0.93, 1.07))
        result.append({
            "date": date.strftime("%Y-%m-%d"), "day": names[wd],
            "predicted_revenue": rev, "upper": int(rev * 1.09), "lower": int(rev * 0.91),
            "predicted_orders": max(1, int(rev / 250)),
            "confidence": round(random.uniform(80, 94), 1),
            "weather": "Rainy" if i == 3 else "Clear", "is_weekend": wd >= 5,
        })
    return result


# ─── Auto-load persisted data on startup ─────────────────────────────────────
# These assignments run once when the module is first imported,
# restoring any datasets that survived a previous server session.
_loaded = load_dataset("financial")
_financial_data, _financial_info = _loaded

_loaded = load_dataset("pos")
_pos_data, _pos_info = _loaded
if _pos_data:
    _uploaded_data = _pos_data
    _upload_info   = _pos_info

_loaded = load_dataset("customer")
_customer_data, _customer_info = _loaded

_loaded = load_dataset("reviews_meta")   # stats + info only; records via sentiment engine
_review_data, _review_info = _loaded

_loaded = load_dataset("menu")
_menu_data, _menu_info = _loaded

del _loaded  # clean up temp variable


# ─── Per-tenant data storage ──────────────────────────────────────────────────
#
# For new tenants each dataset is stored under data/{tenant_id}/{name}.json
# and kept in the _tenant_state in-memory cache below.
# The system tenant (SYSTEM_TENANT_ID = "system") continues to use the
# module-level globals above (no behaviour change for existing demo accounts).

_tenant_state: dict[str, dict] = {}
#  keyed by tenant_id → {
#    "pos_data": list, "pos_info": dict,
#    "financial_data": list, "financial_info": dict,
#    "customer_data": list, "customer_info": dict,
#    "review_data": list,  "review_info": dict,
#    "menu_data": list,    "menu_info": dict,
#    "decision_overrides": dict,
#  }


def _tenant_bucket(tenant_id: str) -> dict:
    """Return (lazily-creating) the in-memory bucket for a tenant."""
    if tenant_id not in _tenant_state:
        _tenant_state[tenant_id] = {
            "pos_data": [], "pos_info": {},
            "financial_data": [], "financial_info": {},
            "customer_data": [], "customer_info": {},
            "review_data": [],  "review_info": {},
            "menu_data": [],    "menu_info": {},
            "decision_overrides": {},
        }
    return _tenant_state[tenant_id]


def save_dataset_for_tenant(tenant_id: str, name: str,
                             data: list, info: dict) -> None:
    """Persist a dataset scoped to a tenant."""
    from tenant_store import SYSTEM_TENANT_ID, get_tenant_data_dir
    if tenant_id == SYSTEM_TENANT_ID:
        save_dataset(name, data, info)
        return
    tenant_dir = get_tenant_data_dir(tenant_id)
    path = os.path.join(tenant_dir, f"{name}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"data": data, "info": info}, f, ensure_ascii=False)
    except Exception:
        pass
    # Update in-memory cache
    bucket = _tenant_bucket(tenant_id)
    bucket[f"{name}_data"] = data
    bucket[f"{name}_info"] = info
    if name == "pos":
        bucket["pos_data"] = data
        bucket["pos_info"] = info


def load_dataset_for_tenant(tenant_id: str, name: str) -> tuple[list, dict]:
    """Load a persisted dataset for a tenant. Returns ([], {}) if missing."""
    from tenant_store import SYSTEM_TENANT_ID, get_tenant_data_dir
    if tenant_id == SYSTEM_TENANT_ID:
        return load_dataset(name)
    bucket = _tenant_bucket(tenant_id)
    cached = bucket.get(f"{name}_data")
    if cached:
        return cached, bucket.get(f"{name}_info", {})
    tenant_dir = get_tenant_data_dir(tenant_id)
    path = os.path.join(tenant_dir, f"{name}.json")
    if not os.path.exists(path):
        return [], {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        data = obj.get("data", [])
        info = obj.get("info", {})
        bucket[f"{name}_data"] = data
        bucket[f"{name}_info"] = info
        return data, info
    except Exception:
        return [], {}


def get_pos_data_for_tenant(tenant_id: str) -> list:
    """Return POS data for any tenant (system or new)."""
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        return get_data()
    data, _ = load_dataset_for_tenant(tenant_id, "pos")
    return data


def get_data_for_tenant(tenant_id: str) -> list:
    """Alias for get_pos_data_for_tenant — preferred in endpoint code."""
    return get_pos_data_for_tenant(tenant_id)


def clear_tenant_data(tenant_id: str) -> None:
    """
    Remove all datasets for a tenant from disk and memory.
    Called when a tenant resets their data or deactivates.
    Does NOT affect the system tenant.
    """
    from tenant_store import SYSTEM_TENANT_ID, get_tenant_data_dir
    if tenant_id == SYSTEM_TENANT_ID:
        return
    if tenant_id in _tenant_state:
        del _tenant_state[tenant_id]
    tenant_dir = get_tenant_data_dir(tenant_id)
    for fname in ["pos", "financial", "customer", "reviews_meta", "menu"]:
        path = os.path.join(tenant_dir, f"{fname}.json")
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def get_decision_overrides_for_tenant(tenant_id: str) -> dict:
    """Return the decision-overrides dict for a tenant."""
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        return _decision_overrides
    return _tenant_bucket(tenant_id)["decision_overrides"]


# ─── Additional per-tenant typed accessors & mutators ─────────────────────────
# These functions centralise every read/write of the five dataset types so that
# new-tenant endpoints never touch the system-tenant module-level globals.

def get_financial_for_tenant(tenant_id: str) -> tuple:
    """Return (financial_data, financial_info) for any tenant."""
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        return _financial_data, _financial_info
    return load_dataset_for_tenant(tenant_id, "financial")


def get_customer_for_tenant(tenant_id: str) -> tuple:
    """Return (customer_data, customer_info) for any tenant."""
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        return _customer_data, _customer_info
    return load_dataset_for_tenant(tenant_id, "customer")


def get_menu_for_tenant(tenant_id: str) -> tuple:
    """Return (menu_data, menu_info) for any tenant."""
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        return _menu_data, _menu_info
    return load_dataset_for_tenant(tenant_id, "menu")


def get_pos_for_tenant(tenant_id: str) -> tuple:
    """Return (pos_data, pos_info) for any tenant."""
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        return _pos_data, _pos_info
    return load_dataset_for_tenant(tenant_id, "pos")


def get_uploaded_for_tenant(tenant_id: str) -> tuple:
    """Return (uploaded_data, upload_info) for the legacy single-file upload."""
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        return _uploaded_data, _upload_info
    bucket = _tenant_bucket(tenant_id)
    return bucket.get("uploaded_data", []), bucket.get("upload_info", {})


def set_pos_for_tenant(tenant_id: str, records: list, info: dict) -> None:
    """Persist POS data for a tenant (memory + disk)."""
    global _pos_data, _pos_info, _uploaded_data, _upload_info
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _pos_data = records
        _pos_info = info
        _uploaded_data = records
        _upload_info = info
        save_dataset("pos", records, info)
        return
    bucket = _tenant_bucket(tenant_id)
    bucket["pos_data"] = records
    bucket["pos_info"] = info
    bucket["uploaded_data"] = records
    bucket["upload_info"] = info
    save_dataset_for_tenant(tenant_id, "pos", records, info)


def set_financial_for_tenant(tenant_id: str, records: list, info: dict) -> None:
    """Persist financial data for a tenant (memory + disk)."""
    global _financial_data, _financial_info
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _financial_data = records
        _financial_info = info
        save_dataset("financial", records, info)
        return
    bucket = _tenant_bucket(tenant_id)
    bucket["financial_data"] = records
    bucket["financial_info"] = info
    save_dataset_for_tenant(tenant_id, "financial", records, info)


def set_customer_for_tenant(tenant_id: str, records: list, info: dict) -> None:
    """Persist customer data for a tenant (memory + disk)."""
    global _customer_data, _customer_info
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _customer_data = records
        _customer_info = info
        save_dataset("customer", records, info)
        return
    bucket = _tenant_bucket(tenant_id)
    bucket["customer_data"] = records
    bucket["customer_info"] = info
    save_dataset_for_tenant(tenant_id, "customer", records, info)


def set_menu_for_tenant(tenant_id: str, records: list, info: dict) -> None:
    """Persist menu data for a tenant (memory + disk)."""
    global _menu_data, _menu_info
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _menu_data = records
        _menu_info = info
        save_dataset("menu", records, info)
        return
    bucket = _tenant_bucket(tenant_id)
    bucket["menu_data"] = records
    bucket["menu_info"] = info
    save_dataset_for_tenant(tenant_id, "menu", records, info)


def set_uploaded_for_tenant(tenant_id: str, records: list, info: dict) -> None:
    """Store legacy single-file upload data in memory for a tenant."""
    global _uploaded_data, _upload_info
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _uploaded_data = records
        _upload_info = info
        return
    bucket = _tenant_bucket(tenant_id)
    bucket["uploaded_data"] = records
    bucket["upload_info"] = info


def set_decision_override_for_tenant(tenant_id: str, decision_id: int,
                                      status: str) -> None:
    """Record approve/reject for a single decision, scoped to the tenant."""
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _decision_overrides[decision_id] = status
    else:
        _tenant_bucket(tenant_id)["decision_overrides"][decision_id] = status


def clear_overrides_for_tenant(tenant_id: str) -> None:
    """Reset all decision overrides for a tenant."""
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _decision_overrides.clear()
    else:
        _tenant_bucket(tenant_id)["decision_overrides"].clear()


def clear_pos_for_tenant(tenant_id: str) -> None:
    """Clear POS data for a tenant (memory + disk)."""
    global _pos_data, _pos_info, _uploaded_data, _upload_info
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _pos_data = []
        _pos_info = {}
        _uploaded_data = []
        _upload_info = {}
        clear_dataset("pos")
        return
    bucket = _tenant_bucket(tenant_id)
    bucket["pos_data"] = []
    bucket["pos_info"] = {}
    bucket["uploaded_data"] = []
    bucket["upload_info"] = {}
    save_dataset_for_tenant(tenant_id, "pos", [], {})


def clear_financial_for_tenant(tenant_id: str) -> None:
    """Clear financial data for a tenant (memory + disk)."""
    global _financial_data, _financial_info
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _financial_data = []
        _financial_info = {}
        clear_dataset("financial")
        return
    bucket = _tenant_bucket(tenant_id)
    bucket["financial_data"] = []
    bucket["financial_info"] = {}
    save_dataset_for_tenant(tenant_id, "financial", [], {})


def clear_customer_for_tenant(tenant_id: str) -> None:
    """Clear customer data for a tenant (memory + disk)."""
    global _customer_data, _customer_info
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _customer_data = []
        _customer_info = {}
        clear_dataset("customer")
        return
    bucket = _tenant_bucket(tenant_id)
    bucket["customer_data"] = []
    bucket["customer_info"] = {}
    save_dataset_for_tenant(tenant_id, "customer", [], {})


def clear_menu_for_tenant(tenant_id: str) -> None:
    """Clear menu data for a tenant (memory + disk)."""
    global _menu_data, _menu_info
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _menu_data = []
        _menu_info = {}
        clear_dataset("menu")
        return
    bucket = _tenant_bucket(tenant_id)
    bucket["menu_data"] = []
    bucket["menu_info"] = {}
    save_dataset_for_tenant(tenant_id, "menu", [], {})


def clear_all_for_tenant(tenant_id: str) -> None:
    """Clear ALL uploaded data + decision overrides for a tenant (used by /upload/clear)."""
    global _uploaded_data, _upload_info
    from tenant_store import SYSTEM_TENANT_ID
    if tenant_id == SYSTEM_TENANT_ID:
        _uploaded_data = []
        _upload_info = {}
        _decision_overrides.clear()
        return
    if tenant_id in _tenant_state:
        _tenant_state[tenant_id] = {
            "pos_data": [], "pos_info": {},
            "financial_data": [], "financial_info": {},
            "customer_data": [], "customer_info": {},
            "review_data": [],  "review_info": {},
            "menu_data": [],    "menu_info": {},
            "decision_overrides": {},
            "uploaded_data": [], "upload_info": {},
        }
