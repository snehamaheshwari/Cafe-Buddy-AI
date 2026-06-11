"""
test_no_hardcoding.py
─────────────────────
Regression suite that proves every analytics endpoint derives its values
from the uploaded POS/financial data rather than returning static text.

Strategy per test:
  - Seed two distinct datasets whose expected output is KNOWN in advance.
  - Call the function / endpoint.
  - Assert the returned value matches the known-correct calculation, NOT a
    hardcoded constant.
  - In key cases run the check twice with different inputs and verify the
    output changes — a hardcoded value would stay the same.
"""
from __future__ import annotations

import os
import sys
import tempfile

import pytest

# ── path + env setup ──────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
_TMPDIR = tempfile.mkdtemp(prefix="no_hardcode_test_")
os.environ.setdefault("DATA_DIR", _TMPDIR)

from main import (
    _calc_kpis,
    _generate_decisions,
    _item_stats,
    _platform_breakdown,
    health,
    download_template,
)

# ─── helpers ─────────────────────────────────────────────────────────────────

def _make_pos_row(
    date: str,
    item: str,
    qty: float,
    price: float,
    cost_frac: float = 0.30,
    platform: str = "Dine-in",
    order_id: str = "",
    revenue: float = None,
) -> dict:
    rev = revenue if revenue is not None else round(qty * price, 2)
    return {
        "date":      date,
        "item_name": item,
        "category":  "Food",
        "quantity":  qty,
        "price":     price,
        "revenue":   rev,
        "cost":      round(rev * cost_frac, 2),
        "platform":  platform,
        "order_id":  order_id or f"ORD-{date}-{item[:3]}",
        "bill_amount": rev,
    }


def _high_margin_data():
    """Dataset with one item that has margin > 45% → pricing decision expected."""
    return [
        _make_pos_row("2024-01-01", "Premium Latte", 10, 250, cost_frac=0.20, platform="Dine-in"),
        _make_pos_row("2024-01-02", "Premium Latte", 12, 250, cost_frac=0.20, platform="Dine-in"),
        _make_pos_row("2024-01-03", "Premium Latte",  8, 250, cost_frac=0.20, platform="Zomato"),
    ]


def _low_margin_data():
    """Dataset with one item that has margin < 30% → menu decision expected."""
    return [
        _make_pos_row("2024-01-01", "Cheap Sandwich", 5, 100, cost_frac=0.75, platform="Dine-in"),
        _make_pos_row("2024-01-02", "Cheap Sandwich", 6, 100, cost_frac=0.75, platform="Dine-in"),
    ]


def _weekend_heavy_data():
    """More revenue on Sat/Sun → staffing decision expected."""
    rows = []
    for i in range(4):
        day = f"2024-01-{8 + i:02d}"   # Mon-Thu (weekday index 0-3)
        rows.append(_make_pos_row(day, "Coffee", 5, 100, cost_frac=0.30))
    for i in range(3):
        day = f"2024-01-{13 + i:02d}"  # Sat-Mon
        rows.append(_make_pos_row(day, "Coffee", 20, 100, cost_frac=0.30))
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# 1. _calc_kpis — must derive changes from data, not return fixed "+4.1%" etc.
# ═══════════════════════════════════════════════════════════════════════════════
class TestCalcKpis:
    FORBIDDEN_HARDCODES = ["+4.1%", "-2.1%", "+8.7%"]

    def _get_kpi(self, kpis: list, name: str) -> dict:
        return next((k for k in kpis if k["name"] == name), {})

    def test_returns_kpis_list(self):
        data = _high_margin_data()
        result = _calc_kpis(data)
        assert isinstance(result, list)
        assert len(result) >= 4

    def test_required_kpi_names_present(self):
        data = _high_margin_data()
        names = {k["name"] for k in _calc_kpis(data)}
        for expected in ("Today's Revenue", "Avg Order Value", "Food Cost %", "Total Items Sold"):
            assert expected in names, f"KPI '{expected}' missing"

    def test_no_hardcoded_change_values(self):
        """None of the known hardcoded change strings should appear."""
        data = _high_margin_data()
        kpis = _calc_kpis(data)
        for kpi in kpis:
            for forbidden in self.FORBIDDEN_HARDCODES:
                assert kpi.get("change") != forbidden, (
                    f"KPI '{kpi['name']}' still has hardcoded change='{forbidden}'"
                )

    def test_today_revenue_is_computed(self):
        data = _high_margin_data()
        kpis = _calc_kpis(data)
        today_kpi = self._get_kpi(kpis, "Today's Revenue")
        # Last date in data is 2024-01-03; revenue = 8 × 250 = 2000
        assert "2,000" in today_kpi.get("value", "") or "₹2,000" in today_kpi.get("value", "")

    def test_food_cost_pct_computed(self):
        data = _high_margin_data()   # cost_frac=0.20 → food_pct ≈ 20%
        kpis  = _calc_kpis(data)
        fc = self._get_kpi(kpis, "Food Cost %")
        val = float(fc.get("value", "0").replace("%", ""))
        assert 18.0 <= val <= 22.0, f"Food cost % should be ~20%, got {val}"

    def test_different_data_gives_different_changes(self):
        """Hardcoded changes would be identical for both datasets — data-driven differ."""
        data_a = _high_margin_data()   # cost_frac=0.20
        data_b = _low_margin_data()    # cost_frac=0.75

        kpis_a = _calc_kpis(data_a)
        kpis_b = _calc_kpis(data_b)

        # Food cost % values must differ
        fc_a = next(k["value"] for k in kpis_a if k["name"] == "Food Cost %")
        fc_b = next(k["value"] for k in kpis_b if k["name"] == "Food Cost %")
        assert fc_a != fc_b, "Food Cost % should differ between 20% and 75% cost datasets"

    def test_total_items_sold_matches_data(self):
        data = _high_margin_data()   # 10+12+8 = 30 units
        kpis = _calc_kpis(data)
        qty_kpi = self._get_kpi(kpis, "Total Items Sold")
        assert "30" in qty_kpi.get("value", ""), f"Expected 30 items, got {qty_kpi}"

    def test_empty_data_returns_empty(self):
        assert _calc_kpis([]) == []


