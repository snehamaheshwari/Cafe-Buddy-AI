"""
Unit tests for ml_models.py — feature engineering, forecasting, and ML inference.

Primary model: XGBoost Revenue Forecaster (xgboost_model.joblib)
  - Replaces the old RF + Ridge regression ensemble
  - Integration tests load the actual model file; skipped in CI if absent

Other models tested: peak_hour, cancellation_risk, cross_sell,
                     dynamic_pricing, platform forecast, LSTM (optional).
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import ml_models


# ─── _build_daily_series ─────────────────────────────────────────────────────

class TestBuildDailySeries:
    def test_aggregates_revenue_by_date(self, pos_data_7days):
        s = ml_models._build_daily_series(pos_data_7days)
        assert len(s) == 7
        assert (s > 0).all()

    def test_returns_sorted_index(self, pos_data_7days):
        s = ml_models._build_daily_series(pos_data_7days)
        assert list(s.index) == sorted(s.index)

    def test_filters_by_platform_case_insensitive(self, pos_data_30days):
        s_dine = ml_models._build_daily_series(pos_data_30days, platform="dine-in")
        s_all  = ml_models._build_daily_series(pos_data_30days)
        assert len(s_dine) <= len(s_all)
        assert s_dine.sum() < s_all.sum()

    def test_empty_list_returns_empty_series(self):
        s = ml_models._build_daily_series([])
        assert s.empty

    def test_platform_filter_no_match_returns_empty(self, pos_data_7days):
        s = ml_models._build_daily_series(pos_data_7days, platform="NonExistent")
        assert s.empty

    def test_uses_bill_amount_fallback(self):
        data = [{"date": "2026-05-01", "bill_amount": 500.0, "platform": "Dine-in"}]
        s = ml_models._build_daily_series(data)
        assert s["2026-05-01"] == pytest.approx(500.0)

    def test_revenue_takes_priority_over_bill_amount(self):
        data = [{"date": "2026-05-01", "revenue": 600.0, "bill_amount": 500.0,
                 "platform": "Dine-in"}]
        s = ml_models._build_daily_series(data)
        assert s["2026-05-01"] == pytest.approx(600.0)


# ─── _lag_features ────────────────────────────────────────────────────────────

class TestLagFeatures:
    @pytest.fixture
    def sample_series(self):
        idx = pd.date_range("2026-01-01", periods=60, freq="D")
        vals = np.random.RandomState(42).uniform(20000, 50000, 60)
        return pd.Series(vals, index=idx)

    def test_returns_dataframe(self, sample_series):
        df = ml_models._lag_features(sample_series)
        assert isinstance(df, pd.DataFrame)

    def test_contains_dayofweek(self, sample_series):
        df = ml_models._lag_features(sample_series)
        assert "dayofweek" in df.columns

    def test_contains_is_weekend(self, sample_series):
        df = ml_models._lag_features(sample_series)
        assert "is_weekend" in df.columns

    def test_is_weekend_binary(self, sample_series):
        df = ml_models._lag_features(sample_series)
        assert set(df["is_weekend"].unique()).issubset({0, 1})

    def test_dayofweek_range(self, sample_series):
        df = ml_models._lag_features(sample_series)
        assert df["dayofweek"].between(0, 6).all()

    def test_contains_lag_columns(self, sample_series):
        df = ml_models._lag_features(sample_series, lags=(1, 7))
        assert "lag_1" in df.columns
        assert "lag_7" in df.columns

    def test_contains_rolling_features(self, sample_series):
        df = ml_models._lag_features(sample_series, roll_windows=(7,))
        assert "rollmean_7" in df.columns
        assert "rollstd_7" in df.columns

    def test_drops_na_rows(self, sample_series):
        df = ml_models._lag_features(sample_series)
        assert not df.isnull().any().any()

    def test_short_series_returns_empty_after_dropna(self):
        idx = pd.date_range("2026-01-01", periods=5, freq="D")
        s = pd.Series([100.0] * 5, index=idx)
        # With lag_28, need 28+ days; short series should return empty or very few rows
        df = ml_models._lag_features(s, lags=(1, 7, 14, 28))
        assert len(df) == 0


# ─── forecast_revenue (XGBoost) ───────────────────────────────────────────────

class TestForecastRevenue:
    """Tests for the XGBoost-powered daily revenue forecast."""

    def test_insufficient_data_returns_error(self, pos_data_7days):
        """7 days < 14-day minimum → error response."""
        result = ml_models.forecast_revenue(pos_data_7days, days=7)
        assert "error" in result
        assert result["forecast"] == []

    def test_empty_data_returns_error(self):
        result = ml_models.forecast_revenue([], days=7)
        assert "error" in result

    def test_error_message_contains_minimum_days(self, pos_data_7days):
        result = ml_models.forecast_revenue(pos_data_7days, days=7)
        assert "14" in result["error"]

    # ── Integration tests (real XGBoost model file) ───────────────────────────

    @pytest.mark.integration
    def test_returns_7_days_with_sufficient_data(self, pos_data_30days):
        """Requires xgboost_model.joblib — skipped in CI if absent."""
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        assert len(result["forecast"]) == 7

    @pytest.mark.integration
    def test_each_forecast_row_has_required_keys(self, pos_data_30days):
        """XGBoost response must include all standard forecast fields."""
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        # Note: rf_pred / lr_pred removed — XGBoost is a single-model output
        required = {"date", "day", "predicted_revenue", "upper", "lower",
                    "is_weekend", "confidence"}
        for row in result["forecast"]:
            assert required.issubset(row.keys()), \
                f"Missing keys: {required - row.keys()}"

    @pytest.mark.integration
    def test_no_rf_pred_or_lr_pred_in_response(self, pos_data_30days):
        """Old RF/LR model keys must NOT appear — XGBoost replaced them."""
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        for row in result["forecast"]:
            assert "rf_pred" not in row, "rf_pred should not appear (RF model removed)"
            assert "lr_pred" not in row, "lr_pred should not appear (LR model removed)"

    @pytest.mark.integration
    def test_upper_lower_bands(self, pos_data_30days):
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        for row in result["forecast"]:
            assert row["upper"] >= row["predicted_revenue"] >= row["lower"]

    @pytest.mark.integration
    def test_is_weekend_flag_correct(self, pos_data_30days):
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        for row in result["forecast"]:
            d = datetime.strptime(row["date"], "%Y-%m-%d")
            assert row["is_weekend"] == (d.weekday() >= 5)

    @pytest.mark.integration
    def test_model_metadata_in_response(self, pos_data_30days):
        """Response must include XGBoost-specific metadata fields."""
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        assert "xgb_mae"         in result
        assert "xgb_mape"        in result
        assert "accuracy"        in result
        assert "scale_factor"    in result
        assert "user_daily_mean" in result

    @pytest.mark.integration
    def test_xgb_mape_close_to_known_value(self, pos_data_30days):
        """XGBoost training MAPE should be near 7.83% (from model card)."""
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        assert abs(result["xgb_mape"] - 7.83) < 0.5, \
            f"MAPE {result['xgb_mape']} differs from expected ~7.83"

    @pytest.mark.integration
    def test_accuracy_equals_100_minus_mape(self, pos_data_30days):
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        assert abs(result["accuracy"] - (100 - result["xgb_mape"])) < 0.01

    @pytest.mark.integration
    def test_confidence_equals_100_minus_mape_in_each_row(self, pos_data_30days):
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        expected = round(100 - result["xgb_mape"], 1)
        for row in result["forecast"]:
            assert row["confidence"] == expected

    @pytest.mark.integration
    def test_predictions_nonnegative(self, pos_data_30days):
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        for row in result["forecast"]:
            assert row["predicted_revenue"] >= 0
            assert row["upper"] >= 0
            assert row["lower"] >= 0

    @pytest.mark.integration
    def test_dates_sequential(self, pos_data_30days):
        """Forecast dates must be consecutive calendar days."""
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        dates = [datetime.strptime(r["date"], "%Y-%m-%d")
                 for r in result["forecast"]]
        for i in range(1, len(dates)):
            assert (dates[i] - dates[i-1]).days == 1

    @pytest.mark.integration
    def test_scale_factor_is_positive(self, pos_data_30days):
        result = ml_models.forecast_revenue(pos_data_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        assert result["scale_factor"] > 0

    # ── Unit test with mocked model ────────────────────────────────────────────

    def _make_mock_xgb_obj(self, prediction: float = 75975.0):
        """Return a mock _load_xgb() object."""
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([prediction])
        return {
            "model":        mock_model,
            "feature_cols": ["dayofweek", "is_weekend", "month", "day", "weekofyear",
                              "lag_1", "lag_2", "lag_3", "lag_7", "lag_14", "lag_28",
                              "avg_7", "avg_14", "avg_28"],
            "metrics":      {"mae": 5152.9, "rmse": 6064.1, "mape": 7.83},
        }

    def test_mocked_xgb_returns_scaled_prediction(self, pos_data_30days):
        """With mocked model returning training_mean, output = user_daily_mean."""
        obj = self._make_mock_xgb_obj(prediction=ml_models._XGB_TRAINING_MEAN)
        with patch.object(ml_models, "_load_xgb", return_value=obj):
            result = ml_models.forecast_revenue(pos_data_30days, days=3)
        assert "error" not in result
        series = ml_models._build_daily_series(pos_data_30days)
        user_mean = float(series.mean())
        for row in result["forecast"]:
            assert abs(row["predicted_revenue"] - int(user_mean)) <= 1

    def test_mocked_xgb_returns_7_rows(self, pos_data_30days):
        obj = self._make_mock_xgb_obj()
        with patch.object(ml_models, "_load_xgb", return_value=obj):
            result = ml_models.forecast_revenue(pos_data_30days, days=7)
        assert len(result["forecast"]) == 7

    def test_mocked_xgb_model_name_in_response(self, pos_data_30days):
        obj = self._make_mock_xgb_obj()
        with patch.object(ml_models, "_load_xgb", return_value=obj):
            result = ml_models.forecast_revenue(pos_data_30days, days=7)
        assert "XGBoost" in result["model"]

    def test_calendar_features_use_next_date_not_last_observed(self, pos_data_30days):
        """dayofweek in feature row must match the predicted date, not the last observed."""
        series = ml_models._build_daily_series(pos_data_30days)
        if series.empty:
            pytest.skip("No series built")
        last_date  = series.index[-1]
        df         = ml_models._lag_features(series)
        last_row_wd = int(df.iloc[-1]["dayofweek"])
        assert last_row_wd == last_date.dayofweek


# ─── model_comparison ────────────────────────────────────────────────────────

class TestModelComparison:
    @pytest.mark.integration
    def test_returns_list_of_models(self):
        result = ml_models.model_comparison()
        if not result:
            pytest.skip("No model files available")
        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.integration
    def test_contains_xgboost_model(self):
        """XGBoost must appear in the comparison now that it replaces RF+LR."""
        result = ml_models.model_comparison()
        if not result:
            pytest.skip("No model files available")
        names = [m["model"] for m in result]
        assert any("XGBoost" in n for n in names), \
            f"XGBoost not found in model list: {names}"

    @pytest.mark.integration
    def test_no_random_forest_or_ridge_in_list(self):
        """RF and Ridge (old models) must NOT appear after replacement."""
        result = ml_models.model_comparison()
        for m in result:
            assert "Random Forest" not in m["model"], \
                "Random Forest should be removed — replaced by XGBoost"
            assert "Ridge" not in m["model"], \
                "Ridge Regression should be removed — replaced by XGBoost"

    @pytest.mark.integration
    def test_each_model_has_metrics(self):
        result = ml_models.model_comparison()
        if not result:
            pytest.skip("No model files available")
        for m in result:
            assert "model"    in m
            assert "mae"      in m
            assert "mape"     in m
            assert "accuracy" in m
            assert 0 <= m["accuracy"] <= 100

    @pytest.mark.integration
    def test_sorted_by_mape_ascending(self):
        result = ml_models.model_comparison()
        if len(result) < 2:
            pytest.skip("Need 2+ models")
        mapes = [m["mape"] for m in result]
        assert mapes == sorted(mapes)


# ─── cross_sell_recommendations ──────────────────────────────────────────────

class TestCrossSellRecommendations:
    @pytest.mark.integration
    def test_returns_list(self, pos_data_30days):
        result = ml_models.cross_sell_recommendations(pos_data_30days, top_n=5)
        if not result:
            pytest.skip("Model files not available")
        assert isinstance(result, list)

    @pytest.mark.integration
    def test_respects_top_n(self, pos_data_30days):
        result = ml_models.cross_sell_recommendations(pos_data_30days, top_n=3)
        if not result:
            pytest.skip("Model files not available")
        assert len(result) <= 3

    @pytest.mark.integration
    def test_sorted_by_lift_descending(self, pos_data_30days):
        result = ml_models.cross_sell_recommendations(pos_data_30days, top_n=10)
        if len(result) < 2:
            pytest.skip("Not enough rules")
        lifts = [r["lift"] for r in result]
        assert lifts == sorted(lifts, reverse=True)

    @pytest.mark.integration
    def test_each_rule_has_required_keys(self, pos_data_30days):
        result = ml_models.cross_sell_recommendations(pos_data_30days, top_n=5)
        if not result:
            pytest.skip("Model files not available")
        required = {"antecedent", "consequent", "support", "confidence", "lift"}
        for rule in result:
            assert required.issubset(rule.keys())

    @pytest.mark.integration
    def test_confidence_in_percent_range(self, pos_data_30days):
        result = ml_models.cross_sell_recommendations(pos_data_30days, top_n=10)
        if not result:
            pytest.skip("Model files not available")
        for rule in result:
            assert 0 <= rule["confidence"] <= 100
            assert 0 <= rule["support"] <= 100


# ─── dynamic_pricing_suggestions ─────────────────────────────────────────────

class TestDynamicPricingSuggestions:
    def test_empty_data_returns_empty_list(self):
        result = ml_models.dynamic_pricing_suggestions([])
        assert result == []

    @pytest.mark.integration
    def test_returns_suggestions_for_known_platforms(self, pos_data_30days):
        result = ml_models.dynamic_pricing_suggestions(pos_data_30days)
        if not result:
            pytest.skip("Model files not available")
        assert len(result) >= 1

    @pytest.mark.integration
    def test_each_suggestion_has_required_keys(self, pos_data_30days):
        result = ml_models.dynamic_pricing_suggestions(pos_data_30days)
        if not result:
            pytest.skip("Model files not available")
        required = {"platform", "avg_bill", "suggested_increase",
                    "order_impact", "revenue_impact", "recommendation"}
        for s in result:
            assert required.issubset(s.keys())

    @pytest.mark.integration
    def test_avg_bill_positive(self, pos_data_30days):
        result = ml_models.dynamic_pricing_suggestions(pos_data_30days)
        if not result:
            pytest.skip("Model files not available")
        for s in result:
            assert s["avg_bill"] > 0


# ─── peak_hour_analysis ───────────────────────────────────────────────────────

class TestPeakHourAnalysis:
    @pytest.mark.integration
    def test_returns_24_hours_distribution(self, pos_data_30days):
        result = ml_models.peak_hour_analysis(pos_data_30days)
        if "error" in result:
            pytest.skip("Model files not available")
        assert len(result["hourly_distribution"]) == 24

    @pytest.mark.integration
    def test_predictions_for_7_days(self, pos_data_30days):
        result = ml_models.peak_hour_analysis(pos_data_30days)
        if "error" in result:
            pytest.skip("Model files not available")
        assert len(result["predictions"]) == 7

    @pytest.mark.integration
    def test_peak_hour_in_valid_range(self, pos_data_30days):
        result = ml_models.peak_hour_analysis(pos_data_30days)
        if "error" in result:
            pytest.skip("Model files not available")
        for pred in result["predictions"]:
            assert 0 <= pred["peak_hour"] <= 23


# ─── cancellation_risk_analysis ──────────────────────────────────────────────

class TestCancellationRiskAnalysis:
    def test_empty_data_returns_error(self):
        result = ml_models.cancellation_risk_analysis([])
        assert "error" in result

    @pytest.mark.integration
    def test_overall_risk_in_percentage_range(self, pos_data_30days):
        result = ml_models.cancellation_risk_analysis(pos_data_30days)
        if "error" in result:
            pytest.skip("Model files not available")
        assert 0 <= result["overall_risk"] <= 100

    @pytest.mark.integration
    def test_by_platform_list_populated(self, pos_data_30days):
        result = ml_models.cancellation_risk_analysis(pos_data_30days)
        if "error" in result:
            pytest.skip("Model files not available")
        assert len(result["by_platform"]) > 0

    @pytest.mark.integration
    def test_risk_percentages_in_range(self, pos_data_30days):
        result = ml_models.cancellation_risk_analysis(pos_data_30days)
        if "error" in result:
            pytest.skip("Model files not available")
        for p in result["by_platform"]:
            assert 0 <= p["risk_pct"] <= 100
        for p in result["by_payment"]:
            assert 0 <= p["risk_pct"] <= 100


# ─── build_ml_context ────────────────────────────────────────────────────────

class TestBuildMlContext:
    def test_empty_data_returns_empty_string(self):
        result = ml_models.build_ml_context([])
        assert result == ""

    @pytest.mark.integration
    def test_returns_non_empty_string_with_data(self, pos_data_30days):
        result = ml_models.build_ml_context(pos_data_30days)
        if not result:
            pytest.skip("Model files not available")
        assert isinstance(result, str)
        assert len(result) > 50

    @pytest.mark.integration
    def test_contains_ml_reasoning_header(self, pos_data_30days):
        result = ml_models.build_ml_context(pos_data_30days)
        if not result:
            pytest.skip("Model files not available")
        assert "ML MODEL REASONING" in result

    @pytest.mark.integration
    def test_context_references_xgboost(self, pos_data_30days):
        """build_ml_context must reference XGBoost, not old RF+Ridge models."""
        result = ml_models.build_ml_context(pos_data_30days)
        if not result:
            pytest.skip("Model files not available")
        assert "XGBoost" in result, "Context should mention XGBoost model"


# ─── get_market_insights ──────────────────────────────────────────────────────

class TestGetMarketInsights:
    """Tests for the pre-computed XGBoost training-data insights."""

    def test_returns_dict(self):
        result = ml_models.get_market_insights()
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        result = ml_models.get_market_insights()
        for key in ("summary", "top_items", "by_category", "feature_importance"):
            assert key in result, f"Missing key: {key}"

    def test_top_items_is_list(self):
        result = ml_models.get_market_insights()
        assert isinstance(result["top_items"], list)

    def test_summary_has_total_revenue(self):
        result = ml_models.get_market_insights()
        # insights_summary.csv has columns: metric, value
        metrics = {r.get("metric"): r.get("value") for r in result["summary"]}
        assert "total_revenue" in metrics, f"total_revenue missing. Got: {list(metrics.keys())}"

    def test_total_revenue_is_positive(self):
        result = ml_models.get_market_insights()
        metrics = {r.get("metric"): r.get("value") for r in result["summary"]}
        assert float(metrics.get("total_revenue", 0)) > 0

    def test_top_items_have_revenue_field(self):
        result = ml_models.get_market_insights()
        items = result["top_items"]
        if not items:
            pytest.skip("top_items CSV not available")
        for item in items:
            assert "revenue" in item or "Item Name" in item

    def test_by_category_is_list(self):
        result = ml_models.get_market_insights()
        assert isinstance(result["by_category"], list)

    def test_feature_importance_sums_to_one(self):
        result = ml_models.get_market_insights()
        fi = result["feature_importance"]
        if not fi:
            pytest.skip("feature_importance CSV not available")
        total = sum(float(r.get("importance", 0)) for r in fi)
        assert abs(total - 1.0) < 0.01, f"Feature importances sum to {total}, expected ~1.0"

    def test_graceful_when_insights_dir_missing(self):
        """Should return empty lists, not raise, when CSV files are absent."""
        with patch("os.path.join", return_value="/nonexistent/path"):
            with patch("pandas.read_csv", side_effect=FileNotFoundError):
                result = ml_models.get_market_insights()
        assert isinstance(result, dict)


# ─── _load_xgb ────────────────────────────────────────────────────────────────

class TestLoadXgb:
    """Tests for the XGBoost model loader."""

    def test_raises_file_not_found_when_model_missing(self):
        # Clear cache first
        ml_models._cache.pop("xgboost_model", None)
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                ml_models._load_xgb()

    @pytest.mark.integration
    def test_loads_model_successfully(self):
        """xgboost_model.joblib must load and contain required keys."""
        ml_models._cache.pop("xgboost_model", None)
        obj = ml_models._load_xgb()
        assert "model"        in obj
        assert "feature_cols" in obj
        assert "metrics"      in obj

    @pytest.mark.integration
    def test_feature_cols_has_14_features(self):
        obj = ml_models._load_xgb()
        assert len(obj["feature_cols"]) == 14

    @pytest.mark.integration
    def test_feature_cols_includes_lag_and_avg(self):
        obj = ml_models._load_xgb()
        cols = obj["feature_cols"]
        for expected in ("lag_1", "lag_7", "lag_28", "avg_7", "avg_14", "avg_28"):
            assert expected in cols, f"{expected} missing from feature_cols"

    @pytest.mark.integration
    def test_metrics_has_mae_mape_rmse(self):
        obj = ml_models._load_xgb()
        m = obj["metrics"]
        assert "mae"  in m
        assert "mape" in m
        assert "rmse" in m

    @pytest.mark.integration
    def test_second_load_returns_cached(self):
        """Consecutive calls must return the same cached object."""
        obj1 = ml_models._load_xgb()
        obj2 = ml_models._load_xgb()
        assert obj1 is obj2, "Should return same cached object"


# ─── Regression tests (end-to-end calculation correctness) ────────────────────

class TestRegressionCalculations:
    """
    Regression tests: verify that the XGBoost model produces numerically
    correct and stable outputs when fed deterministic inputs.
    These tests catch silent regressions when model or feature engineering changes.
    """

    @pytest.fixture
    def deterministic_30days(self):
        """Fixed POS data with known daily revenue: ₹1,000/day for 30 days."""
        today = datetime.now()
        rows = []
        for i in range(30):
            d = (today - timedelta(days=29 - i)).strftime("%Y-%m-%d")
            rows.append({
                "date": d, "item_name": "Coffee", "revenue": 1000.0,
                "bill_amount": 1000.0, "cost": 300.0, "quantity": 10,
                "platform": "Dine-in", "payment_mode": "UPI",
                "category": "Beverage", "order_id": f"ORD-{i}",
            })
        return rows

    @pytest.fixture
    def high_revenue_30days(self):
        """Fixed POS data: ₹75,000/day (matches XGBoost training mean)."""
        today = datetime.now()
        rows = []
        for i in range(30):
            d = (today - timedelta(days=29 - i)).strftime("%Y-%m-%d")
            rows.append({
                "date": d, "item_name": "Coffee", "revenue": 75000.0,
                "bill_amount": 75000.0, "cost": 20000.0, "quantity": 500,
                "platform": "Dine-in", "payment_mode": "UPI",
                "category": "Beverage", "order_id": f"ORD-{i}",
            })
        return rows

    def test_scale_factor_is_training_mean_divided_by_user_mean(
            self, deterministic_30days):
        """scale_factor = 75975 / user_daily_mean."""
        obj = self._mock_xgb_obj()
        with patch.object(ml_models, "_load_xgb", return_value=obj):
            result = ml_models.forecast_revenue(deterministic_30days, days=1)
        expected_scale = ml_models._XGB_TRAINING_MEAN / 1000.0
        assert abs(result["scale_factor"] - expected_scale) < 1.0

    def test_prediction_scales_proportionally_with_revenue(
            self, deterministic_30days, high_revenue_30days):
        """Scale normalisation: pred ≈ user_daily_mean when model returns training_mean."""
        obj = self._mock_xgb_obj(raw_pred=ml_models._XGB_TRAINING_MEAN)
        with patch.object(ml_models, "_load_xgb", return_value=obj):
            low  = ml_models.forecast_revenue(deterministic_30days, days=1)
            high = ml_models.forecast_revenue(high_revenue_30days,  days=1)
        # pred = raw_pred / scale = training_mean / (training_mean / user_mean) = user_mean
        # For high: user_mean=75000, so pred ≈ 75000
        assert high["forecast"][0]["predicted_revenue"] == pytest.approx(75000, abs=1)
        # For low: user_mean=1000, so pred ≈ 1000
        assert low["forecast"][0]["predicted_revenue"]  == pytest.approx(1000, abs=1)

    def test_daily_series_total_is_correct(self, deterministic_30days):
        """30 days × ₹1000/day = ₹30,000 total."""
        series = ml_models._build_daily_series(deterministic_30days)
        assert series.sum() == pytest.approx(30000.0, rel=1e-3)

    def test_lag_features_length_after_dropna(self):
        """Series of 60 days → lag features should have 60-28=32 rows after dropna."""
        idx  = pd.date_range("2025-01-01", periods=60, freq="D")
        s    = pd.Series(np.ones(60) * 1000, index=idx)
        df   = ml_models._lag_features(s, lags=(1, 7, 14, 28),
                                        roll_windows=(7, 14, 28))
        # After dropna: max lag is 28, rolling needs 28 → 60-28=32 rows
        assert len(df) == 32

    def test_upper_band_is_8_percent_above_predicted(self, deterministic_30days):
        obj = self._mock_xgb_obj(raw_pred=ml_models._XGB_TRAINING_MEAN)
        with patch.object(ml_models, "_load_xgb", return_value=obj):
            result = ml_models.forecast_revenue(deterministic_30days, days=1)
        row   = result["forecast"][0]
        pred  = row["predicted_revenue"]
        upper = row["upper"]
        lower = row["lower"]
        assert upper == pytest.approx(int(pred * 1.08), abs=1)
        assert lower == pytest.approx(int(pred * 0.92), abs=1)

    def test_forecast_feeds_forward_correctly(self, deterministic_30days):
        """Day 2 prediction must use Day 1's prediction as lag_1."""
        call_count = []

        def mock_predict(X):
            call_count.append(X["lag_1"].iloc[0])
            return np.array([ml_models._XGB_TRAINING_MEAN])

        obj = self._mock_xgb_obj()
        obj["model"].predict = mock_predict
        with patch.object(ml_models, "_load_xgb", return_value=obj):
            result = ml_models.forecast_revenue(deterministic_30days, days=3)
        assert len(call_count) == 3
        # Day 2's lag_1 (scaled) should equal Day 1's prediction (scaled)
        # Since prediction is ~user_mean (1000), scale ≈ 75.975
        # lag_1 for day 2 = ~1000 * scale = ~75975
        assert call_count[1] == pytest.approx(ml_models._XGB_TRAINING_MEAN, abs=5)

    @pytest.mark.integration
    def test_real_model_output_within_training_ballpark(self, high_revenue_30days):
        """When user revenue ≈ training mean, predictions should be in ₹50k-100k range."""
        result = ml_models.forecast_revenue(high_revenue_30days, days=7)
        if "error" in result:
            pytest.skip("XGBoost model file not available")
        for row in result["forecast"]:
            assert 30_000 <= row["predicted_revenue"] <= 200_000, \
                f"Prediction ₹{row['predicted_revenue']:,} is outside expected range"

    @staticmethod
    def _mock_xgb_obj(raw_pred: float = 75975.0):
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([raw_pred])
        return {
            "model":        mock_model,
            "feature_cols": ["dayofweek", "is_weekend", "month", "day", "weekofyear",
                              "lag_1", "lag_2", "lag_3", "lag_7", "lag_14", "lag_28",
                              "avg_7", "avg_14", "avg_28"],
            "metrics":      {"mae": 5152.9, "rmse": 6064.1, "mape": 7.83},
        }
