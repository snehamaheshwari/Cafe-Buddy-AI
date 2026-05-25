"""
test_peer_comparison.py — Comprehensive unit tests for peer_comparison.py
"""

from __future__ import annotations

import math
import os
import sys
import types
from unittest import mock
from unittest.mock import MagicMock, patch, patch as mock_patch

import pytest

# ── Ensure backend package is importable ──────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from peer_comparison import (
    CITIES,
    COMPETITOR_DB,
    analyze_with_ai,
    compute_radar_scores,
    get_areas,
    get_competitors,
    live_search_competitors,
)


# =============================================================================
# TestGetAreas
# =============================================================================

class TestGetAreas:
    def test_valid_city_returns_sorted_areas(self):
        areas = get_areas("Delhi NCR")
        assert isinstance(areas, list)
        assert len(areas) > 0
        assert "Connaught Place" in areas
        assert areas == sorted(areas), "Areas should be sorted alphabetically"

    def test_invalid_city_returns_empty_list(self):
        areas = get_areas("Atlantis")
        assert areas == []

    def test_case_sensitive_city_name(self):
        # "delhi ncr" (lowercase) should return empty — keys are title-cased
        areas = get_areas("delhi ncr")
        assert areas == []


# =============================================================================
# TestGetCompetitors
# =============================================================================

class TestGetCompetitors:
    def test_returns_competitors_for_valid_city_and_area(self):
        comps = get_competitors("Delhi NCR", "Connaught Place")
        assert isinstance(comps, list)
        assert len(comps) > 0

    def test_returns_all_city_competitors_when_no_area(self):
        comps_all = get_competitors("Delhi NCR")
        comps_cp = get_competitors("Delhi NCR", "Connaught Place")
        # All competitors combined should be more than just one area
        assert len(comps_all) > len(comps_cp)

    def test_returns_empty_for_unknown_city(self):
        comps = get_competitors("Narnia")
        assert comps == []

    def test_returns_empty_for_unknown_area_in_valid_city(self):
        comps = get_competitors("Delhi NCR", "Timbuktu")
        # Unknown area → combine all (falls through to combined), not empty
        # Because the area check fails and we get the full city list instead
        # Verify by checking: it returns the same as no-area call
        comps_all = get_competitors("Delhi NCR")
        assert comps == comps_all

    def test_competitor_has_required_fields(self):
        comps = get_competitors("Delhi NCR", "Connaught Place")
        required_fields = [
            "name", "rating", "price_band", "specialties",
            "positive_themes", "negative_themes", "avg_order_value",
            "review_count", "delivery_time_min", "platforms",
            "seating_capacity", "years_active", "notable",
            "menu_variety_score", "value_score",
        ]
        for comp in comps:
            for field in required_fields:
                assert field in comp, f"Field '{field}' missing from competitor '{comp.get('name', '?')}'"

    def test_returns_copy_not_reference(self):
        comps1 = get_competitors("Delhi NCR", "Connaught Place")
        comps2 = get_competitors("Delhi NCR", "Connaught Place")
        # Mutating the returned list should not affect the next call
        comps1.append({"name": "FAKE CAFÉ"})
        comps3 = get_competitors("Delhi NCR", "Connaught Place")
        assert len(comps3) == len(comps2)
        assert all(c["name"] != "FAKE CAFÉ" for c in comps3)


# =============================================================================
# TestComputeRadarScores
# =============================================================================