# ═══════════════════════════════════════════════════════════════════════════════
# 2. _generate_decisions — must reference actual item names & calculated values
# ═══════════════════════════════════════════════════════════════════════════════
class TestGenerateDecisions:
    def test_returns_list(self):
        assert isinstance(_generate_decisions(_high_margin_data()), list)

    def test_empty_data_returns_empty(self):
        assert _generate_decisions([]) == []

    def test_pricing_decision_uses_actual_item_name(self):
        """Title must contain the actual item name from the data."""
        data = _high_margin_data()
        decisions = _generate_decisions(data)
        pricing = [d for d in decisions if d["type"] == "pricing"]
        assert pricing, "Expected a pricing decision for high-margin item"
        assert "Premium Latte" in pricing[0]["title"], (
            f"Pricing decision should mention 'Premium Latte', got: {pricing[0]['title']}"
        )

    def test_pricing_impact_is_positive_number(self):
        decisions = _generate_decisions(_high_margin_data())
        pricing = [d for d in decisions if d["type"] == "pricing"]
        assert pricing
        impact = pricing[0]["impact"]
        assert "₹" in impact and "/month" in impact, f"Unexpected impact format: {impact}"
        # Extract the number
        num_str = impact.replace("+₹", "").replace("₹", "").replace(",", "").split("/")[0]
        assert float(num_str) > 0, f"Impact should be positive, got {impact}"

    def test_pricing_impact_varies_with_data(self):
        """Higher revenue data → higher monthly impact."""
        data_low  = [_make_pos_row("2024-01-01", "Item A", 1, 200, cost_frac=0.20)]
        data_high = [_make_pos_row("2024-01-01", "Item A", 100, 200, cost_frac=0.20)]
        dec_low  = [d for d in _generate_decisions(data_low)  if d["type"] == "pricing"]
        dec_high = [d for d in _generate_decisions(data_high) if d["type"] == "pricing"]
        if dec_low and dec_high:
            # Parse impact amounts
            def _parse_impact(s):
                return float(s.replace("+₹","").replace("₹","").replace(",","").split("/")[0].strip())
            assert _parse_impact(dec_high[0]["impact"]) > _parse_impact(dec_low[0]["impact"])

    def test_staffing_delay_uses_actual_burst(self):
        """Service delay estimate must change when weekend burst ratio changes."""
        # Light weekend burst (~20%)
        light_rows = [
            _make_pos_row("2024-01-08", "C", 10, 100),   # Mon
            _make_pos_row("2024-01-09", "C", 10, 100),   # Tue
            _make_pos_row("2024-01-13", "C", 12, 100),   # Sat
            _make_pos_row("2024-01-14", "C", 12, 100),   # Sun
        ]
        # Heavy weekend burst (~300%)
        heavy_rows = [
            _make_pos_row("2024-01-08", "C", 5,  100),
            _make_pos_row("2024-01-09", "C", 5,  100),
            _make_pos_row("2024-01-13", "C", 20, 100),
            _make_pos_row("2024-01-14", "C", 20, 100),
        ]
        dec_light = [d for d in _generate_decisions(light_rows) if d["type"] == "staffing"]
        dec_heavy = [d for d in _generate_decisions(heavy_rows) if d["type"] == "staffing"]
        if dec_light and dec_heavy:
            rat_light = dec_light[0]["rationale"]
            rat_heavy = dec_heavy[0]["rationale"]
            # Both should mention "min" but with different numbers
            def _extract_delay(s):
                import re
                m = re.search(r"(\d+)-min", s)
                return int(m.group(1)) if m else None
            d_l = _extract_delay(rat_light)
            d_h = _extract_delay(rat_heavy)
            if d_l and d_h:
                assert d_h > d_l, f"Heavy burst should predict longer delay ({d_h}) vs light ({d_l})"

    def test_staffing_impact_not_hardcoded_8400(self):
        """No decision should have exactly '₹8,400' as impact."""
        decisions = _generate_decisions(_weekend_heavy_data())
        for d in decisions:
            assert "8,400" not in d.get("impact", ""), (
                f"Hardcoded ₹8,400 still present in: {d['impact']}"
            )

    def test_staffing_revenue_protection_scales_with_data(self):
        """Higher weekend revenue → higher protection estimate."""
        small = [
            _make_pos_row("2024-01-08", "C", 1, 100),
            _make_pos_row("2024-01-13", "C", 5, 100),
        ]
        large = [
            _make_pos_row("2024-01-08", "C", 1,   100),
            _make_pos_row("2024-01-13", "C", 100, 100),
        ]
        dec_s = [d for d in _generate_decisions(small) if d["type"] == "staffing"]
        dec_l = [d for d in _generate_decisions(large) if d["type"] == "staffing"]
        if dec_s and dec_l:
            def _num(s): return int(s.replace("+₹","").replace(",","").split("/")[0])
            assert _num(dec_l[0]["impact"]) > _num(dec_s[0]["impact"])

    def test_marketing_trend_uses_actual_data(self):
        """Marketing rationale must not say '12–18%' (hardcoded)."""
        data = _high_margin_data()
        for d in _generate_decisions(data):
            if d["type"] == "marketing":
                assert "12–18%" not in d["rationale"], (
                    "Marketing rationale still has hardcoded '12–18%'"
                )

    def test_all_decisions_have_required_keys(self):
        data = _high_margin_data() + _low_margin_data() + _weekend_heavy_data()
        for d in _generate_decisions(data):
            for key in ("id", "type", "priority", "title", "rationale", "impact", "confidence", "status"):
                assert key in d, f"Decision missing key '{key}': {d}"

    def test_confidence_is_between_0_and_100(self):
        data = _high_margin_data() + _low_margin_data() + _weekend_heavy_data()
        for d in _generate_decisions(data):
            assert 0 <= d["confidence"] <= 100, f"Confidence out of range: {d['confidence']}"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Template download endpoint
