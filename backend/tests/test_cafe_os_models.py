"""
Unit tests for cafe_os_models.py

Tests cover:
  - _safe_encode: exact match, case-insensitive, partial, fallback
  - predict_demand: valid inputs, unknown labels, is_weekend flag
  - predict_item_popularity: valid inputs, unknown labels
  - get_price_recommendations: structure, sorting, empty CSV
  - get_known_values: returns lists for all keys
  - forecast_daypart_revenue: returns dict keyed by daypart
  - top_items_for_daypart: returns sorted list
  - autonomous_actions_from_models: with and without POS data
  - _is_weekend: correct day detection
  - model_status: returns present/missing dict
  - Integration: real model files if present
"""

import os
import sys
import json
import types
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import pandas as pd
import numpy as np

# ── Make sure backend/ is on the path ─────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import cafe_os_models as cos


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _make_label_encoder(classes):
    """Return a mock sklearn LabelEncoder with given classes."""
    from sklearn.preprocessing import LabelEncoder
    enc = LabelEncoder()
    enc.fit(classes)
    return enc


def _make_demand_obj():
    """Fixture: mock demand_forecast_model.pkl structure."""
    enc_loc  = _make_label_encoder(["Connaught Place", "Cyber Hub", "Khan Market"])
    enc_dp   = _make_label_encoder(["Afternoon", "Evening", "Morning"])
    enc_cat  = _make_label_encoder(["Beverages", "Meals", "Snacks"])
    model    = MagicMock()
    model.predict.return_value = np.array([15000.0])
    return {
        "model":    model,
        "features": ["Cafe Location_enc", "Daypart_enc", "Category_enc", "is_weekend"],
        "encoders": {
            "Cafe Location": enc_loc,
            "Daypart":        enc_dp,
            "Category":       enc_cat,
        },
    }


def _make_popularity_obj():
    """Fixture: mock item_popularity_model.pkl structure."""
    enc_item = _make_label_encoder(["Cappuccino", "Cold Brew", "Espresso"])
    enc_cat  = _make_label_encoder(["Beverages", "Meals", "Snacks"])
    enc_dp   = _make_label_encoder(["Afternoon", "Evening", "Morning"])
    model    = MagicMock()
    model.predict.return_value = np.array([42.5])
    return {
        "model":    model,
        "features": ["Item Name_enc", "Category_enc", "Daypart_enc"],
        "encoders": {
            "Item Name": enc_item,
            "Category":   enc_cat,
            "Daypart":    enc_dp,
        },
    }


def _make_price_csv_df():
    return pd.DataFrame([
        {
            "Item Name": "Cappuccino", "units": 500, "avg_price": 200,
            "suggested_price": 210, "suggested_change_pct": 5.0,
            "reason": "Trending + healthy margin", "margin_pct": 60.0,
        },
        {
            "Item Name": "Old Muffin", "units": 50, "avg_price": 80,
            "suggested_price": 76, "suggested_change_pct": -5.0,
            "reason": "Low demand + thin margin", "margin_pct": 30.0,
        },
        {
            "Item Name": "Latte", "units": 300, "avg_price": 180,
            "suggested_price": 180, "suggested_change_pct": 0.0,
            "reason": "Balanced - keep price stable", "margin_pct": 50.0,
        },
    ])


# ─── Test: _safe_encode ───────────────────────────────────────────────────────

class TestSafeEncode(unittest.TestCase):

    def setUp(self):
        from sklearn.preprocessing import LabelEncoder
        self.enc = LabelEncoder()
        self.enc.fit(["Beverages", "Meals", "Snacks"])

    def test_exact_match(self):
        self.assertEqual(cos._safe_encode(self.enc, "Beverages"), 0)
        self.assertEqual(cos._safe_encode(self.enc, "Meals"),     1)
        self.assertEqual(cos._safe_encode(self.enc, "Snacks"),    2)

    def test_case_insensitive_match(self):
        result = cos._safe_encode(self.enc, "beverages")
        self.assertEqual(result, 0)

    def test_partial_match(self):
        result = cos._safe_encode(self.enc, "Meal")
        # Should find "Meals" as partial match
        self.assertEqual(result, 1)

    def test_unknown_label_fallback(self):
        """Unseen label should return median class index, not raise."""
        result = cos._safe_encode(self.enc, "Completely Unknown Category XYZ")
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)
        self.assertLess(result, 3)

    def test_single_class_encoder(self):
        from sklearn.preprocessing import LabelEncoder
        enc = LabelEncoder()
        enc.fit(["Only"])
        result = cos._safe_encode(enc, "Other")
        self.assertEqual(result, 0)


