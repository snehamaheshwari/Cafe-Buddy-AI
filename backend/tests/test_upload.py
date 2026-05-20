"""
Unit tests for multi_upload.py — column detection, parsers, append logic,
and financial percentage auto-fix.
"""
import io
import math
import pytest
import pandas as pd

from multi_upload import (
    _norm, _detect, _safe_float, _safe_str,
    _parse_financial, _parse_pos, _parse_customer,
    FIN_ALIASES, POS_ALIASES, CUST_ALIASES as CUSTOMER_ALIASES,
)


# ─── _norm ────────────────────────────────────────────────────────────────────

class TestNorm:
    def test_lowercases_string(self):
        assert _norm("Revenue") == "revenue"

    def test_strips_leading_trailing_whitespace(self):
        assert _norm("  date  ") == "date"

    def test_collapses_internal_whitespace(self):
        assert _norm("daily   revenue") == "daily revenue"

    def test_strips_non_ascii_printable_chars(self):
        result = _norm("rev\x00enue")
        assert "\x00" not in result

    def test_handles_special_characters(self):
        result = _norm("Gross Margin %")
        assert result == "gross margin %"

    def test_handles_unicode_replacement(self):
        result = _norm("revenue​")  # zero-width space
        assert "revenue" in result

    def test_empty_string(self):
        assert _norm("") == ""


# ─── _detect ─────────────────────────────────────────────────────────────────

class TestDetect:
    COLS = ["Date", "Daily Revenue", "Gross Margin %", "Food Cost %",
            "Labour Cost", "Net Profit %", "Electricity Cost", "Rent",
            "Marketing Spend", "Packaging Cost", "Swiggy Commission"]

    def test_exact_match(self):
        result = _detect(self.COLS, FIN_ALIASES, "date")
        assert result == "Date"

    def test_alias_match_revenue(self):
        result = _detect(self.COLS, FIN_ALIASES, "daily_revenue")
        assert result == "Daily Revenue"

    def test_alias_match_gross_margin(self):
        result = _detect(self.COLS, FIN_ALIASES, "gross_margin")
        assert result == "Gross Margin %"

    def test_alias_match_food_cost(self):
        result = _detect(self.COLS, FIN_ALIASES, "food_cost")
        assert result == "Food Cost %"

    def test_alias_match_commission(self):
        result = _detect(self.COLS, FIN_ALIASES, "commission")
        assert result == "Swiggy Commission"

    def test_returns_none_for_missing_key(self):
        result = _detect(["SomeRandomCol"], FIN_ALIASES, "date")
        assert result is None

    def test_pos_order_id_detection(self):
        cols = ["Order ID", "Item Name", "Quantity", "Platform"]
        result = _detect(cols, POS_ALIASES, "order_id")
        assert result == "Order ID"

    def test_pos_bill_amount_detection(self):
        cols = ["Bill Amount", "GST", "Discount", "Platform"]
        result = _detect(cols, POS_ALIASES, "bill_amount")
        assert result == "Bill Amount"

    def test_substring_match(self):
        cols = ["order_date_time"]
        result = _detect(cols, POS_ALIASES, "timestamp")
        assert result == "order_date_time"


# ─── _safe_float ─────────────────────────────────────────────────────────────

class TestSafeFloat:
    def test_plain_number(self):
        assert _safe_float(123.45) == pytest.approx(123.45)

    def test_string_with_rupee_symbol(self):
        assert _safe_float("₹1,234.56") == pytest.approx(1234.56)

    def test_string_with_percent_sign(self):
        assert _safe_float("32.5%") == pytest.approx(32.5)

    def test_string_with_comma(self):
        assert _safe_float("12,500") == pytest.approx(12500.0)

    def test_nan_returns_default(self):
        assert _safe_float(float("nan")) == 0.0

    def test_none_returns_default(self):
        assert _safe_float(pd.NA) == 0.0

    def test_custom_default(self):
        assert _safe_float(float("nan"), default=-1.0) == -1.0

    def test_invalid_string_returns_default(self):
        assert _safe_float("not a number") == 0.0

    def test_integer_input(self):
        assert _safe_float(42) == pytest.approx(42.0)

    def test_zero_string(self):
        assert _safe_float("0") == 0.0


