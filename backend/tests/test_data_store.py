"""
Unit tests for data_store.py — analytics helpers and shared state.
"""
import pytest
from datetime import datetime, timedelta
from data_store import (
    item_stats, platform_breakdown, category_breakdown,
    daily_revenue, weekday_forecast, get_data,
)
import data_store as _ds


# ─── item_stats ───────────────────────────────────────────────────────────────

class TestItemStats:
    def test_aggregates_qty_and_revenue(self, pos_data_7days):
        stats = item_stats(pos_data_7days)
        names = [s["name"] for s in stats]
        assert "Cappuccino" in names
        assert "Pasta Combo" in names

    def test_calculates_margin_correctly(self, pos_data_7days):
        stats = item_stats(pos_data_7days)
        cap = next(s for s in stats if s["name"] == "Cappuccino")
        # Cappuccino: price=120, cost=35 → margin = (120-35)/120 = 70.8%
        assert abs(cap["margin_pct"] - 70.8) < 1.0

    def test_sorts_by_revenue_descending(self, pos_data_7days):
        stats = item_stats(pos_data_7days)
        revenues = [s["revenue"] for s in stats]
        assert revenues == sorted(revenues, reverse=True)

    def test_returns_empty_for_empty_data(self):
        assert item_stats([]) == []

    def test_single_item(self):
        data = [{"date": "2026-05-01", "item_name": "Latte",
                 "quantity": 5.0, "revenue": 600.0, "cost": 150.0,
                 "platform": "Dine-in"}]
        stats = item_stats(data)
        assert len(stats) == 1
        assert stats[0]["name"] == "Latte"
        assert stats[0]["qty"] == 5.0
        assert stats[0]["revenue"] == 600.0
        assert abs(stats[0]["margin_pct"] - 75.0) < 0.1

    def test_margin_cannot_exceed_100(self, pos_data_7days):
        stats = item_stats(pos_data_7days)
        for s in stats:
            assert s["margin_pct"] <= 100.0

    def test_margin_aggregates_across_multiple_days(self, pos_data_7days):
        stats = item_stats(pos_data_7days)
        pasta = next(s for s in stats if s["name"] == "Pasta Combo")
        # 5 weekdays × 7 qty + 2 weekend × 10 qty = 55 total
        assert pasta["qty"] == 55.0


# ─── platform_breakdown ───────────────────────────────────────────────────────

class TestPlatformBreakdown:
    def test_aggregates_all_platforms(self, multi_platform_pos):
        result = platform_breakdown(multi_platform_pos)
        platforms = {r["platform"] for r in result}
        assert {"Dine-in", "Zomato", "Swiggy", "Takeaway"} == platforms

    def test_revenue_proportional_to_order_count(self, multi_platform_pos):
        result = platform_breakdown(multi_platform_pos)
        # All items are Espresso at ₹80 revenue, qty=1
        # Dine-in: 40 orders × ₹80 = ₹3,200
        di = next(r for r in result if r["platform"] == "Dine-in")
        assert di["revenue"] == pytest.approx(40 * 80.0)

    def test_orders_counted_as_quantity(self, multi_platform_pos):
        result = platform_breakdown(multi_platform_pos)
        di = next(r for r in result if r["platform"] == "Dine-in")
        assert di["orders"] == 40

    def test_empty_data_returns_empty_list(self):
        assert platform_breakdown([]) == []

    def test_single_platform(self):
        data = [{"date": "2026-05-01", "item_name": "Coffee",
                 "quantity": 3.0, "revenue": 360.0, "cost": 90.0,
                 "platform": "Zomato"}]
        result = platform_breakdown(data)
        assert len(result) == 1
        assert result[0]["platform"] == "Zomato"
        assert result[0]["orders"] == 3


# ─── category_breakdown ───────────────────────────────────────────────────────

