"""
ML Models — load & run inference on the trained café models.
All models live in backend/models/.  Loaded lazily on first use.
"""
from __future__ import annotations

import json
import os
import warnings
import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

_DIR = os.path.join(os.path.dirname(__file__), "models")

# ─── Lazy model cache ─────────────────────────────────────────────────────────

_cache: dict = {}

def _load(name: str):
    if name not in _cache:
        import pickle
        with open(os.path.join(_DIR, name), "rb") as f:
            _cache[name] = pickle.load(f)
    return _cache[name]


# ─── Feature engineering helpers ─────────────────────────────────────────────

def _build_daily_series(pos_data: list, platform: Optional[str] = None) -> pd.Series:
    """Aggregate POS rows → daily revenue pd.Series indexed by date."""
    agg: dict = defaultdict(float)
    for r in pos_data:
        if platform and r.get("platform", "").strip().lower() != platform.lower():
            continue
        agg[r["date"]] += r.get("revenue", r.get("bill_amount", 0))
    if not agg:
        return pd.Series(dtype=float)
    s = pd.Series(agg)
    s.index = pd.to_datetime(s.index)
    return s.sort_index()


def _lag_features(series: pd.Series, lags=(1, 2, 3, 7, 14, 28),
                  roll_windows=(7, 14, 28)) -> pd.DataFrame:
    """Build lag + rolling-mean/std features expected by RF and Linear models."""
    df = pd.DataFrame({"revenue": series})
    df["dayofweek"]  = df.index.dayofweek
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
    df["month"]      = df.index.month
    df["dayofmonth"] = df.index.day
    df["weekofyear"] = df.index.isocalendar().week.astype(int)
    for lag in lags:
        df[f"lag_{lag}"] = df["revenue"].shift(lag)
    for w in roll_windows:
        df[f"rollmean_{w}"] = df["revenue"].shift(1).rolling(w).mean()
        df[f"rollstd_{w}"]  = df["revenue"].shift(1).rolling(w).std()
    return df.dropna()


# ─── 1. Revenue Forecast (Random Forest + Linear Regression) ──────────────────

def forecast_revenue(pos_data: list, days: int = 7) -> dict:
    """Forecast next `days` days using Random Forest and Linear Regression models."""
    series = _build_daily_series(pos_data)
    if series.empty or len(series) < 30:
        return {"error": "Insufficient data (need ≥30 days of POS history)", "forecast": []}

    rf_obj  = _load("random_forest.pkl")
    lr_obj  = _load("linear_regression.pkl")
    rf_model = rf_obj["model"]
    lr_model = lr_obj["model"]
    feature_cols = rf_obj["feature_cols"]

    # Extend series by rolling-forward one day at a time
    extended = series.copy()
    result = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for i in range(1, days + 1):
        next_date = extended.index[-1] + timedelta(days=1)
        wd = next_date.dayofweek

        feat_df = _lag_features(extended)
        if feat_df.empty:
            break
        last_row = feat_df.iloc[[-1]][feature_cols].copy()

        # Calendar features must reflect next_date (not the last observed day)
        for col, val in [
            ("dayofweek",  wd),
            ("is_weekend", 1 if wd >= 5 else 0),
            ("month",      next_date.month),
            ("dayofmonth", next_date.day),
            ("weekofyear", int(next_date.isocalendar()[1])),
        ]:
            if col in last_row.columns:
                last_row[col] = val

        rf_pred  = float(rf_model.predict(last_row)[0])
        lr_pred  = float(lr_model.predict(last_row)[0])
        ensemble = round((rf_pred * 0.6 + lr_pred * 0.4))  # weighted ensemble

        extended[next_date] = ensemble  # feed forward
        result.append({
            "date":              next_date.strftime("%Y-%m-%d"),
            "day":               day_names[wd],
            "predicted_revenue": max(0, int(ensemble)),
            "rf_pred":           max(0, int(rf_pred)),
            "lr_pred":           max(0, int(lr_pred)),
            "upper":             max(0, int(ensemble * 1.08)),
            "lower":             max(0, int(ensemble * 0.92)),
            "is_weekend":        wd >= 5,
            "confidence":        round(100 - rf_obj["metrics"]["mape"], 1),
        })

    # Apply historical weekend uplift if the user's data shows weekends are busier.
    # The training models (IIM campus data) may have an inverted weekend pattern;
    # we correct by blending the model's weekend/weekday ratio toward the observed ratio.
    we_total, we_days = 0.0, set()
    wd_total, wd_days = 0.0, set()
    for dt, rev in series.items():
        if dt.dayofweek >= 5:
            we_total += rev; we_days.add(str(dt))
        else:
            wd_total += rev; wd_days.add(str(dt))
    obs_we_avg = we_total / max(len(we_days), 1)
    obs_wd_avg = wd_total / max(len(wd_days), 1)

    if obs_we_avg > obs_wd_avg and obs_wd_avg > 0:
        hist_ratio = obs_we_avg / obs_wd_avg      # e.g. 1.20 if weekends are 20% busier
        for r in result:
            if r["is_weekend"]:
                # Blend 70% model-based, 30% historical-ratio correction
                corrected = round(r["predicted_revenue"] * (0.7 + 0.3 * hist_ratio))
                r["predicted_revenue"] = max(0, corrected)
                r["upper"]  = max(0, int(corrected * 1.08))
                r["lower"]  = max(0, int(corrected * 0.92))
                r["rf_pred"] = max(0, round(r["rf_pred"] * (0.7 + 0.3 * hist_ratio)))
                r["lr_pred"] = max(0, round(r["lr_pred"] * (0.7 + 0.3 * hist_ratio)))

    return {
        "forecast":          result,
        "model":             "Ensemble (RF 60% + Ridge 40%)",
        "rf_mae":            round(rf_obj["metrics"]["mae"], 0),
        "rf_mape":           round(rf_obj["metrics"]["mape"], 1),
        "lr_mae":            round(lr_obj["metrics"]["mae"], 0),
        "lr_mape":           round(lr_obj["metrics"]["mape"], 1),
        "accuracy":          round(100 - rf_obj["metrics"]["mape"], 1),
        "training_records":  len(series),
        "weekend_uplift_applied": obs_we_avg > obs_wd_avg,
    }


