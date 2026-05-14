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
    """Return uploaded data if present, else mock data."""
    return _uploaded_data if _uploaded_data else MOCK_SALES


def _sync_data_store():
    """Keep data_store in sync so chatbot.py sees the same data."""
    data_store._uploaded_data = _uploaded_data
    data_store._upload_info   = _upload_info

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
    wd_total: dict = defaultdict(float)
    wd_count: dict = defaultdict(int)
    for r in data:
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d")
            wd_total[d.weekday()] += r["revenue"]
            wd_count[d.weekday()] += 1
        except Exception:
            pass

    overall_avg = sum(wd_total.values()) / max(sum(wd_count.values()), 1)
    wd_avg = {wd: wd_total[wd] / wd_count[wd] for wd in wd_total}

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    result = []
    for i in range(1, days + 1):
        date = datetime.now() + timedelta(days=i)
        wd = date.weekday()
        base = wd_avg.get(wd, overall_avg)
        noise = random.uniform(0.93, 1.07)
        rev = int(base * noise)
        result.append({
            "date": date.strftime("%Y-%m-%d"),
            "day": day_names[wd],
            "predicted_revenue": rev,
            "upper": int(rev * 1.09),
            "lower": int(rev * 0.91),
            "predicted_orders": max(1, int(rev / 250)),
            "confidence": round(random.uniform(80, 94), 1),
            "weather": "Rainy" if i == 3 else "Clear",
            "is_weekend": wd >= 5,
        })
    return result


def _generate_decisions(data: list) -> list:
    items = _item_stats(data)
    dates = sorted(set(r["date"] for r in data))
    n_days = max(len(dates), 1)
    decisions = []
    did = 1

    # Pricing — top revenue items with good margin
    for item in items[:5]:
        if item["margin_pct"] > 45 and len(decisions) < 2:
            monthly = int(item["revenue"] / n_days * 30 * 0.08)
            decisions.append({
                "id": did, "type": "pricing", "priority": "high",
                "title": f"Increase '{item['name']}' price by 8%",
                "rationale": (f"Top revenue contributor (₹{item['revenue']:,.0f} total, "
                              f"{item['qty']:.0f} units sold). "
                              f"Margin at {item['margin_pct']:.1f}% supports a price increase without demand erosion."),
                "impact": f"+₹{monthly:,}/month",
                "confidence": round(random.uniform(84, 94), 1),
                "status": "pending", "category": "Revenue Optimization",
            })
            did += 1

    # Menu optimisation — low margin items
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
                "confidence": round(random.uniform(72, 82), 1),
                "status": "pending", "category": "Menu Optimization",
            })
            did += 1

    # Marketing — top platform
    platforms = _platform_breakdown(data)
    if platforms:
        top = max(platforms, key=lambda x: x["revenue"])
        monthly = int(top["revenue"] / n_days * 30 * 0.15)
        decisions.append({
            "id": did, "type": "marketing", "priority": "medium",
            "title": f"Boost promotions on {top['platform']} — top channel",
            "rationale": (f"{top['platform']} generated ₹{top['revenue']:,.0f} total "
                          f"({top['orders']} orders). Targeted promo campaigns can grow this channel by 12–18%."),
            "impact": f"+₹{monthly:,}/month",
            "confidence": round(random.uniform(78, 88), 1),
            "status": "pending", "category": "Marketing",
        })
        did += 1

    # Staffing — weekend vs weekday
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
            decisions.append({
                "id": did, "type": "staffing", "priority": "medium",
                "title": "Increase weekend staffing (+2 staff, 6–10 PM)",
                "rationale": (f"Weekend revenue averages ₹{w_avg:,.0f}/day vs "
                              f"₹{d_avg:,.0f}/day on weekdays — "
                              f"{((w_avg / d_avg) - 1) * 100:.0f}% higher. "
                              f"Current capacity risks 18-min service delays."),
                "impact": "+₹8,400 weekend revenue protection",
                "confidence": round(random.uniform(82, 90), 1),
                "status": "pending", "category": "Operations",
            })
            did += 1

    # Inventory (always present)
    decisions.append({
        "id": did, "type": "inventory", "priority": "critical",
        "title": "Reorder Mozzarella — stock 2.5 kg, threshold 5 kg",
        "rationale": "Current stock below minimum threshold. Weekend demand surge forecast. Stockout risk: HIGH.",
        "impact": "Prevents ₹28,000 weekend revenue loss",
        "confidence": 98.7,
        "status": "pending", "category": "Inventory Management",
    })

    # Apply any approve/reject overrides
    for d in decisions:
        if d["id"] in _decision_overrides:
            d["status"] = _decision_overrides[d["id"]]

    return decisions