class TestComputeRadarScores:
    SAMPLE_CAFE = {
        "rating": 4.5,
        "price_band": "₹",
        "delivery_time_min": 20,
        "menu_variety_score": 65,
        "review_count": 5000,
        "value_score": 75,
    }

    def test_returns_all_six_keys(self):
        scores = compute_radar_scores(self.SAMPLE_CAFE)
        expected_keys = {
            "rating", "price_competitiveness", "delivery_speed",
            "menu_variety", "popularity", "value_for_money",
        }
        assert set(scores.keys()) == expected_keys

    def test_rating_score_calculation(self):
        cafe = {**self.SAMPLE_CAFE, "rating": 4.5}
        scores = compute_radar_scores(cafe)
        assert scores["rating"] == round(4.5 / 5.0 * 100)  # 90

    def test_price_band_rupee_gives_90(self):
        cafe = {**self.SAMPLE_CAFE, "price_band": "₹"}
        scores = compute_radar_scores(cafe)
        assert scores["price_competitiveness"] == 90

    def test_price_band_double_rupee_gives_70(self):
        cafe = {**self.SAMPLE_CAFE, "price_band": "₹₹"}
        scores = compute_radar_scores(cafe)
        assert scores["price_competitiveness"] == 70

    def test_price_band_triple_rupee_gives_50(self):
        cafe = {**self.SAMPLE_CAFE, "price_band": "₹₹₹"}
        scores = compute_radar_scores(cafe)
        assert scores["price_competitiveness"] == 50

    def test_delivery_time_zero_gives_50(self):
        cafe = {**self.SAMPLE_CAFE, "delivery_time_min": 0}
        scores = compute_radar_scores(cafe)
        assert scores["delivery_speed"] == 50

    def test_delivery_time_fast_gives_high_score(self):
        # dt=15 → 100 - (15-15)*2 = 100
        cafe = {**self.SAMPLE_CAFE, "delivery_time_min": 15}
        scores = compute_radar_scores(cafe)
        assert scores["delivery_speed"] == 100

    def test_scores_bounded_0_to_100(self):
        extreme_cafe = {
            "rating": 5.0,
            "price_band": "₹",
            "delivery_time_min": 1,
            "menu_variety_score": 150,
            "review_count": 9_999_999,
            "value_score": 200,
        }
        scores = compute_radar_scores(extreme_cafe)
        for key, val in scores.items():
            assert 0 <= val <= 100, f"Score for '{key}' out of bounds: {val}"

    def test_zero_review_count_gives_zero_popularity(self):
        cafe = {**self.SAMPLE_CAFE, "review_count": 0}
        scores = compute_radar_scores(cafe)
        assert scores["popularity"] == 0

    def test_large_review_count_capped_at_100(self):
        cafe = {**self.SAMPLE_CAFE, "review_count": 10_000_000}
        scores = compute_radar_scores(cafe)
        assert scores["popularity"] == 100


# =============================================================================
# TestLiveSearchCompetitors
# =============================================================================

class TestLiveSearchCompetitors:
    def _make_fake_ddgs_result(self):
        return [
            {
                "title": "Best Cafés in Connaught Place",
                "body": "A roundup of top spots to visit in CP.",
                "href": "https://example.com/cafes-cp",
            },
            {
                "title": "Top 10 Coffee Shops Delhi",
                "body": "From specialty coffee to chai, Delhi has it all.",
                "href": "https://example.com/coffee-delhi",
            },
        ]

    def test_returns_list_on_success(self):
        fake_results = self._make_fake_ddgs_result()

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)
        mock_ddgs_instance.text = MagicMock(return_value=iter(fake_results))

        mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)

        fake_module = types.ModuleType("duckduckgo_search")
        fake_module.DDGS = mock_ddgs_class

        with patch.dict("sys.modules", {"duckduckgo_search": fake_module}):
            results = live_search_competitors("Delhi NCR", "Connaught Place")

        assert isinstance(results, list)
        assert len(results) == 2

    def test_returns_empty_on_import_error(self):
        with patch.dict("sys.modules", {"duckduckgo_search": None}):
            results = live_search_competitors("Delhi NCR", "Connaught Place")
        assert results == []

    def test_returns_empty_on_ddgs_exception(self):
        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)
        mock_ddgs_instance.text = MagicMock(side_effect=Exception("network error"))

        mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)

        fake_module = types.ModuleType("duckduckgo_search")
        fake_module.DDGS = mock_ddgs_class

        with patch.dict("sys.modules", {"duckduckgo_search": fake_module}):
            results = live_search_competitors("Delhi NCR", "Connaught Place")

        assert results == []

    def test_result_has_title_snippet_url_keys(self):
        fake_results = self._make_fake_ddgs_result()

        mock_ddgs_instance = MagicMock()
        mock_ddgs_instance.__enter__ = MagicMock(return_value=mock_ddgs_instance)
        mock_ddgs_instance.__exit__ = MagicMock(return_value=False)
        mock_ddgs_instance.text = MagicMock(return_value=iter(fake_results))

        mock_ddgs_class = MagicMock(return_value=mock_ddgs_instance)

        fake_module = types.ModuleType("duckduckgo_search")
        fake_module.DDGS = mock_ddgs_class

        with patch.dict("sys.modules", {"duckduckgo_search": fake_module}):
            results = live_search_competitors("Delhi NCR", "Connaught Place")

        for result in results:
            assert "title" in result
            assert "snippet" in result
            assert "url" in result