# ─── 2. Platform Forecasting ───────────────────────────────────────────────────

def forecast_by_platform(pos_data: list, days: int = 7) -> list:
    """Forecast per-platform revenue for next `days` days using Ridge models."""
    pf_obj = _load("platform_forecasters.pkl")
    platforms = pf_obj["platforms"]
    results = []

    for plat in platforms:
        series = _build_daily_series(pos_data, platform=plat)
        if series.empty or len(series) < 5:
            continue
        m = pf_obj["models"][plat]
        model     = m["model"]
        lags      = m["lags"]   # e.g. [1, 7, 14, 28]
        forecast  = []

        extended = series.copy()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i in range(1, days + 1):
            n = len(extended)
            feat = {}
            for lag in lags:
                feat[f"lag_{lag}"] = float(extended.iloc[-lag]) if n >= lag else 0.0
            X = pd.DataFrame([feat])
            pred = max(0.0, float(model.predict(X)[0]))
            next_date = extended.index[-1] + timedelta(days=1)
            extended[next_date] = pred
            forecast.append({
                "date": next_date.strftime("%Y-%m-%d"),
                "day":  day_names[next_date.dayofweek],
                "predicted_revenue": int(pred),
            })

        total_hist = round(float(series.sum()), 0)
        results.append({
            "platform":       plat,
            "forecast":       forecast,
            "historical_avg": round(float(series.mean()), 0),
            "total_revenue":  int(total_hist),
        })

    return results


# ─── 3. Peak Hour Analysis ─────────────────────────────────────────────────────