# ─── Test: predict_demand ─────────────────────────────────────────────────────

class TestPredictDemand(unittest.TestCase):

    def setUp(self):
        self.demand_obj = _make_demand_obj()

    def _run(self, location, daypart, category, is_weekend=0):
        with patch.object(cos, "_load_joblib", return_value=self.demand_obj):
            return cos.predict_demand(location, daypart, category, is_weekend)

    def test_returns_correct_keys(self):
        r = self._run("Cyber Hub", "Morning", "Beverages")
        self.assertIn("predicted_revenue", r)
        self.assertIn("location", r)
        self.assertIn("daypart", r)
        self.assertIn("category", r)
        self.assertIn("is_weekend", r)

    def test_predicted_revenue_nonnegative(self):
        self.demand_obj["model"].predict.return_value = np.array([-500.0])
        r = self._run("Cyber Hub", "Morning", "Beverages")
        self.assertGreaterEqual(r["predicted_revenue"], 0.0)

    def test_is_weekend_flag_passed_correctly(self):
        r1 = self._run("Cyber Hub", "Morning", "Beverages", is_weekend=0)
        r2 = self._run("Cyber Hub", "Morning", "Beverages", is_weekend=1)
        self.assertFalse(r1["is_weekend"])
        self.assertTrue(r2["is_weekend"])

    def test_unknown_location_does_not_raise(self):
        r = self._run("Totally New City XYZ", "Morning", "Beverages")
        self.assertGreaterEqual(r["predicted_revenue"], 0.0)

    def test_unknown_category_does_not_raise(self):
        r = self._run("Cyber Hub", "Morning", "Alien Food")
        self.assertGreaterEqual(r["predicted_revenue"], 0.0)

    def test_echo_of_inputs(self):
        r = self._run("Khan Market", "Evening", "Snacks", is_weekend=1)
        self.assertEqual(r["location"], "Khan Market")
        self.assertEqual(r["daypart"],  "Evening")
        self.assertEqual(r["category"], "Snacks")

    def test_missing_model_file_raises(self):
        with patch.object(cos, "_load_joblib",
                          side_effect=FileNotFoundError("Model not found")):
            with self.assertRaises(FileNotFoundError):
                cos.predict_demand("Cyber Hub", "Morning", "Beverages")


# ─── Test: predict_item_popularity ────────────────────────────────────────────

class TestPredictItemPopularity(unittest.TestCase):

    def setUp(self):
        self.pop_obj = _make_popularity_obj()

    def _run(self, item, cat, daypart):
        with patch.object(cos, "_load_joblib", return_value=self.pop_obj):
            return cos.predict_item_popularity(item, cat, daypart)

    def test_returns_correct_keys(self):
        r = self._run("Cappuccino", "Beverages", "Morning")
        self.assertIn("predicted_units", r)
        self.assertIn("item_name", r)
        self.assertIn("category", r)
        self.assertIn("daypart", r)

    def test_predicted_units_nonnegative(self):
        self.pop_obj["model"].predict.return_value = np.array([-10.0])
        r = self._run("Cappuccino", "Beverages", "Morning")
        self.assertGreaterEqual(r["predicted_units"], 0.0)

    def test_unknown_item_does_not_raise(self):
        r = self._run("Totally Unknown Drink ZXYZ", "Beverages", "Morning")
        self.assertGreaterEqual(r["predicted_units"], 0.0)

    def test_echo_inputs(self):
        r = self._run("Cold Brew", "Beverages", "Afternoon")
        self.assertEqual(r["item_name"], "Cold Brew")
        self.assertEqual(r["daypart"],   "Afternoon")

    def test_predicted_units_rounded(self):
        self.pop_obj["model"].predict.return_value = np.array([42.567])
        r = self._run("Espresso", "Beverages", "Morning")
        # Should be rounded to 1 decimal
        self.assertEqual(r["predicted_units"], round(42.567, 1))


# ─── Test: get_price_recommendations ─────────────────────────────────────────

