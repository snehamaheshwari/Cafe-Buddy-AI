"""
Shared pytest fixtures for the Cafe Buddy backend test suite.
"""
import sys
import os

# Ensure backend/ is on sys.path so modules import correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timedelta


# ─── POS data fixtures ────────────────────────────────────────────────────────

def _make_pos_row(date: str, item: str = "Cappuccino", qty: float = 2.0,
                  revenue: float = 240.0, cost: float = 70.0,
                  platform: str = "Dine-in", payment_mode: str = "UPI",
                  order_id: str = None, category: str = "Beverage") -> dict:
    return {
        "date": date,
        "item_name": item,
        "quantity": qty,
        "revenue": revenue,
        "cost": cost,
        "platform": platform,
        "payment_mode": payment_mode,
        "order_id": order_id or f"ORD-{date}-{item[:3]}",
        "category": category,
        "bill_amount": revenue,
    }


@pytest.fixture
def pos_data_7days():
    """7 days of POS data with 3 items per day — weekends included."""
    base = datetime(2026, 5, 11)  # Monday
    rows = []
    items = [
        ("Cappuccino",    "Beverage", 120.0, 35.0),
        ("Pasta Combo",   "Main",     280.0, 120.0),
        ("Garlic Bread",  "Starter",   80.0,  25.0),
    ]
    for i in range(7):
        d = (base + timedelta(days=i)).strftime("%Y-%m-%d")
        is_we = i >= 5
        for item, cat, price, cost in items:
            qty = 10.0 if is_we else 7.0
            rows.append(_make_pos_row(
                date=d, item=item, qty=qty,
                revenue=qty * price, cost=qty * cost,
                platform="Dine-in", category=cat,
                order_id=f"ORD-{d}-{item[:3]}",
            ))
    return rows


@pytest.fixture
def pos_data_30days():
    """30 days of POS data — weekends ~20% higher (realistic café pattern)."""
    base = datetime(2026, 4, 18)
    rows = []
    items = [
        ("Cappuccino",    "Beverage", 120.0, 35.0),
        ("Pasta Combo",   "Main",     280.0, 120.0),
        ("Cold Coffee",   "Beverage", 150.0, 45.0),
        ("Caesar Salad",  "Starter",  180.0, 70.0),
        ("Tiramisu",      "Dessert",  160.0, 55.0),
    ]
    platforms = ["Dine-in", "Zomato", "Swiggy", "Takeaway"]
    for i in range(30):
        d = (base + timedelta(days=i)).strftime("%Y-%m-%d")
        is_we = (base + timedelta(days=i)).weekday() >= 5
        for j, (item, cat, price, cost) in enumerate(items):
            qty = 12.0 if is_we else 8.0
            rows.append(_make_pos_row(
                date=d, item=item, qty=qty,
                revenue=qty * price, cost=qty * cost,
                platform=platforms[j % len(platforms)],
                category=cat,
                order_id=f"ORD-{d}-{item[:3]}-{j}",
            ))
    return rows


@pytest.fixture
def multi_platform_pos():
    """POS data across multiple platforms for platform analysis tests."""
    rows = []
    platforms = {"Dine-in": 40, "Zomato": 30, "Swiggy": 20, "Takeaway": 10}
    date = "2026-05-10"
    for plat, count in platforms.items():
        for k in range(count):
            rows.append(_make_pos_row(
                date=date, item="Espresso", qty=1.0,
                revenue=80.0, cost=20.0, platform=plat,
                order_id=f"ORD-{plat[:2]}-{k}",
            ))
    return rows


@pytest.fixture
def financial_records_fractional():
    """Financial records where pct columns are stored as decimals (0.32 = 32%)."""
    return [
        {"date": "2026-05-01", "daily_revenue": 45000.0,
         "gross_margin_pct": 0.42, "food_cost_pct": 0.31,
         "labor_cost_pct": 0.18, "net_profit": 0.12,
         "electricity": 2000, "rent": 5000, "marketing": None,
         "packaging": None, "commission": None},
        {"date": "2026-05-02", "daily_revenue": 48000.0,
         "gross_margin_pct": 0.40, "food_cost_pct": 0.33,
         "labor_cost_pct": 0.19, "net_profit": 0.10,
         "electricity": 2000, "rent": 5000, "marketing": None,
         "packaging": None, "commission": None},
    ]


@pytest.fixture
def financial_records_percentage():
    """Financial records where pct columns are already in percentage form (32%)."""
    return [
        {"date": "2026-05-01", "daily_revenue": 45000.0,
         "gross_margin_pct": 42.0, "food_cost_pct": 31.0,
         "labor_cost_pct": 18.0, "net_profit": 12.0,
         "electricity": 2000, "rent": 5000, "marketing": None,
         "packaging": None, "commission": None},
    ]
