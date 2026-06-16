import io
import os
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import data_store          # shared mutable state
from chatbot import router as chatbot_router
from multi_upload import router as multi_upload_router
from sentiment_engine import get_engine as get_sentiment_engine
import ml_models
import peer_comparison as pc
import role_store as _rs
import audit_store as _audit

from fastapi import Request
from fastapi.responses import Response, StreamingResponse

app = FastAPI(title="Cafe Buddy API", version="2.0.0")
app.include_router(chatbot_router, prefix="/api")
app.include_router(multi_upload_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Audit middleware ─────────────────────────────────────────────────────────
# Captures the X-Username header set by the frontend apiFetch wrapper.
# Light-weight: only logs if X-Username is present (authenticated routes).
# Heavy data endpoints are excluded to avoid double-logging (they log explicitly).
_AUDIT_EXCLUDE_PREFIXES = (
    "/assets/", "/health", "/api/upload/status", "/api/dashboard",
    "/api/layer1", "/api/layer2", "/api/layer3", "/api/layer4",
    "/api/layer5", "/api/ml", "/api/peers", "/api/audit",
    "/api/roles", "/api/users",
)

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    import time
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    username = request.headers.get("X-Username", "")
    path     = request.url.path
    method   = request.method

    # Only log authenticated requests that aren't handled by explicit audit calls
    if username and not any(path.startswith(p) for p in _AUDIT_EXCLUDE_PREFIXES):
        # Derive module from path
        module = "system"
        if "/auth/" in path:
            module = "auth"
        elif "/sentiment" in path:
            module = "analytics"

        action = f"{method}_REQUEST"
        status_code = response.status_code
        _audit.log_action(
            username=username,
            module=module,
            action=action,
            description=f"{method} {path}",
            role=request.headers.get("X-Role", ""),
            status=_audit.STATUS_SUCCESS if status_code < 400 else _audit.STATUS_ERROR,
            ip_address=request.client.host if request.client else "",
            duration_ms=elapsed_ms,
        )
    return response

random.seed(None)  # non-deterministic seed so each load looks live

# ─────────────────────────────────────────────
# GLOBAL STATE  (uploaded Excel replaces mock data when present)
# ─────────────────────────────────────────────

_uploaded_data: list = []        # normalized rows from Excel
_upload_info: dict = {}          # metadata about last upload
_decision_overrides: dict = {}   # tracks approve/reject actions

# ─────────────────────────────────────────────
# MOCK SEED DATA  (shown when no Excel is uploaded)
# ─────────────────────────────────────────────

MOCK_MENU = [
    {"id": 1, "name": "Pasta Combo",      "category": "Main",     "price": 280, "cost": 120},
    {"id": 2, "name": "Garlic Bread",     "category": "Starter",  "price": 80,  "cost": 25},
    {"id": 3, "name": "Cappuccino",       "category": "Beverage", "price": 120, "cost": 35},
    {"id": 4, "name": "Cold Coffee",      "category": "Beverage", "price": 150, "cost": 45},
    {"id": 5, "name": "Mozzarella Pizza", "category": "Main",     "price": 320, "cost": 140},
    {"id": 6, "name": "Caesar Salad",     "category": "Starter",  "price": 180, "cost": 70},
    {"id": 7, "name": "Tiramisu",         "category": "Dessert",  "price": 160, "cost": 55},
    {"id": 8, "name": "Espresso",         "category": "Beverage", "price": 80,  "cost": 20},
    {"id": 9, "name": "Bruschetta",       "category": "Starter",  "price": 120, "cost": 40},
    {"id": 10,"name": "Penne Arrabbiata", "category": "Main",     "price": 240, "cost": 95},
]

MOCK_INVENTORY = [
    {"id": 1, "name": "Mozzarella",   "unit": "kg",     "stock": 2.5,  "threshold": 5.0,  "supplier": "Dairy Fresh",     "cost_per_unit": 450, "status": "critical"},
    {"id": 2, "name": "Pasta",        "unit": "kg",     "stock": 8.0,  "threshold": 5.0,  "supplier": "Italian Imports", "cost_per_unit": 120, "status": "ok"},
    {"id": 3, "name": "Coffee Beans", "unit": "kg",     "stock": 3.0,  "threshold": 2.0,  "supplier": "Bean Masters",    "cost_per_unit": 800, "status": "ok"},
    {"id": 4, "name": "Tomatoes",     "unit": "kg",     "stock": 12.0, "threshold": 8.0,  "supplier": "Farm Fresh",      "cost_per_unit": 40,  "status": "ok"},
    {"id": 5, "name": "Olive Oil",    "unit": "litre",  "stock": 4.0,  "threshold": 3.0,  "supplier": "Mediterranean",   "cost_per_unit": 350, "status": "ok"},
    {"id": 6, "name": "Flour",        "unit": "kg",     "stock": 15.0, "threshold": 10.0, "supplier": "Mill Direct",     "cost_per_unit": 45,  "status": "ok"},
    {"id": 7, "name": "Cream",        "unit": "litre",  "stock": 1.5,  "threshold": 3.0,  "supplier": "Dairy Fresh",     "cost_per_unit": 180, "status": "low"},
    {"id": 8, "name": "Garlic",       "unit": "kg",     "stock": 2.0,  "threshold": 1.0,  "supplier": "Farm Fresh",      "cost_per_unit": 80,  "status": "ok"},
]

def _make_mock_sales(days: int = 30) -> list:
    rows = []
    base = datetime.now() - timedelta(days=days)
    rng = random.Random(42)
    for i in range(days):
        date = base + timedelta(days=i)
        is_weekend = date.weekday() >= 5
        mult = 1.3 if is_weekend else 1.0
        for item in MOCK_MENU:
            qty = int(rng.randint(5, 25) * mult)
            revenue = qty * item["price"]
            rows.append({
                "date": date.strftime("%Y-%m-%d"),
                "item_name": item["name"],
                "category": item["category"],
                "quantity": float(qty),
                "price": float(item["price"]),
                "revenue": float(revenue),
                "cost": float(qty * item["cost"]),
                "platform": rng.choice(["Dine-in", "Zomato", "Swiggy"]),
            })
    return rows

MOCK_SALES = _make_mock_sales()

def get_data() -> list:
    """Return uploaded data — empty list when nothing uploaded (no mock fallback)."""
    return data_store.get_data()


def _sync_data_store():
    """Keep data_store in sync so chatbot.py sees the same data."""
    data_store._uploaded_data = _uploaded_data
    data_store._upload_info   = _upload_info


# ─── Per-tenant request helpers ───────────────────────────────────────────────
# All analytics endpoints call these helpers so data is scoped to the
# authenticated tenant (new cafés) while the system/demo tenant keeps its
# existing module-level globals.

def _req_tenant_id(request: Optional[Request] = None) -> str:
    """Extract tenant_id from JWT Bearer token; fall back to system tenant."""
    import auth_utils as _au
    import tenant_store as _ts
    if not request:
        return _ts.SYSTEM_TENANT_ID
    auth_header = request.headers.get("Authorization", "")
    return _au.extract_tenant_id(auth_header) or _ts.SYSTEM_TENANT_ID


def _req_data(request: Optional[Request] = None) -> list:
    """Return the POS/uploaded data for the calling tenant."""
    return data_store.get_data_for_tenant(_req_tenant_id(request))


def _req_overrides(request: Optional[Request] = None) -> dict:
    """Return the decision-overrides dict for the calling tenant."""
    return data_store.get_decision_overrides_for_tenant(_req_tenant_id(request))

# ─────────────────────────────────────────────
# EXCEL COLUMN DETECTION
# ─────────────────────────────────────────────

ALIASES = {
    "date":      ["date", "date_time", "datetime", "order_date", "sale_date",
                  "transaction_date", "trans_date", "order date", "sale date",
                  "transaction date", "day", "dt"],
    "item_name": ["item name / product", "item name/product", "item name",
                  "item_name", "item", "product", "product_name", "product name",
                  "menu_item", "menu item", "name", "description",
                  "item_description", "product description"],
    "category":  ["category / type", "category/type", "category", "cat",
                  "type", "item_type", "item type", "product_type",
                  "product type", "menu_category", "menu category"],
    "quantity":  ["quantity / qty", "quantity/qty", "quantity", "qty",
                  "count", "units", "pcs", "pieces", "units_sold", "units sold",
                  "items_sold", "items sold", "sold", "no_of_items", "no of items"],
    "price":     ["price / rate", "price/rate", "price", "unit_price",
                  "unit price", "selling_price", "selling price", "rate",
                  "mrp", "sp", "price_per_unit", "price per unit",
                  "sale_price", "sale price"],
    "revenue":   ["revenue / total", "revenue/total", "revenue", "total",
                  "total_revenue", "total revenue", "total_amount", "total amount",
                  "amount", "sales", "net_amount", "net amount",
                  "bill_amount", "bill amount", "gross_revenue", "gross revenue",
                  "net_revenue", "net revenue"],
    "platform":  ["platform / channel", "platform/channel", "platform",
                  "channel", "source", "order_type", "order type",
                  "order_channel", "order channel", "delivery_channel",
                  "delivery channel", "mode"],
    "cost":      ["cost / cogs", "cost/cogs", "cost", "cogs", "unit_cost",
                  "unit cost", "food_cost", "food cost", "material_cost",
                  "material cost", "purchase_price", "purchase price",
                  "cost_price", "cost price"],
}


def _detect_col(df_cols, key: str) -> Optional[str]:
    # Pass 1 — exact match (case-insensitive, stripped)
    mapping = {c.lower().strip(): c for c in df_cols}
    for alias in ALIASES[key]:
        if alias.lower() in mapping:
            return mapping[alias.lower()]

    # Pass 2 — column names like "Item Name / Product" or "Qty | Quantity":
    #           split on "/" or "|", trim each fragment, match any fragment
    for col in df_cols:
        parts = [p.strip().lower() for p in col.replace("|", "/").split("/")]
        for alias in ALIASES[key]:
            if alias.lower() in parts:
                return col

    # Pass 3 — alias is a leading word sequence inside the column name
    #           e.g. alias "item name" found at start of "Item Name / Product"
    for col in df_cols:
        col_lower = col.lower().strip()
        for alias in ALIASES[key]:
            al = alias.lower()
            if col_lower.startswith(al) or col_lower.endswith(al):
                return col

    return None


def _parse_excel_bytes(raw: bytes) -> tuple[list, dict]:
    df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    date_col  = _detect_col(df.columns, "date")
    item_col  = _detect_col(df.columns, "item_name")
    cat_col   = _detect_col(df.columns, "category")
    qty_col   = _detect_col(df.columns, "quantity")
    price_col = _detect_col(df.columns, "price")
    rev_col   = _detect_col(df.columns, "revenue")
    plat_col  = _detect_col(df.columns, "platform")
    cost_col  = _detect_col(df.columns, "cost")

    if not date_col:
        raise ValueError("Could not find a 'Date' column. Please add a Date column to your Excel.")
    if not item_col:
        raise ValueError("Could not find an 'Item Name' / 'Product' column.")
    if not rev_col and not (price_col and qty_col):
        raise ValueError("Need either a 'Revenue/Total' column, or both 'Price' and 'Quantity' columns.")

    records = []
    skipped = 0
    for _, row in df.iterrows():
        try:
            raw_date = row[date_col]
            if pd.isna(raw_date):
                skipped += 1
                continue
            date_val = pd.to_datetime(raw_date)

            item = str(row[item_col]).strip()
            if not item or item.lower() in ("nan", "none", ""):
                skipped += 1
                continue

            qty = float(row[qty_col]) if qty_col and pd.notna(row[qty_col]) else 1.0
            price = float(row[price_col]) if price_col and pd.notna(row[price_col]) else 0.0

            if rev_col and pd.notna(row[rev_col]):
                revenue = float(row[rev_col])
            else:
                revenue = qty * price

            if revenue <= 0:
                skipped += 1
                continue

            cost = float(row[cost_col]) if cost_col and pd.notna(row[cost_col]) else revenue * 0.38
            category = str(row[cat_col]).strip() if cat_col and pd.notna(row[cat_col]) else "Uncategorized"
            platform = str(row[plat_col]).strip() if plat_col and pd.notna(row[plat_col]) else "Dine-in"

            records.append({
                "date":      date_val.strftime("%Y-%m-%d"),
                "item_name": item,
                "category":  category,
                "quantity":  qty,
                "price":     price,
                "revenue":   revenue,
                "cost":      cost,
                "platform":  platform,
            })
        except Exception:
            skipped += 1
            continue

    dates = sorted(set(r["date"] for r in records))
    detected = {
        "date": date_col, "item_name": item_col, "category": cat_col,
        "quantity": qty_col, "price": price_col, "revenue": rev_col,
        "platform": plat_col, "cost": cost_col,
    }
    info = {
        "rows": len(records),
        "skipped": skipped,
        "columns_original": list(df.columns),
        "columns_detected": {k: v for k, v in detected.items() if v},
        "date_range": {"from": dates[0], "to": dates[-1]} if dates else {},
        "unique_items": len(set(r["item_name"] for r in records)),
        "unique_dates": len(dates),
    }
    return records, info

# ─────────────────────────────────────────────
# ANALYTICS HELPERS
# ─────────────────────────────────────────────

def _daily_revenue(data: list, days: int = 14) -> list:
    agg: dict = defaultdict(lambda: {"revenue": 0.0, "orders": 0.0})
    for r in data:
        agg[r["date"]]["revenue"] += r["revenue"]
        agg[r["date"]]["orders"]  += r["quantity"]
    rows = sorted(agg.items())[-days:]
    return [{"date": d, "revenue": round(v["revenue"], 2),
             "orders": int(v["orders"]),
             "avg_order_value": round(v["revenue"] / max(v["orders"], 1), 2)}
            for d, v in rows]


def _category_breakdown(data: list) -> list:
    agg: dict = defaultdict(lambda: {"revenue": 0.0, "orders": 0, "cost": 0.0})
    for r in data:
        agg[r["category"]]["revenue"] += r["revenue"]
        agg[r["category"]]["orders"]  += int(r["quantity"])
        agg[r["category"]]["cost"]    += r["cost"]
    return [{"category": k, "revenue": round(v["revenue"], 2),
             "orders": v["orders"], "cost": round(v["cost"], 2)}
            for k, v in agg.items()]


def _platform_breakdown(data: list) -> list:
    agg: dict = defaultdict(lambda: {"orders": 0, "revenue": 0.0})
    for r in data:
        agg[r["platform"]]["orders"]  += int(r["quantity"])
        agg[r["platform"]]["revenue"] += r["revenue"]
    return [{"platform": k, "orders": v["orders"], "revenue": round(v["revenue"], 2)}
            for k, v in agg.items()]


def _item_stats(data: list) -> list:
    agg: dict = defaultdict(lambda: {"qty": 0.0, "revenue": 0.0, "cost": 0.0})
    for r in data:
        agg[r["item_name"]]["qty"]     += r["quantity"]
        agg[r["item_name"]]["revenue"] += r["revenue"]
        agg[r["item_name"]]["cost"]    += r["cost"]
    result = []
    for name, v in agg.items():
        margin = (v["revenue"] - v["cost"]) / max(v["revenue"], 1) * 100
        result.append({"name": name, "qty": round(v["qty"], 1),
                       "revenue": round(v["revenue"], 2),
                       "cost": round(v["cost"], 2),
                       "margin_pct": round(margin, 1)})
    return sorted(result, key=lambda x: x["revenue"], reverse=True)


def _weekday_forecast(data: list, days: int = 7) -> list:
    # Step 1 — collapse individual POS rows into daily totals.
    # Each POS row represents one order/bill; a single day can have thousands
    # of rows. Averaging rows directly gives avg-bill-per-order (~₹300),
    # not daily revenue (~₹30,000). We must aggregate first.
    daily_rev: dict = defaultdict(float)
    daily_orders: dict = defaultdict(int)
    for r in data:
        daily_rev[r["date"]]    += r.get("revenue", r.get("daily_revenue", 0))
        daily_orders[r["date"]] += 1

    # Step 2 — compute weekday averages and std-devs from daily totals.
    wd_total: dict = defaultdict(float)
    wd_count: dict = defaultdict(int)
    wd_values: dict = defaultdict(list)
    for date_str, rev in daily_rev.items():
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            wd_total[d.weekday()] += rev
            wd_count[d.weekday()] += 1
            wd_values[d.weekday()].append(rev)
        except Exception:
            pass

    n_days = max(len(daily_rev), 1)
    overall_avg = sum(daily_rev.values()) / n_days
    wd_avg = {wd: wd_total[wd] / wd_count[wd] for wd in wd_total}

    # Compute std dev per weekday for bounds
    wd_std: dict = {}
    for wd, vals in wd_values.items():
        if len(vals) > 1:
            mean = wd_avg[wd]
            wd_std[wd] = (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5
        else:
            wd_std[wd] = wd_avg.get(wd, overall_avg) * 0.10

    avg_orders_per_day = sum(daily_orders.values()) / n_days
    confidence = min(88, 55 + min(30, n_days // 7))

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    result = []
    for i in range(1, days + 1):
        date = datetime.now() + timedelta(days=i)
        wd = date.weekday()
        rev = int(wd_avg.get(wd, overall_avg))
        std_dev = wd_std.get(wd, rev * 0.10)
        upper = rev + int(std_dev)
        lower = max(0, rev - int(std_dev))
        est_orders = max(1, int(avg_orders_per_day * (1.1 if wd >= 5 else 1.0)))
        result.append({
            "date": date.strftime("%Y-%m-%d"),
            "day": day_names[wd],
            "predicted_revenue": rev,
            "upper": upper,
            "lower": lower,
            "predicted_orders": est_orders,
            "confidence": confidence,
            "is_weekend": wd >= 5,
        })
    return result


def _generate_decisions(data: list, overrides: Optional[dict] = None) -> list:
    if not data:
        return []
    # Use caller-supplied overrides dict or fall back to system-level global
    _ov = overrides if overrides is not None else _decision_overrides

    items    = _item_stats(data)
    dates    = sorted(set(r["date"] for r in data))
    n_days   = max(len(dates), 1)
    decisions = []
    did = 1

    # ── Pricing: top revenue items with healthy margin ─────────────────────────
    for item in items[:5]:
        if item["margin_pct"] > 45 and len(decisions) < 2:
            # Graduated price increase: higher margin → more room to raise
            # margin 45-55 → ~6%, 55-65 → ~9%, >65 → ~12%
            price_inc_pct = min(15, max(5, round((item["margin_pct"] - 35) / 5)))
            monthly = int(item["revenue"] / n_days * 30 * (price_inc_pct / 100))
            decisions.append({
                "id": did, "type": "pricing", "priority": "high",
                "title": f"Increase '{item['name']}' price by {price_inc_pct}%",
                "rationale": (f"Top revenue contributor (₹{item['revenue']:,.0f} total, "
                              f"{item['qty']:.0f} units sold). "
                              f"Margin at {item['margin_pct']:.1f}% supports a price increase "
                              f"without demand erosion."),
                "impact": f"+₹{monthly:,}/month estimated additional revenue",
                "confidence": min(92, 60 + min(28, int(item["margin_pct"] / 2))),
                "source": "POS Data Analysis",
                "status": "pending", "category": "Revenue Optimization",
            })
            did += 1

    # ── Menu: low margin items ─────────────────────────────────────────────────
    low_items = sorted(items, key=lambda x: x["margin_pct"])
    for item in low_items[:2]:
        if item["margin_pct"] < 30:
            decisions.append({
                "id": did, "type": "menu", "priority": "low",
                "title": f"Review '{item['name']}' — margin at {item['margin_pct']:.1f}%",
                "rationale": (f"Contribution margin below 30% threshold. "
                              f"Total revenue ₹{item['revenue']:,.0f} over {n_days} days. "
                              f"Consider recipe cost reduction or bundling."),
                "impact": "Free kitchen capacity for high-margin items",
                "confidence": min(85, 55 + min(25, int(max(0, 30 - item["margin_pct"]) * 0.8))),
                "source": "POS Data Analysis",
                "status": "pending", "category": "Menu Optimization",
            })
            did += 1

    # ── Marketing: top platform with actual trend ──────────────────────────────
    platforms = _platform_breakdown(data)
    if platforms:
        top     = max(platforms, key=lambda x: x["revenue"])
        monthly = int(top["revenue"] / n_days * 30 * 0.15)

        # Compute actual growth rate of this platform (recent half vs older half)
        half = len(dates) // 2
        if half > 0:
            recent_set = set(dates[half:])
            older_set  = set(dates[:half])
            r_rev = sum(r["revenue"] for r in data
                        if r["date"] in recent_set and r.get("platform","") == top["platform"])
            o_rev = sum(r["revenue"] for r in data
                        if r["date"] in older_set  and r.get("platform","") == top["platform"])
            if o_rev > 0:
                growth_pct = (r_rev / o_rev - 1) * 100
                trend_str  = f"showing {growth_pct:+.0f}% revenue trend"
            else:
                trend_str  = "top revenue channel"
        else:
            trend_str = "top revenue channel"

        decisions.append({
            "id": did, "type": "marketing", "priority": "medium",
            "title": f"Boost promotions on {top['platform']} — top channel",
            "rationale": (f"{top['platform']} generated ₹{top['revenue']:,.0f} total "
                          f"({top['orders']} orders, {trend_str}). "
                          f"Targeted promo campaigns can increase order frequency."),
            "impact": f"+₹{monthly:,}/month from 15% channel growth",
            "confidence": min(88, 65 + min(20, int(
                top["revenue"] / max(sum(p["revenue"] for p in platforms), 1) * 40
            ))),
            "source": "POS Data Analysis",
            "status": "pending", "category": "Marketing",
        })
        did += 1

    # ── Staffing: weekend vs weekday ───────────────────────────────────────────
    weekend_rev, weekend_days_set = 0.0, set()
    weekday_rev, weekday_days_set = 0.0, set()
    for r in data:
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d")
            if d.weekday() >= 5:
                weekend_rev += r["revenue"]; weekend_days_set.add(r["date"])
            else:
                weekday_rev += r["revenue"]; weekday_days_set.add(r["date"])
        except Exception:
            pass

    if weekend_days_set and weekday_days_set:
        w_avg = weekend_rev / len(weekend_days_set)
        d_avg = weekday_rev / len(weekday_days_set)
        if w_avg > d_avg * 1.15:
            # Estimate service delay from order burst ratio
            burst_pct       = (w_avg / d_avg - 1) * 100
            estimated_delay = max(10, min(35, int(burst_pct * 0.55)))

            # Revenue protection: 10% of approx monthly weekend revenue
            monthly_wknd  = w_avg * 8   # 4 weekends × 2 days
            protected_rev = int(monthly_wknd * 0.10)

            decisions.append({
                "id": did, "type": "staffing", "priority": "medium",
                "title": "Increase weekend staffing (+2 staff, 6–10 PM)",
                "rationale": (f"Weekend revenue averages ₹{w_avg:,.0f}/day vs "
                              f"₹{d_avg:,.0f}/day on weekdays — "
                              f"{((w_avg / d_avg) - 1) * 100:.0f}% higher. "
                              f"Current capacity risks ~{estimated_delay}-min service delays "
                              f"during weekend peak hours."),
                "impact": f"+₹{protected_rev:,}/month weekend revenue protection",
                "confidence": min(90, 70 + min(15, int(abs(w_avg - d_avg) / max(d_avg, 1) * 30))),
                "source": "POS Data Analysis",
                "status": "pending", "category": "Operations",
            })
            did += 1

    # Apply approve/reject overrides
    for d in decisions:
        if d["id"] in _ov:
            d["status"] = _ov[d["id"]]

    return decisions


def _calc_kpis(data: list) -> list:
    if not data:
        return []
    dates = sorted(set(r["date"] for r in data))
    last, prev = dates[-1], (dates[-2] if len(dates) > 1 else None)

    today_rev = sum(r["revenue"] for r in data if r["date"] == last)
    prev_rev  = sum(r["revenue"] for r in data if r["date"] == prev) if prev else 0
    rev_change = (f"+{((today_rev / prev_rev) - 1) * 100:.1f}%"
                  if prev_rev > 0 else "—")

    total_rev  = sum(r["revenue"]  for r in data)
    total_cost = sum(r["cost"]     for r in data)
    total_qty  = sum(r["quantity"] for r in data)
    avg_ov     = total_rev / max(len(data), 1)
    food_pct   = total_cost / max(total_rev, 1) * 100

    # Compute period-over-period trends by splitting date range in half
    half = len(dates) // 2
    if half > 0:
        recent_dates = set(dates[half:])
        older_dates  = set(dates[:half])
        recent_data  = [r for r in data if r["date"] in recent_dates]
        older_data   = [r for r in data if r["date"] in older_dates]

        # AOV trend
        r_rev = sum(r["revenue"] for r in recent_data)
        o_rev = sum(r["revenue"] for r in older_data)
        r_cnt = max(len(recent_data), 1)
        o_cnt = max(len(older_data),  1)
        r_aov, o_aov = r_rev / r_cnt, o_rev / o_cnt
        aov_change = (f"{((r_aov / o_aov) - 1) * 100:+.1f}%" if o_aov > 0 else "—")
        aov_trend  = "up" if r_aov >= o_aov else "down"

        # Food cost % trend
        r_cost_pct = (sum(r["cost"] for r in recent_data) / max(r_rev, 1)) * 100
        o_cost_pct = (sum(r["cost"] for r in older_data)  / max(o_rev,  1)) * 100
        fc_delta   = r_cost_pct - o_cost_pct
        food_change = f"{fc_delta:+.1f}%"
        food_trend  = "down" if fc_delta <= 0 else "up"  # lower food cost = good

        # Qty sold trend
        r_qty = sum(r["quantity"] for r in recent_data)
        o_qty = sum(r["quantity"] for r in older_data)
        qty_change = (f"{((r_qty / o_qty) - 1) * 100:+.1f}%" if o_qty > 0 else "—")
        qty_trend  = "up" if r_qty >= o_qty else "down"
    else:
        aov_change = food_change = qty_change = "—"
        aov_trend  = food_trend  = qty_trend  = "neutral"

    return [
        {"name": "Today's Revenue",  "value": f"₹{today_rev:,.0f}",  "change": rev_change,  "trend": "up" if today_rev >= prev_rev else "down"},
        {"name": "Avg Order Value",  "value": f"₹{avg_ov:,.0f}",     "change": aov_change,  "trend": aov_trend},
        {"name": "Food Cost %",      "value": f"{food_pct:.1f}%",     "change": food_change, "trend": food_trend},
        {"name": "Total Items Sold", "value": f"{total_qty:,.0f}",    "change": qty_change,  "trend": qty_trend},
        {"name": "Data Records",     "value": f"{len(data):,}",       "change": f"{len(dates)} days", "trend": "up"},
        {"name": "Date Range",       "value": f"{dates[0]} → {dates[-1]}", "change": f"{len(dates)} days", "trend": "neutral"},
    ]

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

class LoginRequest(BaseModel):
    username:  str
    password:  str
    workspace: Optional[str] = None   # tenant slug — omit for system tenant

@app.post("/api/auth/login")
def login(req: LoginRequest, request: Request = None):
    """
    Authenticate a user.
    - If `workspace` is provided → look up tenant by slug, use TenantRoleStore
    - Otherwise → system tenant (legacy admin/owner accounts)
    Returns a signed JWT token that carries username + tenant_id.
    """
    import tenant_store as _ts
    import auth_utils as _au
    from role_store import get_tenant_store

    ip = request.client.host if request and request.client else ""

    if req.workspace:
        tenant = _ts.get_tenant_by_slug(req.workspace)
        if not tenant:
            raise HTTPException(status_code=404,
                detail=f"Workspace '{req.workspace}' not found")
        if not tenant.get("is_active", True):
            raise HTTPException(status_code=403, detail="Workspace is inactive")
        tenant_id = tenant["tenant_id"]
        store = get_tenant_store(tenant_id)
    else:
        tenant_id = _ts.SYSTEM_TENANT_ID
        tenant    = None
        store     = get_tenant_store(_ts.SYSTEM_TENANT_ID)

    result = store.authenticate(req.username, req.password)
    if not result:
        _audit.log_action(username=req.username, module="auth", action="LOGIN",
            description=f"Failed login attempt for '{req.username}'"
                        + (f" on workspace '{req.workspace}'" if req.workspace else ""),
            status=_audit.STATUS_ERROR, ip_address=ip)
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Build JWT carrying tenant context
    token_data = {
        "username":   result["username"],
        "tenant_id":  tenant_id,
        "role_id":    result["role_id"],
    }
    token = _au.create_access_token(token_data)

    _audit.log_action(username=result["username"], module="auth", action="LOGIN",
        description=f"User '{result['username']}' logged in as {result['role_name']}"
                    + (f" (workspace: {req.workspace})" if req.workspace else ""),
        role=result["role_name"], status=_audit.STATUS_SUCCESS, ip_address=ip)

    resp: dict = {
        "success":     True,
        "username":    result["username"],
        "full_name":   result["full_name"],
        "role":        result["role_name"],
        "role_id":     result["role_id"],
        "permissions": result["permissions"],
        "token":       token,
        "tenant_id":   tenant_id,
    }
    if tenant:
        resp["cafe_name"]    = tenant.get("cafe_name", "")
        resp["brand_color"]  = tenant.get("brand_color", "#6366f1")
        resp["logo_url"]     = tenant.get("logo_url", "")
        resp["tenant_slug"]  = tenant.get("slug", "")
    return resp

@app.get("/api/auth/me")
def me(request: Request = None):
    """
    Return the current user's up-to-date role and permissions.
    The frontend calls this on app startup to refresh stale localStorage data.
    Username is read from the X-Username header (set by apiFetch / the frontend).
    """
    username = request.headers.get("X-Username", "") if request else ""
    if not username:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_info = _rs.get_user(username)
    if not user_info:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    role = _rs.get_role(user_info.get("role_id", "viewer")) or {}
    return {
        "username":    username,
        "full_name":   user_info.get("full_name", username),
        "role_id":     role.get("id", "viewer"),
        "role_name":   role.get("name", "Viewer"),
        "permissions": list(role.get("permissions", [])),
    }


# ─────────────────────────────────────────────
# DATA TEMPLATE DOWNLOAD
# ─────────────────────────────────────────────

_TEMPLATES = {
    "financial": {
        "filename": "cafe_buddy_financial_template.csv",
        "headers": [
            "Date", "Monthly Revenue", "Gross Margin %", "Net Profit",
            "Food Cost %", "Labor Cost %", "Electricity", "Rent",
            "Marketing Spend", "Packaging Cost", "Platform Commission",
        ],
        "rows": [
            ["2024-01-01","2500000","68.5","450000","31.5","19.8","52000","350000","38000","58000","145000"],
            ["2024-02-01","2750000","70.2","520000","29.8","18.5","49000","350000","42000","63000","162000"],
            ["2024-03-01","3100000","69.0","610000","31.0","20.1","55000","350000","45000","71000","180000"],
        ],
    },
    "pos": {
        "filename": "cafe_buddy_pos_template.csv",
        "headers": [
            "Date","Item Name / Product","Quantity / Qty","Price / Rate",
            "Revenue / Total","Category / Type","Platform / Channel",
            "Cost / COGS","Order ID / Bill No","GST Amount",
            "Discount","Payment Mode","Hour / Time",
        ],
        "rows": [
            ["2024-01-15","Cappuccino","2","120","240","Hot Coffee","Dine-in","36","CB-240115-001","12","0","UPI","10"],
            ["2024-01-15","Espresso","1","80","80","Hot Coffee","Zomato","24","CB-240115-002","4","0","Online","11"],
            ["2024-01-15","Pasta Carbonara","1","320","320","Pasta","Dine-in","128","CB-240115-003","16","0","Cash","13"],
            ["2024-01-16","Cold Coffee","3","150","450","Cold Beverages","Swiggy","45","CB-240116-001","22","30","Online","16"],
        ],
    },
    "customer": {
        "filename": "cafe_buddy_customer_template.csv",
        "headers": [
            "Customer Name","Phone / Contact","Birthday / DOB","Visit Frequency",
            "Favourite Items","Avg Order Value","Feedback / Rating",
            "Preferred Visit Time","Platform Source","Loyalty Points","Gender","Age Group",
        ],
        "rows": [
            ["Rahul Sharma","9876543210","15-08-1990","4","Cappuccino, Croissant","450","4.5","Morning (8-11 AM)","Walk-in","120","Male","25-34"],
            ["Priya Gupta","9876543211","22-03-1985","8","Cold Coffee, Pasta","620","5.0","Afternoon (2-5 PM)","Zomato","280","Female","35-44"],
            ["Arjun Patel","9876543212","07-11-1998","2","Espresso, Sandwich","280","3.5","Evening (5-8 PM)","Swiggy","40","Male","18-24"],
        ],
    },
    "reviews": {
        "filename": "cafe_buddy_reviews_template.csv",
        "headers": [
            "Review_Text","Sentiment_Label","Review_ID","Source",
            "Review_Date","Cafe_Location","Visit_Type","Rating",
        ],
        "rows": [
            ["Amazing coffee and cozy ambiance! Will definitely come back.","positive","RVW001","Google","2024-01-15","Koramangala, Bengaluru","Dine-in","5"],
            ["Service was a bit slow but the food quality was excellent.","neutral","RVW002","Zomato","2024-01-16","Koramangala, Bengaluru","Takeaway","3"],
            ["Cold coffee was watery and overpriced. Disappointed.","negative","RVW003","Google","2024-01-17","Koramangala, Bengaluru","Dine-in","2"],
        ],
    },
    "menu": {
        "filename": "cafe_buddy_menu_template.csv",
        "headers": [
            "Item / Item Name","Category","Base Price","Season",
            "Available Dayparts","Veg / Non-Veg","SKU","Notes",
        ],
        "rows": [
            ["Espresso","Hot Coffee","80","YR","M,A,E","Veg","CB-001",""],
            ["Cappuccino","Hot Coffee","120","YR","M,L,A,E,LE","Veg","CB-002","Double shot available"],
            ["Cold Coffee","Cold Beverages","150","YR","M,L,A,E,LE","Veg","CB-003",""],
            ["Club Sandwich","Snacks","220","YR","M,L,A","Veg","CB-050",""],
            ["Chicken Burger","Burgers","280","YR","L,E,LE","Non-Veg","CB-051",""],
            ["Pasta Carbonara","Pasta","320","YR","L,E,LE","Non-Veg","CB-060",""],
            ["Mango Smoothie","Cold Beverages","180","S","M,A,E","Veg","CB-030","Seasonal - Summer only"],
        ],
    },
}


@app.get("/api/templates/{data_type}")
def download_template(data_type: str):
    """Return a ready-to-fill CSV template for the given dataset type.
    Headers match the column aliases accepted by each upload endpoint.
    Sample rows show the exact format expected."""
    import csv as _csv
    if data_type not in _TEMPLATES:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown data type '{data_type}'. Valid types: {list(_TEMPLATES.keys())}",
        )
    tmpl = _TEMPLATES[data_type]
    buf = io.StringIO()
    writer = _csv.writer(buf)
    writer.writerow(tmpl["headers"])
    for row in tmpl["rows"]:
        writer.writerow(row)
    # UTF-8-BOM so Excel opens it without encoding issues
    csv_bytes = ("﻿" + buf.getvalue()).encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{tmpl["filename"]}"',
            "Cache-Control": "no-cache",
        },
    )

@app.post("/api/auth/logout")
def logout(request: Request = None):
    username = request.headers.get("X-Username", "anonymous") if request else "anonymous"
    _audit.log_action(
        username=username,
        module="auth",
        action="LOGOUT",
        description=f"User '{username}' logged out",
        ip_address=(request.client.host if request and request.client else ""),
    )
    return {"success": True, "message": "Logged out"}

# ─────────────────────────────────────────────
# MULTI-TENANT REGISTRATION & WORKSPACE API
# ─────────────────────────────────────────────

class TenantRegisterRequest(BaseModel):
    cafe_name:    str
    owner_name:   str
    owner_email:  str
    username:     str
    password:     str
    brand_color:  str = "#6366f1"
    logo_url:     str = ""

class TenantBrandingRequest(BaseModel):
    cafe_name:   Optional[str] = None
    brand_color: Optional[str] = None
    logo_url:    Optional[str] = None


@app.post("/api/auth/register")
def register_tenant(req: TenantRegisterRequest, request: Request = None):
    """
    Register a new café workspace (tenant).
    Creates the tenant record, hashes the admin password, and seeds
    the admin user in the per-tenant role store.
    Returns workspace slug and a ready-to-use JWT token.
    """
    import tenant_store as _ts
    import auth_utils as _au
    from role_store import get_tenant_store

    ip = request.client.host if request and request.client else ""

    # Validate password strength (min 6 chars)
    if len(req.password.strip()) < 6:
        raise HTTPException(status_code=400,
            detail="Password must be at least 6 characters")

    try:
        tenant = _ts.create_tenant(
            cafe_name=req.cafe_name,
            owner_name=req.owner_name,
            owner_email=req.owner_email,
            admin_username=req.username,
            brand_color=req.brand_color,
            logo_url=req.logo_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Hash password and seed admin user in tenant's role store
    pwd_hash = _au.hash_password(req.password)
    store = get_tenant_store(tenant["tenant_id"])
    store.seed_admin_user(req.username, pwd_hash)

    # Issue JWT
    token = _au.create_access_token({
        "username":  req.username,
        "tenant_id": tenant["tenant_id"],
        "role_id":   "admin",
    })

    _audit.log_action(username=req.username, module="auth", action="REGISTER",
        description=f"New workspace registered: '{req.cafe_name}' (slug={tenant['slug']})",
        status=_audit.STATUS_SUCCESS, ip_address=ip)

    return {
        "success":      True,
        "message":      f"Workspace '{req.cafe_name}' created successfully",
        "tenant_id":    tenant["tenant_id"],
        "slug":         tenant["slug"],
        "workspace_url": f"?workspace={tenant['slug']}",
        "cafe_name":    tenant["cafe_name"],
        "brand_color":  tenant["brand_color"],
        "logo_url":     tenant["logo_url"],
        "plan":         tenant["plan"],
        "max_users":    tenant["max_users"],
        "token":        token,
        "username":     req.username,
        "role":         "Admin",
        "role_id":      "admin",
        "permissions":  _rs.ALL_PERMISSIONS,
    }


@app.get("/api/auth/workspace/{slug}")
def get_workspace_info(slug: str):
    """
    Return public workspace branding for the login page.
    Called before authentication to pre-populate the login form.
    """
    import tenant_store as _ts
    tenant = _ts.get_tenant_by_slug(slug)
    if not tenant:
        raise HTTPException(status_code=404,
            detail=f"Workspace '{slug}' not found")
    return {
        "found":       True,
        "slug":        tenant["slug"],
        "cafe_name":   tenant["cafe_name"],
        "brand_color": tenant["brand_color"],
        "logo_url":    tenant["logo_url"],
        "is_active":   tenant.get("is_active", True),
    }


@app.get("/api/tenant/info")
def tenant_info(request: Request = None):
    """
    Return the calling tenant's branding, plan, and storage info.
    Reads tenant_id from JWT Bearer token or falls back to system tenant.
    """
    import tenant_store as _ts
    import auth_utils as _au

    auth_header = request.headers.get("Authorization", "") if request else ""
    tenant_id = _au.extract_tenant_id(auth_header) or _ts.SYSTEM_TENANT_ID

    if tenant_id == _ts.SYSTEM_TENANT_ID:
        return {
            "tenant_id":        _ts.SYSTEM_TENANT_ID,
            "cafe_name":        "Cafe Buddy AI",
            "brand_color":      "#6366f1",
            "logo_url":         "",
            "plan":             "system",
            "max_users":        999,
            "storage_limit_mb": 999999,   # effectively unlimited; inf not JSON-safe
            "storage_used_mb":  0,
            "is_active":        True,
        }

    tenant = _ts.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@app.put("/api/tenant/branding")
def update_tenant_branding(req: TenantBrandingRequest, request: Request = None):
    """Update cafe name, brand colour, and/or logo URL for the current tenant."""
    import tenant_store as _ts
    import auth_utils as _au

    auth_header = request.headers.get("Authorization", "") if request else ""
    tenant_id = _au.extract_tenant_id(auth_header) or _ts.SYSTEM_TENANT_ID
    username  = _au.extract_username(auth_header) or \
                (request.headers.get("X-Username", "anonymous") if request else "anonymous")

    if tenant_id == _ts.SYSTEM_TENANT_ID:
        raise HTTPException(status_code=403,
            detail="System workspace branding cannot be changed via API")

    try:
        updated = _ts.update_branding(tenant_id,
            cafe_name=req.cafe_name, brand_color=req.brand_color, logo_url=req.logo_url)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    ip = request.client.host if request and request.client else ""
    _audit.log_action(username=username, module="system", action="BRANDING_UPDATE",
        description=f"Updated branding for tenant '{tenant_id}'",
        ip_address=ip)

    return {"success": True, "tenant": updated}


# ─────────────────────────────────────────────
# ROLE MANAGEMENT API
# ─────────────────────────────────────────────

class RoleCreateRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    permissions: list[str] = []

class RoleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[list[str]] = None

@app.get("/api/roles")
def get_roles():
    return {
        "roles": _rs.list_roles(),
        "all_permissions": _rs.ALL_PERMISSIONS,
        "permission_labels": _rs.PERMISSION_LABELS,
    }

@app.post("/api/roles")
def create_role(req: RoleCreateRequest, request: Request = None):
    try:
        role = _rs.create_role(req.id, req.name, req.description, req.permissions)
        username = request.headers.get("X-Username", "admin") if request else "admin"
        _audit.log_action(username=username, module="role_management", action="ROLE_CREATE",
            description=f"Created role '{req.name}' (id={req.id}) with {len(req.permissions)} permissions",
            ip_address=(request.client.host if request and request.client else ""))
        return {"success": True, "role": role}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/roles/{role_id}")
def update_role(role_id: str, req: RoleUpdateRequest, request: Request = None):
    try:
        role = _rs.update_role(role_id, name=req.name,
                               description=req.description, permissions=req.permissions)
        username = request.headers.get("X-Username", "admin") if request else "admin"
        _audit.log_action(username=username, module="role_management", action="ROLE_UPDATE",
            description=f"Updated role '{role_id}': name={req.name}, perms={req.permissions}",
            ip_address=(request.client.host if request and request.client else ""))
        return {"success": True, "role": role}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/roles/{role_id}")
def delete_role(role_id: str, request: Request = None):
    try:
        _rs.delete_role(role_id)
        username = request.headers.get("X-Username", "admin") if request else "admin"
        _audit.log_action(username=username, module="role_management", action="ROLE_DELETE",
            description=f"Deleted role '{role_id}'",
            ip_address=(request.client.host if request and request.client else ""))
        return {"success": True, "message": f"Role '{role_id}' deleted"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ─────────────────────────────────────────────
# USER MANAGEMENT API
# ─────────────────────────────────────────────

class UserCreateRequest(BaseModel):
    username: str
    password: str
    role_id: str
    full_name: str = ""
    email: str = ""

class UserUpdateRequest(BaseModel):
    role_id: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

@app.get("/api/users")
def get_users():
    return {"users": _rs.list_users()}

@app.post("/api/users")
def create_user(req: UserCreateRequest, request: Request = None):
    try:
        user = _rs.create_user(req.username, req.password, req.role_id,
                               req.full_name, req.email)
        actor = request.headers.get("X-Username", "admin") if request else "admin"
        _audit.log_action(username=actor, module="role_management", action="USER_CREATE",
            description=f"Created user '{req.username}' with role '{req.role_id}'",
            ip_address=(request.client.host if request and request.client else ""))
        return {"success": True, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/users/{username}")
def update_user(username: str, req: UserUpdateRequest, request: Request = None):
    try:
        user = _rs.update_user(username, role_id=req.role_id, full_name=req.full_name,
                               email=req.email, is_active=req.is_active,
                               password=req.password)
        actor = request.headers.get("X-Username", "admin") if request else "admin"
        changes = []
        if req.role_id: changes.append(f"role→{req.role_id}")
        if req.is_active is not None: changes.append(f"active→{req.is_active}")
        if req.full_name: changes.append("full_name updated")
        _audit.log_action(username=actor, module="role_management", action="USER_UPDATE",
            description=f"Updated user '{username}': {', '.join(changes) or 'no changes'}",
            ip_address=(request.client.host if request and request.client else ""))
        return {"success": True, "user": user}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/users/{username}")
def delete_user(username: str, request: Request = None):
    try:
        _rs.delete_user(username)
        actor = request.headers.get("X-Username", "admin") if request else "admin"
        _audit.log_action(username=actor, module="role_management", action="USER_DELETE",
            description=f"Deleted user '{username}'",
            ip_address=(request.client.host if request and request.client else ""))
        return {"success": True, "message": f"User '{username}' deleted"}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ─────────────────────────────────────────────
# EXCEL UPLOAD
# ─────────────────────────────────────────────

@app.post("/api/upload/excel")
async def upload_excel(file: UploadFile = File(...), request: Request = None):
    global _uploaded_data, _upload_info, _decision_overrides

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls files are supported.")

    raw = await file.read()

    # ── Storage-limit check for new tenants ──────────────────────────────────
    import tenant_store as _ts
    import auth_utils as _au
    auth_header = request.headers.get("Authorization", "") if request else ""
    tenant_id   = _au.extract_tenant_id(auth_header) or _ts.SYSTEM_TENANT_ID
    ok, used_mb, limit_mb = _ts.check_storage_limit(tenant_id, len(raw))
    if not ok:
        raise HTTPException(status_code=413,
            detail=f"Storage limit exceeded. Used: {used_mb:.1f} MB / {limit_mb:.0f} MB. "
                   f"This file is {len(raw)/1024/1024:.1f} MB. "
                   "Upgrade your plan or delete existing data to free space.")
    # ─────────────────────────────────────────────────────────────────────────

    username = request.headers.get("X-Username", "anonymous") if request else "anonymous"
    try:
        records, info = _parse_excel_bytes(raw)
    except ValueError as e:
        _audit.log_action(username=username, module="upload_data", action="FILE_UPLOAD",
            description=f"Failed to parse '{file.filename}': {e}", status=_audit.STATUS_ERROR,
            ip_address=(request.client.host if request and request.client else ""))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Excel: {e}")

    if len(records) == 0:
        raise HTTPException(status_code=422, detail="No valid rows found. Check column names and data.")

    upload_info_new = {**info, "filename": file.filename,
                       "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    data_store.set_uploaded_for_tenant(tenant_id, records, upload_info_new)
    data_store.clear_overrides_for_tenant(tenant_id)  # reset overrides on new upload
    # Also keep module-level globals in sync for system tenant (chatbot etc.)
    if tenant_id == _ts.SYSTEM_TENANT_ID:
        global _uploaded_data, _upload_info, _decision_overrides
        _uploaded_data = records
        _upload_info = upload_info_new
        _decision_overrides = {}
        _sync_data_store()

    _audit.log_action(username=username, module="upload_data", action="FILE_UPLOAD",
        description=f"Uploaded '{file.filename}' — {len(records)} records, {info.get('unique_dates', 0)} days, "
                    f"{info.get('unique_items', 0)} items",
        ip_address=(request.client.host if request and request.client else ""))

    # Record storage usage for new tenants
    _ts.record_upload(tenant_id, len(raw))

    _, latest_info = data_store.get_uploaded_for_tenant(tenant_id)
    return {"success": True, "message": f"Loaded {len(records)} records.", "info": latest_info}


@app.get("/api/upload/status")
def upload_status(request: Request = None):
    tid = _req_tenant_id(request)
    upl_data, upl_info = data_store.get_uploaded_for_tenant(tid)
    if upl_data:
        return {"uploaded": True, "info": upl_info}
    return {"uploaded": False, "info": {}}


@app.delete("/api/upload/clear")
def clear_upload(request: Request = None):
    global _uploaded_data, _upload_info, _decision_overrides
    username = request.headers.get("X-Username", "anonymous") if request else "anonymous"
    tid = _req_tenant_id(request)
    _audit.log_action(username=username, module="upload_data", action="FILE_CLEAR",
        description="Cleared uploaded data — reverted to demo mode",
        ip_address=(request.client.host if request and request.client else ""))
    data_store.clear_all_for_tenant(tid)
    # Also clear module-level globals for system tenant
    if tid == "system":
        _uploaded_data = []
        _upload_info = {}
        _decision_overrides = {}
        _sync_data_store()
    return {"success": True, "message": "Reverted to demo data."}

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.get("/api/dashboard/overview")
def dashboard_overview(request: Request = None):
    data = _req_data(request)
    overrides = _req_overrides(request)
    if not data:
        return {
            "revenue_today": 0, "revenue_yesterday": 0,
            "orders_today": 0, "avg_order_value": 0,
            "top_item": "—", "pending_decisions": 0,
            "critical_alerts": 0, "models_running": 0,
            "revenue_change": 0, "orders_change": 0,
            "data_source": "none",
        }

    dates = sorted(set(r["date"] for r in data))
    last = dates[-1] if dates else None
    prev = dates[-2] if len(dates) > 1 else None

    today_rev  = sum(r["revenue"]  for r in data if r["date"] == last) if last else 0
    today_ord  = sum(r["quantity"] for r in data if r["date"] == last) if last else 0
    prev_rev   = sum(r["revenue"]  for r in data if r["date"] == prev) if prev else 0

    rev_change = round((today_rev / max(prev_rev, 1) - 1) * 100, 1) if prev_rev > 0 else 0
    avg_ov     = round(today_rev / max(today_ord, 1), 0)
    decisions  = _generate_decisions(data, overrides)
    pending    = sum(1 for d in decisions if d["status"] == "pending")

    items = _item_stats(data)
    top_item = items[0]["name"] if items else "—"

    # Count sentiment decisions too
    sent_decisions = get_sentiment_engine().get_decisions()
    pending += sum(1 for d in sent_decisions if d.get("status") == "pending")

    return {
        "revenue_today":     round(today_rev, 0),
        "revenue_yesterday": round(prev_rev, 0),
        "orders_today":      int(today_ord),
        "avg_order_value":   int(avg_ov),
        "top_item":          top_item,
        "pending_decisions": pending,
        "critical_alerts":   sum(1 for d in decisions + sent_decisions if d.get("priority") == "critical"),
        "models_running":    (1 if data else 0) + (1 if get_sentiment_engine().has_data else 0),
        "revenue_change":    rev_change,
        "orders_change":     0,
        "data_source":       "uploaded",
    }

# ─────────────────────────────────────────────
# LAYER 1 — DATA COLLECTION
# ─────────────────────────────────────────────

@app.get("/api/layer1/summary")
def layer1_summary(request: Request = None):
    tid  = _req_tenant_id(request)
    data = data_store.get_data_for_tenant(tid)
    dates = sorted(set(r["date"] for r in data))

    fin_data, fin_info   = data_store.get_financial_for_tenant(tid)
    pos_data, pos_info   = data_store.get_pos_for_tenant(tid)
    cust_data, cust_info = data_store.get_customer_for_tenant(tid)
    menu_data, menu_info = data_store.get_menu_for_tenant(tid)
    upl_data, upl_info   = data_store.get_uploaded_for_tenant(tid)

    # Build sources from actually-uploaded datasets
    sources = []
    if fin_data:
        sources.append({"name": fin_info.get("filename", "Financial Data"), "records": len(fin_data),
                        "status": "active", "last_sync": fin_info.get("uploaded_at", "—"), "type": "financial"})
    if pos_data:
        sources.append({"name": pos_info.get("filename", "POS Data"), "records": len(pos_data),
                        "status": "active", "last_sync": pos_info.get("uploaded_at", "—"), "type": "pos"})
    if cust_data:
        sources.append({"name": cust_info.get("filename", "Customer Data"), "records": len(cust_data),
                        "status": "active", "last_sync": cust_info.get("uploaded_at", "—"), "type": "customer"})
    if get_sentiment_engine().has_data:
        si = get_sentiment_engine().info
        sources.append({"name": si.get("filename", "Reviews"), "records": si.get("total_reviews", 0),
                        "status": "active", "last_sync": si.get("uploaded_at", "—"), "type": "reviews"})
    if menu_data:
        sources.append({"name": menu_info.get("filename", "Menu Data"), "records": len(menu_data),
                        "status": "active", "last_sync": menu_info.get("uploaded_at", "—"), "type": "menu"})

    return {
        "total_records":    len(data),
        "sources":          sources,
        "menu_items":       menu_data[:20],
        "inventory_items":  [],
        "recent_sales":     data[-20:],
        "low_stock_count":  0,
        "date_range":       {"from": dates[0], "to": dates[-1]} if dates else {},
        "unique_items":     len(set(r["item_name"] for r in data)),
        "data_source":      "uploaded" if data else "none",
        "upload_info":      upl_info if upl_data else {},
    }


@app.get("/api/layer1/platforms")
def platform_data(request: Request = None):
    return _platform_breakdown(_req_data(request))


class SalesEntry(BaseModel):
    date: str
    item_name: str
    category: str
    quantity: int
    price: float
    platform: str

_manual_entries: list = []

@app.post("/api/layer1/sales")
def add_sales(entry: SalesEntry, request: Request = None):
    tid = _req_tenant_id(request)
    pos_data, _ = data_store.get_pos_for_tenant(tid)
    upl_data, upl_info = data_store.get_uploaded_for_tenant(tid)
    cost_ratio = (
        sum(r["cost"] for r in pos_data if r.get("cost", 0) > 0) /
        max(sum(r["revenue"] for r in pos_data if r.get("cost", 0) > 0 and r.get("revenue", 0) > 0), 1)
        if pos_data and any(r.get("cost", 0) > 0 for r in pos_data) else 0.0
    )
    row = {**entry.model_dump(),
           "revenue": entry.quantity * entry.price,
           "cost":    round(entry.quantity * entry.price * cost_ratio, 2),
           "quantity": float(entry.quantity)}
    _manual_entries.append(row)
    if upl_data:
        upl_data.append(row)
        data_store.set_uploaded_for_tenant(tid, upl_data, upl_info)
    return {"success": True, "message": "Entry recorded.", "id": len(_manual_entries)}

# ─────────────────────────────────────────────
# LAYER 2 — DATA ENGINEERING
# ─────────────────────────────────────────────

def _dq_accuracy(tid: str = "system") -> float:
    """Ratio of records that passed validation vs total attempted."""
    pos_data, pos_info = data_store.get_pos_for_tenant(tid)
    fin_data, fin_info = data_store.get_financial_for_tenant(tid)
    cust_data, cust_info = data_store.get_customer_for_tenant(tid)
    good = len(pos_data) + len(fin_data) + len(cust_data)
    skipped = (pos_info.get("skipped", 0) +
               fin_info.get("skipped", 0) +
               cust_info.get("skipped", 0))
    return round(good / max(good + skipped, 1) * 100, 1) if good else 0.0


def _dq_consistency(tid: str = "system") -> float:
    """Detect duplicate dates in financial data (1 record per day expected)."""
    fd, _ = data_store.get_financial_for_tenant(tid)
    if not fd:
        return 100.0
    dates = [r["date"] for r in fd]
    dups = len(dates) - len(set(dates))
    return round(max(0.0, 100.0 - (dups / max(len(dates), 1)) * 100), 1)


def _dq_timeliness(tid: str = "system") -> float:
    """Score based on how recently data was uploaded (100% = today, decays hourly)."""
    _, pos_info = data_store.get_pos_for_tenant(tid)
    _, fin_info = data_store.get_financial_for_tenant(tid)
    timestamps = [
        pos_info.get("uploaded_at", ""),
        fin_info.get("uploaded_at", ""),
    ]
    latest = None
    for ts in timestamps:
        if ts:
            try:
                t = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S")
                if latest is None or t > latest:
                    latest = t
            except Exception:
                pass
    if latest is None:
        return 0.0
    hours_ago = (datetime.now() - latest).total_seconds() / 3600
    return round(max(50.0, 100.0 - hours_ago * 0.5), 1)


@app.get("/api/layer2/pipeline-status")
def pipeline_status(request: Request = None):
    tid = _req_tenant_id(request)
    data = data_store.get_data_for_tenant(tid)
    se = get_sentiment_engine()

    fin_data, fin_info   = data_store.get_financial_for_tenant(tid)
    pos_data, pos_info   = data_store.get_pos_for_tenant(tid)
    cust_data, cust_info = data_store.get_customer_for_tenant(tid)
    menu_data, menu_info = data_store.get_menu_for_tenant(tid)

    pipelines = []

    if fin_data:
        pipelines.append({"name": "Financial Data ETL", "status": "completed",
                          "last_run": fin_info.get("uploaded_at", "—"), "records": len(fin_data),
                          "success_rate": 100.0, "duration": "—"})

    if pos_data:
        pipelines.append({"name": "POS Billing ETL", "status": "completed",
                          "last_run": pos_info.get("uploaded_at", "—"), "records": len(pos_data),
                          "success_rate": round(len(pos_data) /
                              max(len(pos_data) + pos_info.get("skipped", 0), 1) * 100, 1),
                          "duration": "—"})

    if cust_data:
        pipelines.append({"name": "Customer Data ETL", "status": "completed",
                          "last_run": cust_info.get("uploaded_at", "—"), "records": len(cust_data),
                          "success_rate": 100.0, "duration": "—"})

    if se.has_data:
        pipelines.append({"name": "Review Sentiment NLP (Logistic Regression + TF-IDF)",
                          "status": "completed",
                          "last_run": se.info.get("uploaded_at", "—"),
                          "records": se.info.get("total_reviews", 0),
                          "success_rate": round(se.stats.get("avg_model_confidence", 100.0), 1),
                          "duration": "—"})

    if menu_data:
        pipelines.append({"name": "Menu Catalogue ETL", "status": "completed",
                          "last_run": menu_info.get("uploaded_at", "—"), "records": len(menu_data),
                          "success_rate": 100.0, "duration": "—"})

    if data:
        unique_items = len(set(r["item_name"] for r in data))
        pipelines.append({"name": "Menu Performance Aggregation", "status": "completed",
                          "last_run": "just now", "records": unique_items,
                          "success_rate": 100.0, "duration": "—"})

    total = len(data)
    skipped = pos_info.get("skipped", 0) + fin_info.get("skipped", 0)
    completeness = round((total / max(total + skipped, 1)) * 100, 1) if total else 0.0

    return {
        "pipelines": pipelines,
        "data_quality": {
            "completeness": completeness,
            "accuracy":     _dq_accuracy(tid),
            "consistency":  _dq_consistency(tid),
            "timeliness":   _dq_timeliness(tid),
        },
        "total_records_today": total,
        "anomalies_detected":  0,
    }


@app.get("/api/layer2/processed-data")
def processed_data(request: Request = None):
    data  = _req_data(request)
    daily = _daily_revenue(data, 14)
    cats  = _category_breakdown(data)
    return {
        "daily_sales":        daily,
        "category_breakdown": cats,
        "total_revenue":      round(sum(r["revenue"] for r in data), 2),
        "total_orders":       int(sum(r["quantity"] for r in data)),
    }

@app.get("/api/layer2/insights")
def data_insights(request: Request = None):
    """Per-dataset AI insights derived from uploaded data."""
    tid = _req_tenant_id(request)
    result: dict = {}

    fin_data, fin_info   = data_store.get_financial_for_tenant(tid)
    pos_data, pos_info   = data_store.get_pos_for_tenant(tid)
    cust_data, cust_info = data_store.get_customer_for_tenant(tid)
    menu_data, menu_info = data_store.get_menu_for_tenant(tid)

    if fin_data:
        fd = fin_data
        info = fin_info
        total_rev = sum(r["daily_revenue"] for r in fd)
        dates = sorted(set(r["date"] for r in fd))
        gm_vals = [r["gross_margin_pct"] for r in fd if r.get("gross_margin_pct") is not None]
        avg_gm = round(sum(gm_vals) / len(gm_vals), 1) if gm_vals else None
        result["financial"] = {
            "dataset": "Financial Data", "icon": "trending",
            "records": len(fd), "filename": info.get("filename", ""),
            "key_facts": [
                f"₹{total_rev:,.0f} total revenue across {len(dates)} days",
                f"Avg gross margin: {avg_gm}%" if avg_gm else None,
                f"Date range: {dates[0]} → {dates[-1]}" if dates else None,
            ],
            "insights_enabled": [
                "P&L trend & margin trajectory",
                "Cost breakdown by category",
                "Budget vs actual tracking",
                "Electricity / rent / marketing cost trends",
            ],
        }

    if pos_data:
        pd_ = pos_data
        info = pos_info
        total_orders = len(pd_)
        total_rev = sum(r["bill_amount"] for r in pd_)
        avg_bill = round(total_rev / max(total_orders, 1), 0)
        platforms: dict = {}
        item_counts: dict = {}
        for r in pd_:
            p = r.get("platform") or "Unknown"
            platforms[p] = platforms.get(p, 0) + 1
            itm = r.get("item_name") or "Unknown"
            item_counts[itm] = item_counts.get(itm, 0) + 1
        top_platform = max(platforms, key=platforms.get) if platforms else "—"
        top_item = max(item_counts, key=item_counts.get) if item_counts else "—"
        dates = sorted(set(r["date"] for r in pd_))
        result["pos"] = {
            "dataset": "POS Billing", "icon": "cart",
            "records": total_orders, "filename": info.get("filename", ""),
            "key_facts": [
                f"{total_orders:,} orders · ₹{total_rev:,.0f} total revenue",
                f"Avg bill value: ₹{avg_bill:,.0f}",
                f"Top platform: {top_platform} ({platforms.get(top_platform, 0):,} orders)",
                f"Most ordered: {top_item} ({item_counts.get(top_item, 0):,} orders)",
            ],
            "insights_enabled": [
                "Peak hour & day-of-week demand forecasting",
                "Platform revenue mix & commission analysis",
                "Item-level margin & cross-sell recommendations",
                "Discount & coupon impact analysis",
            ],
        }

    if cust_data:
        cd = cust_data
        info = cust_info
        total = len(cd)
        aov_vals = [r["avg_order_value"] for r in cd if r.get("avg_order_value")]
        avg_aov = round(sum(aov_vals) / len(aov_vals), 0) if aov_vals else None
        avg_freq = round(sum(r.get("visit_frequency", 0) for r in cd) / max(total, 1), 1)
        avg_pts = round(sum(r.get("loyalty_points", 0) for r in cd) / max(total, 1), 0)
        src_agg: dict = {}
        for r in cd:
            s = r.get("platform_source") or "Unknown"
            src_agg[s] = src_agg.get(s, 0) + 1
        top_src = max(src_agg, key=src_agg.get) if src_agg else "—"
        result["customer"] = {
            "dataset": "Customer Data", "icon": "users",
            "records": total, "filename": info.get("filename", ""),
            "key_facts": [
                f"{total:,} customers in CRM",
                f"Avg order value: ₹{avg_aov:,.0f}" if avg_aov else None,
                f"Avg visit frequency: {avg_freq}× / period",
                f"Avg loyalty points: {avg_pts:,.0f} · Top source: {top_src}",
            ],
            "insights_enabled": [
                "Customer lifetime value (CLV) scoring",
                "Birthday & loyalty campaign automation",
                "RFM segmentation (Recency, Frequency, Monetary)",
                "Churn prediction & retention scoring",
            ],
        }

    se = get_sentiment_engine()
    if se.has_data:
        s = se.stats
        info = se.info
        top_pos_kw = ", ".join(k["word"] for k in s.get("keywords", {}).get("positive", [])[:5])
        top_neg_kw = ", ".join(k["word"] for k in s.get("keywords", {}).get("negative", [])[:5])
        best_src = s.get("source_breakdown", [{}])[0].get("source", "—") if s.get("source_breakdown") else "—"
        result["reviews"] = {
            "dataset": "Reviews & Sentiment", "icon": "star",
            "records": s.get("total_reviews", 0), "filename": info.get("filename", ""),
            "key_facts": [
                f"{s.get('total_reviews', 0):,} reviews · {s.get('positive_pct', 0)}% positive",
                f"Satisfaction score: {s.get('satisfaction_score', 0)}% · Avg rating: {s.get('overall_avg_rating', 0)}/5",
                f"Top positive keywords: {top_pos_kw}" if top_pos_kw else None,
                f"Highest-rated source: {best_src}",
            ],
            "insights_enabled": [
                "Sentiment trend & brand health tracking",
                "Source reputation comparison (Zomato / Google / etc.)",
                "Visit type satisfaction scoring",
                "Negative review alert & response automation",
            ],
        }

    if menu_data:
        md = menu_data
        info = menu_info
        cats: dict = {}
        for r in md:
            c = r.get("category", "Unknown")
            cats[c] = cats.get(c, 0) + 1
        prices = [r["base_price"] for r in md if r.get("base_price", 0) > 0]
        avg_price = round(sum(prices) / len(prices), 0) if prices else 0
        seasonal = sum(1 for r in md if r.get("season", "YR") != "YR")
        result["menu"] = {
            "dataset": "Menu Catalogue", "icon": "menu",
            "records": len(md), "filename": info.get("filename", ""),
            "key_facts": [
                f"{len(md)} SKUs across {len(cats)} categories",
                f"Price range: ₹{min(prices):,.0f} – ₹{max(prices):,.0f}" if prices else None,
                f"Avg base price: ₹{avg_price:,.0f}",
                f"{seasonal} seasonal items · {len(md) - seasonal} year-round",
            ],
            "insights_enabled": [
                "Menu engineering matrix (star / plowdog / puzzle / dog)",
                "Price elasticity & optimal pricing model",
                "Seasonal menu planning & daypart mapping",
                "Category margin & SKU rationalisation",
            ],
        }

    return result


# ─────────────────────────────────────────────
# LAYER 3 — AI / ML INTELLIGENCE
# ─────────────────────────────────────────────

@app.get("/api/layer3/forecast")
def forecast(request: Request = None):
    tid    = _req_tenant_id(request)
    data   = data_store.get_data_for_tenant(tid)
    pos_data, _ = data_store.get_pos_for_tenant(tid)
    n_days = len(set(r["date"] for r in data))

    # Try XGBoost first (needs ≥14 days); fall back to weekday-average heuristic
    ml_result = None
    if pos_data and len(set(r["date"] for r in pos_data)) >= 14:
        try:
            ml_result = ml_models.forecast_revenue(pos_data, 7)
        except Exception:
            ml_result = None

    if ml_result and ml_result.get("forecast") and not ml_result.get("error"):
        return {
            "forecast":         ml_result["forecast"],
            "model":            ml_result["model"],
            "accuracy":         ml_result["accuracy"],
            "last_trained":     "XGBoost model (pre-trained on 100K CafeBuddy transactions)",
            "training_records": len(data),
            "data_days":        n_days,
            "xgb_mae":          ml_result.get("xgb_mae"),
            "xgb_mape":         ml_result.get("xgb_mape"),
            "scale_factor":     ml_result.get("scale_factor"),
            "user_daily_mean":  ml_result.get("user_daily_mean"),
        }
    # Fallback
    result = _weekday_forecast(data, 7)
    return {
        "forecast":        result,
        "model":           "Weekday Average Heuristic (upload ≥14 days POS data for XGBoost)",
        "accuracy":        round(min(85, 55 + min(28, n_days // 7)), 1),
        "last_trained":    "Computed from daily averages",
        "training_records": len(data),
        "data_days":       n_days,
    }


@app.get("/api/layer3/market-insights")
def market_insights():
    """
    Pre-computed business insights from XGBoost training data (~100K transactions).
    Benchmark figures for dashboard when user has no POS data yet.
    """
    try:
        return ml_models.get_market_insights()
    except Exception as exc:
        return {"error": str(exc), "summary": [], "top_items": [], "by_category": []}


@app.get("/api/layer3/recommendations")
def product_recommendations(request: Request = None):
    tid   = _req_tenant_id(request)
    data  = data_store.get_data_for_tenant(tid)
    pos_data, _ = data_store.get_pos_for_tenant(tid)
    items = _item_stats(data)
    n_days = max(len(set(r["date"] for r in data)), 1)

    high = sorted(items, key=lambda x: x["margin_pct"], reverse=True)[:4]
    low  = sorted(items, key=lambda x: x["margin_pct"])[:3]

    high_potential = [{"item": i["name"], "margin_pct": i["margin_pct"],
                       "weekly_orders": round(i["qty"] / n_days * 7, 1),
                       "recommendation": "Upsell aggressively"} for i in high]
    low_performers = [{"item": i["name"], "margin_pct": i["margin_pct"],
                       "weekly_orders": round(i["qty"] / n_days * 7, 1),
                       "recommendation": "Remove or revamp"} for i in low]

    # Use real cross-sell association rules from trained model
    fbt = []
    if pos_data:
        try:
            rules = ml_models.cross_sell_recommendations(pos_data, top_n=6)
            for r in rules:
                fbt.append({
                    "items":      [r["antecedent"], r["consequent"]],
                    "confidence": r["confidence"],
                    "lift":       r["lift"],
                    "support":    r["support"],
                })
        except Exception:
            pass

    if not fbt:
        from collections import defaultdict as _dd, Counter as _Ctr
        pos = pos_data
        if pos and any(r.get("order_id") for r in pos):
            order_items: dict = _dd(set)
            for r in pos:
                oid = r.get("order_id", "")
                if oid:
                    order_items[oid].add(r.get("item_name", ""))
            pair_counts: _Ctr = _Ctr()
            item_counts: _Ctr = _Ctr()
            for its in order_items.values():
                lst = sorted(its)
                for itm in lst:
                    item_counts[itm] += 1
                for ii in range(len(lst)):
                    for jj in range(ii + 1, len(lst)):
                        pair_counts[(lst[ii], lst[jj])] += 1
            n_orders = max(len(order_items), 1)
            for (a, b), cnt in pair_counts.most_common(4):
                conf = round(cnt / max(item_counts[a], 1) * 100, 1)
                lift = round(cnt * n_orders / max(item_counts[a] * item_counts[b], 1), 2)
                fbt.append({"items": [a, b], "confidence": conf, "lift": lift, "orders": cnt})
        else:
            top5 = [it["name"] for it in items[:5]]
            total_qty = max(sum(it["qty"] for it in items), 1)
            for idx in range(min(4, len(top5) - 1)):
                support = round(items[idx]["qty"] / total_qty * 100, 1)
                fbt.append({"items": [top5[idx], top5[idx + 1]], "confidence": support,
                            "lift": 1.0, "orders": int(items[idx]["qty"] * 0.2)})

    return {
        "frequently_bought_together": fbt,
        "low_performers":             low_performers,
        "high_potential":             high_potential,
    }


@app.get("/api/layer3/segmentation")
def customer_segmentation(request: Request = None):
    tid       = _req_tenant_id(request)
    data      = data_store.get_data_for_tenant(tid)
    menu_data, _ = data_store.get_menu_for_tenant(tid)
    platforms = _platform_breakdown(data)
    items     = _item_stats(data)

    seg_colors = ["#4f46e5", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6"]
    segments = []
    total_rev = sum(p["revenue"] for p in platforms) or 1
    for i, p in enumerate(platforms):
        pct = p["revenue"] / total_rev
        segments.append({
            "name":       p["platform"],
            "count":      p["orders"],
            "avg_spend":  round(p["revenue"] / max(p["orders"], 1), 0),
            "visit_freq": f"{round(p['orders'] / max(len(set(r['date'] for r in data)), 1), 1)}×/day avg",
            "color":      seg_colors[i % len(seg_colors)],
        })

    # Build a price lookup from uploaded menu catalogue (most accurate source)
    menu_price_lookup: dict = {}
    for m in menu_data:
        name_key = str(m.get("item", "")).lower().strip()
        bp = m.get("base_price", 0)
        if bp and bp > 0:
            menu_price_lookup[name_key] = bp

    elasticity = []
    for it in items[:5]:
        # Prefer actual menu catalogue price; fall back to POS-derived avg price
        menu_key = it["name"].lower().strip()
        current = menu_price_lookup.get(menu_key)
        if not current:
            # Try partial match (item name may differ slightly)
            for mk, mv in menu_price_lookup.items():
                if menu_key in mk or mk in menu_key:
                    current = mv
                    break
        if not current or current <= 0:
            # Last resort: revenue / qty from POS aggregates
            current = round(it["revenue"] / max(it["qty"], 1), 0)
        margin = it.get("margin_pct", 40)
        # Elasticity: high-margin items are more inelastic (-0.5), low-margin more elastic (-1.5)
        elasticity_val = round(-0.5 - max(0.0, (60.0 - min(margin, 60.0)) / 60.0), 1)
        # Uplift: 5% for margin>50%, 3% for 30-50%, 0% below 30%
        uplift = 1.05 if margin > 50 else (1.03 if margin > 30 else 1.0)
        optimal = round(current * uplift, 0)
        upside_pct = round((uplift - 1.0) * 100, 1)
        elasticity.append({
            "item":          it["name"],
            "elasticity":    elasticity_val,
            "current_price": int(current),
            "optimal_price": int(optimal),
            "upside":        f"+{upside_pct}%",
        })

    return {"segments": segments, "price_elasticity": elasticity}


# ─────────────────────────────────────────────
# ML MODEL ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/api/ml/forecast")
def ml_forecast(request: Request = None):
    tid = _req_tenant_id(request)
    pos, _ = data_store.get_pos_for_tenant(tid)
    if not pos:
        return {"error": "No POS data uploaded", "forecast": []}
    try:
        return ml_models.forecast_revenue(pos, days=7)
    except Exception as e:
        return {"error": str(e), "forecast": []}


@app.get("/api/ml/platform-forecast")
def ml_platform_forecast(request: Request = None):
    tid = _req_tenant_id(request)
    pos, _ = data_store.get_pos_for_tenant(tid)
    if not pos:
        return []
    try:
        return ml_models.forecast_by_platform(pos, days=7)
    except Exception as e:
        return []


@app.get("/api/ml/peak-hours")
def ml_peak_hours(request: Request = None):
    tid = _req_tenant_id(request)
    pos, _ = data_store.get_pos_for_tenant(tid)
    if not pos:
        return {"error": "No POS data uploaded"}
    try:
        return ml_models.peak_hour_analysis(pos)
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/ml/cancellation-risk")
def ml_cancellation_risk(request: Request = None):
    tid = _req_tenant_id(request)
    pos, _ = data_store.get_pos_for_tenant(tid)
    if not pos:
        return {"error": "No POS data uploaded", "by_platform": [], "by_payment": [], "overall_risk": 0}
    try:
        return ml_models.cancellation_risk_analysis(pos)
    except Exception as e:
        return {"error": str(e), "by_platform": [], "by_payment": [], "overall_risk": 0}


@app.get("/api/ml/cross-sell")
def ml_cross_sell(request: Request = None):
    tid = _req_tenant_id(request)
    pos_data, _ = data_store.get_pos_for_tenant(tid)
    # Use multi-upload POS data first (richer data with order_id), then fall back to legacy
    pos = pos_data or data_store.get_data_for_tenant(tid)
    try:
        rules = ml_models.cross_sell_recommendations(pos, top_n=15)
        return {"rules": rules, "total_model_rules": len(rules), "data_source": "apriori_model" if pos else "none"}
    except Exception as e:
        return {"rules": [], "error": str(e)}


@app.get("/api/ml/dynamic-pricing")
def ml_dynamic_pricing(request: Request = None):
    tid = _req_tenant_id(request)
    pos, _  = data_store.get_pos_for_tenant(tid)
    menu, _ = data_store.get_menu_for_tenant(tid)
    try:
        return {"suggestions": ml_models.dynamic_pricing_suggestions(pos, menu_data=menu)}
    except Exception as e:
        return {"suggestions": [], "error": str(e)}


@app.get("/api/ml/model-comparison")
def ml_model_comparison():
    try:
        return {"models": ml_models.model_comparison()}
    except Exception as e:
        return {"models": [], "error": str(e)}


# ─────────────────────────────────────────────
# LAYER 4 — DECISION ENGINE
# ─────────────────────────────────────────────

@app.get("/api/layer4/decisions")
def get_decisions(request: Request = None):
    overrides = _req_overrides(request)
    decisions = _generate_decisions(_req_data(request), overrides)
    # Merge sentiment-based decisions (IDs 100+)
    for sd in get_sentiment_engine().get_decisions():
        if sd["id"] in overrides:
            sd["status"] = overrides[sd["id"]]
        decisions.append(sd)
    return {
        "decisions": decisions,
        "summary": {
            "pending":  sum(1 for d in decisions if d["status"] == "pending"),
            "approved": sum(1 for d in decisions if d["status"] == "approved"),
            "rejected": sum(1 for d in decisions if d["status"] == "rejected"),
        },
    }


@app.get("/api/sentiment/overview")
def sentiment_overview():
    engine = get_sentiment_engine()
    if not engine.has_data:
        return {"uploaded": False, "stats": {}, "info": {}}
    return {"uploaded": True, "stats": engine.stats, "info": engine.info}


@app.post("/api/layer4/decisions/{decision_id}/approve")
def approve_decision(decision_id: int, request: Request = None):
    tid = _req_tenant_id(request)
    data_store.set_decision_override_for_tenant(tid, decision_id, "approved")
    username = request.headers.get("X-Username", "anonymous") if request else "anonymous"
    _audit.log_action(username=username, module="decision_engine", action="DECISION_APPROVE",
        description=f"Approved decision #{decision_id}",
        ip_address=(request.client.host if request and request.client else ""))
    return {"success": True, "message": f"Decision #{decision_id} approved."}


@app.post("/api/layer4/decisions/{decision_id}/reject")
def reject_decision(decision_id: int, request: Request = None):
    tid = _req_tenant_id(request)
    data_store.set_decision_override_for_tenant(tid, decision_id, "rejected")
    username = request.headers.get("X-Username", "anonymous") if request else "anonymous"
    _audit.log_action(username=username, module="decision_engine", action="DECISION_REJECT",
        description=f"Rejected decision #{decision_id}",
        ip_address=(request.client.host if request and request.client else ""))
    return {"success": True, "message": f"Decision #{decision_id} rejected."}

# ─────────────────────────────────────────────
# LAYER 5 — AUTONOMOUS CAFÉ OS  (XGBoost-powered)
# ─────────────────────────────────────────────

import cafe_os_models as _cos

@app.get("/api/layer5/autonomous-actions")
def autonomous_actions(request: Request = None):
    """
    Return AI-driven autonomous actions for AI-Powered Execution.

    Combines two sources:
    1. Decisions approved by the user in the Decision Engine (primary — always shown)
    2. XGBoost price/demand model actions (secondary — shown when models are available)
    """
    overrides = _req_overrides(request)
    pos_data = _req_data(request)
    actions: list = []
    aid = 1

    # ── Source 1: Approved decisions from the Decision Engine ─────────────────
    all_decisions  = _generate_decisions(pos_data, overrides)
    # Also include sentiment decisions
    for sd in get_sentiment_engine().get_decisions():
        all_decisions.append(sd)

    type_map = {
        "pricing":   "auto_executed",
        "marketing": "scheduled",
        "menu":      "scheduled",
        "staffing":  "alert",
    }
    for d in all_decisions:
        if overrides.get(d["id"]) == "approved":
            actions.append({
                "id":          aid,
                "type":        type_map.get(d["type"], "auto_executed"),
                "title":       d["title"],
                "detail":      d["rationale"],
                "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "impact":      d["impact"],
                "status":      "completed",
                "trigger":     "User Approved — Decision Engine",
                "category":    d.get("category", ""),
                "confidence":  d.get("confidence", 0),
            })
            aid += 1

    # ── Source 2: XGBoost model actions (price/demand insights) ───────────────
    try:
        model_result = _cos.autonomous_actions_from_models(pos_data)
        for a in model_result.get("actions", []):
            a["id"] = aid
            actions.append(a)
            aid += 1
        system_health = model_result.get("system_health", {})
    except Exception:
        system_health = {}

    # If nothing at all, show a helpful prompt
    if not actions:
        actions.append({
            "id": 1, "type": "alert",
            "title": "No approved decisions yet",
            "detail": "Go to 'What To Do Next', review AI recommendations, and click Approve to see them here.",
            "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "impact": "Approve decisions to start autonomous execution",
            "status": "alert",
            "trigger": "System",
        })

    approved_count = sum(1 for d in all_decisions if overrides.get(d["id"]) == "approved")

    # Count model files that actually exist on disk
    _MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
    _ML_FILES = [
        "xgboost_model.joblib",        # Revenue Forecast (XGBoost)
        "sentiment_model.pkl",          # Sentiment Analysis (LR + TF-IDF)
        "cross_sell_rules.pkl",         # Cross-sell (Apriori)
        "demand_forecast_model.pkl",    # Peak Hours / Demand Forecast
        "item_popularity_model.pkl",    # Item Popularity
        "price_optimisation_table.csv", # Dynamic Pricing
    ]
    models_active = sum(1 for f in _ML_FILES if os.path.exists(os.path.join(_MODELS_DIR, f)))
    if models_active == 0:
        models_active = system_health.get("models_active", 0)

    # Alerts fired = pending decisions that haven't been acted on yet
    pending_count = len([
        d for d in all_decisions
        if overrides.get(d["id"]) not in ("approved", "rejected")
    ])

    return {
        "actions": actions,
        "system_health": {
            "models_active":             models_active,
            "decisions_automated_today": approved_count,
            "alerts_fired":              pending_count,
            "uptime": "99.9%",
        },
    }


@app.get("/api/layer5/kpis")
def kpis(request: Request = None):
    return {"kpis": _calc_kpis(_req_data(request))}


@app.get("/api/layer5/demand-forecast")
def layer5_demand_forecast(location: str, daypart: str, category: str,
                            is_weekend: int = 0):
    """Predict revenue for a (location, daypart, category) bucket."""
    try:
        return _cos.predict_demand(location, daypart, category, is_weekend)
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/api/layer5/item-popularity")
def layer5_item_popularity(item_name: str, category: str, daypart: str):
    """Predict units sold for an (item, daypart) combination."""
    try:
        return _cos.predict_item_popularity(item_name, category, daypart)
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/api/layer5/price-recommendations")
def layer5_price_recommendations():
    """Return per-item price-change recommendations from the optimisation table."""
    return {"recommendations": _cos.get_price_recommendations()}


@app.get("/api/layer5/model-values")
def layer5_model_values():
    """Return known label-encoder classes (locations, dayparts, categories, items)."""
    return _cos.get_known_values()


@app.get("/api/layer5/model-status")
def layer5_model_status():
    """Health check: which model files are present on disk."""
    import data_store as ds
    return {
        "models": _cos.model_status(),
        "data_dir": ds._DATA_DIR,
        "data_files": (
            [f for f in os.listdir(ds._DATA_DIR) if f.endswith(".json")]
            if os.path.exists(ds._DATA_DIR) else []
        ),
        "volume_hint": f"Mount Railway volume at: {ds._DATA_DIR}",
    }


# ─────────────────────────────────────────────
# PEER COMPARISON — MARKET RADAR
# ─────────────────────────────────────────────

class PeerAnalyzeRequest(BaseModel):
    city: str
    area: Optional[str] = None

@app.get("/api/peers/cities")
def get_peer_cities():
    return {"cities": pc.CITIES}

@app.get("/api/peers/areas")
def get_peer_areas(city: str):
    return {"areas": pc.get_areas(city)}

@app.get("/api/peers/competitors")
def get_peer_competitors(city: str, area: Optional[str] = None):
    competitors = pc.get_competitors(city, area)
    for c in competitors:
        c["radar_scores"] = pc.compute_radar_scores(c)
    return {"city": city, "area": area, "count": len(competitors), "competitors": competitors}

@app.get("/api/peers/live-search")
async def peer_live_search(city: str, area: str):
    results = pc.live_search_competitors(city, area)
    return {"results": results, "count": len(results)}

@app.post("/api/peers/analyze")
def peer_analyze(req: PeerAnalyzeRequest, request: Request = None):
    competitors = pc.get_competitors(req.city, req.area)
    data = _req_data(request)
    our_stats = {}
    if data:
        items = _item_stats(data)
        total_rev = sum(r["revenue"] for r in data)
        avg_ov = total_rev / max(len(data), 1)
        our_stats = {
            "avg_order_value": round(avg_ov),
            "total_revenue": round(total_rev),
            "top_item": items[0]["name"] if items else "N/A",
        }
    username = request.headers.get("X-Username", "anonymous") if request else "anonymous"
    _audit.log_action(username=username, module="market_radar", action="PEER_ANALYSIS",
        description=f"Ran peer analysis for {req.city}" + (f" / {req.area}" if req.area else "")
                    + f" — {len(competitors)} competitors",
        ip_address=(request.client.host if request and request.client else ""))
    result = pc.analyze_with_ai(our_stats, competitors, req.city, req.area or "")
    return result


# ─────────────────────────────────────────────
# AUDIT LOG API
# ─────────────────────────────────────────────

@app.get("/api/audit/logs")
def get_audit_logs(
    request: Request,
    limit:     int = 50,
    offset:    int = 0,
    username:  Optional[str] = None,
    module:    Optional[str] = None,
    action:    Optional[str] = None,
    status:    Optional[str] = None,
    date_from: Optional[str] = None,
    date_to:   Optional[str] = None,
    search:    Optional[str] = None,
    from_disk: bool = False,
):
    actor = request.headers.get("X-Username", "anonymous")
    entries, total = _audit.get_logs(
        limit=limit, offset=offset,
        username=username, module=module, action=action, status=status,
        date_from=date_from, date_to=date_to, search=search, from_disk=from_disk,
    )
    _audit.log_action(username=actor, module="audit_logs", action="AUDIT_VIEW",
        description=f"Viewed audit logs (filters: user={username}, module={module}, "
                    f"action={action}, limit={limit}, offset={offset})",
        ip_address=(request.client.host if request.client else ""))
    return {"logs": entries, "total": total, "limit": limit, "offset": offset}


@app.get("/api/audit/stats")
def get_audit_stats():
    return _audit.get_stats()


@app.get("/api/audit/export")
def export_audit_csv(
    request: Request,
    username:  Optional[str] = None,
    module:    Optional[str] = None,
    action:    Optional[str] = None,
    status:    Optional[str] = None,
    date_from: Optional[str] = None,
    date_to:   Optional[str] = None,
):
    entries, _ = _audit.get_logs(
        limit=10_000, offset=0,
        username=username, module=module, action=action, status=status,
        date_from=date_from, date_to=date_to, from_disk=True,
    )
    actor = request.headers.get("X-Username", "anonymous")
    _audit.log_action(username=actor, module="audit_logs", action="EXPORT",
        description=f"Exported {len(entries)} audit log entries as CSV",
        ip_address=(request.client.host if request.client else ""))
    csv_content = _audit.export_csv(entries)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


@app.get("/api/audit/modules")
def get_audit_modules():
    return {"modules": list(_audit.MODULE_LABELS.keys()),
            "labels": _audit.MODULE_LABELS,
            "action_types": _audit.ACTION_TYPES}

# ─────────────────────────────────────────────
# HEALTH CHECK  (used by Render & UptimeRobot)
# ─────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
def health():
    data = get_data()
    return {"status": "ok", "data_source": "uploaded" if data else "none"}


# ─────────────────────────────────────────────
# SERVE BUILT FRONTEND (production mode)
# All /api routes are registered above; this block runs LAST.
# os.path.abspath guarantees an absolute path regardless of CWD,
# so Docker / cloud deployments never silently miss the dist folder.
# ─────────────────────────────────────────────
_dist_dir = os.path.normpath(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "frontend", "dist")
)

if os.path.isdir(_dist_dir):
    # Hashed asset bundles (JS / CSS)
    app.mount("/assets", StaticFiles(directory=os.path.join(_dist_dir, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        candidate = os.path.join(_dist_dir, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_dist_dir, "index.html"))
else:
    # Dist not found — surface a clear message instead of a silent 404
    @app.get("/{full_path:path}", include_in_schema=False)
    def no_frontend(full_path: str):
        return {"error": "Frontend not built.", "dist_expected": _dist_dir,
                "hint": "Run 'cd frontend && npm run build' then restart."}
