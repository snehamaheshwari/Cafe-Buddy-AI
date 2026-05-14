"""
Multi-dataset upload routes for Cafe Buddy.
Handles three distinct data types:
  1. Financial Data   — costs, margins, revenue, commissions
  2. POS Billing Data — orders, items, payments, timestamps
  3. Customer Data    — CRM, loyalty, preferences, feedback
Supports both .xlsx / .xls (Excel) and .csv files.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

import data_store

router = APIRouter()

# ─────────────────────────────────────────────
# SHARED COLUMN-DETECTION UTILITY
# ─────────────────────────────────────────────

def _detect(df_cols: list, aliases: dict, key: str) -> Optional[str]:
    """
    3-pass detection:
      1. Exact lowercase match
      2. Any fragment of a slash/pipe-separated column matches
      3. Alias is a prefix or suffix of the column name
    """
    mapping = {c.lower().strip(): c for c in df_cols}

    for alias in aliases.get(key, []):
        if alias.lower() in mapping:
            return mapping[alias.lower()]

    for col in df_cols:
        parts = [p.strip().lower() for p in col.replace("|", "/").split("/")]
        for alias in aliases.get(key, []):
            if alias.lower() in parts:
                return col

    for col in df_cols:
        cl = col.lower().strip()
        for alias in aliases.get(key, []):
            al = alias.lower()
            if cl.startswith(al) or cl.endswith(al):
                return col

    return None


def _read_file(raw: bytes, filename: str) -> pd.DataFrame:
    """Auto-detect CSV vs Excel."""
    if filename.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(raw))
    return pd.read_excel(io.BytesIO(raw), engine="openpyxl")


def _safe_float(val, default: float = 0.0) -> float:
    try:
        if pd.isna(val):
            return default
        s = str(val).replace(",", "").replace("₹", "").replace("%", "").strip()
        return float(s)
    except Exception:
        return default


def _safe_str(val, default: str = "") -> str:
    try:
        if pd.isna(val):
            return default
        return str(val).strip()
    except Exception:
        return default


# ─────────────────────────────────────────────
# 1. FINANCIAL DATA
# ─────────────────────────────────────────────

FIN_ALIASES = {
    "date": [
        "date", "day", "period", "week", "month", "order date", "sale date",
        "transaction date", "report date",
    ],
    "daily_revenue": [
        "daily revenue", "revenue", "total revenue", "gross revenue",
        "net revenue", "sales", "turnover", "gross sales", "income",
    ],
    "gross_margin": [
        "gross margin", "gross margin %", "gross margin pct", "gm",
        "gm %", "gross profit %", "gross profit pct",
    ],
    "net_profit": [
        "net profit", "net profit %", "net income", "profit", "nett profit",
        "net margin", "bottom line",
    ],
    "food_cost": [
        "food cost", "food cost %", "food cost percentage", "cogs %",
        "cost of goods sold %", "material cost %", "ingredient cost",
    ],
    "labor_cost": [
        "labor cost", "labour cost", "labor cost %", "labour cost %",
        "staff cost", "salary cost", "manpower cost", "payroll",
    ],
    "electricity": [
        "electricity", "electricity cost", "power cost", "utility",
        "utilities", "electricity bill", "power bill",
    ],
    "rent": [
        "rent", "rental", "lease", "premises cost", "shop rent",
        "store rent", "rent cost",
    ],
    "marketing": [
        "marketing", "marketing spend", "advertising", "ads",
        "promotion cost", "marketing cost", "ad spend",
    ],
    "packaging": [
        "packaging", "packaging cost", "packing cost",
        "packaging material", "packing material",
    ],
    "commission": [
        "commission", "swiggy commission", "zomato commission",
        "platform commission", "aggregator commission",
        "delivery commission", "online commission",
    ],
}


def _parse_financial(df: pd.DataFrame, filename: str) -> tuple[list, dict]:
    df.columns = [str(c).strip() for c in df.columns]

    date_col    = _detect(df.columns, FIN_ALIASES, "date")
    rev_col     = _detect(df.columns, FIN_ALIASES, "daily_revenue")
    gm_col      = _detect(df.columns, FIN_ALIASES, "gross_margin")
    np_col      = _detect(df.columns, FIN_ALIASES, "net_profit")
    fc_col      = _detect(df.columns, FIN_ALIASES, "food_cost")
    lc_col      = _detect(df.columns, FIN_ALIASES, "labor_cost")
    el_col      = _detect(df.columns, FIN_ALIASES, "electricity")
    rent_col    = _detect(df.columns, FIN_ALIASES, "rent")
    mkt_col     = _detect(df.columns, FIN_ALIASES, "marketing")
    pkg_col     = _detect(df.columns, FIN_ALIASES, "packaging")
    comm_col    = _detect(df.columns, FIN_ALIASES, "commission")

    if not date_col:
        raise ValueError("Could not find a 'Date' column in the financial file.")
    if not rev_col:
        raise ValueError("Could not find a 'Revenue / Daily Revenue' column.")

    records, skipped = [], 0
    for _, row in df.iterrows():
        try:
            raw_date = row[date_col]
            if pd.isna(raw_date):
                skipped += 1; continue
            date_str = pd.to_datetime(raw_date).strftime("%Y-%m-%d")

            revenue = _safe_float(row[rev_col]) if rev_col else 0.0
            if revenue <= 0:
                skipped += 1; continue

            records.append({
                "date":            date_str,
                "daily_revenue":   revenue,
                "gross_margin_pct": _safe_float(row[gm_col])  if gm_col  else None,
                "net_profit":      _safe_float(row[np_col])   if np_col  else None,
                "food_cost_pct":   _safe_float(row[fc_col])   if fc_col  else None,
                "labor_cost_pct":  _safe_float(row[lc_col])   if lc_col  else None,
                "electricity":     _safe_float(row[el_col])   if el_col  else None,
                "rent":            _safe_float(row[rent_col]) if rent_col else None,
                "marketing":       _safe_float(row[mkt_col])  if mkt_col  else None,
                "packaging":       _safe_float(row[pkg_col])  if pkg_col  else None,
                "commission":      _safe_float(row[comm_col]) if comm_col else None,
            })
        except Exception:
            skipped += 1

    dates = sorted(set(r["date"] for r in records))
    detected = {k: v for k, v in {
        "date": date_col, "daily_revenue": rev_col, "gross_margin": gm_col,
        "net_profit": np_col, "food_cost": fc_col, "labor_cost": lc_col,
        "electricity": el_col, "rent": rent_col, "marketing": mkt_col,
        "packaging": pkg_col, "commission": comm_col,
    }.items() if v}

    info = {
        "filename": filename, "rows": len(records), "skipped": skipped,
        "columns_detected": detected,
        "date_range": {"from": dates[0], "to": dates[-1]} if dates else {},
        "unique_dates": len(dates),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return records, info


# ─────────────────────────────────────────────
# 2. POS BILLING DATA
# ─────────────────────────────────────────────

POS_ALIASES = {
    "order_id": [
        "order id", "order_id", "bill id", "bill no", "invoice id",
        "transaction id", "receipt no", "order number", "bill number",
    ],
    "timestamp": [
        "timestamp", "order time", "order timestamp", "date time",
        "datetime", "order date", "date", "time", "created at",
    ],
    "bill_amount": [
        "bill amount", "total amount", "order amount", "invoice amount",
        "net amount", "grand total", "final amount", "payable amount",
        "amount", "total",
    ],
    "gst": [
        "gst", "tax", "gst amount", "taxes", "vat", "tax amount",
        "sgst", "cgst",
    ],
    "discount": [
        "discount", "discount amount", "offer", "discount value",
        "promo discount", "coupon discount",
    ],
    "coupon": [
        "coupon", "coupon code", "promo code", "voucher", "coupon used",
        "offer code", "discount code",
    ],
    "item_name": [
        "item name", "item name / product", "product", "item",
        "menu item", "food item", "dish",
    ],
    "quantity": [
        "quantity", "qty", "count", "units", "item quantity",
        "quantity / qty",
    ],
    "payment_mode": [
        "payment mode", "payment method", "pay mode", "mode of payment",
        "payment type", "payment", "paid via", "pay via",
    ],
    "platform": [
        "platform", "delivery platform", "channel", "order source",
        "platform / channel", "delivery channel", "order channel",
        "source",
    ],
    "peak_hour": [
        "peak hour", "time slot", "hour", "time period", "rush hour",
        "meal period", "slot",
    ],
    "repeat_customer": [
        "repeat customer", "returning customer", "loyal customer",
        "new customer", "is repeat", "customer type",
    ],
    "cancel_reason": [
        "cancellation reason", "cancel reason", "cancelled reason",
        "why cancelled", "cancellation",
    ],
    "refund_reason": [
        "refund reason", "refund", "return reason", "why refunded",
    ],
}


def _parse_pos(df: pd.DataFrame, filename: str) -> tuple[list, dict]:
    df.columns = [str(c).strip() for c in df.columns]

    order_col  = _detect(df.columns, POS_ALIASES, "order_id")
    ts_col     = _detect(df.columns, POS_ALIASES, "timestamp")
    bill_col   = _detect(df.columns, POS_ALIASES, "bill_amount")
    gst_col    = _detect(df.columns, POS_ALIASES, "gst")
    disc_col   = _detect(df.columns, POS_ALIASES, "discount")
    coup_col   = _detect(df.columns, POS_ALIASES, "coupon")
    item_col   = _detect(df.columns, POS_ALIASES, "item_name")
    qty_col    = _detect(df.columns, POS_ALIASES, "quantity")
    pay_col    = _detect(df.columns, POS_ALIASES, "payment_mode")
    plat_col   = _detect(df.columns, POS_ALIASES, "platform")
    peak_col   = _detect(df.columns, POS_ALIASES, "peak_hour")
    repeat_col = _detect(df.columns, POS_ALIASES, "repeat_customer")
    cancel_col = _detect(df.columns, POS_ALIASES, "cancel_reason")
    refund_col = _detect(df.columns, POS_ALIASES, "refund_reason")

    if not ts_col and not order_col:
        raise ValueError("Could not find an 'Order ID' or 'Timestamp' column.")
    if not bill_col:
        raise ValueError("Could not find a 'Bill Amount' / 'Total Amount' column.")

    records, skipped = [], 0
    for _, row in df.iterrows():
        try:
            # Parse date + hour from timestamp
            raw_ts = row[ts_col] if ts_col else None
            if raw_ts is not None and not pd.isna(raw_ts):
                ts     = pd.to_datetime(raw_ts)
                date_s = ts.strftime("%Y-%m-%d")
                hour   = ts.hour
            else:
                date_s = datetime.now().strftime("%Y-%m-%d")
                hour   = 12

            bill = _safe_float(row[bill_col]) if bill_col else 0.0
            if bill <= 0:
                skipped += 1; continue

            # Derive analytics-compatible fields (revenue = bill, item = item_name, etc.)
            item     = _safe_str(row[item_col], "Unknown")  if item_col  else "Unknown"
            qty      = _safe_float(row[qty_col], 1.0)       if qty_col   else 1.0
            platform = _safe_str(row[plat_col], "Dine-in")  if plat_col  else "Dine-in"
            category = "POS Order"   # generic; real category needs item mapping

            records.append({
                # analytics-compatible keys (used by get_data() → AI layers)
                "date":        date_s,
                "item_name":   item,
                "category":    category,
                "quantity":    qty,
                "price":       round(bill / max(qty, 1), 2),
                "revenue":     bill,
                "cost":        round(bill * 0.38, 2),
                "platform":    platform,
                # POS-specific keys
                "order_id":    _safe_str(row[order_col]) if order_col else "",
                "bill_amount": bill,
                "gst":         _safe_float(row[gst_col])    if gst_col    else None,
                "discount":    _safe_float(row[disc_col])   if disc_col   else None,
                "coupon":      _safe_str(row[coup_col])     if coup_col   else "",
                "payment_mode":_safe_str(row[pay_col])      if pay_col    else "",
                "hour":        hour,
                "peak_hour":   _safe_str(row[peak_col])     if peak_col   else _hour_label(hour),
                "repeat":      _safe_str(row[repeat_col])   if repeat_col else "",
                "cancel_reason":_safe_str(row[cancel_col])  if cancel_col else "",
                "refund_reason":_safe_str(row[refund_col])  if refund_col else "",
            })
        except Exception:
            skipped += 1

    dates   = sorted(set(r["date"] for r in records))
    detected = {k: v for k, v in {
        "order_id": order_col, "timestamp": ts_col, "bill_amount": bill_col,
        "gst": gst_col, "discount": disc_col, "coupon": coup_col,
        "item_name": item_col, "quantity": qty_col, "payment_mode": pay_col,
        "platform": plat_col, "peak_hour": peak_col,
        "repeat_customer": repeat_col, "cancel_reason": cancel_col,
        "refund_reason": refund_col,
    }.items() if v}

    info = {
        "filename": filename, "rows": len(records), "skipped": skipped,
        "columns_detected": detected,
        "date_range": {"from": dates[0], "to": dates[-1]} if dates else {},
        "unique_dates": len(dates),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return records, info


def _hour_label(h: int) -> str:
    if 6  <= h < 11: return "Breakfast (6–11)"
    if 11 <= h < 15: return "Lunch (11–15)"
    if 15 <= h < 18: return "Afternoon (15–18)"
    if 18 <= h < 22: return "Dinner (18–22)"
    return "Late Night (22+)"


# ─────────────────────────────────────────────
# 3. CUSTOMER DATA
# ─────────────────────────────────────────────

CUST_ALIASES = {
    "name": [
        "name", "customer name", "full name", "client name",
        "guest name", "user name",
    ],
    "phone": [
        "phone", "phone number", "mobile", "mobile number",
        "contact", "contact number", "cell", "whatsapp",
    ],
    "birthday": [
        "birthday", "dob", "date of birth", "birth date",
        "birth day", "bday",
    ],
    "visit_frequency": [
        "visit frequency", "visits", "frequency", "visit count",
        "total visits", "no of visits", "number of visits",
    ],
    "favorite_items": [
        "favorite items", "favourite items", "preferred items",
        "top items", "fav items", "fav dish", "preferred dish",
    ],
    "avg_order_value": [
        "average order value", "avg order value", "aov",
        "avg order", "avg bill", "average bill", "average spend",
    ],
    "feedback": [
        "feedback", "sentiment", "rating", "review", "score",
        "feedback sentiment", "customer rating", "nps",
    ],
    "preferred_time": [
        "preferred time", "ordering time", "preferred ordering time",
        "visit time", "preferred slot", "usual time",
    ],
    "platform_source": [
        "platform source", "platform", "source", "acquisition source",
        "channel", "how did they find us", "referral",
    ],
    "loyalty_points": [
        "loyalty points", "points", "rewards points", "reward points",
        "loyalty", "loyalty score",
    ],
    "gender": ["gender", "sex"],
    "age_group": [
        "age group", "age", "age bracket", "age range",
        "age category",
    ],
}


def _parse_customer(df: pd.DataFrame, filename: str) -> tuple[list, dict]:
    df.columns = [str(c).strip() for c in df.columns]

    name_col   = _detect(df.columns, CUST_ALIASES, "name")
    phone_col  = _detect(df.columns, CUST_ALIASES, "phone")
    bday_col   = _detect(df.columns, CUST_ALIASES, "birthday")
    freq_col   = _detect(df.columns, CUST_ALIASES, "visit_frequency")
    fav_col    = _detect(df.columns, CUST_ALIASES, "favorite_items")
    aov_col    = _detect(df.columns, CUST_ALIASES, "avg_order_value")
    fb_col     = _detect(df.columns, CUST_ALIASES, "feedback")
    time_col   = _detect(df.columns, CUST_ALIASES, "preferred_time")
    src_col    = _detect(df.columns, CUST_ALIASES, "platform_source")
    pts_col    = _detect(df.columns, CUST_ALIASES, "loyalty_points")
    gender_col = _detect(df.columns, CUST_ALIASES, "gender")
    age_col    = _detect(df.columns, CUST_ALIASES, "age_group")

    if not name_col and not phone_col:
        raise ValueError("Could not find a 'Name' or 'Phone Number' column.")

    records, skipped = [], 0
    for _, row in df.iterrows():
        try:
            name  = _safe_str(row[name_col])  if name_col  else ""
            phone = _safe_str(row[phone_col]) if phone_col else ""
            if not name and not phone:
                skipped += 1; continue

            records.append({
                "name":             name,
                "phone":            phone,
                "birthday":         _safe_str(row[bday_col])  if bday_col  else "",
                "visit_frequency":  int(_safe_float(row[freq_col], 0)) if freq_col else 0,
                "favorite_items":   _safe_str(row[fav_col])   if fav_col   else "",
                "avg_order_value":  _safe_float(row[aov_col]) if aov_col   else None,
                "feedback":         _safe_str(row[fb_col])    if fb_col    else "",
                "preferred_time":   _safe_str(row[time_col])  if time_col  else "",
                "platform_source":  _safe_str(row[src_col])   if src_col   else "",
                "loyalty_points":   _safe_float(row[pts_col]) if pts_col   else 0.0,
                "gender":           _safe_str(row[gender_col])if gender_col else "",
                "age_group":        _safe_str(row[age_col])   if age_col   else "",
            })
        except Exception:
            skipped += 1

    detected = {k: v for k, v in {
        "name": name_col, "phone": phone_col, "birthday": bday_col,
        "visit_frequency": freq_col, "favorite_items": fav_col,
        "avg_order_value": aov_col, "feedback": fb_col,
        "preferred_time": time_col, "platform_source": src_col,
        "loyalty_points": pts_col, "gender": gender_col, "age_group": age_col,
    }.items() if v}

    info = {
        "filename": filename, "rows": len(records), "skipped": skipped,
        "columns_detected": detected,
        "total_customers": len(records),
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return records, info


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────

ALLOWED_TYPES = (".xlsx", ".xls", ".csv")


def _check_ext(filename: str):
    if not any(filename.lower().endswith(ext) for ext in ALLOWED_TYPES):
        raise HTTPException(status_code=400,
                            detail="Only .xlsx, .xls, or .csv files are supported.")


# ── Financial ──────────────────────────────────────────────────────────────────

@router.post("/upload/financial")
async def upload_financial(file: UploadFile = File(...)):
    _check_ext(file.filename)
    raw = await file.read()
    try:
        df = _read_file(raw, file.filename)
        records, info = _parse_financial(df, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {e}")

    if not records:
        raise HTTPException(status_code=422, detail="No valid rows found.")

    data_store._financial_data = records
    data_store._financial_info = info
    return {"success": True, "message": f"Loaded {len(records)} financial records.", "info": info}


@router.delete("/upload/financial/clear")
def clear_financial():
    data_store._financial_data = []
    data_store._financial_info = {}
    return {"success": True}


@router.get("/data/financial/summary")
def financial_summary():
    data = data_store._financial_data
    info = data_store._financial_info
    if not data:
        return {"uploaded": False, "info": {}, "summary": {}}

    total_rev  = sum(r["daily_revenue"] for r in data)
    avg_gm     = _avg_non_none([r["gross_margin_pct"] for r in data])
    avg_np     = _avg_non_none([r["net_profit"]       for r in data])
    avg_fc     = _avg_non_none([r["food_cost_pct"]    for r in data])
    avg_lc     = _avg_non_none([r["labor_cost_pct"]   for r in data])
    total_el   = sum(r["electricity"] or 0  for r in data)
    total_rent = sum(r["rent"]        or 0  for r in data)
    total_mkt  = sum(r["marketing"]   or 0  for r in data)
    total_pkg  = sum(r["packaging"]   or 0  for r in data)
    total_comm = sum(r["commission"]  or 0  for r in data)

    dates = sorted(set(r["date"] for r in data))
    daily = [{"date": d, "revenue": sum(r["daily_revenue"] for r in data if r["date"] == d)}
             for d in dates[-14:]]

    cost_breakdown = [
        {"label": "Electricity",  "value": round(total_el,   2)},
        {"label": "Rent",         "value": round(total_rent, 2)},
        {"label": "Marketing",    "value": round(total_mkt,  2)},
        {"label": "Packaging",    "value": round(total_pkg,  2)},
        {"label": "Commission",   "value": round(total_comm, 2)},
    ]

    return {
        "uploaded": True, "info": info,
        "summary": {
            "total_revenue":    round(total_rev, 2),
            "avg_gross_margin": round(avg_gm, 1) if avg_gm is not None else None,
            "avg_net_profit":   round(avg_np, 1) if avg_np is not None else None,
            "avg_food_cost":    round(avg_fc, 1) if avg_fc is not None else None,
            "avg_labor_cost":   round(avg_lc, 1) if avg_lc is not None else None,
            "records":          len(data),
            "days":             len(dates),
        },
        "daily_revenue": daily,
        "cost_breakdown": cost_breakdown,
        "recent": data[-20:],
    }


# ── POS Billing ────────────────────────────────────────────────────────────────

@router.post("/upload/pos")
async def upload_pos(file: UploadFile = File(...)):
    _check_ext(file.filename)
    raw = await file.read()
    try:
        df = _read_file(raw, file.filename)
        records, info = _parse_pos(df, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {e}")

    if not records:
        raise HTTPException(status_code=422, detail="No valid rows found.")

    data_store._pos_data = records
    data_store._pos_info = info
    # Sync into analytics pipeline
    data_store._uploaded_data = records
    data_store._upload_info   = info
    return {"success": True, "message": f"Loaded {len(records)} POS records.", "info": info}


@router.delete("/upload/pos/clear")
def clear_pos():
    data_store._pos_data      = []
    data_store._pos_info      = {}
    data_store._uploaded_data = []
    data_store._upload_info   = {}
    return {"success": True}


@router.get("/data/pos/summary")
def pos_summary():
    data = data_store._pos_data
    info = data_store._pos_info
    if not data:
        return {"uploaded": False, "info": {}, "summary": {}}

    total_orders    = len(data)
    total_rev       = sum(r["bill_amount"] for r in data)
    avg_bill        = total_rev / max(total_orders, 1)
    total_discount  = sum(r["discount"] or 0 for r in data)
    total_gst       = sum(r["gst"]      or 0 for r in data)

    # Payment mode breakdown
    pay_agg: dict = {}
    for r in data:
        pm = r.get("payment_mode") or "Unknown"
        pay_agg[pm] = pay_agg.get(pm, 0) + 1

    # Platform breakdown
    plat_agg: dict = {}
    for r in data:
        p = r.get("platform") or "Unknown"
        plat_agg[p] = plat_agg.get(p, {"orders": 0, "revenue": 0.0})
        plat_agg[p]["orders"]  += 1
        plat_agg[p]["revenue"] += r["bill_amount"]

    # Peak hour breakdown
    hour_agg: dict = {}
    for r in data:
        label = r.get("peak_hour") or _hour_label(r.get("hour", 12))
        hour_agg[label] = hour_agg.get(label, 0) + 1

    # Repeat customer rate
    repeat_count = sum(1 for r in data
                       if str(r.get("repeat", "")).lower() in ("yes", "true", "1", "repeat", "returning"))
    repeat_pct   = round(repeat_count / max(total_orders, 1) * 100, 1)

    dates = sorted(set(r["date"] for r in data))

    return {
        "uploaded": True, "info": info,
        "summary": {
            "total_orders":   total_orders,
            "total_revenue":  round(total_rev, 2),
            "avg_bill":       round(avg_bill, 2),
            "total_discount": round(total_discount, 2),
            "total_gst":      round(total_gst, 2),
            "repeat_pct":     repeat_pct,
            "days":           len(dates),
        },
        "payment_breakdown": [{"mode": k, "count": v} for k, v in pay_agg.items()],
        "platform_breakdown": [{"platform": k, **v} for k, v in plat_agg.items()],
        "peak_hours": [{"slot": k, "orders": v} for k, v in sorted(hour_agg.items())],
        "recent": data[-20:],
    }


# ── Customer ───────────────────────────────────────────────────────────────────

@router.post("/upload/customer")
async def upload_customer(file: UploadFile = File(...)):
    _check_ext(file.filename)
    raw = await file.read()
    try:
        df = _read_file(raw, file.filename)
        records, info = _parse_customer(df, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {e}")

    if not records:
        raise HTTPException(status_code=422, detail="No valid rows found.")

    data_store._customer_data = records
    data_store._customer_info = info
    return {"success": True, "message": f"Loaded {len(records)} customer records.", "info": info}


@router.delete("/upload/customer/clear")
def clear_customer():
    data_store._customer_data = []
    data_store._customer_info = {}
    return {"success": True}


@router.get("/data/customer/summary")
def customer_summary():
    data = data_store._customer_data
    info = data_store._customer_info
    if not data:
        return {"uploaded": False, "info": {}, "summary": {}}

    total      = len(data)
    avg_aov    = _avg_non_none([r["avg_order_value"] for r in data])
    avg_visits = sum(r["visit_frequency"] for r in data) / max(total, 1)
    avg_pts    = sum(r["loyalty_points"]  for r in data) / max(total, 1)

    # Platform source
    src_agg: dict = {}
    for r in data:
        s = r.get("platform_source") or "Unknown"
        src_agg[s] = src_agg.get(s, 0) + 1

    # Gender
    gender_agg: dict = {}
    for r in data:
        g = r.get("gender") or "Not specified"
        gender_agg[g] = gender_agg.get(g, 0) + 1

    # Age group
    age_agg: dict = {}
    for r in data:
        a = r.get("age_group") or "Not specified"
        age_agg[a] = age_agg.get(a, 0) + 1

    # Feedback sentiment
    pos_fb  = sum(1 for r in data if _sentiment_is_positive(r.get("feedback", "")))
    neg_fb  = sum(1 for r in data if _sentiment_is_negative(r.get("feedback", "")))
    neut_fb = total - pos_fb - neg_fb

    return {
        "uploaded": True, "info": info,
        "summary": {
            "total_customers":  total,
            "avg_order_value":  round(avg_aov, 2) if avg_aov is not None else None,
            "avg_visit_freq":   round(avg_visits, 1),
            "avg_loyalty_pts":  round(avg_pts, 1),
        },
        "platform_source":  [{"source": k, "count": v} for k, v in src_agg.items()],
        "gender_dist":      [{"gender": k, "count": v} for k, v in gender_agg.items()],
        "age_dist":         [{"age_group": k, "count": v} for k, v in age_agg.items()],
        "feedback_sentiment": [
            {"label": "Positive", "count": pos_fb},
            {"label": "Neutral",  "count": neut_fb},
            {"label": "Negative", "count": neg_fb},
        ],
        "recent": data[-20:],
    }


# ── Aggregate status ───────────────────────────────────────────────────────────

@router.get("/upload/status/all")
def upload_status_all():
    return {
        "financial": {
            "uploaded": bool(data_store._financial_data),
            "info":     data_store._financial_info,
        },
        "pos": {
            "uploaded": bool(data_store._pos_data),
            "info":     data_store._pos_info,
        },
        "customer": {
            "uploaded": bool(data_store._customer_data),
            "info":     data_store._customer_info,
        },
    }


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _avg_non_none(values: list) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _sentiment_is_positive(text: str) -> bool:
    text = str(text).lower()
    try:
        score = float(text)
        return score >= 4
    except ValueError:
        pass
    pos_words = {"good", "great", "excellent", "loved", "amazing", "happy",
                 "satisfied", "positive", "superb", "fantastic", "awesome"}
    return any(w in text for w in pos_words)


def _sentiment_is_negative(text: str) -> bool:
    text = str(text).lower()
    try:
        score = float(text)
        return score <= 2
    except ValueError:
        pass
    neg_words = {"bad", "poor", "terrible", "worst", "unhappy", "disappointed",
                 "negative", "horrible", "awful", "disgust", "rude", "slow"}
    return any(w in text for w in neg_words)