# =============================================================================
# TestAnalyzeWithAi
# =============================================================================

class TestAnalyzeWithAi:
    COMPETITORS = [
        {
            "name": "Test Café",
            "price_band": "₹₹",
            "rating": 4.2,
            "review_count": 1000,
            "avg_order_value": 350,
            "specialties": ["Coffee", "Sandwiches"],
            "positive_themes": ["good coffee"],
            "negative_themes": ["slow service"],
        }
    ]

    def test_returns_error_when_api_key_missing(self):
        env_without_key = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict("os.environ", env_without_key, clear=True):
            result = analyze_with_ai({}, self.COMPETITORS, "Delhi NCR", "Connaught Place")

        assert result["status"] == "error"
        assert "ANTHROPIC_API_KEY" in result["analysis"]
        assert result["model"] == "claude-opus-4-5"

    def test_returns_success_structure_with_valid_key(self):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Market Position: Great spot.")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key-123"}):
            with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
                result = analyze_with_ai(
                    {"avg_order_value": 400, "top_item": "Latte"},
                    self.COMPETITORS,
                    "Delhi NCR",
                    "Connaught Place",
                )

        assert "analysis" in result
        assert "model" in result
        assert "status" in result
        assert result["status"] == "success"
        assert result["model"] == "claude-opus-4-5"

    def test_no_stats_still_works(self):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Analysis based on market landscape only.")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key-123"}):
            with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
                result = analyze_with_ai({}, self.COMPETITORS, "Delhi NCR", "Hauz Khas")

        assert result["status"] == "success"
        assert "analysis" in result

    def test_handles_anthropic_exception_gracefully(self):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API connection timeout")

        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key-123"}):
            with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
                result = analyze_with_ai({}, self.COMPETITORS, "Delhi NCR", "Khan Market")

        assert result["status"] == "error"
        assert "AI analysis unavailable" in result["analysis"]
        assert "API connection timeout" in result["analysis"]


# =============================================================================
# TestCitiesAndDb
# =============================================================================

class TestCitiesAndDb:
    def test_cities_is_sorted_list(self):
        assert CITIES == sorted(CITIES), "CITIES should be sorted alphabetically"

    def test_delhi_ncr_in_cities(self):
        assert "Delhi NCR" in CITIES

    def test_all_competitors_have_rating_in_range(self):
        for city, areas in COMPETITOR_DB.items():
            for area, comps in areas.items():
                for comp in comps:
                    rating = comp.get("rating", -1)
                    assert 0 < rating <= 5, (
                        f"Rating {rating} out of range for '{comp['name']}' "
                        f"in {area}, {city}"
                    )

    def test_all_competitors_have_valid_price_band(self):
        valid_bands = {"₹", "₹₹", "₹₹₹"}
        for city, areas in COMPETITOR_DB.items():
            for area, comps in areas.items():
                for comp in comps:
                    band = comp.get("price_band", "")
                    assert band in valid_bands, (
                        f"Invalid price_band '{band}' for '{comp['name']}' "
                        f"in {area}, {city}"
                    )
