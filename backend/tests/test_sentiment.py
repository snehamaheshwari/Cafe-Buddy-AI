"""
Unit tests for sentiment_engine.py.
Uses the pre-trained Logistic Regression + TF-IDF + LabelEncoder model.
"""
import pytest
import pandas as pd
from sentiment_engine import SentimentEngine, clean_text


# ─── clean_text ───────────────────────────────────────────────────────────────

class TestCleanText:
    def test_lowercases_input(self):
        assert clean_text("Great Coffee!") == clean_text("great coffee!")

    def test_removes_urls(self):
        result = clean_text("Visit https://example.com for more")
        assert "http" not in result

    def test_removes_at_mentions(self):
        assert "@" not in clean_text("@CafeBuddy is great")

    def test_removes_hashtags(self):
        assert "#" not in clean_text("Love #coffee and #food")

    def test_removes_special_characters(self):
        assert "!" not in clean_text("Amazing food!!!")

    def test_collapses_whitespace(self):
        assert "  " not in clean_text("too    many    spaces")

    def test_removes_short_tokens(self):
        result = clean_text("I am so happy")
        # short tokens (≤2 chars) removed
        assert " I " not in result and " am " not in result

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_strips_numbers(self):
        assert "5" not in clean_text("Rated 5 stars")

    def test_retains_meaningful_words(self):
        result = clean_text("excellent pasta and coffee")
        assert "excellent" in result
        assert "pasta" in result


# ─── SentimentEngine — pre-trained model loads ───────────────────────────────

class TestSentimentEnginePretrainedModel:
    """The engine loads a pre-trained model at init — _fitted must be True."""

    def test_fitted_on_init(self):
        eng = SentimentEngine()
        assert eng._fitted is True

    def test_predict_returns_valid_label(self):
        eng = SentimentEngine()
        label = eng.predict("The food was great and service was quick")
        assert label in ("Positive", "Neutral", "Negative")

    def test_predict_batch_returns_list_of_valid_labels(self):
        eng = SentimentEngine()
        results = eng.predict_batch(["Great food!", "Terrible service", "Okay place"])
        assert len(results) == 3
        assert all(r in ("Positive", "Neutral", "Negative") for r in results)

    def test_predict_batch_empty_returns_empty(self):
        eng = SentimentEngine()
        assert eng.predict_batch([]) == []

    def test_predict_with_confidence_returns_4_tuple(self):
        eng = SentimentEngine()
        result = eng.predict_with_confidence("Best coffee in town!")
        assert len(result) == 4
        label, conf, neg_p, pos_p = result
        assert label in ("Positive", "Neutral", "Negative")
        assert 0.0 <= conf <= 100.0
        assert 0.0 <= neg_p <= 1.0
        assert 0.0 <= pos_p <= 1.0

    def test_confidence_probabilities_sum_to_one_approx(self):
        eng = SentimentEngine()
        _, _, neg_p, pos_p = eng.predict_with_confidence("Amazing ambiance and food")
        # neg + pos <= 1 (neutral takes the rest)
        assert neg_p + pos_p <= 1.01

    def test_predict_returns_string_not_int(self):
        eng = SentimentEngine()
        assert isinstance(eng.predict("Nice place"), str)

    def test_no_data_initially(self):
        eng = SentimentEngine()
        # A fresh engine (after load_state fails) has no records
        eng._records = []
        eng._stats = {}
        assert eng.has_data is False
        assert eng.stats == {}
        assert eng.records == []


# ─── SentimentEngine — process_dataframe ─────────────────────────────────────

def _make_review_df(n: int = 20) -> pd.DataFrame:
    half = n // 2
    return pd.DataFrame({
        "Review_ID":       [f"R{i:03d}" for i in range(n)],
        "Source":          ["Google"] * half + ["Zomato"] * half,
        "Review_Date":     ["2026-05-01"] * n,
        "Cafe_Location":   ["Branch A"] * n,
        "Visit_Type":      ["Dine-In"] * n,
        "Rating":          [5] * half + [1] * half,
        "Sentiment_Label": ["Positive"] * half + ["Negative"] * half,
        "Review_Text":     ["Excellent food, great service, highly recommend"] * half
                           + ["Terrible experience, cold food, rude staff, disappointed"] * half,
    })