# ─── _safe_str ────────────────────────────────────────────────────────────────

class TestSafeStr:
    def test_string_value(self):
        assert _safe_str("hello") == "hello"

    def test_strips_whitespace(self):
        assert _safe_str("  hello  ") == "hello"

    def test_nan_returns_default(self):
        assert _safe_str(float("nan")) == ""

    def test_custom_default(self):
        assert _safe_str(float("nan"), default="unknown") == "unknown"

    def test_converts_number_to_string(self):
        assert _safe_str(42) == "42"


# ─── _parse_financial ─────────────────────────────────────────────────────────

class TestParseFinancial:
    def _make_df(self, pct_values, revenue=45000):
        """Build a minimal financial DataFrame."""
        return pd.DataFrame({
            "Date":           ["2026-05-01", "2026-05-02"],
            "Daily Revenue":  [revenue, revenue + 3000],
            "Gross Margin %": pct_values,
            "Food Cost %":    pct_values,
            "Labour Cost %":  pct_values,
            "Net Profit %":   pct_values,
        })

    def test_requires_date_column(self):
        df = pd.DataFrame({"Revenue": [1000], "Gross Margin %": [0.4]})
        with pytest.raises(ValueError, match="Date"):
            _parse_financial(df, "test.csv")

    def test_requires_revenue_column(self):
        df = pd.DataFrame({"Date": ["2026-05-01"], "Gross Margin %": [0.4]})
        with pytest.raises(ValueError, match="[Rr]evenue"):
            _parse_financial(df, "test.csv")

    def test_skips_rows_with_zero_revenue(self):
        df = pd.DataFrame({
            "Date":          ["2026-05-01", "2026-05-02"],
            "Daily Revenue": [0.0, 45000.0],
            "Gross Margin %": [0.4, 0.4],
        })
        records, info = _parse_financial(df, "test.csv")
        assert len(records) == 1
        assert info["skipped"] == 1

    def test_auto_fix_fractional_percentages(self):
        """Excel-stored 0.32 should become 32.0 after auto-fix."""
        df = self._make_df([0.32, 0.31])
        records, _ = _parse_financial(df, "test.xlsx")
        assert all(r["gross_margin_pct"] > 10 for r in records), \
            "Fractional pct (0.32) should be multiplied to 32.0"

    def test_no_auto_fix_when_already_percentage(self):
        """Values already in % form (e.g. 32.0) must NOT be doubled."""
        df = self._make_df([32.0, 31.0])
        records, _ = _parse_financial(df, "test.xlsx")
        assert all(r["gross_margin_pct"] < 100 for r in records)
        assert all(r["gross_margin_pct"] > 10 for r in records)

    def test_auto_fix_median_threshold(self):
        """Median ≤ 1.5 triggers the fix; median > 1.5 does not."""
        df_decimal = self._make_df([0.40, 0.42])
        df_pct     = self._make_df([40.0, 42.0])
        recs_dec, _ = _parse_financial(df_decimal, "d.xlsx")
        recs_pct, _ = _parse_financial(df_pct, "p.xlsx")
        # Both should end up in same range
        assert recs_dec[0]["gross_margin_pct"] == pytest.approx(recs_pct[0]["gross_margin_pct"])

    def test_info_contains_correct_row_count(self):
        df = self._make_df([0.4, 0.4])
        _, info = _parse_financial(df, "test.csv")
        assert info["rows"] == 2

    def test_info_contains_date_range(self):
        df = self._make_df([0.4, 0.4])
        _, info = _parse_financial(df, "test.csv")
        assert "from" in info["date_range"]
        assert "to" in info["date_range"]

    def test_none_columns_stored_as_none(self):
        df = pd.DataFrame({
            "Date": ["2026-05-01"],
            "Daily Revenue": [45000.0],
        })
        records, _ = _parse_financial(df, "test.csv")
        assert records[0]["gross_margin_pct"] is None
        assert records[0]["commission"] is None


# ─── _parse_pos ───────────────────────────────────────────────────────────────