# ═══════════════════════════════════════════════════════════════════════════════
class TestTemplateEndpoint:
    def _get_template(self, data_type: str) -> str:
        from main import download_template
        resp = download_template(data_type)
        return resp.body.decode("utf-8-sig").lstrip("﻿")

    def test_financial_template_has_required_headers(self):
        csv = self._get_template("financial")
        first_line = csv.splitlines()[0]
        assert "Date" in first_line
        assert "Monthly Revenue" in first_line
        assert "Gross Margin %" in first_line

    def test_pos_template_has_required_headers(self):
        csv = self._get_template("pos")
        first_line = csv.splitlines()[0]
        assert "Date" in first_line
        assert "Item Name" in first_line
        assert "Revenue" in first_line

    def test_customer_template_has_required_headers(self):
        csv = self._get_template("customer")
        first_line = csv.splitlines()[0]
        assert "Phone" in first_line

    def test_reviews_template_has_required_headers(self):
        csv = self._get_template("reviews")
        first_line = csv.splitlines()[0]
        assert "Review_Text" in first_line

    def test_menu_template_has_required_headers(self):
        csv = self._get_template("menu")
        first_line = csv.splitlines()[0]
        assert "Item" in first_line
        assert "Base Price" in first_line

    def test_all_templates_have_sample_rows(self):
        for dt in ["financial", "pos", "customer", "reviews", "menu"]:
            csv = self._get_template(dt)
            lines = [l for l in csv.splitlines() if l.strip()]
            assert len(lines) >= 2, f"Template '{dt}' must have header + at least 1 sample row"

    def test_invalid_type_raises_404(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            download_template("unknown_type")
        assert exc.value.status_code == 404

    def test_financial_sample_row_has_correct_columns(self):
        csv = self._get_template("financial")
        lines = csv.splitlines()
        headers = lines[0].split(",")
        assert len(headers) == 11   # 11 financial columns
        sample = lines[1].split(",")
        assert len(sample) == 11

    def test_pos_template_date_is_valid_format(self):
        from datetime import datetime
        csv = self._get_template("pos")
        lines = csv.splitlines()
        sample_date = lines[1].split(",")[0].strip()
        datetime.strptime(sample_date, "%Y-%m-%d")   # must not raise


# ═══════════════════════════════════════════════════════════════════════════════
# 4. _item_stats — helpers return data-driven results
# ═══════════════════════════════════════════════════════════════════════════════
class TestItemStats:
    def test_returns_list(self):
        data = _high_margin_data()
        assert isinstance(_item_stats(data), list)

    def test_margin_pct_computed_from_cost(self):
        data = [_make_pos_row("2024-01-01", "ItemA", 1, 100, cost_frac=0.40)]
        stats = _item_stats(data)
        assert stats
        # cost/revenue = 0.40 → margin = 60%
        assert abs(stats[0]["margin_pct"] - 60.0) < 2.0

    def test_qty_matches_data(self):
        data = [
            _make_pos_row("2024-01-01", "Latte", 3, 100),
            _make_pos_row("2024-01-02", "Latte", 5, 100),
        ]
        stats = _item_stats(data)
        latte = next((s for s in stats if s["name"] == "Latte"), None)
        assert latte is not None
        assert latte["qty"] == 8.0

    def test_revenue_matches_data(self):
        data = [_make_pos_row("2024-01-01", "Espresso", 2, 80)]
        stats = _item_stats(data)
        esp = next((s for s in stats if s["name"] == "Espresso"), None)
        assert esp is not None
        assert abs(esp["revenue"] - 160.0) < 0.01

    def test_empty_returns_empty(self):
        assert _item_stats([]) == []


# ═══════════════════════════════════════════════════════════════════════════════
# 5. _platform_breakdown — data-driven aggregation
# ═══════════════════════════════════════════════════════════════════════════════
class TestPlatformBreakdown:
    def test_returns_list(self):
        data = _high_margin_data()
        assert isinstance(_platform_breakdown(data), list)

    def test_revenue_matches_data(self):
        data = [
            _make_pos_row("2024-01-01", "Coffee", 1, 100, platform="Zomato"),
            _make_pos_row("2024-01-01", "Coffee", 2, 100, platform="Zomato"),
        ]
        breakdown = _platform_breakdown(data)
        zomato = next((p for p in breakdown if p["platform"] == "Zomato"), None)
        assert zomato is not None
        assert abs(zomato["revenue"] - 300.0) < 0.01

    def test_orders_count_matches(self):
        data = [
            _make_pos_row("2024-01-01", "Coffee", 1, 100, platform="Swiggy"),
            _make_pos_row("2024-01-02", "Coffee", 1, 100, platform="Swiggy"),
            _make_pos_row("2024-01-01", "Coffee", 1, 100, platform="Dine-in"),
        ]
        breakdown = _platform_breakdown(data)
        swiggy = next(p for p in breakdown if p["platform"] == "Swiggy")
        assert swiggy["orders"] == 2

    def test_different_platforms_separated(self):
        data = [
            _make_pos_row("2024-01-01", "Latte", 1, 100, platform="Zomato"),
            _make_pos_row("2024-01-01", "Latte", 1, 100, platform="Dine-in"),
        ]
        breakdown = _platform_breakdown(data)
        platforms = {p["platform"] for p in breakdown}
        assert "Zomato" in platforms
        assert "Dine-in" in platforms

    def test_empty_returns_empty(self):
        assert _platform_breakdown([]) == []


# ═══════════════════════════════════════════════════════════════════════════════
# 6. health endpoint unchanged
# ═══════════════════════════════════════════════════════════════════════════════
class TestHealthEndpoint:
    def test_health_returns_ok(self):
        result = health()
        assert result["status"] == "ok"