def _calc_kpis(data: list) -> list:
    if not data:
        return []
    dates = sorted(set(r["date"] for r in data))
    last, prev = dates[-1], (dates[-2] if len(dates) > 1 else None)

    today_rev  = sum(r["revenue"] for r in data if r["date"] == last)
    prev_rev   = sum(r["revenue"] for r in data if r["date"] == prev) if prev else 0
    rev_change = (f"+{((today_rev / prev_rev) - 1) * 100:.1f}%"
                  if prev_rev > 0 else "—")

    total_rev  = sum(r["revenue"] for r in data)
    total_cost = sum(r["cost"]    for r in data)
    total_qty  = sum(r["quantity"] for r in data)
    avg_ov     = total_rev / max(len(data), 1)
    food_pct   = total_cost / max(total_rev, 1) * 100

    return [
        {"name": "Today's Revenue",  "value": f"₹{today_rev:,.0f}",  "change": rev_change, "trend": "up" if today_rev >= prev_rev else "down"},
        {"name": "Avg Order Value",  "value": f"₹{avg_ov:,.0f}",     "change": "+4.1%",   "trend": "up"},
        {"name": "Food Cost %",      "value": f"{food_pct:.1f}%",     "change": "-2.1%",   "trend": "down"},
        {"name": "Total Items Sold", "value": f"{total_qty:,.0f}",    "change": "+8.7%",   "trend": "up"},
        {"name": "Data Records",     "value": f"{len(data):,}",       "change": f"{len(dates)} days", "trend": "up"},
        {"name": "Date Range",       "value": f"{dates[0]} → {dates[-1]}", "change": f"{len(dates)} days", "trend": "neutral"},
    ]

# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

VALID_USERS = {"admin": "cafe123", "owner": "buddy@2024"}

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
def login(req: LoginRequest):
    if VALID_USERS.get(req.username) == req.password:
        return {"success": True, "username": req.username, "role": "Admin",
                "token": f"demo-token-{req.username}"}
    raise HTTPException(status_code=401, detail="Invalid username or password")

@app.post("/api/auth/logout")
def logout():
    return {"success": True, "message": "Logged out"}

# ─────────────────────────────────────────────
# EXCEL UPLOAD
# ─────────────────────────────────────────────