class TestProcessDataframe:
    def test_returns_records_list_and_stats_dict(self):
        eng = SentimentEngine()
        records, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        assert isinstance(records, list)
        assert isinstance(stats, dict)

    def test_record_count_matches_input(self):
        eng = SentimentEngine()
        records, _ = eng.process_dataframe(_make_review_df(20), "t.csv")
        assert len(records) == 20

    def test_has_data_true_after_processing(self):
        eng = SentimentEngine()
        eng.process_dataframe(_make_review_df(20), "t.csv")
        assert eng.has_data is True

    def test_stats_total_reviews_correct(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        assert stats["total_reviews"] == 20

    def test_sentiment_counts_sum_to_total(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        assert stats["positive"] + stats["neutral"] + stats["negative"] == stats["total_reviews"]

    def test_percentages_sum_to_100(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        total_pct = stats["positive_pct"] + stats["neutral_pct"] + stats["negative_pct"]
        assert abs(total_pct - 100.0) < 0.6  # allow tiny rounding delta

    def test_satisfaction_score_in_range(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        assert 0 <= stats["satisfaction_score"] <= 100

    def test_avg_rating_in_range(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        assert 1.0 <= stats["overall_avg_rating"] <= 5.0

    def test_nps_in_valid_range(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        assert -100 <= stats["nps"] <= 100

    def test_source_breakdown_present(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        sources = {s["source"] for s in stats["source_breakdown"]}
        assert "Google" in sources and "Zomato" in sources

    def test_keywords_present_for_each_sentiment(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        kw = stats.get("keywords", {})
        assert "positive" in kw and "negative" in kw

    def test_aspect_analysis_present(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        assert "aspect_analysis" in stats
        assert len(stats["aspect_analysis"]) == 5  # 5 aspect dimensions

    def test_aspect_scores_in_range(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        for asp in stats["aspect_analysis"]:
            if asp["total"] > 0:
                assert 0 <= asp["score"] <= 100
                assert 0 <= asp["positive_pct"] <= 100
                assert 0 <= asp["negative_pct"] <= 100

    def test_actionable_insights_present(self):
        eng = SentimentEngine()
        _, stats = eng.process_dataframe(_make_review_df(20), "t.csv")
        assert "actionable_insights" in stats
        assert isinstance(stats["actionable_insights"], list)

    def test_uploaded_label_respected(self):
        """When Sentiment_Label is provided and valid, it should be used."""
        eng = SentimentEngine()
        df = pd.DataFrame({
            "Review_ID":       ["R001"],
            "Source":          ["Google"],
            "Review_Date":     ["2026-05-01"],
            "Cafe_Location":   ["A"],
            "Visit_Type":      ["Dine-In"],
            "Rating":          [5],
            "Sentiment_Label": ["Positive"],
            "Review_Text":     ["Great food"],
        })
        records, _ = eng.process_dataframe(df, "t.csv")
        assert records[0]["sentiment"] == "Positive"

    def test_rating_clamped_1_to_5(self):
        eng = SentimentEngine()
        df = pd.DataFrame({
            "Review_ID":       ["R001", "R002"],
            "Source":          ["Google", "Zomato"],
            "Review_Date":     ["2026-05-01"] * 2,
            "Cafe_Location":   ["A"] * 2,
            "Visit_Type":      ["Dine-In"] * 2,
            "Rating":          [10, -3],
            "Sentiment_Label": ["Positive", "Negative"],
            "Review_Text":     ["Great!", "Terrible!"],
        })
        records, _ = eng.process_dataframe(df, "t.csv")
        for r in records:
            assert 1 <= r["rating"] <= 5

    def test_each_record_has_required_fields(self):
        eng = SentimentEngine()
        records, _ = eng.process_dataframe(_make_review_df(10), "t.csv")
        required = {"review_id", "source", "review_date", "location",
                    "visit_type", "rating", "sentiment", "review_text",
                    "confidence", "neg_prob", "pos_prob"}
        for r in records:
            assert required.issubset(r.keys()), f"Missing keys: {required - r.keys()}"

    def test_confidence_in_range_for_each_record(self):
        eng = SentimentEngine()
        records, _ = eng.process_dataframe(_make_review_df(10), "t.csv")
        for r in records:
            assert 0 <= r["confidence"] <= 100

    def test_empty_review_text_skipped(self):
        eng = SentimentEngine()
        df = pd.DataFrame({
            "Review_ID":       ["R001", "R002"],
            "Source":          ["Google"] * 2,
            "Review_Date":     ["2026-05-01"] * 2,
            "Cafe_Location":   ["A"] * 2,
            "Visit_Type":      ["Dine-In"] * 2,
            "Rating":          [4, 3],
            "Sentiment_Label": ["Positive", ""],
            "Review_Text":     ["Good food", ""],   # second row empty
        })
        records, _ = eng.process_dataframe(df, "t.csv")
        assert len(records) == 1  # empty text skipped


# ─── get_chat_context ────────────────────────────────────────────────────────

class TestGetChatContext:
    def test_empty_returns_empty_string(self):
        eng = SentimentEngine()
        eng._records = []
        eng._stats = {}
        assert eng.get_chat_context() == ""

    def test_returns_string_after_processing(self):
        eng = SentimentEngine()
        eng.process_dataframe(_make_review_df(20), "t.csv")
        ctx = eng.get_chat_context()
        assert isinstance(ctx, str) and len(ctx) > 100

    def test_context_contains_key_sections(self):
        eng = SentimentEngine()
        eng.process_dataframe(_make_review_df(20), "t.csv")
        ctx = eng.get_chat_context()
        assert "SENTIMENT ANALYSIS" in ctx
        assert "ASPECT ANALYSIS" in ctx
        assert "ACTIONABLE INSIGHTS" in ctx

    def test_context_contains_review_count(self):
        eng = SentimentEngine()
        eng.process_dataframe(_make_review_df(20), "t.csv")
        ctx = eng.get_chat_context()
        assert "20" in ctx


# ─── get_decisions ───────────────────────────────────────────────────────────

class TestGetDecisions:
    def _engine_with_high_negative(self):
        eng = SentimentEngine()
        eng._stats = {
            "total_reviews": 100,
            "positive": 50, "positive_pct": 50.0,
            "neutral":  20, "neutral_pct":  20.0,
            "negative": 30, "negative_pct": 30.0,
            "satisfaction_score": 60.0,
            "nps": -10,
            "promoters": 30, "detractors": 40,
            "aspect_analysis": [
                {"aspect": "Service & Staff", "total": 40, "score": 30,
                 "positive": 12, "negative": 20, "positive_pct": 30.0,
                 "negative_pct": 50.0, "status": "critical"},
            ],
            "actionable_insights": [],
        }
        return eng

    def test_empty_stats_returns_empty(self):
        eng = SentimentEngine()
        eng._stats = {}
        assert eng.get_decisions() == []

    def test_high_negative_pct_creates_critical_decision(self):
        eng = self._engine_with_high_negative()
        decisions = eng.get_decisions()
        assert any(d["priority"] == "critical" for d in decisions)

    def test_all_decisions_have_required_keys(self):
        eng = self._engine_with_high_negative()
        decisions = eng.get_decisions()
        required = {"id", "type", "priority", "title", "rationale", "action",
                    "confidence", "impact", "status"}
        for d in decisions:
            missing = required - d.keys()
            assert not missing, f"Missing keys: {missing}"

    def test_confidence_values_in_range(self):
        eng = self._engine_with_high_negative()
        for d in eng.get_decisions():
            assert 0 <= d["confidence"] <= 100

    def test_decision_ids_unique(self):
        eng = self._engine_with_high_negative()
        ids = [d["id"] for d in eng.get_decisions()]
        assert len(ids) == len(set(ids))

    def test_low_negative_no_critical(self):
        eng = SentimentEngine()
        eng._stats = {
            "total_reviews": 100,
            "positive": 80, "positive_pct": 80.0,
            "neutral":  15, "neutral_pct":  15.0,
            "negative":  5, "negative_pct":  5.0,
            "satisfaction_score": 87.5,
            "nps": 60,
            "promoters": 70, "detractors": 10,
            "aspect_analysis": [],
            "actionable_insights": [],
        }
        decisions = eng.get_decisions()
        assert not any(d["priority"] == "critical" for d in decisions)