class TestCategoryBreakdown:
    def test_groups_by_category(self, pos_data_7days):
        result = category_breakdown(pos_data_7days)
        cats = {r["category"] for r in result}
        assert "Beverage" in cats
        assert "Main" in cats
        assert "Starter" in cats

    def test_margin_is_correct(self, pos_data_7days):
        result = category_breakdown(pos_data_7days)
        bev = next(r for r in result if r["category"] == "Beverage")
        # Cappuccino: price=120, cost=35, margin=70.8%
        assert bev["margin_pct"] > 60.0

    def test_returns_empty_for_no_data(self):
        assert category_breakdown([]) == []

    def test_revenue_sums_correctly(self, pos_data_7days):
        result = category_breakdown(pos_data_7days)
        total = sum(r["revenue"] for r in result)
        expected = sum(r["revenue"] for r in pos_data_7days)
        assert total == pytest.approx(expected)


# ─── daily_revenue ────────────────────────────────────────────────────────────

class TestDailyRevenue:
    def test_returns_at_most_n_days(self, pos_data_30days):
        result = daily_revenue(pos_data_30days, days=7)
        assert len(result) <= 7

    def test_returns_last_n_days_sorted_asc(self, pos_data_30days):
        result = daily_revenue(pos_data_30days, days=14)
        dates = [r["date"] for r in result]
        assert dates == sorted(dates)

    def test_revenue_aggregated_per_day(self, pos_data_7days):
        result = daily_revenue(pos_data_7days, days=7)
        for row in result:
            assert row["revenue"] > 0
            assert row["orders"] > 0

    def test_avg_order_value_positive(self, pos_data_7days):
        result = daily_revenue(pos_data_7days, days=7)
        for row in result:
            assert row["avg_order_value"] > 0

    def test_empty_data_returns_empty_list(self):
        assert daily_revenue([]) == []


# ─── weekday_forecast ─────────────────────────────────────────────────────────

class TestWeekdayForecast:
    def test_returns_n_days(self, pos_data_30days):
        result = weekday_forecast(pos_data_30days, days=7)
        assert len(result) == 7

    def test_each_row_has_required_keys(self, pos_data_30days):
        result = weekday_forecast(pos_data_30days, days=7)
        required = {"date", "day", "predicted_revenue", "upper", "lower",
                    "predicted_orders", "confidence", "is_weekend"}
        for row in result:
            assert required.issubset(row.keys())

    def test_upper_gt_predicted_gt_lower(self, pos_data_30days):
        result = weekday_forecast(pos_data_30days, days=7)
        for row in result:
            assert row["upper"] >= row["predicted_revenue"] >= row["lower"]

    def test_is_weekend_flag_correct(self, pos_data_30days):
        result = weekday_forecast(pos_data_30days, days=7)
        for row in result:
            d = datetime.strptime(row["date"], "%Y-%m-%d")
            assert row["is_weekend"] == (d.weekday() >= 5)

    def test_empty_data_still_returns_forecasts(self):
        result = weekday_forecast([], days=5)
        assert len(result) == 5


# ─── get_data priority ────────────────────────────────────────────────────────

class TestGetData:
    def test_returns_pos_when_available(self, pos_data_7days):
        original = _ds._pos_data[:]
        _ds._pos_data = pos_data_7days
        try:
            result = get_data()
            assert result is pos_data_7days
        finally:
            _ds._pos_data = original

    def test_falls_back_to_uploaded_data(self, pos_data_7days):
        original_pos      = _ds._pos_data[:]
        original_uploaded = _ds._uploaded_data[:]
        _ds._pos_data      = []
        _ds._uploaded_data = pos_data_7days
        try:
            result = get_data()
            assert result is pos_data_7days
        finally:
            _ds._pos_data      = original_pos
            _ds._uploaded_data = original_uploaded

    def test_returns_empty_when_nothing_loaded(self):
        original_pos      = _ds._pos_data[:]
        original_uploaded = _ds._uploaded_data[:]
        _ds._pos_data      = []
        _ds._uploaded_data = []
        try:
            result = get_data()
            assert result == []
        finally:
            _ds._pos_data      = original_pos
            _ds._uploaded_data = original_uploaded