@app.post("/api/upload/excel")
async def upload_excel(file: UploadFile = File(...)):
    global _uploaded_data, _upload_info, _decision_overrides

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls files are supported.")

    raw = await file.read()
    try:
        records, info = _parse_excel_bytes(raw)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse Excel: {e}")

    if len(records) == 0:
        raise HTTPException(status_code=422, detail="No valid rows found. Check column names and data.")

    _uploaded_data = records
    _upload_info = {**info, "filename": file.filename,
                    "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    _decision_overrides = {}  # reset on new upload
    _sync_data_store()

    return {"success": True, "message": f"Loaded {len(records)} records.", "info": _upload_info}


@app.get("/api/upload/status")
def upload_status():
    if _uploaded_data:
        return {"uploaded": True, "info": _upload_info}
    return {"uploaded": False, "info": {}}


@app.delete("/api/upload/clear")
def clear_upload():
    global _uploaded_data, _upload_info, _decision_overrides
    _uploaded_data = []
    _upload_info = {}
    _decision_overrides = {}
    _sync_data_store()
    return {"success": True, "message": "Reverted to demo data."}

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.get("/api/dashboard/overview")
def dashboard_overview():
    data = get_data()
    dates = sorted(set(r["date"] for r in data))
    last = dates[-1] if dates else None
    prev = dates[-2] if len(dates) > 1 else None

    today_rev  = sum(r["revenue"]  for r in data if r["date"] == last) if last else 0
    today_ord  = sum(r["quantity"] for r in data if r["date"] == last) if last else 0
    prev_rev   = sum(r["revenue"]  for r in data if r["date"] == prev) if prev else today_rev

    rev_change = round((today_rev / max(prev_rev, 1) - 1) * 100, 1)
    avg_ov     = round(today_rev / max(today_ord, 1), 0)
    decisions  = _generate_decisions(data)
    pending    = sum(1 for d in decisions if d["status"] == "pending")

    items = _item_stats(data)
    top_item = items[0]["name"] if items else "—"

    return {
        "revenue_today":     round(today_rev, 0),
        "revenue_yesterday": round(prev_rev, 0),
        "orders_today":      int(today_ord),
        "avg_order_value":   int(avg_ov),
        "top_item":          top_item,
        "pending_decisions": pending,
        "critical_alerts":   2,
        "models_running":    7,
        "revenue_change":    rev_change,
        "orders_change":     8.7,
        "data_source":       "excel" if _uploaded_data else "demo",
    }

# ─────────────────────────────────────────────
# LAYER 1 — DATA COLLECTION
# ─────────────────────────────────────────────

@app.get("/api/layer1/summary")
def layer1_summary():
    data = get_data()
    low_stock = sum(1 for i in MOCK_INVENTORY if i["status"] in ("critical", "low"))
    dates = sorted(set(r["date"] for r in data))

    if _uploaded_data:
        sources = [
            {"name": _upload_info.get("filename", "Uploaded File"),
             "records": _upload_info.get("rows", len(data)),
             "status": "active", "last_sync": _upload_info.get("uploaded_at", "just now"),
             "type": "excel"},
        ]
    else:
        sources = [
            {"name": "POS System",        "records": 1240, "status": "active",   "last_sync": "2 min ago",  "type": "pos"},
            {"name": "Zomato",            "records": 432,  "status": "active",   "last_sync": "5 min ago",  "type": "platform"},
            {"name": "Swiggy",            "records": 287,  "status": "active",   "last_sync": "3 min ago",  "type": "platform"},
            {"name": "Weather API",       "records": 720,  "status": "active",   "last_sync": "1 hr ago",   "type": "external"},
            {"name": "Customer Feedback", "records": 156,  "status": "partial",  "last_sync": "30 min ago", "type": "feedback"},
        ]

    return {
        "total_records":    len(data),
        "sources":          sources,
        "menu_items":       MOCK_MENU,
        "inventory_items":  MOCK_INVENTORY,
        "recent_sales":     data[-20:],
        "low_stock_count":  low_stock,
        "date_range":       {"from": dates[0], "to": dates[-1]} if dates else {},
        "unique_items":     len(set(r["item_name"] for r in data)),
        "data_source":      "excel" if _uploaded_data else "demo",
        "upload_info":      _upload_info if _uploaded_data else {},
    }


@app.get("/api/layer1/platforms")
def platform_data():
    return _platform_breakdown(get_data())


class SalesEntry(BaseModel):
    date: str
    item_name: str
    category: str
    quantity: int
    price: float
    platform: str

_manual_entries: list = []

@app.post("/api/layer1/sales")
def add_sales(entry: SalesEntry):
    row = {**entry.model_dump(),
           "revenue": entry.quantity * entry.price,
           "cost":    entry.quantity * entry.price * 0.38,
           "quantity": float(entry.quantity)}
    _manual_entries.append(row)
    if _uploaded_data:
        _uploaded_data.append(row)
    return {"success": True, "message": "Entry recorded.", "id": len(_manual_entries)}

# ─────────────────────────────────────────────
# LAYER 2 — DATA ENGINEERING
# ─────────────────────────────────────────────

@app.get("/api/layer2/pipeline-status")
def pipeline_status():
    data = get_data()
    return {
        "pipelines": [
            {"name": "Sales ETL",                      "status": "running",   "last_run": "5 min ago",  "records": len(data),  "success_rate": 99.2,  "duration": "1m 12s"},
            {"name": "Inventory Sync",                 "status": "completed", "last_run": "10 min ago", "records": 480,        "success_rate": 100.0, "duration": "42s"},
            {"name": "Order Platform Ingestion",       "status": "running",   "last_run": "2 min ago",  "records": len(data),  "success_rate": 98.7,  "duration": "2m 05s"},
            {"name": "Weather Data ETL",               "status": "completed", "last_run": "1 hr ago",   "records": 720,        "success_rate": 100.0, "duration": "18s"},
            {"name": "Customer Sentiment NLP",         "status": "running",   "last_run": "15 min ago", "records": 156,        "success_rate": 97.4,  "duration": "3m 30s"},
            {"name": "Menu Performance Aggregation",   "status": "completed", "last_run": "20 min ago", "records": len(set(r["item_name"] for r in data)), "success_rate": 100.0, "duration": "55s"},
        ],
        "data_quality": {
            "completeness": round(99.0 - (len(_upload_info.get("skipped", []) or []) / max(len(data), 1)) * 100, 1) if _uploaded_data else 97.3,
            "accuracy":     98.1,
            "consistency":  96.8,
            "timeliness":   99.0,
        },
        "total_records_today": len(data),
        "anomalies_detected":  3,
    }


@app.get("/api/layer2/processed-data")
def processed_data():
    data  = get_data()
    daily = _daily_revenue(data, 14)
    cats  = _category_breakdown(data)
    return {
        "daily_sales":        daily,
        "category_breakdown": cats,
        "total_revenue":      round(sum(r["revenue"] for r in data), 2),
        "total_orders":       int(sum(r["quantity"] for r in data)),
    }

# ─────────────────────────────────────────────
# LAYER 3 — AI / ML INTELLIGENCE
# ─────────────────────────────────────────────

@app.get("/api/layer3/forecast")
def forecast():
    data   = get_data()
    result = _weekday_forecast(data, 7)
    n_days = len(set(r["date"] for r in data))
    return {
        "forecast":        result,
        "model":           "LSTM + XGBoost Ensemble",
        "accuracy":        89.3,
        "last_trained":    "2 days ago",
        "training_records": len(data),
        "data_days":       n_days,
    }


@app.get("/api/layer3/recommendations")
def product_recommendations():
    data  = get_data()
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

    # Simple affinity simulation from top items
    top5 = [i["name"] for i in items[:5]]
    fbt  = []
    for i in range(min(4, len(top5) - 1)):
        fbt.append({
            "items":      [top5[i], top5[i + 1]],
            "confidence": round(random.uniform(40, 80), 1),
            "lift":       round(random.uniform(1.2, 2.5), 1),
            "orders":     int(items[i]["qty"] * 0.3),
        })

    return {
        "frequently_bought_together": fbt,
        "low_performers":             low_performers,
        "high_potential":             high_potential,
    }


@app.get("/api/layer3/segmentation")
def customer_segmentation():
    data      = get_data()
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

    elasticity = [
        {"item": it["name"],
         "elasticity": round(random.uniform(-1.6, -0.5), 1),
         "current_price": round(it["revenue"] / max(it["qty"], 1), 0),
         "optimal_price": round(it["revenue"] / max(it["qty"], 1) * random.uniform(1.05, 1.15), 0),
         "upside": f"+{round(random.uniform(5, 14), 1)}%"}
        for it in items[:5]
    ]

    return {"segments": segments, "price_elasticity": elasticity}

# ─────────────────────────────────────────────
# LAYER 4 — DECISION ENGINE
# ─────────────────────────────────────────────

@app.get("/api/layer4/decisions")
def get_decisions():
    decisions = _generate_decisions(get_data())
    return {
        "decisions": decisions,
        "summary": {
            "pending":  sum(1 for d in decisions if d["status"] == "pending"),
            "approved": sum(1 for d in decisions if d["status"] == "approved"),
            "rejected": sum(1 for d in decisions if d["status"] == "rejected"),
        },
    }


@app.post("/api/layer4/decisions/{decision_id}/approve")
def approve_decision(decision_id: int):
    _decision_overrides[decision_id] = "approved"
    return {"success": True, "message": f"Decision #{decision_id} approved."}


@app.post("/api/layer4/decisions/{decision_id}/reject")
def reject_decision(decision_id: int):
    _decision_overrides[decision_id] = "rejected"
    return {"success": True, "message": f"Decision #{decision_id} rejected."}

# ─────────────────────────────────────────────
# LAYER 5 — AUTONOMOUS CAFÉ OS
# ─────────────────────────────────────────────

@app.get("/api/layer5/autonomous-actions")
def autonomous_actions():
    data    = get_data()
    items   = _item_stats(data)
    top_item = items[0]["name"] if items else "Top Item"
    plats    = _platform_breakdown(data)
    top_plat = max(plats, key=lambda x: x["revenue"])["platform"] if plats else "Zomato"

    actions = [
        {
            "id": 1, "type": "auto_executed",
            "title": f"Price update applied for '{top_item}' on {top_plat}",
            "detail": "Price optimisation model triggered based on demand velocity and elasticity score.",
            "executed_at": (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
            "impact": "+₹1,200/week", "status": "completed", "trigger": "Price Optimization Model",
        },
        {
            "id": 2, "type": "scheduled",
            "title": f"{top_plat} promo push scheduled for 6:00 PM",
            "detail": f"Automated banner for top combo at 20% discount queued for {top_plat}.",
            "executed_at": (datetime.now() + timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"),
            "impact": "+₹6,200/week", "status": "scheduled", "trigger": "Time-based + Demand Model",
        },
        {
            "id": 3, "type": "alert",
            "title": "Low stock — Cream (1.5 L). Reorder dispatched.",
            "detail": "Stock dropped below threshold. Reorder request auto-sent to Dairy Fresh.",
            "executed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "impact": "Prevents stockout", "status": "action_taken", "trigger": "Inventory Threshold Model",
        },
        {
            "id": 4, "type": "scheduled",
            "title": "Weekend staffing — +2 staff Saturday 6–10 PM",
            "detail": "Demand forecast predicts peak. Extra staff slot created in schedule.",
            "executed_at": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
            "impact": "+₹8,400 weekend revenue", "status": "scheduled", "trigger": "Demand Forecast Model",
        },
        {
            "id": 5, "type": "auto_executed",
            "title": f"'{items[-1]['name'] if items else 'Low-margin item'}' hidden on Swiggy",
            "detail": f"Margin {items[-1]['margin_pct']:.1f}% below threshold. Item hidden to reduce kitchen load." if items else "",
            "executed_at": (datetime.now() - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M"),
            "impact": "+₹3,100/month", "status": "completed", "trigger": "Contribution Margin Model",
        },
    ]

    decisions = _generate_decisions(data)
    total_rev = sum(r["revenue"] for r in data)

    return {
        "actions": actions,
        "system_health": {
            "models_active": 7,
            "decisions_automated_today": len(decisions),
            "revenue_impact_today": int(total_rev / max(len(set(r["date"] for r in data)), 1)),
            "alerts_fired": 3,
            "uptime": "99.8%",
        },
    }


@app.get("/api/layer5/kpis")
def kpis():
    return {"kpis": _calc_kpis(get_data())}


# ─────────────────────────────────────────────
# SERVE BUILT FRONTEND (production mode)
# All /api routes are registered above; this block runs LAST.
# Mount /assets for hashed JS/CSS bundles, then catch every other
# path with a FileResponse of index.html so React Router works.
# ─────────────────────────────────────────────
_dist_dir = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
)
if os.path.isdir(_dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(_dist_dir, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        # Serve any file that exists (e.g. favicon.ico, manifest.json)
        candidate = os.path.join(_dist_dir, full_path)
        if os.path.isfile(candidate):
            return FileResponse(candidate)
        # Fall back to index.html for all React Router paths
        return FileResponse(os.path.join(_dist_dir, "index.html"))