class TestParsePos:
    def _make_pos_df(self):
        return pd.DataFrame({
            "Order ID":    ["O001", "O002", "O003"],
            "Order Date":  ["2026-05-01", "2026-05-01", "2026-05-02"],
            "Item Name":   ["Cappuccino", "Pasta Combo", "Cold Coffee"],
            "Quantity":    [2, 1, 3],
            "Bill Amount": [240, 280, 450],
            "Platform":    ["Dine-in", "Zomato", "Swiggy"],
            "Payment Mode":["UPI", "Card", "Cash"],
        })

    def test_parses_basic_pos_data(self):
        df = self._make_pos_df()
        records, info = _parse_pos(df, "pos.xlsx")
        assert len(records) == 3

    def test_each_record_has_required_fields(self):
        df = self._make_pos_df()
        records, _ = _parse_pos(df, "pos.xlsx")
        required = {"date", "item_name", "quantity", "bill_amount",
                    "platform", "payment_mode", "revenue", "cost"}
        for r in records:
            assert required.issubset(r.keys())

    def test_revenue_equals_bill_amount_when_no_cost(self):
        df = self._make_pos_df()
        records, _ = _parse_pos(df, "pos.xlsx")
        for r in records:
            assert r["revenue"] == r["bill_amount"]

    def test_order_id_captured(self):
        df = self._make_pos_df()
        records, _ = _parse_pos(df, "pos.xlsx")
        order_ids = {r.get("order_id") for r in records}
        assert "O001" in order_ids

    def test_null_date_falls_back_to_today(self):
        """POS parser substitutes today's date when the date cell is empty."""
        from datetime import date
        df = self._make_pos_df()
        df.loc[0, "Order Date"] = None
        records, _ = _parse_pos(df, "pos.xlsx")
        # Row is kept (not skipped) with today as fallback date
        assert len(records) == 3
        today = date.today().strftime("%Y-%m-%d")
        assert records[0]["date"] == today

    def test_info_contains_metadata(self):
        df = self._make_pos_df()
        _, info = _parse_pos(df, "pos.xlsx")
        assert "rows" in info
        assert "filename" in info


# ─── _parse_customer ─────────────────────────────────────────────────────────

class TestParseCustomer:
    def _make_customer_df(self):
        return pd.DataFrame({
            "Customer ID":  ["C001", "C002", "C003"],
            "Name":         ["Alice", "Bob", "Carol"],
            "Phone":        ["9876543210", "9123456780", "9001234567"],
            "Email":        ["a@a.com", "b@b.com", "c@c.com"],
            "Visit Date":   ["2026-05-01", "2026-05-01", "2026-05-02"],
            "Total Spent":  [1200.0, 850.0, 2100.0],
            "Visits":       [3, 1, 7],
        })

    def test_parses_basic_customer_data(self):
        df = self._make_customer_df()
        records, info = _parse_customer(df, "cust.xlsx")
        assert len(records) == 3

    def test_each_record_has_phone(self):
        df = self._make_customer_df()
        records, _ = _parse_customer(df, "cust.xlsx")
        for r in records:
            assert "phone" in r

    def test_info_row_count_matches(self):
        df = self._make_customer_df()
        _, info = _parse_customer(df, "cust.xlsx")
        assert info["rows"] == 3


# ─── POS append dedup logic ───────────────────────────────────────────────────