def peak_hour_analysis(pos_data: list) -> dict:
    """Return actual hourly distribution + model-predicted peak hours."""
    ph_obj = _load("peak_hour_classifier.pkl")
    hourly_profile = ph_obj["hourly_profile"]  # {hour: total_orders}

    # Actual distribution from POS data
    actual: dict = defaultdict(int)
    for r in pos_data:
        h = r.get("hour", 12)
        actual[h] = actual.get(h, 0) + 1

    hour_dist = []
    for h in range(24):
        hour_dist.append({
            "hour":         h,
            "label":        f"{h:02d}:00",
            "actual_orders": actual.get(h, 0),
            "model_profile": hourly_profile.get(h, 0),
        })

    # Predict next 7 days peak hours using classifier
    model        = ph_obj["model"]
    feature_cols = ph_obj["feature_cols"]
    predictions  = []
    day_names    = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i in range(7):
        d = datetime.now() + timedelta(days=i + 1)
        X = pd.DataFrame([{
            "DayOfWeek": d.weekday(),
            "IsWeekend": 1 if d.weekday() >= 5 else 0,
            "Month":     d.month,
        }])
        peak_hour = int(model.predict(X[feature_cols])[0])
        predictions.append({
            "date":      d.strftime("%Y-%m-%d"),
            "day":       day_names[d.weekday()],
            "peak_hour": peak_hour,
            "peak_label": f"{peak_hour:02d}:00–{peak_hour+1:02d}:00",
            "is_weekend": d.weekday() >= 5,
        })

    # Top 3 busiest hours from actual data
    if actual:
        top_hours = sorted(actual.items(), key=lambda x: -x[1])[:3]
    else:
        top_hours = sorted(hourly_profile.items(), key=lambda x: -x[1])[:3]

    return {
        "hourly_distribution": hour_dist,
        "predictions":         predictions,
        "top_hours":           [{"hour": h, "orders": c} for h, c in top_hours],
    }


# ─── 4. Cancellation Risk ─────────────────────────────────────────────────────

def cancellation_risk_analysis(pos_data: list) -> dict:
    """Compute cancellation risk by platform / payment mode / customer type."""
    cc_obj  = _load("cancellation_classifier.pkl")
    model   = cc_obj["model"]
    encoder = cc_obj["encoder"]
    cat_cols = cc_obj["cat_cols"]   # ['Platform','Customer_Type','Payment_Mode','Discount_Name','Repeat_Customer']
    num_cols = cc_obj["num_cols"]   # ['Gross_Amount','Discount_Value','Net_Amount','Hour','DayOfWeek','IsWeekend','Month']
    feature_names = cc_obj["feature_names"]

    if not pos_data:
        return {"error": "No POS data", "by_platform": [], "by_payment": [], "overall_risk": 0}

    # Aggregate sample orders to compute risk by segment
    platform_groups: dict = defaultdict(list)
    payment_groups:  dict = defaultdict(list)

    for r in pos_data:
        plat = r.get("platform", "Dine-in").strip()
        pay  = r.get("payment_mode", "Cash").strip()
        platform_groups[plat].append(r)
        payment_groups[pay].append(r)

    def _predict_risk(group: list) -> float:
        rows = []
        for r in group[:200]:   # cap at 200 for speed
            bill   = float(r.get("bill_amount", r.get("revenue", 300)))
            disc   = float(r.get("discount") or 0)
            hour   = int(r.get("hour", 12))
            dow    = datetime.strptime(r["date"], "%Y-%m-%d").weekday() if r.get("date") else 3
            month  = datetime.strptime(r["date"], "%Y-%m-%d").month if r.get("date") else 5
            rows.append({
                "Platform":        r.get("platform", "Dine-In"),
                "Customer_Type":   "Casual",
                "Payment_Mode":    r.get("payment_mode", "Cash"),
                "Discount_Name":   "No Discount" if disc == 0 else "Zomato Offer",
                "Repeat_Customer": "Yes" if str(r.get("repeat","")).lower() in ("yes","true","1","repeat") else "No",
                "Gross_Amount":    bill,
                "Discount_Value":  disc,
                "Net_Amount":      bill - disc,
                "Hour":            hour,
                "DayOfWeek":       dow,
                "IsWeekend":       1 if dow >= 5 else 0,
                "Month":           month,
            })
        if not rows:
            return 0.0
        df = pd.DataFrame(rows)
        # One-hot encode cat cols
        try:
            cat_enc = encoder.transform(df[cat_cols])
            cat_df  = pd.DataFrame(cat_enc, columns=encoder.get_feature_names_out(cat_cols))
        except Exception:
            return 0.0
        num_df = df[num_cols].reset_index(drop=True)
        X = pd.concat([num_df, cat_df], axis=1)
        # Align to expected feature names
        for col in feature_names:
            if col not in X.columns:
                X[col] = 0
        X = X[feature_names]
        probs = model.predict_proba(X)[:, 1]
        return round(float(probs.mean()) * 100, 1)

    by_platform = []
    for plat, grp in sorted(platform_groups.items()):
        risk = _predict_risk(grp)
        by_platform.append({"platform": plat, "risk_pct": risk, "orders": len(grp)})

    by_payment = []
    for pay, grp in sorted(payment_groups.items()):
        risk = _predict_risk(grp)
        by_payment.append({"payment_mode": pay, "risk_pct": risk, "orders": len(grp)})

    overall = round(sum(r["risk_pct"] * r["orders"] for r in by_platform) /
                    max(sum(r["orders"] for r in by_platform), 1), 1)

    return {
        "overall_risk":  overall,
        "by_platform":   sorted(by_platform, key=lambda x: -x["risk_pct"]),
        "by_payment":    sorted(by_payment,  key=lambda x: -x["risk_pct"]),
        "model_auc":     round(cc_obj["auc"] * 100, 1),
    }