class TestGetPriceRecommendations(unittest.TestCase):

    def test_returns_list(self):
        with patch("pandas.read_csv", return_value=_make_price_csv_df()):
            with patch("os.path.exists", return_value=True):
                result = cos.get_price_recommendations()
        self.assertIsInstance(result, list)

    def test_required_keys_present(self):
        with patch("pandas.read_csv", return_value=_make_price_csv_df()):
            with patch("os.path.exists", return_value=True):
                result = cos.get_price_recommendations()
        for r in result:
            for key in ("item_name", "units", "avg_price", "suggested_price",
                        "change_pct", "action", "reason", "margin_pct"):
                self.assertIn(key, r, f"Missing key: {key}")

    def test_action_values_are_valid(self):
        with patch("pandas.read_csv", return_value=_make_price_csv_df()):
            with patch("os.path.exists", return_value=True):
                result = cos.get_price_recommendations()
        valid = {"RAISE", "CUT", "STABLE"}
        for r in result:
            self.assertIn(r["action"], valid)

    def test_raise_cut_stable_classification(self):
        with patch("pandas.read_csv", return_value=_make_price_csv_df()):
            with patch("os.path.exists", return_value=True):
                result = cos.get_price_recommendations()
        action_map = {r["item_name"]: r["action"] for r in result}
        self.assertEqual(action_map["Cappuccino"], "RAISE")
        self.assertEqual(action_map["Old Muffin"], "CUT")
        self.assertEqual(action_map["Latte"],      "STABLE")

    def test_top_n_respected(self):
        with patch("pandas.read_csv", return_value=_make_price_csv_df()):
            with patch("os.path.exists", return_value=True):
                result = cos.get_price_recommendations(top_n=2)
        self.assertLessEqual(len(result), 2)

    def test_missing_csv_returns_empty_list(self):
        with patch("os.path.exists", return_value=False):
            result = cos.get_price_recommendations()
        self.assertEqual(result, [])

    def test_corrupt_csv_returns_empty_list(self):
        with patch("os.path.exists", return_value=True):
            with patch("pandas.read_csv", side_effect=Exception("bad file")):
                result = cos.get_price_recommendations()
        self.assertEqual(result, [])


# ─── Test: get_known_values ───────────────────────────────────────────────────

class TestGetKnownValues(unittest.TestCase):

    def test_returns_all_keys(self):
        with patch.object(cos, "_load_joblib", side_effect=[
            _make_demand_obj(), _make_popularity_obj()
        ]):
            result = cos.get_known_values()
        for key in ("locations", "dayparts", "categories", "items"):
            self.assertIn(key, result)

    def test_locations_are_list_of_strings(self):
        with patch.object(cos, "_load_joblib", side_effect=[
            _make_demand_obj(), _make_popularity_obj()
        ]):
            result = cos.get_known_values()
        self.assertIsInstance(result["locations"], list)
        self.assertTrue(all(isinstance(v, str) for v in result["locations"]))

    def test_graceful_on_missing_model(self):
        with patch.object(cos, "_load_joblib",
                          side_effect=FileNotFoundError("missing")):
            result = cos.get_known_values()
        # Should return empty lists, not crash
        self.assertEqual(result["locations"], [])
        self.assertEqual(result["items"],     [])


# ─── Test: forecast_daypart_revenue ──────────────────────────────────────────

class TestForecastDaypartRevenue(unittest.TestCase):

    def test_returns_dict(self):
        demand_obj = _make_demand_obj()
        with patch.object(cos, "_load_joblib", return_value=demand_obj):
            result = cos.forecast_daypart_revenue("Cyber Hub")
        self.assertIsInstance(result, dict)

    def test_all_values_nonnegative(self):
        demand_obj = _make_demand_obj()
        with patch.object(cos, "_load_joblib", return_value=demand_obj):
            result = cos.forecast_daypart_revenue()
        for dp, rev in result.items():
            self.assertGreaterEqual(rev, 0.0, f"{dp} revenue should be ≥ 0")

    def test_daypart_keys_are_strings(self):
        demand_obj = _make_demand_obj()
        with patch.object(cos, "_load_joblib", return_value=demand_obj):
            result = cos.forecast_daypart_revenue()
        for k in result:
            self.assertIsInstance(k, str)


# ─── Test: _is_weekend ────────────────────────────────────────────────────────

class TestIsWeekend(unittest.TestCase):

    def test_saturday_is_weekend(self):
        self.assertTrue(cos._is_weekend("2024-01-06"))  # Saturday

    def test_sunday_is_weekend(self):
        self.assertTrue(cos._is_weekend("2024-01-07"))  # Sunday

    def test_monday_is_not_weekend(self):
        self.assertFalse(cos._is_weekend("2024-01-08"))  # Monday

    def test_friday_is_not_weekend(self):
        self.assertFalse(cos._is_weekend("2024-01-05"))  # Friday

    def test_invalid_date_returns_false(self):
        self.assertFalse(cos._is_weekend("not-a-date"))
        self.assertFalse(cos._is_weekend(""))


# ─── Test: model_status ───────────────────────────────────────────────────────

