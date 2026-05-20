"""
Unit tests for sentiment_engine.py — text preprocessing, model training,
prediction, stats computation, and persistence helpers.
"""
import pytest
import pandas as pd
from sentiment_engine import SentimentEngine, clean_text, LABEL_MAP, REVERSE_MAP


# ─── clean_text ───────────────────────────────────────────────────────────────

class TestCleanText:
    def test_lowercases_input(self):
        assert clean_text("Great Coffee!") == clean_text("great coffee!")

    def test_removes_urls(self):
        result = clean_text("Visit https://example.com for more")
        assert "http" not in result
        assert "example" not in result

    def test_removes_at_mentions(self):
        result = clean_text("@CafeBuddy is great")
        assert "@" not in result

    def test_removes_hashtags(self):
        result = clean_text("Love #coffee and #food")
        assert "#" not in result

    def test_removes_special_characters(self):
        result = clean_text("Amazing food!!!")
        assert "!" not in result

    def test_collapses_extra_whitespace(self):
        result = clean_text("too    many    spaces")
        assert "  " not in result

    def test_removes_short_tokens(self):
        # Tokens ≤2 chars are removed
        result = clean_text("I am so happy")
        assert " I " not in result
        assert " am " not in result

    def test_removes_stopwords(self):
        result = clean_text("this coffee is the best in the world")
        assert "this" not in result

    def test_empty_string(self):
        result = clean_text("")
        assert result == ""

    def test_handles_numbers(self):
        result = clean_text("Rated 5 stars")
        # Numbers get stripped by [^a-zA-Z\s] pattern
        assert "5" not in result

    def test_meaningful_words_retained(self):
        result = clean_text("excellent pasta and coffee")
        assert "excellent" in result
        assert "pasta" in result


# ─── SentimentEngine — initialization ────────────────────────────────────────

class TestSentimentEngineInit:
    def test_has_data_false_initially(self):
        eng = SentimentEngine()
        assert eng.has_data is False

    def test_stats_empty_initially(self):
        eng = SentimentEngine()
        assert eng.stats == {}

    def test_records_empty_initially(self):
        eng = SentimentEngine()
        assert eng.records == []

    def test_predict_returns_unknown_without_training(self):
        eng = SentimentEngine()
        result = eng.predict("Great food!")
        assert result == "Unknown"

    def test_predict_batch_returns_unknowns_without_training(self):
        eng = SentimentEngine()
        results = eng.predict_batch(["Great food!", "Terrible service!"])
        assert results == ["Unknown", "Unknown"]


# ─── SentimentEngine — fit & predict ─────────────────────────────────────────

class TestSentimentEngineFit:
    @pytest.fixture
    def trained_engine(self):
        eng = SentimentEngine()
        texts = [
            "Excellent food and service",
            "Amazing coffee, loved it",
            "Great ambience and staff",
            "Wonderful experience overall",
            "Delicious pasta, highly recommend",
            "Terrible service, waited too long",
            "Cold food, very disappointed",
            "Worst experience ever",
            "Rude staff, never coming back",
            "Food was bad and overpriced",
            "Average experience, nothing special",
            "Okay place, could be better",
            "Decent food but slow service",
            "Not bad, not great either",
        ]
        labels = ["Positive"] * 5 + ["Negative"] * 5 + ["Neutral"] * 4
        eng.fit(texts, labels)
        return eng

    def test_fit_sets_fitted_flag(self, trained_engine):
        assert trained_engine._fitted is True

    def test_predict_returns_valid_label(self, trained_engine):
        result = trained_engine.predict("Amazing food and great service")
        assert result in ("Positive", "Neutral", "Negative")

    def test_predict_positive_review(self, trained_engine):
        result = trained_engine.predict("Absolutely delicious food, loved every bite")
        assert result in ("Positive", "Neutral")  # generous: model may vary

    def test_predict_negative_review(self, trained_engine):
        result = trained_engine.predict("Terrible cold food, rude staff, disgusting")
        assert result in ("Negative", "Neutral")

    def test_predict_batch_returns_list(self, trained_engine):
        results = trained_engine.predict_batch(["Great!", "Awful!"])
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(r in ("Positive", "Neutral", "Negative") for r in results)

    def test_fit_returns_true_on_sufficient_data(self):
        eng = SentimentEngine()
        texts  = ["good " * 3] * 6 + ["bad " * 3] * 6
        labels = ["Positive"] * 6 + ["Negative"] * 6
        result = eng.fit(texts, labels)
        assert result is True

    def test_fit_returns_false_on_too_few_samples(self):
        eng = SentimentEngine()
        result = eng.fit(["good", "bad"], ["Positive", "Negative"])
        assert result is False


# ─── SentimentEngine — process_dataframe ─────────────────────────────────────

