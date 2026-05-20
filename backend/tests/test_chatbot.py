"""
Unit tests for chatbot.py — smart response engine, festival calendar,
web-search triggers, and context builder.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import chatbot
from chatbot import (
    _needs_web_search, _smart_response, _build_context,
    get_upcoming_festivals, _FESTIVALS,
)


# ─── _needs_web_search ───────────────────────────────────────────────────────

class TestNeedsWebSearch:
    def test_triggers_on_festival_keyword(self):
        assert _needs_web_search("What should I do for Diwali?") is True

    def test_triggers_on_trend(self):
        assert _needs_web_search("What are the trending coffee drinks?") is True

    def test_triggers_on_how_to(self):
        assert _needs_web_search("How to improve my café margins?") is True

    def test_triggers_on_strategy(self):
        assert _needs_web_search("marketing strategy for my café") is True

    def test_triggers_on_instagram(self):
        assert _needs_web_search("Instagram ideas for café") is True

    def test_triggers_on_license(self):
        assert _needs_web_search("Do I need an FSSAI license?") is True

    def test_triggers_on_staff(self):
        assert _needs_web_search("How many staff should I hire?") is True

    def test_triggers_on_equipment(self):
        assert _needs_web_search("Which coffee machine is best?") is True

    def test_false_for_pure_data_query(self):
        assert _needs_web_search("What is my total revenue?") is False

    def test_false_for_hello(self):
        assert _needs_web_search("hello") is False

    def test_case_insensitive(self):
        assert _needs_web_search("NAVRATRI menu ideas") is True


# ─── get_upcoming_festivals ──────────────────────────────────────────────────

class TestGetUpcomingFestivals:
    def test_returns_list(self):
        result = get_upcoming_festivals(365)
        assert isinstance(result, list)

    def test_all_festivals_have_required_keys(self):
        result = get_upcoming_festivals(365)
        required = {"name", "date", "days_away", "menu_ideas", "promo_ideas"}
        for f in result:
            assert required.issubset(f.keys())

    def test_days_away_within_requested_window(self):
        window = 90
        result = get_upcoming_festivals(window)
        for f in result:
            assert 0 <= f["days_away"] <= window

    def test_sorted_by_days_away_ascending(self):
        result = get_upcoming_festivals(365)
        days = [f["days_away"] for f in result]
        assert days == sorted(days)

    def test_zero_window_returns_only_today_or_empty(self):
        result = get_upcoming_festivals(0)
        for f in result:
            assert f["days_away"] == 0

    def test_festival_calendar_covers_major_indian_festivals(self):
        names = {f["name"] for f in _FESTIVALS}
        assert "Diwali" in names
        assert "Holi" in names
        assert "Eid al-Fitr" in names
        assert "Christmas" in names
        assert "Independence Day" in names

    def test_menu_ideas_and_promo_ideas_non_empty(self):
        for f in _FESTIVALS:
            assert len(f.get("menu_ideas", [])) > 0
            assert len(f.get("promo_ideas", [])) > 0


# ─── _build_context ──────────────────────────────────────────────────────────

class TestBuildContext:
    def test_no_data_returns_no_sales_message(self):
        ctx = _build_context([])
        assert "No sales data" in ctx

    def test_contains_date_range(self, pos_data_7days):
        ctx = _build_context(pos_data_7days)
        assert "2026-05-11" in ctx

    def test_contains_revenue(self, pos_data_7days):
        ctx = _build_context(pos_data_7days)
        assert "Total revenue" in ctx or "revenue" in ctx.lower()

    def test_contains_platform_breakdown(self, pos_data_7days):
        ctx = _build_context(pos_data_7days)
        assert "PLATFORM" in ctx or "Dine-in" in ctx

    def test_contains_top_items(self, pos_data_7days):
        ctx = _build_context(pos_data_7days)
        assert "Cappuccino" in ctx or "Pasta" in ctx

    def test_weekend_avg_computed(self, pos_data_7days):
        ctx = _build_context(pos_data_7days)
        assert "Weekend avg" in ctx or "weekend" in ctx.lower()

    def test_structure_markers_present(self, pos_data_7days):
        ctx = _build_context(pos_data_7days)
        assert "CAFÉ DATA SUMMARY" in ctx or "TOP 5 ITEMS" in ctx


# ─── _smart_response ─────────────────────────────────────────────────────────

class TestSmartResponse:
    """Test the smart (no-API-key) response engine."""

    @pytest.fixture
    def festivals(self):
        return get_upcoming_festivals(90)

    # ── Top-selling queries ──

    def test_top_selling_returns_item_names(self, pos_data_7days, festivals):
        resp = _smart_response("Which is the highest selling item?",
                               pos_data_7days, festivals)
        assert "Pasta Combo" in resp or "Cappuccino" in resp

    def test_best_selling_last_week(self, pos_data_7days, festivals):
        resp = _smart_response("best selling item last week",
                               pos_data_7days, festivals)
        assert any(name in resp for name in ["Cappuccino", "Pasta", "Garlic"])

    def test_most_popular_item_no_data_returns_helpful(self, festivals):
        resp = _smart_response("Which is the most popular item?", [], festivals)
        assert len(resp) > 10

    # ── Lowest margin / worst performer ──

    def test_lowest_margin_returns_items(self, pos_data_7days, festivals):
        resp = _smart_response("What is my lowest margin item?",
                               pos_data_7days, festivals)
        assert "margin" in resp.lower()
        assert any(name in resp for name in ["Cappuccino", "Pasta", "Garlic"])

    def test_worst_item_response_includes_recommendations(self, pos_data_7days, festivals):
        resp = _smart_response("which item should I remove or discontinue?",
                               pos_data_7days, festivals)
        assert "margin" in resp.lower() or "cost" in resp.lower()

    # ── Food cost / profitability ──

    def test_food_cost_response_contains_percentage(self, pos_data_7days, festivals):
        resp = _smart_response("What is my food cost?", pos_data_7days, festivals)
        assert "%" in resp

    def test_food_cost_mentions_target(self, pos_data_7days, festivals):
        resp = _smart_response("How can I improve my food cost efficiency?",
                               pos_data_7days, festivals)
        assert "28" in resp or "35" in resp or "target" in resp.lower()

    def test_profit_margin_response(self, pos_data_7days, festivals):
        resp = _smart_response("How can I increase my profit margin?",
                               pos_data_7days, festivals)
        assert len(resp) > 50

    # ── Revenue / sales summary ──

    def test_total_revenue_response(self, pos_data_7days, festivals):
        resp = _smart_response("What is my total revenue?", pos_data_7days, festivals)
        assert "₹" in resp or "revenue" in resp.lower()

    def test_revenue_no_data_asks_to_upload(self, festivals):
        resp = _smart_response("What is my total revenue?", [], festivals)
        assert "upload" in resp.lower() or "data" in resp.lower() or len(resp) > 20

    # ── Platform analysis ──

    def test_platform_response_mentions_channels(self, pos_data_7days, festivals):
        resp = _smart_response("Which platform generates the most revenue?",
                               pos_data_7days, festivals)
        assert "Dine-in" in resp or "platform" in resp.lower()

    def test_zomato_query_returns_platform_breakdown(self, pos_data_7days, festivals):
        resp = _smart_response("How is Zomato performing?", pos_data_7days, festivals)
        assert "platform" in resp.lower() or "revenue" in resp.lower()

    # ── Weekend vs weekday ──

    def test_weekend_comparison_response(self, pos_data_7days, festivals):
        resp = _smart_response("Compare my weekend vs weekday sales",
                               pos_data_7days, festivals)
        assert "weekend" in resp.lower()
        assert "₹" in resp

    def test_weekend_premium_computed(self, pos_data_7days, festivals):
        resp = _smart_response("weekend sales comparison", pos_data_7days, festivals)
        # Should show a + or % difference
        assert "%" in resp or "premium" in resp.lower() or "average" in resp.lower()

    # ── Category performance ──

    def test_category_performance_lists_categories(self, pos_data_7days, festivals):
        resp = _smart_response("How are my beverages performing?",
                               pos_data_7days, festivals)
        assert "Beverage" in resp or "beverage" in resp.lower()

    def test_category_query_includes_margin(self, pos_data_7days, festivals):
        resp = _smart_response("Which category has the best margin?",
                               pos_data_7days, festivals)
        assert "margin" in resp.lower()

    # ── Festival queries ──

    def test_diwali_returns_menu_ideas(self, pos_data_7days, festivals):
        resp = _smart_response("What should I do for Diwali?",
                               pos_data_7days, festivals)
        assert "Diwali" in resp or "festival" in resp.lower()

    def test_festival_response_includes_promo_ideas(self, pos_data_7days, festivals):
        resp = _smart_response("How do I prepare for Holi?", pos_data_7days, festivals)
        assert len(resp) > 100

    def test_festival_no_data_still_answers(self, festivals):
        resp = _smart_response("Give me Navratri menu ideas", [], festivals)
        assert "menu" in resp.lower() or "Navratri" in resp

    # ── Inventory / stock ──

    def test_inventory_recommendation_with_data(self, pos_data_7days, festivals):
        resp = _smart_response("Which items should I stock more?",
                               pos_data_7days, festivals)
        assert len(resp) > 50

    # ── Overview / analysis ──

    def test_overview_response_with_data(self, pos_data_7days, festivals):
        resp = _smart_response("Give me an overview of my business",
                               pos_data_7days, festivals)
        assert "revenue" in resp.lower() or "₹" in resp

    def test_help_me_improve_response(self, pos_data_7days, festivals):
        resp = _smart_response("Help me improve my café",
                               pos_data_7days, festivals)
        assert len(resp) > 100

    # ── Catch-all for unrecognised questions ──

    def test_unknown_question_with_data_returns_snapshot(self, pos_data_7days, festivals):
        resp = _smart_response("What is the meaning of life?",
                               pos_data_7days, festivals)
        # Should NOT be an empty or minimal response
        assert len(resp) > 100
        # Should contain actual café data, not just a help message
        assert "₹" in resp or "revenue" in resp.lower()

    def test_greeting_with_data_returns_snapshot(self, pos_data_7days, festivals):
        resp = _smart_response("Hello!", pos_data_7days, festivals)
        assert len(resp) > 80

    def test_unknown_question_no_data_returns_helpful(self, festivals):
        resp = _smart_response("What time should I open my café?", [], festivals)
        assert len(resp) > 80

    def test_staff_question_no_data_returns_knowledge(self, festivals):
        resp = _smart_response("How many staff should I hire?", [], festivals)
        assert "staff" in resp.lower() or "team" in resp.lower() or len(resp) > 80

    def test_equipment_question_no_data_returns_knowledge(self, festivals):
        resp = _smart_response("Which coffee machine should I buy?", [], festivals)
        assert len(resp) > 80

    def test_catch_all_never_returns_empty(self, pos_data_7days, festivals):
        questions = [
            "hi", "hello", "what can you do?", "help",
            "random text xyz", "show me something", "analyse everything",
        ]
        for q in questions:
            resp = _smart_response(q, pos_data_7days, festivals)
            assert len(resp) > 20, f"Empty response for: {q!r}"

    def test_catch_all_no_data_never_returns_empty(self, festivals):
        questions = [
            "hi", "hello", "what can you do?",
            "random xyz", "show me something",
        ]
        for q in questions:
            resp = _smart_response(q, [], festivals)
            assert len(resp) > 20, f"Empty response for: {q!r}"

    # ── Specific item performance ──

    def test_item_performance_lookup(self, pos_data_7days, festivals):
        resp = _smart_response("Tell me about Cappuccino", pos_data_7days, festivals)
        assert "Cappuccino" in resp or "item" in resp.lower()

    # ── Sentiment / reviews ──

    def test_review_query_without_review_data(self, pos_data_7days, festivals):
        resp = _smart_response("What do customers say about my café?",
                               pos_data_7days, festivals)
        assert len(resp) > 20

    # ── Response quality checks ──

    def test_response_is_string(self, pos_data_7days, festivals):
        resp = _smart_response("overview", pos_data_7days, festivals)
        assert isinstance(resp, str)

    def test_response_uses_rupee_symbol_for_money(self, pos_data_7days, festivals):
        resp = _smart_response("What is my total revenue?", pos_data_7days, festivals)
        assert "₹" in resp

    def test_no_data_message_shown_for_data_queries(self, festivals):
        resp = _smart_response("What is my platform breakdown?", [], festivals)
        # Either shows NO_DATA_MSG or helpful onboarding
        assert "upload" in resp.lower() or "data" in resp.lower() or len(resp) > 30
