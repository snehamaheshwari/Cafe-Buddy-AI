"""
peer_comparison.py — Market Radar / Peer Comparison module for Cafe Buddy AI.

Provides a pre-fetched competitor database for Indian cities, live DuckDuckGo
search integration, AI-powered analysis via the Anthropic SDK, and radar score
computation for SVG visualisation.
"""

from __future__ import annotations

import math
import os
from typing import Optional

# ─────────────────────────────────────────────
# COMPETITOR DATABASE
# city → area → list[competitor dict]
# ─────────────────────────────────────────────

COMPETITOR_DB: dict[str, dict[str, list[dict]]] = {
    "Mumbai": {
        "Bandra": [
            {
                "name": "The Bagel Shop",
                "area": "Bandra",
                "city": "Mumbai",
                "rating": 4.4,
                "review_count": 2840,
                "avg_order_value": 420,
                "price_band": "₹₹",
                "specialties": ["Bagels", "Specialty Coffee", "Brunch"],
                "positive_themes": ["great ambience", "friendly staff", "fresh bagels"],
                "negative_themes": ["long wait times", "limited parking"],
                "delivery_time_min": 28,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 45,
                "years_active": 6,
                "notable": "Iconic Bandra brunch spot with loyal weekend crowd",
                "menu_variety_score": 72,
                "value_score": 68,
            },
            {
                "name": "Prithvi Café",
                "area": "Bandra",
                "city": "Mumbai",
                "rating": 4.2,
                "review_count": 3610,
                "avg_order_value": 280,
                "price_band": "₹",
                "specialties": ["Filter Coffee", "South Indian", "Chai"],
                "positive_themes": ["authentic flavours", "great value", "cosy vibe"],
                "negative_themes": ["noisy on weekends", "slow billing"],
                "delivery_time_min": 22,
                "platforms": ["Zomato", "Dine-in"],
                "seating_capacity": 60,
                "years_active": 14,
                "notable": "Old-school gem loved by writers and artists",
                "menu_variety_score": 58,
                "value_score": 82,
            },
            {
                "name": "Sequel Juice Bar & Café",
                "area": "Bandra",
                "city": "Mumbai",
                "rating": 4.3,
                "review_count": 1920,
                "avg_order_value": 550,
                "price_band": "₹₹₹",
                "specialties": ["Cold Press Juice", "Acai Bowls", "Vegan"],
                "positive_themes": ["healthy options", "Instagrammable", "quick service"],
                "negative_themes": ["expensive", "small portions"],
                "delivery_time_min": 35,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 30,
                "years_active": 4,
                "notable": "Hotspot for health-conscious millennials",
                "menu_variety_score": 65,
                "value_score": 52,
            },
        ],
        "Andheri": [
            {
                "name": "Blue Tokai Coffee Roasters",
                "area": "Andheri",
                "city": "Mumbai",
                "rating": 4.5,
                "review_count": 4120,
                "avg_order_value": 390,
                "price_band": "₹₹",
                "specialties": ["Specialty Coffee", "Single Origin", "Pour Over"],
                "positive_themes": ["best coffee in area", "knowledgeable baristas", "clean space"],
                "negative_themes": ["pricey for coffee only", "no food variety"],
                "delivery_time_min": 25,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 40,
                "years_active": 5,
                "notable": "Premium Indian specialty coffee chain with cult following",
                "menu_variety_score": 55,
                "value_score": 60,
            },
            {
                "name": "Theobroma",
                "area": "Andheri",
                "city": "Mumbai",
                "rating": 4.6,
                "review_count": 6800,
                "avg_order_value": 460,
                "price_band": "₹₹",
                "specialties": ["Brownies", "Patisserie", "Coffee"],
                "positive_themes": ["best brownies", "consistent quality", "great packaging"],
                "negative_themes": ["always crowded", "parking issues"],
                "delivery_time_min": 30,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 55,
                "years_active": 12,
                "notable": "Mumbai's most beloved patisserie chain — benchmark for desserts",
                "menu_variety_score": 80,
                "value_score": 72,
            },
            {
                "name": "Café Mocha",
                "area": "Andheri",
                "city": "Mumbai",
                "rating": 3.9,
                "review_count": 2100,
                "avg_order_value": 320,
                "price_band": "₹₹",
                "specialties": ["Waffles", "Coffee", "Sandwiches"],
                "positive_themes": ["good portions", "comfortable seating"],
                "negative_themes": ["inconsistent coffee", "slow service", "average food"],
                "delivery_time_min": 38,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 70,
                "years_active": 8,
                "notable": "Mid-range café catering to office crowd",
                "menu_variety_score": 68,
                "value_score": 65,
            },
        ],
        "Powai": [
            {
                "name": "Nescafé Lounge @ Hiranandani",
                "area": "Powai",
                "city": "Mumbai",
                "rating": 3.8,
                "review_count": 980,
                "avg_order_value": 240,
                "price_band": "₹",
                "specialties": ["Quick Bites", "Coffee", "Sandwiches"],
                "positive_themes": ["convenient location", "fast service"],
                "negative_themes": ["basic food quality", "noisy atmosphere"],
                "delivery_time_min": 20,
                "platforms": ["Zomato", "Dine-in"],
                "seating_capacity": 35,
                "years_active": 3,
                "notable": "Quick-service format popular with Hiranandani IT crowd",
                "menu_variety_score": 45,
                "value_score": 78,
            },
            {
                "name": "The Nutcracker",
                "area": "Powai",
                "city": "Mumbai",
                "rating": 4.1,
                "review_count": 1540,
                "avg_order_value": 480,
                "price_band": "₹₹₹",
                "specialties": ["Brunch", "Eggs Benedict", "Artisan Coffee"],
                "positive_themes": ["beautiful decor", "tasty brunch", "good wifi"],
                "negative_themes": ["expensive for portions", "limited vegan options"],
                "delivery_time_min": 40,
                "platforms": ["Zomato", "Dine-in"],
                "seating_capacity": 50,
                "years_active": 5,
                "notable": "Go-to weekend brunch café for Powai professionals",
                "menu_variety_score": 70,
                "value_score": 55,
            },
        ],
    },
    "Bangalore": {
        "Koramangala": [
            {
                "name": "Third Wave Coffee",
                "area": "Koramangala",
                "city": "Bangalore",
                "rating": 4.4,
                "review_count": 5200,
                "avg_order_value": 350,
                "price_band": "₹₹",
                "specialties": ["Specialty Coffee", "Cold Brew", "Artisan Drinks"],
                "positive_themes": ["excellent cold brew", "great work space", "fast wifi"],
                "negative_themes": ["crowded evenings", "limited food menu"],
                "delivery_time_min": 22,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 60,
                "years_active": 4,
                "notable": "Fastest growing specialty coffee chain in Bangalore",
                "menu_variety_score": 60,
                "value_score": 70,
            },
            {
                "name": "Matteo Coffea",
                "area": "Koramangala",
                "city": "Bangalore",
                "rating": 4.3,
                "review_count": 3400,
                "avg_order_value": 420,
                "price_band": "₹₹",
                "specialties": ["Single Origin", "Espresso", "Pastries"],
                "positive_themes": ["passionate baristas", "quiet atmosphere", "great espresso"],
                "negative_themes": ["small seating", "no parking"],
                "delivery_time_min": 30,
                "platforms": ["Zomato", "Dine-in"],
                "seating_capacity": 25,
                "years_active": 7,
                "notable": "Specialty coffee pioneer in Bangalore's café culture",
                "menu_variety_score": 50,
                "value_score": 62,
            },
            {
                "name": "Hole in the Wall Café",
                "area": "Koramangala",
                "city": "Bangalore",
                "rating": 4.2,
                "review_count": 2890,
                "avg_order_value": 380,
                "price_band": "₹₹",
                "specialties": ["All-Day Breakfast", "Sandwiches", "Coffee"],
                "positive_themes": ["cosy vibe", "good breakfast", "pet-friendly"],
                "negative_themes": ["limited seating", "busy on weekends"],
                "delivery_time_min": 35,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 35,
                "years_active": 6,
                "notable": "Neighbourhood favourite with loyal regulars",
                "menu_variety_score": 65,
                "value_score": 68,
            },
        ],
        "Indiranagar": [
            {
                "name": "Hatti Kaapi",
                "area": "Indiranagar",
                "city": "Bangalore",
                "rating": 4.2,
                "review_count": 4500,
                "avg_order_value": 180,
                "price_band": "₹",
                "specialties": ["Filter Coffee", "South Indian Snacks", "Chai"],
                "positive_themes": ["authentic filter coffee", "affordable", "quick service"],
                "negative_themes": ["basic ambience", "limited seating"],
                "delivery_time_min": 15,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 30,
                "years_active": 9,
                "notable": "The filter coffee institution loved by all Bangaloreans",
                "menu_variety_score": 40,
                "value_score": 92,
            },
            {
                "name": "Café Azzure",
                "area": "Indiranagar",
                "city": "Bangalore",
                "rating": 4.0,
                "review_count": 1680,
                "avg_order_value": 520,
                "price_band": "₹₹₹",
                "specialties": ["Mediterranean", "Pasta", "Cocktails"],
                "positive_themes": ["beautiful ambience", "great for dates", "good pasta"],
                "negative_themes": ["slow service", "overpriced", "small portions"],
                "delivery_time_min": 45,
                "platforms": ["Zomato", "Dine-in"],
                "seating_capacity": 65,
                "years_active": 3,
                "notable": "Upscale café-restaurant targeting premium diners",
                "menu_variety_score": 75,
                "value_score": 48,
            },
        ],
    },
    "Delhi NCR": {
        "Connaught Place": [
            {
                "name": "Chaayos",
                "area": "Connaught Place",
                "city": "Delhi NCR",
                "rating": 4.1,
                "review_count": 7200,
                "avg_order_value": 220,
                "price_band": "₹",
                "specialties": ["Meri Wali Chai", "Sandwiches", "Maggi"],
                "positive_themes": ["customizable chai", "consistent quality", "quick service"],
                "negative_themes": ["basic interiors", "crowded"],
                "delivery_time_min": 18,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 50,
                "years_active": 8,
                "notable": "India's largest chai café chain — strong loyalty programme",
                "menu_variety_score": 55,
                "value_score": 85,
            },
            {
                "name": "Costa Coffee",
                "area": "Connaught Place",
                "city": "Delhi NCR",
                "rating": 3.9,
                "review_count": 3100,
                "avg_order_value": 380,
                "price_band": "₹₹",
                "specialties": ["Coffee", "Sandwiches", "Pastries"],
                "positive_themes": ["air conditioned", "reliable wifi", "clean bathrooms"],
                "negative_themes": ["average coffee quality", "pricey", "corporate feel"],
                "delivery_time_min": 28,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 80,
                "years_active": 10,
                "notable": "Global chain with strong brand recognition in CP",
                "menu_variety_score": 62,
                "value_score": 55,
            },
            {
                "name": "The Piano Man Jazz Club & Café",
                "area": "Connaught Place",
                "city": "Delhi NCR",
                "rating": 4.5,
                "review_count": 2650,
                "avg_order_value": 680,
                "price_band": "₹₹₹",
                "specialties": ["Live Jazz", "Craft Beer", "Continental"],
                "positive_themes": ["live music", "unique experience", "great cocktails"],
                "negative_themes": ["expensive", "reservation required", "far from metro"],
                "delivery_time_min": 0,
                "platforms": ["Dine-in"],
                "seating_capacity": 90,
                "years_active": 11,
                "notable": "Delhi's premier jazz venue — no delivery, dine-in only",
                "menu_variety_score": 70,
                "value_score": 58,
            },
        ],
        "Hauz Khas": [
            {
                "name": "Social",
                "area": "Hauz Khas",
                "city": "Delhi NCR",
                "rating": 4.3,
                "review_count": 8900,
                "avg_order_value": 560,
                "price_band": "₹₹",
                "specialties": ["Craft Beer", "Fusion Food", "Cocktails"],
                "positive_themes": ["great vibe", "good for groups", "innovative menu"],
                "negative_themes": ["very crowded", "loud music", "service slow"],
                "delivery_time_min": 35,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 120,
                "years_active": 9,
                "notable": "Multi-city café-bar chain with the biggest footprint in HKV",
                "menu_variety_score": 85,
                "value_score": 65,
            },
            {
                "name": "Kunzum Travel Café",
                "area": "Hauz Khas",
                "city": "Delhi NCR",
                "rating": 4.2,
                "review_count": 1850,
                "avg_order_value": 0,
                "price_band": "₹",
                "specialties": ["Pay-what-you-wish", "Board Games", "Travel Books"],
                "positive_themes": ["unique concept", "community feel", "intellectual crowd"],
                "negative_themes": ["not for everyone", "very small", "no food"],
                "delivery_time_min": 0,
                "platforms": ["Dine-in"],
                "seating_capacity": 20,
                "years_active": 13,
                "notable": "Pay-what-you-wish model — niche but iconic brand in Delhi",
                "menu_variety_score": 15,
                "value_score": 95,
            },
            {
                "name": "Imperfecto HKV",
                "area": "Hauz Khas",
                "city": "Delhi NCR",
                "rating": 4.1,
                "review_count": 5400,
                "avg_order_value": 620,
                "price_band": "₹₹₹",
                "specialties": ["Mediterranean", "Cocktails", "Rooftop Dining"],
                "positive_themes": ["rooftop views", "great cocktails", "lively atmosphere"],
                "negative_themes": ["crowded on weekends", "noisy", "pricey drinks"],
                "delivery_time_min": 40,
                "platforms": ["Zomato", "Dine-in"],
                "seating_capacity": 110,
                "years_active": 10,
                "notable": "Popular HKV rooftop bar-café with bohemian Mediterranean vibe",
                "menu_variety_score": 74,
                "value_score": 52,
            },
        ],
        "Khan Market": [
            {
                "name": "The Big Chill Café",
                "area": "Khan Market",
                "city": "Delhi NCR",
                "rating": 4.5,
                "review_count": 9800,
                "avg_order_value": 750,
                "price_band": "₹₹₹",
                "specialties": ["Pasta", "Wood-fired Pizza", "Desserts"],
                "positive_themes": ["iconic Delhi institution", "must-try desserts", "great pasta"],
                "negative_themes": ["long queues", "no reservations", "pricey"],
                "delivery_time_min": 45,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 75,
                "years_active": 22,
                "notable": "Delhi's most iconic Italian café — cult following with legendary queues",
                "menu_variety_score": 80,
                "value_score": 55,
            },
            {
                "name": "Amici Café",
                "area": "Khan Market",
                "city": "Delhi NCR",
                "rating": 4.0,
                "review_count": 3200,
                "avg_order_value": 480,
                "price_band": "₹₹",
                "specialties": ["Italian", "Coffee", "Brunch"],
                "positive_themes": ["reliable Italian food", "good coffee", "pleasant ambience"],
                "negative_themes": ["average portions", "slow service on weekends"],
                "delivery_time_min": 35,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 55,
                "years_active": 12,
                "notable": "Consistent neighbourhood Italian café popular with Khan Market regulars",
                "menu_variety_score": 68,
                "value_score": 62,
            },
            {
                "name": "Costa Coffee Khan Market",
                "area": "Khan Market",
                "city": "Delhi NCR",
                "rating": 3.8,
                "review_count": 2100,
                "avg_order_value": 380,
                "price_band": "₹₹",
                "specialties": ["Coffee", "Sandwiches", "Pastries"],
                "positive_themes": ["air conditioned", "quick service", "familiar menu"],
                "negative_themes": ["corporate feel", "overpriced", "average quality"],
                "delivery_time_min": 25,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 60,
                "years_active": 8,
                "notable": "Global chain serving Khan Market's office and shopping crowd",
                "menu_variety_score": 58,
                "value_score": 54,
            },
        ],
        "Lajpat Nagar": [
            {
                "name": "Café Lota",
                "area": "Lajpat Nagar",
                "city": "Delhi NCR",
                "rating": 4.3,
                "review_count": 4600,
                "avg_order_value": 420,
                "price_band": "₹₹",
                "specialties": ["Indian Fusion", "Heritage Food", "Chai"],
                "positive_themes": ["unique Indian fusion menu", "heritage setting", "great chai"],
                "negative_themes": ["limited seating", "can get crowded", "slow service"],
                "delivery_time_min": 30,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 50,
                "years_active": 9,
                "notable": "Creative Indian fusion menu with heritage craft décor — a South Delhi favourite",
                "menu_variety_score": 72,
                "value_score": 70,
            },
            {
                "name": "Roastery Coffee House Lajpat",
                "area": "Lajpat Nagar",
                "city": "Delhi NCR",
                "rating": 4.2,
                "review_count": 2800,
                "avg_order_value": 400,
                "price_band": "₹₹",
                "specialties": ["Specialty Coffee", "Brunch", "Cold Brew"],
                "positive_themes": ["excellent specialty coffee", "cosy interior", "good brunch options"],
                "negative_themes": ["pricey for the area", "limited parking"],
                "delivery_time_min": 28,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 45,
                "years_active": 5,
                "notable": "Specialty coffee outpost bringing third-wave coffee culture to Lajpat Nagar",
                "menu_variety_score": 63,
                "value_score": 65,
            },
        ],
        "Saket": [
            {
                "name": "Farzi Café",
                "area": "Saket",
                "city": "Delhi NCR",
                "rating": 4.3,
                "review_count": 6200,
                "avg_order_value": 750,
                "price_band": "₹₹₹",
                "specialties": ["Modern Indian", "Cocktails", "Molecular Gastronomy"],
                "positive_themes": ["innovative presentations", "great cocktails", "fun experience"],
                "negative_themes": ["expensive", "small portions", "loud music"],
                "delivery_time_min": 45,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 100,
                "years_active": 7,
                "notable": "Modern Indian bistro known for molecular gastronomy and creative cocktails",
                "menu_variety_score": 82,
                "value_score": 50,
            },
            {
                "name": "Mamagoto",
                "area": "Saket",
                "city": "Delhi NCR",
                "rating": 4.2,
                "review_count": 5100,
                "avg_order_value": 580,
                "price_band": "₹₹",
                "specialties": ["Pan-Asian", "Noodles", "Sushi"],
                "positive_themes": ["flavourful Asian food", "good for groups", "vibrant décor"],
                "negative_themes": ["crowded on weekends", "average service speed"],
                "delivery_time_min": 38,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 85,
                "years_active": 11,
                "notable": "Popular Pan-Asian chain with a playful brand identity and strong delivery volumes",
                "menu_variety_score": 78,
                "value_score": 63,
            },
        ],
        "Cyber Hub Gurugram": [
            {
                "name": "Molecule Air Bar",
                "area": "Cyber Hub Gurugram",
                "city": "Delhi NCR",
                "rating": 4.1,
                "review_count": 7800,
                "avg_order_value": 800,
                "price_band": "₹₹₹",
                "specialties": ["Molecular Cocktails", "Fusion", "Live Music"],
                "positive_themes": ["stunning molecular cocktails", "great ambience", "good for groups"],
                "negative_themes": ["very expensive", "crowded on weekends", "loud"],
                "delivery_time_min": 0,
                "platforms": ["Dine-in"],
                "seating_capacity": 130,
                "years_active": 8,
                "notable": "Cyber Hub landmark renowned for molecular mixology and premium nightlife experience",
                "menu_variety_score": 78,
                "value_score": 44,
            },
            {
                "name": "Pirates of the Grill",
                "area": "Cyber Hub Gurugram",
                "city": "Delhi NCR",
                "rating": 4.0,
                "review_count": 9200,
                "avg_order_value": 750,
                "price_band": "₹₹₹",
                "specialties": ["Grills", "BBQ", "Continental"],
                "positive_themes": ["generous portions", "great grills", "good for corporate dinners"],
                "negative_themes": ["pricey", "service inconsistent on busy nights", "noisy"],
                "delivery_time_min": 50,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 150,
                "years_active": 12,
                "notable": "Gurugram's go-to grill restaurant for corporate teams and family gatherings",
                "menu_variety_score": 75,
                "value_score": 48,
            },
            {
                "name": "Soi 7",
                "area": "Cyber Hub Gurugram",
                "city": "Delhi NCR",
                "rating": 4.2,
                "review_count": 6400,
                "avg_order_value": 720,
                "price_band": "₹₹₹",
                "specialties": ["Thai", "Asian Fusion", "Craft Beer"],
                "positive_themes": ["excellent craft beer selection", "authentic Thai flavours", "stylish setting"],
                "negative_themes": ["pricey", "reservation needed on weekends", "parking can be tough"],
                "delivery_time_min": 40,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 120,
                "years_active": 9,
                "notable": "Cyber Hub's top Thai-fusion pub with an impressive craft beer tap list",
                "menu_variety_score": 80,
                "value_score": 50,
            },
        ],
        "Sector 18 Noida": [
            {
                "name": "The Brew Estate",
                "area": "Sector 18 Noida",
                "city": "Delhi NCR",
                "rating": 4.0,
                "review_count": 4300,
                "avg_order_value": 650,
                "price_band": "₹₹₹",
                "specialties": ["Craft Beer", "Continental", "Fusion"],
                "positive_themes": ["wide craft beer selection", "good food", "great ambience"],
                "negative_themes": ["pricey", "crowded on weekends", "slow service at peak hours"],
                "delivery_time_min": 40,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 110,
                "years_active": 6,
                "notable": "Noida's favourite craft beer destination with a strong weekend crowd",
                "menu_variety_score": 74,
                "value_score": 52,
            },
            {
                "name": "Café Delhi Heights Noida",
                "area": "Sector 18 Noida",
                "city": "Delhi NCR",
                "rating": 4.2,
                "review_count": 5600,
                "avg_order_value": 680,
                "price_band": "₹₹₹",
                "specialties": ["All-day Dining", "Continental", "Cocktails"],
                "positive_themes": ["extensive menu", "great desserts", "reliable quality"],
                "negative_themes": ["expensive", "crowded", "parking difficult"],
                "delivery_time_min": 38,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 120,
                "years_active": 10,
                "notable": "Noida's premium all-day diner loved for consistent quality and large portions",
                "menu_variety_score": 82,
                "value_score": 55,
            },
        ],
        "Sector 120 Noida": [
            {
                "name": "Cafe Ciro",
                "area": "Sector 120 Noida",
                "city": "Delhi NCR",
                "rating": 4.4,
                "review_count": 1531,
                "avg_order_value": 700,
                "price_band": "₹₹₹",
                "specialties": ["White Sauce Pasta", "Wood-fired Pizza", "Mocktails", "Specialty Coffee"],
                "positive_themes": ["floral decor", "cozy ambiance", "great for photos", "courteous staff", "ample parking"],
                "negative_themes": ["slow during rush hours", "slightly pricey"],
                "delivery_time_min": 30,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 55,
                "years_active": 3,
                "notable": "Sector 120's most photographed cafe — Italian-leaning with strong weekend crowd",
                "menu_variety_score": 70,
                "value_score": 60,
            },
            {
                "name": "Third Wave Coffee — Sector 119",
                "area": "Sector 120 Noida",
                "city": "Delhi NCR",
                "rating": 4.8,
                "review_count": 1587,
                "avg_order_value": 420,
                "price_band": "₹₹",
                "specialties": ["Specialty Coffee", "Single Origin", "Pour Over", "Croissants", "Pancakes"],
                "positive_themes": ["outstanding coffee quality", "friendly patient staff", "cozy vibe", "Instagram-worthy"],
                "negative_themes": ["limited full-meal options", "not ideal for dinner"],
                "delivery_time_min": 25,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 40,
                "years_active": 4,
                "notable": "Sector 119's top-rated cafe — premium specialty coffee with all-day light bites",
                "menu_variety_score": 55,
                "value_score": 72,
            },
        ],
        "Sector 121 Noida": [
            {
                "name": "Yuvan Cafe & Restro",
                "area": "Sector 121 Noida",
                "city": "Delhi NCR",
                "rating": 4.3,
                "review_count": 601,
                "avg_order_value": 500,
                "price_band": "₹₹",
                "specialties": ["North Indian", "Biryani", "Fast Food", "Beverages"],
                "positive_themes": ["cozy neighborhood feel", "good value", "generous portions", "quick service"],
                "negative_themes": ["limited continental options", "basic decor", "small menu"],
                "delivery_time_min": 25,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 35,
                "years_active": 2,
                "notable": "Sector 121's go-to neighborhood restro for casual meals and groups",
                "menu_variety_score": 52,
                "value_score": 78,
            },
            {
                "name": "The Daily Grind Cafe",
                "area": "Sector 121 Noida",
                "city": "Delhi NCR",
                "rating": 4.2,
                "review_count": 380,
                "avg_order_value": 450,
                "price_band": "₹₹",
                "specialties": ["Cold Coffee", "Sandwiches", "Waffles", "Quick Bites"],
                "positive_themes": ["fast service", "good cold coffee", "student crowd friendly", "pocket friendly"],
                "negative_themes": ["small seating area", "average food quality", "basic ambiance"],
                "delivery_time_min": 22,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 25,
                "years_active": 2,
                "notable": "Quick-service cafe popular with Sector 121 residential colony residents",
                "menu_variety_score": 48,
                "value_score": 80,
            },
        ],
        "Sector 122 Noida": [
            {
                "name": "Vintage Cottage Cafe",
                "area": "Sector 122 Noida",
                "city": "Delhi NCR",
                "rating": 4.5,
                "review_count": 290,
                "avg_order_value": 400,
                "price_band": "₹₹",
                "specialties": ["Cheesy Pull Pizza", "Artisan Pasta", "Homemade Quiche", "Seasonal Tarts", "Fresh Coffee"],
                "positive_themes": ["vintage wooden interior", "cottage aesthetic", "cozy fireplace", "friendly service", "unique homemade food"],
                "negative_themes": ["limited reviews — new cafe", "small seating", "no alcohol"],
                "delivery_time_min": 35,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 28,
                "years_active": 1,
                "notable": "Hidden gem — artisanal Italian/continental cafe with hand-crafted menu and cottage-style charm",
                "menu_variety_score": 65,
                "value_score": 75,
            },
            {
                "name": "Ka Kha Ga — The Boutique Cafe",
                "area": "Sector 122 Noida",
                "city": "Delhi NCR",
                "rating": 4.7,
                "review_count": 1240,
                "avg_order_value": 500,
                "price_band": "₹₹",
                "specialties": ["Vegetable Lasagne", "Bruschetta", "Grilled Paneer Jalapeño", "Gourmet Mushroom Cheese", "Live Music"],
                "positive_themes": ["cozy + elegant balance", "soft lighting", "tasteful decor", "live music evenings", "warm hospitable staff", "great for dates"],
                "negative_themes": ["gets busy on weekends", "limited outdoor seating", "no alcohol"],
                "delivery_time_min": 35,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 38,
                "years_active": 2,
                "notable": "Sector 122's boutique Italian/continental cafe — live music, romantic ambiance, highly rated on Zomato & Magicpin",
                "menu_variety_score": 72,
                "value_score": 74,
            },
            {
                "name": "ATHOSC Cafe & Restaurant",
                "area": "Sector 122 Noida",
                "city": "Delhi NCR",
                "rating": 4.8,
                "review_count": 410,
                "avg_order_value": 500,
                "price_band": "₹₹",
                "specialties": ["Wood-fire Pizza", "Authentic Italian Pasta", "Mushroom Soup", "Caesar Salad", "Specialty Coffees"],
                "positive_themes": ["BYOB friendly", "cozy atmosphere", "great for coworking", "live music", "welcoming host", "authentic wood-fire taste"],
                "negative_themes": ["small space", "no in-house alcohol served", "limited parking"],
                "delivery_time_min": 35,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 30,
                "years_active": 2,
                "notable": "Sector 122's highest-rated Italian cafe — BYOB policy, wood-fire pizza, live music; feels like a Rome side-street bistro",
                "menu_variety_score": 68,
                "value_score": 76,
            },
            {
                "name": "Saffron Stories",
                "area": "Sector 122 Noida",
                "city": "Delhi NCR",
                "rating": 4.8,
                "review_count": 870,
                "avg_order_value": 800,
                "price_band": "₹₹₹",
                "specialties": ["Pasta Alfredo", "Afghan Cuisine", "Continental Platters", "North Indian", "Mocktails"],
                "positive_themes": ["elegant ambience", "consistently high rating", "diverse menu", "great for celebrations", "attentive service"],
                "negative_themes": ["no alcohol", "limited parking", "slightly pricey for the area"],
                "delivery_time_min": 40,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 60,
                "years_active": 3,
                "notable": "Upscale multicuisine dining room — Sector 122's premium celebration venue with Afghan, Continental and North Indian fusion",
                "menu_variety_score": 82,
                "value_score": 62,
            },
        ],
        "Gaur City Noida": [
            {
                "name": "Black Club + Cafe",
                "area": "Gaur City Noida",
                "city": "Delhi NCR",
                "rating": 4.7,
                "review_count": 5016,
                "avg_order_value": 850,
                "price_band": "₹₹₹",
                "specialties": ["Wood-fire Pizza", "Pasta", "Cocktails", "Live Music", "Continental"],
                "positive_themes": ["vibrant club-cafe vibe", "stylish black decor", "live music weekends", "friendly attentive staff", "delicious pasta", "energetic atmosphere"],
                "negative_themes": ["slightly expensive", "loud atmosphere", "parking can be tight at Gaur City Mall"],
                "delivery_time_min": 32,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 90,
                "years_active": 5,
                "notable": "Gaur City's most popular cafe — 5000+ Zomato reviews, club meets cafe concept with live music and cocktails",
                "menu_variety_score": 78,
                "value_score": 58,
            },
            {
                "name": "The Food Stories",
                "area": "Gaur City Noida",
                "city": "Delhi NCR",
                "rating": 4.2,
                "review_count": 720,
                "avg_order_value": 550,
                "price_band": "₹₹",
                "specialties": ["North Indian", "Mughlai", "Biryani", "Burgers", "Continental Salads"],
                "positive_themes": ["diverse menu for the whole family", "good value", "quick delivery", "fresh ingredients"],
                "negative_themes": ["average ambiance", "not Italian-focused", "inconsistent service"],
                "delivery_time_min": 28,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 50,
                "years_active": 3,
                "notable": "Gaur City 1's family-friendly multicuisine destination with wide appeal across age groups",
                "menu_variety_score": 76,
                "value_score": 72,
            },
        ],
        "Noida Expressway": [
            {
                "name": "Say Fontina",
                "area": "Noida Expressway",
                "city": "Delhi NCR",
                "rating": 4.7,
                "review_count": 2021,
                "avg_order_value": 850,
                "price_band": "₹₹₹",
                "specialties": ["Wood-fired Pizza (Burrata, Truffle Mushroom)", "Fresh Handmade Pasta", "Mezze Platter", "Tiramisu", "Specialty Coffee"],
                "positive_themes": ["romantic haven", "fresh ingredients", "rustic wood-fired aroma", "excellent service", "great for dates and families", "Sunday kids pizza-making classes"],
                "negative_themes": ["slightly far from Sector 120", "packaging inconsistency for delivery", "pricier than local options"],
                "delivery_time_min": 45,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 65,
                "years_active": 4,
                "notable": "Ranked #10 of 1,167 Noida restaurants on Tripadvisor — Expressway's finest Italian/Mediterranean. Direct competitor to premium Italian cafes. Gulshan One29 Mall, Sector 129.",
                "menu_variety_score": 80,
                "value_score": 62,
            },
            {
                "name": "Dios — The Neighbourhood Bistro",
                "area": "Noida Expressway",
                "city": "Delhi NCR",
                "rating": 4.1,
                "review_count": 699,
                "avg_order_value": 700,
                "price_band": "₹₹₹",
                "specialties": ["Drunken Pasta", "Alfredo Pasta", "Tandoori Chicken Pizza", "S'mores Brownie Skillet", "Quesadillas"],
                "positive_themes": ["cozy dim lighting", "unique crockery", "digital in-seat games", "generous portions", "neighborhood bistro feel", "great dessert presentation"],
                "negative_themes": ["one hygiene complaint noted in reviews", "slightly inconsistent service", "pricing above area average"],
                "delivery_time_min": 48,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 55,
                "years_active": 6,
                "notable": "ETT2 Sector 132's Italian-Mexican bistro hybrid — memorable for interactive digital menus and unique crockery presentation",
                "menu_variety_score": 74,
                "value_score": 60,
            },
            {
                "name": "Spezia Bistro",
                "area": "Noida Expressway",
                "city": "Delhi NCR",
                "rating": 4.5,
                "review_count": 6368,
                "avg_order_value": 1300,
                "price_band": "₹₹₹₹",
                "specialties": ["Wood-fired Pizza", "Handmade Pasta", "Sushi", "Mediterranean Platters", "Craft Burgers"],
                "positive_themes": ["vibrant dining destination", "warm cozy atmosphere", "attentive staff", "innovative Italian-Mediterranean-Japanese fusion menu", "wide dessert selection"],
                "negative_themes": ["food quality inconsistency", "starters and beverages overpriced", "some dishes below expectation"],
                "delivery_time_min": 40,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 100,
                "years_active": 7,
                "notable": "Hajipur Market Sector 104 — 6000+ Justdial ratings. Premium Italian-Mediterranean-Japanese fusion, the upscale benchmark for the Noida corridor.",
                "menu_variety_score": 90,
                "value_score": 45,
            },
            {
                "name": "Osteria — Authentic Italian Pizzeria",
                "area": "Noida Expressway",
                "city": "Delhi NCR",
                "rating": 4.5,
                "review_count": 740,
                "avg_order_value": 600,
                "price_band": "₹₹₹",
                "specialties": ["Handcrafted Wood-fired Pizza (Pesto Burrata, Wild Spinach & Garlic)", "Artisanal Pasta", "Blue Tokai Specialty Coffee"],
                "positive_themes": ["authentic Italian flavors", "high-quality fresh ingredients", "artisanal approach", "cozy ambience in Spectrum Metro", "best pizza in Noida for many reviewers"],
                "negative_themes": ["no alcohol", "mall parking charges", "slightly outside Sector 120 radius"],
                "delivery_time_min": 48,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 42,
                "years_active": 3,
                "notable": "Spectrum Metro Mall Sector 75 — Tripadvisor top-ranked Italian. Purist Italian approach with Blue Tokai coffee partnership. Direct concept competitor.",
                "menu_variety_score": 65,
                "value_score": 68,
            },
        ],
    },
    "Hyderabad": {
        "Jubilee Hills": [
            {
                "name": "Café Niloufer",
                "area": "Jubilee Hills",
                "city": "Hyderabad",
                "rating": 4.3,
                "review_count": 5600,
                "avg_order_value": 160,
                "price_band": "₹",
                "specialties": ["Osmania Biscuit", "Irani Chai", "Samosa"],
                "positive_themes": ["iconic Hyderabad experience", "authentic", "cheap and cheerful"],
                "negative_themes": ["basic decor", "cash only", "crowded mornings"],
                "delivery_time_min": 20,
                "platforms": ["Zomato", "Dine-in"],
                "seating_capacity": 40,
                "years_active": 25,
                "notable": "Legendary Irani café — must-visit for tourists and locals alike",
                "menu_variety_score": 35,
                "value_score": 95,
            },
            {
                "name": "Forest Café",
                "area": "Jubilee Hills",
                "city": "Hyderabad",
                "rating": 4.1,
                "review_count": 2300,
                "avg_order_value": 480,
                "price_band": "₹₹₹",
                "specialties": ["Farm-to-Table", "Organic Coffee", "Healthy Bowls"],
                "positive_themes": ["healthy menu", "beautiful garden seating", "eco-friendly"],
                "negative_themes": ["expensive", "limited parking", "small menu"],
                "delivery_time_min": 40,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 55,
                "years_active": 4,
                "notable": "Hyderabad's top wellness café for health-conscious diners",
                "menu_variety_score": 60,
                "value_score": 50,
            },
        ],
        "Banjara Hills": [
            {
                "name": "Roastery Coffee House",
                "area": "Banjara Hills",
                "city": "Hyderabad",
                "rating": 4.4,
                "review_count": 3780,
                "avg_order_value": 420,
                "price_band": "₹₹",
                "specialties": ["Specialty Coffee", "Croissants", "Brunch"],
                "positive_themes": ["great specialty coffee", "beautiful space", "good pastries"],
                "negative_themes": ["pricey", "can get crowded", "limited parking"],
                "delivery_time_min": 30,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 70,
                "years_active": 6,
                "notable": "Gold standard for specialty coffee in Hyderabad",
                "menu_variety_score": 65,
                "value_score": 62,
            },
            {
                "name": "Runway 9 Café",
                "area": "Banjara Hills",
                "city": "Hyderabad",
                "rating": 3.9,
                "review_count": 1420,
                "avg_order_value": 350,
                "price_band": "₹₹",
                "specialties": ["Waffles", "Mocktails", "Pasta"],
                "positive_themes": ["good desserts", "trendy decor", "good for photos"],
                "negative_themes": ["inconsistent food", "average coffee", "slow delivery"],
                "delivery_time_min": 42,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 60,
                "years_active": 3,
                "notable": "Instagram-friendly café popular with college students",
                "menu_variety_score": 72,
                "value_score": 60,
            },
        ],
    },
    "Pune": {
        "Koregaon Park": [
            {
                "name": "Vohuman Café",
                "area": "Koregaon Park",
                "city": "Pune",
                "rating": 4.3,
                "review_count": 4200,
                "avg_order_value": 120,
                "price_band": "₹",
                "specialties": ["Irani Chai", "Bun Maska", "Omelette"],
                "positive_themes": ["legendary status", "cheap and good", "old-world charm"],
                "negative_themes": ["long queues", "cash only", "basic seating"],
                "delivery_time_min": 15,
                "platforms": ["Zomato", "Dine-in"],
                "seating_capacity": 45,
                "years_active": 30,
                "notable": "Pune's most iconic Irani café — early morning queues are legendary",
                "menu_variety_score": 28,
                "value_score": 96,
            },
            {
                "name": "Café Peter",
                "area": "Koregaon Park",
                "city": "Pune",
                "rating": 4.0,
                "review_count": 2600,
                "avg_order_value": 320,
                "price_band": "₹₹",
                "specialties": ["English Breakfast", "Coffee", "Pancakes"],
                "positive_themes": ["relaxed vibe", "good breakfast", "reasonable prices"],
                "negative_themes": ["slow service on weekends", "dated decor"],
                "delivery_time_min": 32,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 55,
                "years_active": 18,
                "notable": "KP institution trusted by expats and long-time Punekars",
                "menu_variety_score": 62,
                "value_score": 72,
            },
        ],
    },
    "Chennai": {
        "Anna Nagar": [
            {
                "name": "Amethyst Café",
                "area": "Anna Nagar",
                "city": "Chennai",
                "rating": 4.4,
                "review_count": 3900,
                "avg_order_value": 480,
                "price_band": "₹₹₹",
                "specialties": ["Continental", "High Tea", "Patisserie"],
                "positive_themes": ["heritage property", "beautiful garden", "excellent pastries"],
                "negative_themes": ["very expensive", "reservation needed", "limited parking"],
                "delivery_time_min": 45,
                "platforms": ["Zomato", "Dine-in"],
                "seating_capacity": 80,
                "years_active": 15,
                "notable": "Chennai's most beautiful café in a colonial bungalow setting",
                "menu_variety_score": 70,
                "value_score": 50,
            },
            {
                "name": "Brew Room",
                "area": "Anna Nagar",
                "city": "Chennai",
                "rating": 4.1,
                "review_count": 1700,
                "avg_order_value": 340,
                "price_band": "₹₹",
                "specialties": ["Specialty Coffee", "Waffles", "Smoothie Bowls"],
                "positive_themes": ["good specialty coffee", "good wifi", "friendly staff"],
                "negative_themes": ["small menu", "limited seating"],
                "delivery_time_min": 28,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 30,
                "years_active": 3,
                "notable": "Growing specialty coffee destination in Anna Nagar",
                "menu_variety_score": 55,
                "value_score": 66,
            },
        ],
    },
    "Kolkata": {
        "Park Street": [
            {
                "name": "Flurys",
                "area": "Park Street",
                "city": "Kolkata",
                "rating": 4.5,
                "review_count": 8400,
                "avg_order_value": 360,
                "price_band": "₹₹",
                "specialties": ["Patisserie", "English Tea", "Cakes"],
                "positive_themes": ["legendary Kolkata institution", "great cakes", "heritage charm"],
                "negative_themes": ["crowded", "service can be slow", "limited savoury options"],
                "delivery_time_min": 30,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 100,
                "years_active": 95,
                "notable": "Kolkata's most iconic café since 1927 — unmatched brand heritage",
                "menu_variety_score": 75,
                "value_score": 70,
            },
            {
                "name": "Café Coffee Day — Park Street",
                "area": "Park Street",
                "city": "Kolkata",
                "rating": 3.8,
                "review_count": 2200,
                "avg_order_value": 260,
                "price_band": "₹₹",
                "specialties": ["Coffee", "Cold Drinks", "Sandwiches"],
                "positive_themes": ["air conditioned", "familiar menu", "central location"],
                "negative_themes": ["average quality", "corporate chain feel", "overpriced for quality"],
                "delivery_time_min": 25,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 65,
                "years_active": 18,
                "notable": "National chain outpost in Kolkata's busiest café street",
                "menu_variety_score": 60,
                "value_score": 58,
            },
        ],
    },
    "Jaipur": {
        "C-Scheme": [
            {
                "name": "Café Palladio",
                "area": "C-Scheme",
                "city": "Jaipur",
                "rating": 4.6,
                "review_count": 2980,
                "avg_order_value": 720,
                "price_band": "₹₹₹",
                "specialties": ["Italian", "Mediterranean", "High Tea"],
                "positive_themes": ["stunning Italian-inspired decor", "excellent food", "unique experience"],
                "negative_themes": ["very expensive", "only for special occasions", "reservation essential"],
                "delivery_time_min": 0,
                "platforms": ["Dine-in"],
                "seating_capacity": 60,
                "years_active": 7,
                "notable": "One of India's most beautiful cafés — multiple international awards",
                "menu_variety_score": 68,
                "value_score": 45,
            },
            {
                "name": "Curious Life Coffee Roasters",
                "area": "C-Scheme",
                "city": "Jaipur",
                "rating": 4.3,
                "review_count": 1540,
                "avg_order_value": 380,
                "price_band": "₹₹",
                "specialties": ["Specialty Coffee", "Sourdough", "Brunch"],
                "positive_themes": ["excellent single origin coffee", "cosy atmosphere", "great brunch"],
                "negative_themes": ["small space", "limited parking"],
                "delivery_time_min": 32,
                "platforms": ["Zomato", "Swiggy", "Dine-in"],
                "seating_capacity": 28,
                "years_active": 4,
                "notable": "Jaipur's best specialty coffee shop — growing fast",
                "menu_variety_score": 55,
                "value_score": 65,
            },
        ],
    },
}

# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

CITIES: list[str] = sorted(COMPETITOR_DB.keys())


def get_areas(city: str) -> list[str]:
    """Return list of areas for a given city."""
    city_data = COMPETITOR_DB.get(city, {})
    return sorted(city_data.keys())


def get_competitors(city: str, area: Optional[str] = None) -> list[dict]:
    """
    Return competitor list for city+area.
    If area is None or empty, combine all areas in the city.
    """
    city_data = COMPETITOR_DB.get(city, {})
    if area and area in city_data:
        return list(city_data[area])
    # combine all areas
    combined: list[dict] = []
    for comps in city_data.values():
        combined.extend(comps)
    return combined


def live_search_competitors(city: str, area: str) -> list[dict]:
    """
    Use DuckDuckGo search to find live café results for the given city+area.
    Returns up to 6 results with title, snippet, url fields.
    Returns [] gracefully on any failure.
    """
    try:
        from duckduckgo_search import DDGS  # type: ignore
    except ImportError:
        return []

    query = f"best cafes {area} {city} India review rating 2024"
    results: list[dict] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=6):
                results.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("body", r.get("snippet", "")),
                    "url":     r.get("href", r.get("url", "")),
                })
    except Exception:
        return []
    return results


def analyze_with_ai(our_cafe_stats: dict, competitors: list[dict], city: str, area: str) -> dict:
    """
    Call the Anthropic API (claude-opus-4-5) to analyse the competitive landscape
    and return structured insights.
    """
    try:
        import anthropic  # type: ignore

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {
                "analysis": (
                    "⚠️ ANTHROPIC_API_KEY is not set.\n\n"
                    "To fix this in Railway:\n"
                    "1. Go to your Railway project → Cafe-Buddy-AI service\n"
                    "2. Click **Variables** tab\n"
                    "3. Add variable: ANTHROPIC_API_KEY = (your Anthropic API key)\n"
                    "4. Railway will auto-redeploy with the key active.\n\n"
                    "Your Anthropic API key can be found at console.anthropic.com"
                ),
                "model": "claude-opus-4-5",
                "status": "error",
            }
        client = anthropic.Anthropic(api_key=api_key)

        # Summarise competitor data for the prompt
        comp_summary_lines: list[str] = []
        for c in competitors[:8]:  # cap at 8 to keep prompt tight
            comp_summary_lines.append(
                f"- {c['name']} ({c['price_band']}): rating {c['rating']}/5, "
                f"{c['review_count']} reviews, avg order ₹{c['avg_order_value']}, "
                f"specialties: {', '.join(c['specialties'][:3])}, "
                f"positives: {', '.join(c['positive_themes'][:2])}, "
                f"negatives: {', '.join(c['negative_themes'][:2])}"
            )
        comp_text = "\n".join(comp_summary_lines) if comp_summary_lines else "No competitor data available."

        our_text = (
            f"Our Café Stats: avg order value ₹{our_cafe_stats.get('avg_order_value', 'N/A')}, "
            f"top item: {our_cafe_stats.get('top_item', 'N/A')}, "
            f"total revenue: ₹{our_cafe_stats.get('total_revenue', 'N/A')}"
            if our_cafe_stats
            else "No sales data uploaded yet (analysis based on market landscape only)."
        )

        prompt = f"""You are a café business consultant specialising in the Indian café market.

Analyse the competitive landscape for a café in {area}, {city}.

{our_text}

Competitors in this area:
{comp_text}

Provide a concise, actionable analysis covering exactly these four sections:

## Market Position
(2-3 sentences: where our café stands vs the competitive landscape, key differentiators to exploit)

## Top 3 Opportunities
1. (opportunity with specific action)
2. (opportunity with specific action)
3. (opportunity with specific action)

## Competitive Threats
(2-3 bullet points on the biggest risks from the competitor set)

## Quick Wins (Next 30 Days)
(3 specific, low-cost actions we can take immediately to gain competitive edge)

Keep the analysis practical, data-driven, and specific to {area}, {city}. Use ₹ for prices."""

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        analysis_text = message.content[0].text if message.content else "No analysis generated."
        return {
            "analysis": analysis_text,
            "model": "claude-opus-4-5",
            "status": "success",
        }

    except Exception as exc:
        return {
            "analysis": f"AI analysis unavailable: {exc}",
            "model": "claude-opus-4-5",
            "status": "error",
        }