class TestPosAppendDedup:
    """Test the order_id-based deduplication for append mode."""

    def test_dedup_removes_exact_duplicate_order_ids(self):
        existing = [
            {"order_id": "O001", "item_name": "Coffee", "date": "2026-05-01",
             "revenue": 120.0, "cost": 35.0, "quantity": 1.0, "platform": "Dine-in"},
        ]
        incoming = [
            {"order_id": "O001", "item_name": "Coffee", "date": "2026-05-01",
             "revenue": 120.0, "cost": 35.0, "quantity": 1.0, "platform": "Dine-in"},  # dup
            {"order_id": "O002", "item_name": "Tea", "date": "2026-05-01",
             "revenue": 80.0, "cost": 20.0, "quantity": 1.0, "platform": "Dine-in"},   # new
        ]
        existing_ids = {r["order_id"] for r in existing if r.get("order_id")}
        new_recs = [r for r in incoming if not r.get("order_id") or r["order_id"] not in existing_ids]
        merged = existing + new_recs

        assert len(new_recs) == 1
        assert new_recs[0]["order_id"] == "O002"
        assert len(merged) == 2

    def test_dedup_keeps_all_unique_orders(self):
        existing = [{"order_id": f"O{i:03d}", "item_name": "Item",
                     "date": "2026-05-01", "revenue": 100.0, "cost": 30.0,
                     "quantity": 1.0, "platform": "Dine-in"} for i in range(5)]
        incoming = [{"order_id": f"O{i:03d}", "item_name": "Item",
                     "date": "2026-05-02", "revenue": 100.0, "cost": 30.0,
                     "quantity": 1.0, "platform": "Dine-in"} for i in range(5, 10)]
        existing_ids = {r["order_id"] for r in existing}
        new_recs = [r for r in incoming if r["order_id"] not in existing_ids]
        assert len(new_recs) == 5

    def test_rows_without_order_id_are_always_included(self):
        existing = [{"order_id": "O001", "revenue": 100.0, "cost": 30.0,
                     "quantity": 1.0, "item_name": "X", "date": "2026-05-01",
                     "platform": "Dine-in"}]
        incoming = [{"order_id": None, "revenue": 100.0, "cost": 30.0,
                     "quantity": 1.0, "item_name": "Y", "date": "2026-05-01",
                     "platform": "Dine-in"}]
        existing_ids = {r["order_id"] for r in existing if r.get("order_id")}
        new_recs = [r for r in incoming if not r.get("order_id") or r["order_id"] not in existing_ids]
        assert len(new_recs) == 1


# ─── Customer append phone-merge logic ───────────────────────────────────────

class TestCustomerPhoneMerge:
    """Test phone-based upsert for customer append mode."""

    def _merge(self, existing, incoming):
        phone_map = {r["phone"]: i for i, r in enumerate(existing) if r.get("phone")}
        merged = list(existing)
        new_count, updated_count = 0, 0
        for r in incoming:
            phone = r.get("phone", "")
            if phone and phone in phone_map:
                merged[phone_map[phone]] = r
                updated_count += 1
            else:
                merged.append(r)
                new_count += 1
        return merged, new_count, updated_count

    def test_updates_existing_customer_by_phone(self):
        existing = [{"phone": "9876543210", "name": "Alice", "visits": 3, "total_spent": 1200.0}]
        incoming = [{"phone": "9876543210", "name": "Alice", "visits": 5, "total_spent": 2000.0}]
        merged, new_count, updated_count = self._merge(existing, incoming)
        assert len(merged) == 1
        assert merged[0]["visits"] == 5
        assert updated_count == 1
        assert new_count == 0

    def test_adds_new_customer_with_unknown_phone(self):
        existing = [{"phone": "9876543210", "name": "Alice", "visits": 3, "total_spent": 1200.0}]
        incoming = [{"phone": "9000000001", "name": "Bob", "visits": 1, "total_spent": 400.0}]
        merged, new_count, _ = self._merge(existing, incoming)
        assert len(merged) == 2
        assert new_count == 1

    def test_mixed_update_and_new(self):
        existing = [
            {"phone": "9876543210", "name": "Alice", "visits": 3},
            {"phone": "9123456780", "name": "Bob",   "visits": 1},
        ]
        incoming = [
            {"phone": "9876543210", "name": "Alice", "visits": 5},  # update
            {"phone": "9000000001", "name": "Carol", "visits": 2},  # new
        ]
        merged, new_count, updated_count = self._merge(existing, incoming)
        assert len(merged) == 3
        assert new_count == 1
        assert updated_count == 1

    def test_customer_without_phone_always_added(self):
        existing = [{"phone": "9876543210", "name": "Alice", "visits": 3}]
        incoming = [{"phone": "", "name": "Unknown", "visits": 1}]
        merged, new_count, _ = self._merge(existing, incoming)
        assert len(merged) == 2
        assert new_count == 1