class TestSentimentEngineProcessDataframe:
    def _make_review_df(self, n=20):
        pos_texts = ["Excellent food and great service, highly recommend"] * (n // 2)
        neg_texts = ["Terrible experience, cold food and rude staff"] * (n // 2)
        return pd.DataFrame({
            "Review_ID":      [f"R{i:03d}" for i in range(n)],
            "Source":         ["Google"] * (n // 2) + ["Zomato"] * (n // 2),
            "Review_Date":    ["2026-05-01"] * n,
            "Cafe_Location":  ["Branch A"] * n,
            "Visit_Type":     ["Dine-In"] * n,
            "Rating":         [5] * (n // 2) + [1] * (n // 2),
            "Sentiment_Label": ["Positive"] * (n // 2) + ["Negative"] * (n // 2),
            "Review_Text":    pos_texts + neg_texts,
        })

    def test_returns_records_and_stats(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        records, stats = eng.process_dataframe(df, "test.csv")
        assert len(records) == 20
        assert isinstance(stats, dict)

    def test_has_data_true_after_processing(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        eng.process_dataframe(df, "test.csv")
        assert eng.has_data is True

    def test_stats_total_reviews_correct(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        _, stats = eng.process_dataframe(df, "test.csv")
        assert stats["total_reviews"] == 20

    def test_stats_sentiment_counts_sum_to_total(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        _, stats = eng.process_dataframe(df, "test.csv")
        total = stats["positive"] + stats["neutral"] + stats["negative"]
        assert total == stats["total_reviews"]

    def test_stats_percentages_sum_to_100(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        _, stats = eng.process_dataframe(df, "test.csv")
        pct_sum = stats["positive_pct"] + stats["neutral_pct"] + stats["negative_pct"]
        assert abs(pct_sum - 100.0) < 0.5

    def test_satisfaction_score_between_0_and_100(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        _, stats = eng.process_dataframe(df, "test.csv")
        assert 0 <= stats["satisfaction_score"] <= 100

    def test_avg_rating_between_1_and_5(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        _, stats = eng.process_dataframe(df, "test.csv")
        assert 1.0 <= stats["overall_avg_rating"] <= 5.0

    def test_source_breakdown_present(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        _, stats = eng.process_dataframe(df, "test.csv")
        assert "source_breakdown" in stats
        sources = {s["source"] for s in stats["source_breakdown"]}
        assert "Google" in sources
        assert "Zomato" in sources

    def test_visit_breakdown_present(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        _, stats = eng.process_dataframe(df, "test.csv")
        assert "visit_breakdown" in stats
        assert len(stats["visit_breakdown"]) >= 1

    def test_keywords_extracted(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        _, stats = eng.process_dataframe(df, "test.csv")
        assert "keywords" in stats
        assert "positive" in stats["keywords"]
        assert "negative" in stats["keywords"]

    def test_unlabeled_reviews_get_predicted(self):
        eng = SentimentEngine()
        df = self._make_review_df(20)
        # First pass to train the model
        eng.process_dataframe(df, "train.csv")

        # New df with no Sentiment_Label
        new_df = pd.DataFrame({
            "Review_ID":      ["R100"],
            "Source":         ["Google"],
            "Review_Date":    ["2026-05-10"],
            "Cafe_Location":  ["Branch A"],
            "Visit_Type":     ["Dine-In"],
            "Rating":         [4],
            "Sentiment_Label": [""],
            "Review_Text":    ["Great food and wonderful service"],
        })
        records, _ = eng.process_dataframe(new_df, "new.csv")
        assert records[0]["sentiment"] in ("Positive", "Neutral", "Negative")
        assert records[0]["sentiment"] != ""

    def test_each_record_has_required_fields(self):
        eng = SentimentEngine()
        df = self._make_review_df(10)
        records, _ = eng.process_dataframe(df, "test.csv")
        required = {"review_id", "source", "review_date", "location",
                    "visit_type", "rating", "sentiment", "review_text"}
        for r in records:
            assert required.issubset(r.keys())

    def test_rating_clamped_between_1_and_5(self):
        eng = SentimentEngine()
        df = pd.DataFrame({
            "Review_ID":      ["R001", "R002"],
            "Source":         ["Google", "Zomato"],
            "Review_Date":    ["2026-05-01", "2026-05-01"],
            "Cafe_Location":  ["A", "A"],
            "Visit_Type":     ["Dine-In", "Dine-In"],
            "Rating":         [10, -5],   # out-of-range
            "Sentiment_Label": ["Positive", "Negative"],
            "Review_Text":    ["Great!", "Terrible!"],
        })
        records, _ = eng.process_dataframe(df, "test.csv")
        for r in records:
            assert 1 <= r["rating"] <= 5


# ─── SentimentEngine — get_chat_context ──────────────────────────────────────

class TestGetChatContext:
    def test_empty_engine_returns_empty_string(self):
        eng = SentimentEngine()
        assert eng.get_chat_context() == ""

    def test_returns_non_empty_after_processing(self):
        eng = SentimentEngine()
        df = pd.DataFrame({
            "Review_ID":      [f"R{i}" for i in range(10)],
            "Source":         ["Google"] * 10,
            "Review_Date":    ["2026-05-01"] * 10,
            "Cafe_Location":  ["A"] * 10,
            "Visit_Type":     ["Dine-In"] * 10,
            "Rating":         [4] * 10,
            "Sentiment_Label": ["Positive"] * 6 + ["Negative"] * 2 + ["Neutral"] * 2,
            "Review_Text":    ["Good food!"] * 6 + ["Bad service"] * 2 + ["Okay"] * 2,
        })
        eng.process_dataframe(df, "test.csv")
        ctx = eng.get_chat_context()
        assert len(ctx) > 50
        assert "SENTIMENT ANALYSIS" in ctx

    def test_context_contains_review_counts(self):
        eng = SentimentEngine()
        df = pd.DataFrame({
            "Review_ID":      [f"R{i}" for i in range(8)],
            "Source":         ["Google"] * 8,
            "Review_Date":    ["2026-05-01"] * 8,
            "Cafe_Location":  ["A"] * 8,
            "Visit_Type":     ["Dine-In"] * 8,
            "Rating":         [4] * 8,
            "Sentiment_Label": ["Positive"] * 5 + ["Negative"] * 3,
            "Review_Text":    ["Great!"] * 5 + ["Terrible!"] * 3,
        })
        eng.process_dataframe(df, "test.csv")
        ctx = eng.get_chat_context()
        assert "8" in ctx   # total reviews


# ─── SentimentEngine — get_decisions ─────────────────────────────────────────

class TestGetDecisions:
    def _make_engine_with_stats(self, neg_pct=30, pos_pct=50):
        eng = SentimentEngine()
        total = 100
        neg   = int(total * neg_pct / 100)
        pos   = int(total * pos_pct / 100)
        neu   = total - neg - pos
        eng._stats = {
            "total_reviews": total,
            "positive": pos,   "positive_pct": pos_pct,
            "neutral":  neu,   "neutral_pct":  100 - pos_pct - neg_pct,
            "negative": neg,   "negative_pct": neg_pct,
            "satisfaction_score": pos_pct,
            "source_breakdown": [
                {"source": "Zomato", "total": 40, "positive": 20, "neutral": 10,
                 "negative": 10, "positive_pct": 50.0, "negative_pct": 25.0, "satisfaction": 62.5}
            ],
            "visit_breakdown": [
                {"visit_type": "Delivery", "total": 30, "positive": 15, "neutral": 5,
                 "negative": 10, "positive_pct": 50.0, "negative_pct": 33.0, "satisfaction": 58.0}
            ],
            "location_breakdown": [
                {"location": "Branch A", "total": 60, "positive": 50, "neutral": 5,
                 "negative": 5, "positive_pct": 83.0, "negative_pct": 8.0, "satisfaction": 87.5}
            ],
            "keywords": {"positive": [], "neutral": [], "negative": []},
        }
        return eng

    def test_empty_stats_returns_empty_decisions(self):
        eng = SentimentEngine()
        assert eng.get_decisions() == []

    def test_high_negative_pct_creates_critical_decision(self):
        eng = self._make_engine_with_stats(neg_pct=25)
        decisions = eng.get_decisions()
        types = [d["priority"] for d in decisions]
        assert "critical" in types

    def test_low_negative_no_critical_decision(self):
        eng = self._make_engine_with_stats(neg_pct=10, pos_pct=75)
        decisions = eng.get_decisions()
        types = [d["priority"] for d in decisions]
        assert "critical" not in types

    def test_each_decision_has_required_keys(self):
        eng = self._make_engine_with_stats(neg_pct=25)
        decisions = eng.get_decisions()
        required = {"id", "type", "priority", "title", "rationale", "impact",
                    "confidence", "status", "category", "source"}
        for d in decisions:
            assert required.issubset(d.keys())

    def test_confidence_in_valid_range(self):
        eng = self._make_engine_with_stats(neg_pct=25)
        decisions = eng.get_decisions()
        for d in decisions:
            assert 0 <= d["confidence"] <= 100

    def test_decision_ids_are_unique(self):
        eng = self._make_engine_with_stats(neg_pct=30)
        decisions = eng.get_decisions()
        ids = [d["id"] for d in decisions]
        assert len(ids) == len(set(ids))