def compute_radar_scores(cafe: dict) -> dict:
    """
    Return normalised 0-100 scores for six radar axes.
    """
    # Rating: rating/5 * 100
    rating_score = round((cafe.get("rating", 0) / 5.0) * 100)

    # Price competitiveness: lower price band → higher score
    price_band = cafe.get("price_band", "₹₹")
    price_competitiveness = {"₹": 90, "₹₹": 70, "₹₹₹": 50}.get(price_band, 70)

    # Delivery speed: max(40, 100 - (dt - 15) * 2); 50 if dt == 0
    dt = cafe.get("delivery_time_min", 30)
    if dt == 0:
        delivery_speed = 50  # dine-in only
    else:
        delivery_speed = min(100, max(40, 100 - (dt - 15) * 2))

    # Menu variety: direct score
    menu_variety = min(100, max(0, cafe.get("menu_variety_score", 50)))

    # Popularity: log scale from review_count, capped at 100
    review_count = cafe.get("review_count", 0)
    if review_count <= 0:
        popularity = 0
    else:
        # log10(10000) ≈ 4; normalise so 10,000 reviews → 100
        popularity = min(100, round(math.log10(review_count + 1) / math.log10(10001) * 100))

    # Value for money: direct score
    value_for_money = min(100, max(0, cafe.get("value_score", 50)))

    return {
        "rating":               rating_score,
        "price_competitiveness": price_competitiveness,
        "delivery_speed":       delivery_speed,
        "menu_variety":         menu_variety,
        "popularity":           popularity,
        "value_for_money":      value_for_money,
    }