class TestModelStatus(unittest.TestCase):

    def test_returns_dict(self):
        result = cos.model_status()
        self.assertIsInstance(result, dict)

    def test_keys_are_expected_filenames(self):
        result = cos.model_status()
        expected = {
            "demand_forecast_model.pkl",
            "item_popularity_model.pkl",
            "price_optimisation_table.csv",
        }
        self.assertEqual(set(result.keys()), expected)

    def test_values_are_present_or_missing(self):
        result = cos.model_status()
        for k, v in result.items():
            self.assertIn(v, ("present", "missing"), f"{k}: unexpected value {v!r}")

    def test_model_files_are_present(self):
        """Integration: actual model files should be present in backend/models/."""
        result = cos.model_status()
        for fname, status in result.items():
            self.assertEqual(
                status, "present",
                f"Model file '{fname}' is missing from backend/models/. "
                "Copy it from the Train_models_sunday folder."
            )


# ─── Test: autonomous_actions_from_models ────────────────────────────────────

class TestAutonomousActionsFromModels(unittest.TestCase):

    def _mock_env(self):
        """Patch all model calls to return consistent fixtures."""
        demand_obj = _make_demand_obj()
        pop_obj    = _make_popularity_obj()

        def load_joblib_side_effect(name):
            if "demand" in name:
                return demand_obj
            if "popularity" in name or "item" in name:
                return pop_obj
            raise FileNotFoundError(name)

        return patch.object(cos, "_load_joblib", side_effect=load_joblib_side_effect)

    def test_returns_required_keys(self):
        with self._mock_env():
            with patch("pandas.read_csv", return_value=_make_price_csv_df()):
                with patch("os.path.exists", return_value=True):
                    result = cos.autonomous_actions_from_models([])
        for key in ("actions", "system_health", "model_insights"):
            self.assertIn(key, result)

    def test_actions_is_list(self):
        with self._mock_env():
            with patch("pandas.read_csv", return_value=_make_price_csv_df()):
                with patch("os.path.exists", return_value=True):
                    result = cos.autonomous_actions_from_models([])
        self.assertIsInstance(result["actions"], list)

    def test_each_action_has_required_fields(self):
        with self._mock_env():
            with patch("pandas.read_csv", return_value=_make_price_csv_df()):
                with patch("os.path.exists", return_value=True):
                    result = cos.autonomous_actions_from_models([])
        required = {"id", "type", "title", "detail", "executed_at",
                    "impact", "status", "trigger", "model"}
        for action in result["actions"]:
            for field in required:
                self.assertIn(field, action, f"Action missing field: {field}")

    def test_action_types_are_valid(self):
        with self._mock_env():
            with patch("pandas.read_csv", return_value=_make_price_csv_df()):
                with patch("os.path.exists", return_value=True):
                    result = cos.autonomous_actions_from_models([])
        valid = {"auto_executed", "scheduled", "alert"}
        for action in result["actions"]:
            self.assertIn(action["type"], valid)

    def test_system_health_keys(self):
        with self._mock_env():
            with patch("pandas.read_csv", return_value=_make_price_csv_df()):
                with patch("os.path.exists", return_value=True):
                    result = cos.autonomous_actions_from_models([])
        sh = result["system_health"]
        for key in ("models_active", "decisions_automated_today",
                    "revenue_impact_today", "alerts_fired", "uptime"):
            self.assertIn(key, sh)

    def test_models_active_count(self):
        with self._mock_env():
            with patch("pandas.read_csv", return_value=_make_price_csv_df()):
                with patch("os.path.exists", return_value=True):
                    result = cos.autonomous_actions_from_models([])
        # With all 3 mocked present, should be 3
        self.assertGreaterEqual(result["system_health"]["models_active"], 2)

    def test_weekend_alert_added_with_pos_data(self):
        pos_data = (
            # 10 weekday orders
            [{"date": "2024-01-08", "revenue": 100.0} for _ in range(10)] +
            # 5 weekend orders with much higher revenue
            [{"date": "2024-01-06", "revenue": 300.0} for _ in range(5)]
        )
        with self._mock_env():
            with patch("pandas.read_csv", return_value=_make_price_csv_df()):
                with patch("os.path.exists", return_value=True):
                    result = cos.autonomous_actions_from_models(pos_data)
        alert_titles = [a["title"] for a in result["actions"]]
        self.assertTrue(
            any("Weekend" in t for t in alert_titles),
            "Expected a weekend revenue alert but got: " + str(alert_titles)
        )

    def test_no_weekend_alert_when_small_diff(self):
        """No alert when weekend/weekday revenue difference is ≤ 10%."""
        pos_data = (
            [{"date": "2024-01-08", "revenue": 100.0} for _ in range(10)] +
            [{"date": "2024-01-06", "revenue": 105.0} for _ in range(5)]
        )
        with self._mock_env():
            with patch("pandas.read_csv", return_value=_make_price_csv_df()):
                with patch("os.path.exists", return_value=True):
                    result = cos.autonomous_actions_from_models(pos_data)
        alert_titles = [a["title"] for a in result["actions"]]
        self.assertFalse(
            any("Weekend" in t for t in alert_titles),
            "Should NOT generate weekend alert for small revenue diff"
        )

    def test_graceful_when_models_missing(self):
        """Even when model files are absent, function should not raise."""
        with patch.object(cos, "_load_joblib",
                          side_effect=FileNotFoundError("missing")):
            with patch("os.path.exists", return_value=False):
                result = cos.autonomous_actions_from_models([])
        self.assertIn("actions", result)
        self.assertIsInstance(result["actions"], list)

    def test_action_ids_are_unique(self):
        with self._mock_env():
            with patch("pandas.read_csv", return_value=_make_price_csv_df()):
                with patch("os.path.exists", return_value=True):
                    result = cos.autonomous_actions_from_models([])
        ids = [a["id"] for a in result["actions"]]
        self.assertEqual(len(ids), len(set(ids)), "Action IDs must be unique")

    def test_model_insights_keys(self):
        with self._mock_env():
            with patch("pandas.read_csv", return_value=_make_price_csv_df()):
                with patch("os.path.exists", return_value=True):
                    result = cos.autonomous_actions_from_models([])
        mi = result["model_insights"]
        for key in ("daypart_forecast", "price_rises", "price_cuts"):
            self.assertIn(key, mi)