# ─── 5. Cross-sell Recommendations ────────────────────────────────────────────

def cross_sell_recommendations(pos_data: list, top_n: int = 10) -> list:
    """Return top cross-sell rules sorted by lift."""
    cs_obj = _load("cross_sell_rules.pkl")
    rules  = cs_obj["rules"]

    # Gather items actually present in POS data
    pos_items = {r.get("item_name", "").lower().strip() for r in pos_data}

    enriched = []
    for rule in rules:
        enriched.append({
            "antecedent":  rule.get("antecedent", ""),
            "consequent":  rule.get("consequent", ""),
            "support":     round(rule.get("support", 0) * 100, 1),
            "confidence":  round(rule.get("confidence", 0) * 100, 1),
            "lift":        round(rule.get("lift", 1.0), 2),
        })

    # Sort by lift descending, return top N
    return sorted(enriched, key=lambda x: -x["lift"])[:top_n]


# ─── 6. Dynamic Pricing Suggestions ───────────────────────────────────────────

def dynamic_pricing_suggestions(pos_data: list) -> list:
    """Compute price adjustment suggestions using demand elasticity model."""
    dp_obj      = _load("dynamic_pricing.pkl")
    elasticities = dp_obj["elasticities"]  # {'Dine-In': {'orders_per_pp_discount': -0.006, 'intercept': 6.81}}

    if not pos_data:
        return []

    # Current avg bill per platform
    plat_rev: dict  = defaultdict(float)
    plat_cnt: dict  = defaultdict(int)
    for r in pos_data:
        plat = r.get("platform", "Dine-in").strip()
        plat_rev[plat] += r.get("bill_amount", r.get("revenue", 0))
        plat_cnt[plat] += 1

    suggestions = []
    for plat, elast in elasticities.items():
        if plat_cnt.get(plat, 0) == 0:
            continue
        avg_bill = plat_rev[plat] / plat_cnt[plat]
        orders   = plat_cnt[plat]
        slope    = elast.get("orders_per_pp_discount", 0)
        # Slope is negative: each ₹1 increase in price → slope change in daily orders
        # Suggest 5% price increase and show order impact
        price_increase = round(avg_bill * 0.05, 0)
        order_impact   = round(slope * price_increase, 1)  # negative means fewer orders
        rev_impact     = round((price_increase * orders / 30) + (order_impact * avg_bill / 30), 0)
        suggestions.append({
            "platform":        plat,
            "avg_bill":        round(avg_bill, 0),
            "orders":          orders,
            "suggested_increase": f"+5% (₹{price_increase:.0f})",
            "order_impact":    f"{order_impact:+.1f} orders/day",
            "revenue_impact":  f"{'+' if rev_impact >= 0 else ''}₹{abs(int(rev_impact))}/month",
            "elasticity_slope": slope,
            "recommendation":  "Increase" if rev_impact > 0 else "Hold",
        })

    return sorted(suggestions, key=lambda x: -x["orders"])


# ─── 7. LSTM Forecast (optional — needs TensorFlow) ──────────────────────────