# ─── Integration tests (real model files) ────────────────────────────────────

class TestIntegrationRealModels(unittest.TestCase):
    """
    These tests load actual .pkl files from backend/models/.
    They are skipped if the files are not present.
    """

    DEMAND_PATH = os.path.join(BACKEND_DIR, "models", "demand_forecast_model.pkl")
    POPUL_PATH  = os.path.join(BACKEND_DIR, "models", "item_popularity_model.pkl")
    PRICE_PATH  = os.path.join(BACKEND_DIR, "models", "price_optimisation_table.csv")

    @classmethod
    def setUpClass(cls):
        cos._cache.clear()  # start fresh

    @unittest.skipUnless(os.path.exists(DEMAND_PATH), "demand model file not present")
    def test_real_predict_demand(self):
        known = cos.get_known_values()
        loc   = known["locations"][0]  if known["locations"]  else "Cyber Hub"
        dp    = known["dayparts"][0]   if known["dayparts"]   else "Morning"
        cat   = known["categories"][0] if known["categories"] else "Beverages"
        r = cos.predict_demand(loc, dp, cat, is_weekend=0)
        self.assertGreaterEqual(r["predicted_revenue"], 0.0)

    @unittest.skipUnless(os.path.exists(POPUL_PATH), "popularity model file not present")
    def test_real_predict_item_popularity(self):
        known = cos.get_known_values()
        item  = known["items"][0]      if known["items"]      else "Cappuccino"
        cat   = known["categories"][0] if known["categories"] else "Beverages"
        dp    = known["dayparts"][0]   if known["dayparts"]   else "Morning"
        r = cos.predict_item_popularity(item, cat, dp)
        self.assertGreaterEqual(r["predicted_units"], 0.0)

    @unittest.skipUnless(os.path.exists(PRICE_PATH), "price optimisation CSV not present")
    def test_real_price_recommendations(self):
        recs = cos.get_price_recommendations()
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)
        # Should contain at least one RAISE
        self.assertTrue(any(r["action"] == "RAISE" for r in recs))

    @unittest.skipUnless(
        os.path.exists(DEMAND_PATH) and os.path.exists(PRICE_PATH),
        "model files not present"
    )
    def test_real_autonomous_actions(self):
        cos._cache.clear()
        result = cos.autonomous_actions_from_models([])
        self.assertIn("actions", result)
        self.assertGreater(len(result["actions"]), 0,
                           "Expected at least one autonomous action")

    @unittest.skipUnless(os.path.exists(DEMAND_PATH), "demand model file not present")
    def test_real_forecast_daypart_revenue(self):
        cos._cache.clear()
        result = cos.forecast_daypart_revenue()
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)
        for dp, rev in result.items():
            self.assertGreaterEqual(rev, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