def lstm_forecast(pos_data: list, days: int = 7) -> Optional[list]:
    """Run LSTM model if TensorFlow is available."""
    try:
        import tensorflow as tf  # noqa
    except ImportError:
        return None

    series = _build_daily_series(pos_data)
    if len(series) < 21:
        return None

    with open(os.path.join(_DIR, "lstm_config.json")) as f:
        cfg = json.load(f)
    window = cfg.get("window", 21)

    scaler = _load("lstm_scaler.pkl")
    model_path = os.path.join(_DIR, "lstm.keras")
    try:
        model = tf.keras.models.load_model(model_path)
    except Exception:
        return None

    vals   = series.values.reshape(-1, 1)
    scaled = scaler.transform(vals)
    seq    = scaled[-window:].reshape(1, window, 1)

    result = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i in range(days):
        pred_scaled = model.predict(seq, verbose=0)[0, 0]
        pred = float(scaler.inverse_transform([[pred_scaled]])[0, 0])
        next_date = series.index[-1] + timedelta(days=i + 1)
        result.append({
            "date":              next_date.strftime("%Y-%m-%d"),
            "day":               day_names[next_date.dayofweek],
            "predicted_revenue": max(0, int(pred)),
        })
        seq = np.append(seq[0, 1:, :], [[pred_scaled]], axis=0).reshape(1, window, 1)

    return result


# ─── 8. Model Comparison Summary ─────────────────────────────────────────────

def model_comparison() -> list:
    """Return accuracy metrics for all available forecasting models."""
    models = []
    try:
        rf  = _load("random_forest.pkl")
        models.append({
            "model": "Random Forest", "type": "Ensemble",
            "mae": round(rf["metrics"]["mae"], 0),
            "rmse": round(rf["metrics"]["rmse"], 0),
            "mape": round(rf["metrics"]["mape"], 1),
            "accuracy": round(100 - rf["metrics"]["mape"], 1),
        })
    except Exception:
        pass
    try:
        lr  = _load("linear_regression.pkl")
        models.append({
            "model": "Ridge Regression", "type": "Linear",
            "mae": round(lr["metrics"]["mae"], 0),
            "rmse": round(lr["metrics"]["rmse"], 0),
            "mape": round(lr["metrics"]["mape"], 1),
            "accuracy": round(100 - lr["metrics"]["mape"], 1),
        })
    except Exception:
        pass
    try:
        cfg = json.load(open(os.path.join(_DIR, "lstm_config.json")))
        models.append({
            "model": "LSTM (Neural Net)", "type": "Deep Learning",
            "mae": round(cfg["metrics"]["mae"], 0),
            "rmse": round(cfg["metrics"]["rmse"], 0),
            "mape": round(cfg["metrics"]["mape"], 1),
            "accuracy": round(100 - cfg["metrics"]["mape"], 1),
        })
    except Exception:
        pass
    return sorted(models, key=lambda x: x["mape"])


# ─── ML Context for Chatbot ───────────────────────────────────────────────────

def build_ml_context(pos_data: list) -> str:
    """Build a concise ML model reasoning block for chatbot context."""
    if not pos_data:
        return ""
    lines = ["── ML MODEL REASONING ─────────────────────────────────────"]

    # Revenue forecast
    try:
        fc = forecast_revenue(pos_data, days=3)
        if fc.get("forecast"):
            lines.append(f"Revenue Forecast (RF+Ridge Ensemble, MAPE {fc['rf_mape']}%):")
            for d in fc["forecast"]:
                lines.append(f"  {d['day']} {d['date']}: ₹{d['predicted_revenue']:,} "
                             f"(range ₹{d['lower']:,}–₹{d['upper']:,})")
    except Exception:
        pass

    # Peak hours
    try:
        ph = peak_hour_analysis(pos_data)
        if ph.get("top_hours"):
            top = ph["top_hours"]
            lines.append(f"Peak Hours (RF classifier): "
                        + ", ".join(f"{h['hour']:02d}:00 ({h['orders']} orders)" for h in top))
    except Exception:
        pass

    # Cancellation risk
    try:
        cr = cancellation_risk_analysis(pos_data)
        if not cr.get("error"):
            lines.append(f"Cancellation Risk (RF, AUC {cr['model_auc']}%): "
                        f"Overall {cr['overall_risk']}%")
            for p in cr.get("by_platform", [])[:3]:
                lines.append(f"  {p['platform']}: {p['risk_pct']}% risk")
    except Exception:
        pass

    # Cross-sell
    try:
        cs = cross_sell_recommendations(pos_data, top_n=3)
        if cs:
            lines.append("Top Cross-sell Rules:")
            for r in cs:
                lines.append(f"  {r['antecedent']} → {r['consequent']} "
                             f"(lift {r['lift']}, conf {r['confidence']}%)")
    except Exception:
        pass

    lines.append("───────────────────────────────────────────────────────────")
    return "\n".join(lines)
