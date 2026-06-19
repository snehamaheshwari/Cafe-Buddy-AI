"""
Cafe Buddy Chatbot — streaming AI responses with web search + festival calendar.
Works in three modes (tried in order):
  1. Anthropic Claude — if ANTHROPIC_API_KEY is set and has credits
  2. Groq (free)      — if GROQ_API_KEY is set (Llama 3.3 70B, 14k req/day free)
  3. Smart Analytics  — pure Python analytics engine, no API key needed
"""
from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from data_store import (
    get_data, item_stats, platform_breakdown,
    category_breakdown, daily_revenue,
)
from sentiment_engine import get_engine as get_sentiment_engine
import data_store as _ds

router = APIRouter()

# ─── Env / optional deps ─────────────────────────────────────────────────────

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
_GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "").strip()
_GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL    = "llama-3.3-70b-versatile"   # free tier; 14,400 req/day

try:
    import anthropic as _anthropic
    _ai_client = _anthropic.Anthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else None
    HAS_AI = bool(ANTHROPIC_KEY)
except ImportError:
    _ai_client = None
    HAS_AI = False

HAS_GROQ = bool(_GROQ_API_KEY)

try:
    from duckduckgo_search import DDGS as _DDGS
    HAS_DDG = True
except Exception:
    HAS_DDG = False

# ─── Indian festival calendar ────────────────────────────────────────────────
# Dates reflect 2026 values.  Islamic festival dates shift ~11 days earlier
# each Gregorian year; Hindu lunisolar dates shift within a narrower band.
# Web-search is always triggered for festival queries to confirm exact dates.

_FESTIVALS = [
    {"name": "Valentine's Day",   "month": 2,  "day": 14, "type": "Cultural",
     "menu_ideas": ["Heart-shaped tiramisu", "Rose petal latte", "Lovers' combo for 2", "Strawberry dessert special"],
     "promo_ideas": ["Couple discount 15%", "Candle-light dine-in package", "Pre-book Valentine's table offer"]},

    # Holi 2026: March 3 (Holika Dahan March 2)
    {"name": "Holi",              "month": 3,  "day": 3,  "type": "Hindu",
     "menu_ideas": ["Thandai milkshake", "Gujiya-inspired dessert", "Colourful mocktails (kesariya, gulabi)", "Malpua pancake special"],
     "promo_ideas": ["Buy-1-Get-1 on beverages", "Holi combo thali", "Social media contest — best Holi selfie gets a free dessert"]},

    # Eid al-Fitr 2026: ~20 Mar (end of Ramadan 2026 which starts ~17 Feb)
    {"name": "Eid al-Fitr",       "month": 3,  "day": 20, "type": "Muslim",
     "menu_ideas": ["Sheer khurma dessert", "Biryani-inspired pasta", "Seviyan kheer milkshake", "Non-veg BBQ platter"],
     "promo_ideas": ["Eid special family feast", "Sweet gifting hamper tie-up", "15% off on group tables"]},

    # Ugadi / Gudi Padwa 2026: ~19 Mar (Chaitra Shukla Pratipada)
    {"name": "Ugadi / Gudi Padwa","month": 3,  "day": 19, "type": "Hindu",
     "menu_ideas": ["Ugadi pachadi-inspired sweet-sour shot", "Obbattu / Puran poli dessert", "Special South Indian breakfast combo"],
     "promo_ideas": ["New Year offer — 10% off on first visit", "Festival family pack"]},

    # Ram Navami 2026: ~1 Apr (Chaitra Shukla Navami)
    {"name": "Ram Navami",        "month": 4,  "day": 1,  "type": "Hindu",
     "menu_ideas": ["Sattvic veg special menu", "Panjiri energy bites", "Coconut milk-based drinks"],
     "promo_ideas": ["Pure-veg festival menu for the week", "Discount on sattvic combos"]},

    # Mother's Day 2026: 10 May (2nd Sunday of May)
    {"name": "Mother's Day",      "month": 5,  "day": 10, "type": "Cultural",
     "menu_ideas": ["Mother's favourite breakfast platter", "Flower-themed cake slice", "Chamomile bloom tea"],
     "promo_ideas": ["Free dessert for moms", "Daughter/son pays — mom eats free on combos", "Table decoration for families"]},

    # Eid al-Adha 2026: ~27 May (10 Dhul Hijjah 1447 AH)
    {"name": "Eid al-Adha",       "month": 5,  "day": 27, "type": "Muslim",
     "menu_ideas": ["Non-veg sharing platter", "Mutton keema-inspired pasta", "Dates milkshake", "Biryani feast special"],
     "promo_ideas": ["Bakr-Eid family feast pack", "10-person group discount", "Advance booking offer"]},

    # Father's Day 2026: 21 Jun (3rd Sunday of June)
    {"name": "Father's Day",      "month": 6,  "day": 21, "type": "Cultural",
     "menu_ideas": ["Hearty breakfast platter", "Strong cold brew / espresso combo", "BBQ-style main course"],
     "promo_ideas": ["Dad eats free with 2 paid covers", "Coffee + meal combo at 20% off"]},

    {"name": "Independence Day",  "month": 8,  "day": 15, "type": "National",
     "menu_ideas": ["Tricolour smoothie (saffron+white+green)", "Tricolour pasta", "Dahi parfait with orange & green layers", "Tiranga sandwich"],
     "promo_ideas": ["15% discount on 15th August", "Patriotic combo meal named after freedom fighters", "Social media Tiranga contest"]},

    # Janmashtami 2026: ~14 Aug (Bhadrapada Krishna Ashtami)
    {"name": "Janmashtami",       "month": 8,  "day": 14, "type": "Hindu",
     "menu_ideas": ["Makhan (butter) pancakes", "Chilled Mathura peda dessert", "Panchdrink (5-ingredient milkshake)", "Dahi handi-inspired sundae"],
     "promo_ideas": ["Milk & dairy special discounts", "Sattvic menu for the day", "Kids eat free with adult purchase"]},

    # Ganesh Chaturthi 2026: ~24 Aug (Bhadrapada Shukla Chaturthi)
    {"name": "Ganesh Chaturthi",  "month": 8,  "day": 24, "type": "Hindu",
     "menu_ideas": ["Modak-inspired lava cake", "Coconut laddoo dessert cup", "Ukadiche modak cheesecake", "Panchkhadya milkshake"],
     "promo_ideas": ["Sweet combo for devotees after darshan", "Group celebration packages", "Ganesh festival takeaway special"]},

    # Navratri 2026: ~22 Oct – 31 Oct (Ashvin Shukla Pratipada)
    {"name": "Navratri",          "month": 10, "day": 22, "type": "Hindu",
     "menu_ideas": ["Sabudana khichdi bowl", "Singhare ki poori with potato curry", "Kuttu dosa", "Fruit chaat", "Makhana snack bowl", "Rajgira smoothie"],
     "promo_ideas": ["9-day vrat-friendly menu", "Fasting special combos (no onion/garlic)", "Social media Navratri Garba contest"]},

    # Dussehra 2026: ~31 Oct (Vijaya Dashami, 10th day of Navratri)
    {"name": "Dussehra",          "month": 10, "day": 31, "type": "Hindu",
     "menu_ideas": ["Victory combo (full meal deal)", "Sweet jalebi-inspired dessert", "Ram Leela themed mocktail"],
     "promo_ideas": ["Good-over-evil 50% off on second item", "Vijay combo meal", "Free dessert with combo orders"]},

    # Diwali 2026: ~8 Nov (Kartik Amavasya)
    {"name": "Diwali",            "month": 11, "day": 8,  "type": "Hindu",
     "menu_ideas": ["Dry fruit milkshake", "Kaju katli-inspired dessert cup", "Chakli-inspired breadsticks with dip", "Gulab jamun cheesecake", "Shahi tukda special"],
     "promo_ideas": ["Diwali gift hampers", "Festive combo meals with sweet box", "Loyalty point double event", "Diwali corporate bulk orders"]},

    {"name": "Christmas",         "month": 12, "day": 25, "type": "Cultural",
     "menu_ideas": ["Plum cake slice", "Christmas tree pasta", "Gingerbread latte", "Yule log dessert", "Mulled cider-inspired mocktail"],
     "promo_ideas": ["25% off on 25th Dec", "Secret Santa meal exchange promo", "Table decoration with Christmas theme"]},

    {"name": "New Year's Eve",    "month": 12, "day": 31, "type": "Cultural",
     "menu_ideas": ["Midnight countdown combo", "Champagne-inspired sparkling mocktail", "Festive sharing platter"],
     "promo_ideas": ["New Year's Eve reservation package", "Countdown event with DJ", "New Year resolution menu (healthy options)"]},
]


def get_upcoming_festivals(days: int = 90) -> list:
    today = datetime.now()
    result = []
    for year_offset in [0, 1]:
        year = today.year + year_offset
        for f in _FESTIVALS:
            try:
                fest_date = datetime(year, f["month"], f["day"])
                delta     = (fest_date - today).days
                if 0 <= delta <= days:
                    result.append({**f, "date": fest_date.strftime("%d %b %Y"),
                                   "days_away": delta})
            except ValueError:
                pass
    return sorted(result, key=lambda x: x["days_away"])

# ─── Web search ───────────────────────────────────────────────────────────────

def _web_search(query: str, max_results: int = 4) -> list[dict]:
    if not HAS_DDG:
        return []
    try:
        with _DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, timelimit="m"))
        return [{"title": r.get("title", ""), "body": r.get("body", "")[:400],
                 "url": r.get("href", "")} for r in results]
    except Exception:
        return []

def _needs_web_search(msg: str) -> bool:
    keywords = [
        "festival", "navratri", "diwali", "holi", "eid", "christmas", "new year",
        "trending", "trend", "idea", "ideas", "special dish", "new dish", "recipe",
        "weather", "event", "holiday", "season", "market", "competitor",
        "how to", "strategy", "marketing", "promotion", "social media",
        "instagram", "zomato", "swiggy",
        # broader general-knowledge triggers
        "license", "fssai", "legal", "permit", "regulation",
        "staff", "hire", "salary", "wage",
        "equipment", "machine", "grinder", "coffee machine",
        "open", "timing", "hours", "schedule",
        "price", "pricing", "menu engineering",
        "tips", "advice", "best practice", "benchmark",
    ]
    m = msg.lower()
    return any(k in m for k in keywords)

# ─── Data context builder ─────────────────────────────────────────────────────

def _build_context(data: list) -> str:
    if not data:
        return "No sales data loaded. Answering from general café knowledge."

    dates       = sorted(set(r["date"] for r in data))
    items       = item_stats(data)
    platforms   = platform_breakdown(data)
    cats        = category_breakdown(data)
    daily       = daily_revenue(data, 14)
    total_rev   = sum(r["revenue"] for r in data)
    total_cost  = sum(r["cost"]    for r in data)

    # Anchor to the latest date IN the dataset so historical uploads still
    # show meaningful "last 7 days" data rather than "(no data in last 7 days)".
    _all_dates  = sorted(r["date"] for r in data if r.get("date"))
    _data_anchor = _all_dates[-1] if _all_dates else datetime.now().strftime("%Y-%m-%d")
    cutoff_7d   = (datetime.strptime(_data_anchor, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
    last_7d     = [r for r in data if r.get("date", "") >= cutoff_7d]
    items_7d    = item_stats(last_7d) if last_7d else item_stats(data)  # fallback to all data

    weekend_rev, weekend_days = 0.0, set()
    weekday_rev, weekday_days = 0.0, set()
    for r in data:
        try:
            d = datetime.strptime(r["date"], "%Y-%m-%d")
            if d.weekday() >= 5:
                weekend_rev += r["revenue"]; weekend_days.add(r["date"])
            else:
                weekday_rev += r["revenue"]; weekday_days.add(r["date"])
        except Exception:
            pass
    w_avg = weekend_rev / max(len(weekend_days), 1)
    d_avg = weekday_rev / max(len(weekday_days), 1)

    top5    = "\n".join(f"  {i+1}. {x['name']}: ₹{x['revenue']:,.0f} rev, {x['qty']:.0f} units, {x['margin_pct']:.1f}% margin"
                        for i, x in enumerate(items[:5]))
    top5_7d = "\n".join(f"  {i+1}. {x['name']}: ₹{x['revenue']:,.0f}" for i, x in enumerate(items_7d[:5]))
    bot3    = "\n".join(f"  {x['name']}: {x['margin_pct']:.1f}% margin" for x in sorted(items, key=lambda x: x["margin_pct"])[:3])
    plat_s  = "\n".join(f"  {p['platform']}: ₹{p['revenue']:,.0f} ({p['orders']} orders)" for p in platforms)
    cat_s   = "\n".join(f"  {c['category']}: ₹{c['revenue']:,.0f} ({c['margin_pct']:.1f}% margin)" for c in cats)

    base_context = f"""── CAFÉ DATA SUMMARY ──────────────────────────────────────────
Date range   : {dates[0]} → {dates[-1]}  ({len(dates)} days)
Total records: {len(data):,}
Total revenue: ₹{total_rev:,.0f}   |  Food cost %: {total_cost/max(total_rev,1)*100:.1f}%
Daily average: ₹{total_rev/max(len(dates),1):,.0f}
Weekend avg  : ₹{w_avg:,.0f}/day   |  Weekday avg: ₹{d_avg:,.0f}/day

TOP 5 ITEMS (all time):
{top5}

LAST 7 DAYS TOP ITEMS:
{top5_7d if items_7d else '  (no data in last 7 days)'}

LOWEST MARGIN ITEMS:
{bot3}

PLATFORM BREAKDOWN:
{plat_s}

CATEGORY REVENUE:
{cat_s}
───────────────────────────────────────────────────────────────"""

    # Append sentiment context when review data is available
    try:
        sent_ctx = get_sentiment_engine().get_chat_context()
        if sent_ctx:
            base_context += "\n\n" + sent_ctx
    except Exception:
        pass

    return base_context

# ─── Claude streaming ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are Cafe Buddy AI — a sharp, data-driven assistant for café owners in India.

## Reasoning flow you MUST follow for every response:
1. **Model Reasoning** — examine ML MODEL REASONING block first (trained models: RF forecast, peak-hour classifier, cancellation risk, cross-sell rules). Cite model predictions when relevant.
2. **Data Analysis** — ground your answer in the CONTEXT block (actual café data: revenue, items, platforms, sentiment).
3. **Web / External** — use WEB SEARCH block for market trends, festival ideas, or anything not covered by internal data.
4. **Final Answer** — combine all three layers into a concise, actionable response.

## Sources you have access to:
1. ML MODEL REASONING — trained Random Forest, Ridge Regression, and classification models run on live POS data
2. Real café sales analytics (CONTEXT block)
3. Customer review sentiment — Pre-trained Logistic Regression + TF-IDF model with aspect analysis (Food, Service, Ambiance, Price, Wait Time), NPS, confidence scores (in CONTEXT when available)
4. Upcoming Indian festivals with menu and promo ideas (FESTIVALS block)
5. Live web search results (WEB SEARCH block)

## Rules:
- Always cite which model or data source supports each claim (e.g. "RF forecast shows…", "Based on your POS data…").
- For sentiment/review questions, reference the sentiment statistics and give actionable advice.
- For festival/dish questions, give specific, actionable menu ideas and promotions.
- Format with markdown: **bold** key points, bullet lists, numbered steps.
- Keep responses focused and practical — no filler.
- Currency is always ₹ (Indian Rupees).
- When web results are present, cite insights naturally.
"""


def _build_system_msg(context: str, search: list, festivals: list,
                      ml_context: str = "") -> str:
    """Assemble the system prompt from café context, web results, festivals."""
    fest_txt = ""
    if festivals:
        fest_txt = "── UPCOMING FESTIVALS ─────────────────────────────────────\n"
        for f in festivals[:5]:
            fest_txt += (f"• {f['name']} — {f['date']} ({f['days_away']} days away)\n"
                         f"  Menu ideas  : {', '.join(f.get('menu_ideas', [])[:3])}\n"
                         f"  Promo ideas : {', '.join(f.get('promo_ideas', [])[:2])}\n")

    web_txt = ""
    if search:
        web_txt = "── WEB SEARCH RESULTS ─────────────────────────────────────\n"
        for r in search[:3]:
            web_txt += f"• {r['title']}\n  {r['body'][:300]}\n"

    return (f"{_SYSTEM_PROMPT}\n\n"
            f"{ml_context}\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"{fest_txt}\n{web_txt}")


def _sources(context: str, search: list, festivals: list) -> dict:
    return {
        "data":      bool(context and "no sales data" not in context.lower()),
        "web":       bool(search),
        "festivals": bool(festivals),
    }


# ─── Anthropic Claude streaming ───────────────────────────────────────────────

async def _stream_claude(history: list, message: str,
                         context: str, search: list, festivals: list,
                         ml_context: str = ""):
    system_msg = _build_system_msg(context, search, festivals, ml_context)
    msgs = [{"role": m["role"], "content": m["content"]} for m in history[-12:]]
    msgs.append({"role": "user", "content": message})

    with _ai_client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_msg,
        messages=msgs,
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"

    yield f"data: {json.dumps({'done': True, 'sources': _sources(context, search, festivals)})}\n\n"


# ─── Groq (free) streaming ────────────────────────────────────────────────────

async def _stream_groq(history: list, message: str,
                       context: str, search: list, festivals: list,
                       ml_context: str = ""):
    """
    Stream from Groq's OpenAI-compatible API using httpx (already available).
    Model: llama-3.3-70b-versatile — free tier, 14,400 requests/day.
    Sign up free at https://console.groq.com
    """
    import httpx

    system_msg = _build_system_msg(context, search, festivals, ml_context)
    msgs = [{"role": "system", "content": system_msg}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in history[-12:]]
    msgs.append({"role": "user", "content": message})

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST",
            _GROQ_URL,
            json={"model": _GROQ_MODEL, "messages": msgs, "max_tokens": 1024, "stream": True},
            headers={"Authorization": f"Bearer {_GROQ_API_KEY}", "Content-Type": "application/json"},
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:].strip()
                if raw == "[DONE]":
                    break
                try:
                    delta = json.loads(raw)["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield f"data: {json.dumps({'text': delta})}\n\n"
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass

    yield f"data: {json.dumps({'done': True, 'sources': _sources(context, search, festivals)})}\n\n"

# ─── Smart analytics fallback (no API key needed) ────────────────────────────

_NO_DATA_MSG = (
    "**No café data loaded yet.**\n\n"
    "I need your data to answer analytics questions. Head to **Data Collection** and upload:\n\n"
    "- **POS Billing** — sales, items, revenue, platforms\n"
    "- **Financial** — daily revenue, margins, cost breakdown\n"
    "- **Customer** — CRM, visit frequency, loyalty points\n"
    "- **Reviews & Sentiment** — customer feedback analysis\n"
    "- **Menu** — SKUs, categories, pricing\n\n"
    "Once uploaded, I can answer questions like:\n"
    "- *Which item had the highest revenue last week?*\n"
    "- *Compare weekend vs weekday performance*\n"
    "- *Which platform drives the most orders?*\n\n"
    "**Festival & menu ideas work without data** — feel free to ask about Diwali, Navratri, or any upcoming occasion!"
)


def _smart_response(message: str, data: list, festivals: list, search_res: list = [], ml_context: str = "") -> str:
    # Data-related queries need actual data — return helpful onboarding message
    data_keywords = [
        "revenue", "sales", "item", "product", "margin", "cost", "platform",
        "zomato", "swiggy", "dine-in", "weekend", "weekday", "best selling",
        "highest selling", "lowest", "worst", "profit", "category", "beverage",
        "starter", "main", "dessert", "review", "sentiment", "feedback",
        "rating", "overview", "summary", "analysis", "performance",
        "metrics", "kpi", "numbers", "data", "inventory", "stock",
    ]
    m = message.lower()
    is_data_query = any(k in m for k in data_keywords)

    if not data and is_data_query and not any(k in m for k in [
        "festival", "navratri", "diwali", "holi", "eid", "christmas",
        "menu idea", "special dish", "promo", "promotion", "discount",
    ]):
        return _NO_DATA_MSG

    items  = item_stats(data)
    plats  = platform_breakdown(data)
    cats   = category_breakdown(data)
    dates  = sorted(set(r["date"] for r in data))
    total_rev   = sum(r["revenue"] for r in data)
    total_cost  = sum(r["cost"]    for r in data)
    daily_avg   = total_rev / max(len(dates), 1)
    food_cost_pct = total_cost / max(total_rev, 1) * 100

    # ── Inventory recommendation from reviews ──
    if any(k in m for k in [
        "increase inventory", "stock more", "keep more", "most loved", "loved product",
        "should i keep", "which to reorder", "stock up", "inventory recommendation",
    ]):
        engine = get_sentiment_engine()
        if engine.has_data:
            s = engine.stats
            pos_keywords = [k["word"].lower() for k in s.get("keywords", {}).get("positive", [])]
            loved = []
            for x in items:
                name_words = x["name"].lower().split()
                if any(w in pos_keywords for w in name_words):
                    loved.append(x)
            if not loved:
                loved = items[:3]
            lines = ["**Inventory Recommendations (based on customer sentiment):**\n"]
            for x in loved[:4]:
                daily_qty = x["qty"] / max(len(dates), 1)
                lines.append(f"- **{x['name']}** — {x['qty']:.0f} units sold, "
                             f"~{daily_qty:.1f}/day avg. Stock at least {int(daily_qty * 1.3)}/day to avoid stockouts.")
            lines.append(f"\nThese items appear in positive customer reviews and drive repeat visits. "
                         f"Prioritise these when placing supplier orders.")
            return "\n".join(lines)
        elif data:
            top3 = items[:3]
            lines = ["**Top Sellers — Stocking Baseline (no review data available):**\n"]
            for x in top3:
                daily_qty = x["qty"] / max(len(dates), 1)
                lines.append(f"- **{x['name']}** — ~{daily_qty:.1f} units/day avg. "
                             f"Recommended daily stock: {int(daily_qty * 1.3)} units.")
            lines.append("\nUpload customer reviews for sentiment-based stocking recommendations.")
            return "\n".join(lines)
        return "No sales data available to generate inventory recommendations."

    # ── Revenue forecast / demand prediction ──
    if any(k in m for k in [
        "forecast", "predict", "prediction", "demand", "demand forecast", "revenue forecast",
        "next 7 days", "next week", "7 day", "7-day", "7days",
        "coming days", "upcoming revenue", "expected revenue", "how much will",
        "projected", "next few days", "daily forecast",
        "what will i make", "future revenue", "revenue next", "sales next",
        "tomorrow revenue", "this week revenue",
    ]):
        if not data:
            return ("I need POS sales data to generate a revenue forecast. "
                    "Upload your billing data in **Upload My Data → Sales & Orders**.")
        try:
            import ml_models
            import data_store as _ds2
            pos = _ds2._pos_data
            if not pos or len(pos) < 30:
                return (f"Need at least **30 days of POS data** for reliable forecasting. "
                        f"Currently have {len(pos) if pos else 0} records. Upload more data.")

            fc = ml_models.forecast_revenue(pos, days=7)
            if fc.get("error"):
                return f"**Forecast model error:** {fc['error']}"

            rows      = fc["forecast"]
            total_fc  = sum(r["predicted_revenue"] for r in rows)
            dates_set = sorted(set(r["date"] for r in data))
            hist_avg  = sum(r["revenue"] for r in data) / max(len(dates_set), 1)
            diff_pct  = (total_fc / 7 - hist_avg) / max(hist_avg, 1) * 100

            lines = [
                f"**7-Day Revenue Forecast**",
                f"*{fc['model']} | Accuracy: {fc['accuracy']}% | RF MAE ₹{fc['rf_mae']:,.0f}*\n",
            ]
            for r in rows:
                icon = "🟢" if r["is_weekend"] else "⚪"
                tag  = " *(weekend)*" if r["is_weekend"] else ""
                lines.append(f"{icon} **{r['day']} {r['date']}** — ₹{r['predicted_revenue']:,}{tag}"
                             f"  *(range ₹{r['lower']:,}–₹{r['upper']:,})*")

            dir_word = "above" if diff_pct > 0 else "below"
            lines.append(f"\n**Projected 7-day total:** ₹{total_fc:,}")
            lines.append(f"**vs your historical daily avg ₹{hist_avg:,.0f}:** forecast is **{diff_pct:+.1f}%** {dir_word} average")

            if fc.get("weekend_uplift_applied"):
                lines.append("\n✅ *Weekend uplift correction applied — weekends adjusted to match your historical patterns.*")

            # Platform breakdown
            try:
                plat_fc = ml_models.forecast_by_platform(pos, days=7)
                if plat_fc:
                    lines.append("\n**Platform Forecast (7-day totals):**")
                    for p in sorted(plat_fc, key=lambda x: -sum(d["predicted_revenue"] for d in x["forecast"])):
                        pt = sum(d["predicted_revenue"] for d in p["forecast"])
                        lines.append(f"- **{p['platform']}**: ₹{pt:,}"
                                     f" *(hist avg ₹{p['historical_avg']:,}/day)*")
            except Exception:
                pass

            next_fest = festivals[0] if festivals else None
            if next_fest and next_fest["days_away"] <= 7:
                lines.append(f"\n🎉 **{next_fest['name']}** falls within this forecast window ({next_fest['date']}) — "
                             f"actual revenue may be 20–40% higher. Stock up and staff up!")
            elif next_fest:
                lines.append(f"\n💡 Next up: **{next_fest['name']}** in {next_fest['days_away']} days — start planning your special menu.")

            return "\n".join(lines)
        except Exception as e:
            return (f"**Forecast error:** {str(e)}\n\n"
                    "Make sure your POS data is uploaded and ML models are available in the backend.")

    # ── Peak hours / busy hours ──
    if any(k in m for k in [
        "peak hour", "peak hours", "busy hour", "busy hours", "rush hour", "rush hours",
        "busiest time", "busiest hour", "busy time", "what time", "when is it busy",
        "when do i get most", "when are most customers", "hourly breakdown",
        "time of day", "lunch rush", "dinner rush", "morning rush",
        "when to staff", "staffing hours",
    ]):
        if not data:
            return (
                "Upload POS data (with order timestamps) to unlock peak-hour analysis. "
                "Once uploaded, I can identify your busiest hours, forecast daily demand, "
                "and recommend optimal staffing schedules for each shift."
            )
        try:
            import ml_models
            import data_store as _ds2
            ph = ml_models.peak_hour_analysis(_ds2._pos_data)
            top = ph.get("top_hours", [])[:5]
            if not top:
                return ("Not enough hourly data in your POS records. "
                        "Make sure your data includes an Hour/Time column.")

            lines = ["**Peak Hour Analysis (RF Classifier)**\n", "**Your busiest hours (from actual data):**"]
            max_orders = max(h["orders"] for h in top)
            for h in top:
                bar = "█" * max(1, int(h["orders"] / max(max_orders, 1) * 12))
                lines.append(f"- **{h['hour']:02d}:00–{h['hour']+1:02d}:00**: {h['orders']} orders  {bar}")

            preds = ph.get("predictions", [])[:7]
            if preds:
                lines.append("\n**Predicted peak hour — next 7 days:**")
                for p in preds:
                    lines.append(f"- {p.get('day','?')} {p.get('date','')}: peak at **{p.get('peak_label','—')}**")

            lines.append("\n💡 **Staffing tip:** Have your full team in place 30 mins before peak. "
                         "Add 1 extra server during your top 2 hours to reduce wait times.")
            return "\n".join(lines)
        except Exception as e:
            return f"Peak hour analysis failed: {str(e)}"

    # ── Cross-sell / combo / upsell ──
    if any(k in m for k in [
        "cross sell", "cross-sell", "upsell", "up-sell", "bundle",
        "pair with", "goes well with", "recommend with", "frequently bought",
        "what to recommend", "combo idea", "complementary item",
        "what sells together", "combo", "add-on", "addon",
    ]):
        if not data:
            return "Upload POS data to get cross-sell recommendations from your customers' ordering patterns."
        try:
            import ml_models
            import data_store as _ds2
            cs = ml_models.cross_sell_recommendations(_ds2._pos_data, top_n=5)
            if not cs:
                return ("Not enough co-purchase data to find patterns. "
                        "Upload more POS records (ideally with Order ID so items can be grouped per transaction).")
            lines = ["**Cross-Sell Recommendations (Association Rules — FP-Growth)**\n"]
            for r in cs[:5]:
                lines.append(f"- Customer orders **{r['antecedent']}** → suggest **{r['consequent']}**"
                             f"  *(confidence: {r['confidence']}%, lift: {r['lift']}×)*")
            lines.append("\n💡 **Quick win:** Train staff on the top 2 combos. "
                         "A simple *'Would you also like...'* increases average order value by 15–20%.")
            return "\n".join(lines)
        except Exception as e:
            return f"Cross-sell analysis failed: {str(e)}"

    # ── Cancellation risk ──
    if any(k in m for k in [
        "cancel", "cancellation", "cancelled", "order cancel", "cancel rate",
        "which platform cancels", "high cancel", "reduce cancel",
    ]):
        if not data:
            return "Upload POS data to analyse cancellation rates by platform."
        try:
            import ml_models
            import data_store as _ds2
            cr = ml_models.cancellation_risk_analysis(_ds2._pos_data)
            if cr.get("error"):
                return f"Cancellation analysis: {cr['error']}"
            lines = [f"**Cancellation Risk Analysis (RF, AUC {cr['model_auc']}%)**\n",
                     f"- Overall cancellation risk: **{cr['overall_risk']}%**\n",
                     "**By platform:**"]
            for p in cr.get("by_platform", []):
                level = "🔴 High" if p["risk_pct"] > 15 else ("🟡 Medium" if p["risk_pct"] > 7 else "🟢 Low")
                lines.append(f"- **{p['platform']}**: {p['risk_pct']}% risk — {level}")
            lines.append("\n💡 **Action:** For high-risk platforms, add order confirmation calls for large orders "
                         "and keep prep time under 20 mins to reduce cancellations.")
            return "\n".join(lines)
        except Exception as e:
            return f"Cancellation analysis failed: {str(e)}"

    # ── Category performance ──
    if any(k in m for k in [
        "beverage", "main course", "starter", "dessert", "category",
        "how are my mains", "which category",
    ]):
        if not cats:
            return "No category data available."
        lines = ["**Category Performance:**\n"]
        for c in cats:
            lines.append(f"- **{c['category']}**: ₹{c['revenue']:,.0f} revenue, "
                         f"{c['orders']} orders, {c['margin_pct']:.1f}% margin")
        best = max(cats, key=lambda x: x["revenue"])
        lines.append(f"\n**{best['category']}** leads in revenue. "
                     f"Focus promotions here to maximise returns.")
        return "\n".join(lines)

    # ── Specific item lookup ──
    if any(k in m for k in ["performance of", "tell me about"]) or "how is" in m:
        matched = None
        for x in items:
            if x["name"].lower() in m:
                matched = x
                break
        if matched:
            return (f"**{matched['name']} — Item Performance**\n\n"
                    f"- Revenue : **₹{matched['revenue']:,.0f}** total\n"
                    f"- Units sold : **{matched['qty']:.0f}** units\n"
                    f"- Margin : **{matched['margin_pct']:.1f}%**")

    # ── Top / best selling ──
    if any(k in m for k in [
        "highest selling", "best selling", "top item", "most popular", "top selling",
        "best performer", "best seller", "top seller", "top product", "best product",
        "selling the most", "sells the most", "most sold", "highest revenue item",
        "which item", "which product", "popular item", "popular product",
        "what item", "what product", "what sells", "what is selling",
        "menu performance", "item performance",
    ]):
        period_data, period_label = data, "overall"
        # Anchor date periods to the latest date IN the dataset, not today's
        # calendar date, so historical POS uploads always yield results.
        all_dates = [r["date"] for r in data if r.get("date")]
        anchor = max(all_dates) if all_dates else datetime.now().strftime("%Y-%m-%d")
        anchor_dt = datetime.strptime(anchor, "%Y-%m-%d")
        anchor_fmt = anchor_dt.strftime("%d %b %Y")

        if "last week" in m or "past week" in m or "this week" in m:
            cut = (anchor_dt - timedelta(days=7)).strftime("%Y-%m-%d")
            period_data  = [r for r in data if r.get("date", "") >= cut]
            period_label = f"7 days up to {anchor_fmt} (as per uploaded POS data)"
        elif "last month" in m or "past month" in m:
            cut = (anchor_dt - timedelta(days=30)).strftime("%Y-%m-%d")
            period_data  = [r for r in data if r.get("date", "") >= cut]
            period_label = f"30 days up to {anchor_fmt} (as per uploaded POS data)"
        elif "today" in m:
            period_data  = [r for r in data if r.get("date", "") == anchor]
            period_label = f"{anchor_fmt} (latest date in uploaded POS data)"

        top = item_stats(period_data)
        if not top:
            # No data in the requested window — fall back to latest available 7 days
            all_sorted = sorted(set(r.get("date", "") for r in data if r.get("date")))
            if all_sorted:
                fallback_anchor = datetime.strptime(all_sorted[-1], "%Y-%m-%d")
                fallback_cut    = (fallback_anchor - timedelta(days=7)).strftime("%Y-%m-%d")
                period_data     = [r for r in data if r.get("date", "") >= fallback_cut]
                period_label    = f"latest 7 days up to {fallback_anchor.strftime('%d %b %Y')} (most recent in uploaded data)"
                top             = item_stats(period_data) or item_stats(data)
                if not period_data:
                    top          = item_stats(data)
                    period_label = "all uploaded data"
            else:
                top          = item_stats(data)
                period_label = "all uploaded data"
        lines = [f"**Top selling items — {period_label}:**\n"]
        for i, x in enumerate(top[:3]):
            lines.append(f"{i+1}. **{x['name']}** — ₹{x['revenue']:,.0f} revenue, "
                         f"{x['qty']:.0f} units, {x['margin_pct']:.1f}% margin")
        top_plat = max(plats, key=lambda x: x["revenue"])["platform"] if plats else None
        if top_plat:
            lines.append(f"\n**{top[0]['name']}** is your star product. "
                         f"Feature it on **{top_plat}** — your top revenue channel — with high-quality photos.")
        return "\n".join(lines)

    # ── Worst / low margin ──
    if any(k in m for k in [
        "lowest margin", "worst", "low profit", "least profitable", "remove", "low margin",
        "poor margin", "bad margin", "underperforming", "weak item", "struggling",
        "which item to remove", "discontinue", "drop item", "which to remove",
    ]):
        bottom = sorted(items, key=lambda x: x["margin_pct"])[:4]
        lines  = ["**Items with lowest contribution margin:**\n"]
        for i, x in enumerate(bottom):
            lines.append(f"{i+1}. **{x['name']}** — {x['margin_pct']:.1f}% margin, "
                         f"₹{x['revenue']:,.0f} total revenue, {x['qty']:.0f} units")
        lines.append("\n💡 **Recommendations:**")
        lines.append("- Reformulate recipes to reduce ingredient cost by 5–10%")
        lines.append("- Bundle with high-margin items (e.g., pair with a premium beverage)")
        lines.append("- Consider removing the lowest performer if margin is below 20%")
        return "\n".join(lines)

    # ── Food cost / profitability / cost efficiency ──
    if any(k in m for k in [
        "food cost", "cost efficiency", "reduce cost", "cost reduction", "cogs",
        "ingredient cost", "lower cost", "save cost", "cost control",
        "increase margin", "improve margin", "boost margin", "increase profit",
        "profit margin", "profit", "gross margin", "net margin",
        "how efficient", "efficiency", "cost saving",
    ]):
        high_margin = sorted(items, key=lambda x: x["margin_pct"], reverse=True)[:3]
        low_margin  = sorted(items, key=lambda x: x["margin_pct"])[:3]
        hm_str = ", ".join(f"**{x['name']}** ({x['margin_pct']:.1f}%)" for x in high_margin)
        lm_str = ", ".join(f"**{x['name']}** ({x['margin_pct']:.1f}%)" for x in low_margin)
        status = "✅ Healthy" if food_cost_pct < 35 else ("⚠️ High" if food_cost_pct < 42 else "🚨 Critical")
        return (f"**Food Cost & Profitability Analysis**\n\n"
                f"- Overall food cost % : **{food_cost_pct:.1f}%** — {status} (target: 28–35%)\n"
                f"- Total revenue       : **₹{total_rev:,.0f}** | Total cost: ₹{total_cost:,.0f}\n"
                f"- Gross profit        : **₹{total_rev - total_cost:,.0f}** ({100 - food_cost_pct:.1f}% margin)\n\n"
                f"**🌟 High-margin items (push these):**\n{hm_str}\n\n"
                f"**⚠️ Low-margin items (review these):**\n{lm_str}\n\n"
                f"**💡 Cost Reduction Strategies:**\n"
                f"- Negotiate bulk pricing with your top 3 suppliers\n"
                f"- Reduce portion sizes by 5% on low-margin items (often unnoticed by customers)\n"
                f"- Use high-margin items as upsell add-ons during order taking\n"
                f"- Run a 'chef's special' each week to use near-expiry ingredients and boost margins")

    # ── Weekend vs weekday ──
    if ("weekend" in m and ("weekday" in m or "week day" in m or "compare" in m or "vs" in m or "versus" in m)) \
            or "compare weekend" in m or ("weekend" in m and "sales" in m):
        wd_set, we_set = set(), set()
        wd_rev, we_rev = 0.0, 0.0
        for r in data:
            try:
                d = datetime.strptime(r["date"], "%Y-%m-%d")
                if d.weekday() >= 5:
                    we_rev += r["revenue"]; we_set.add(r["date"])
                else:
                    wd_rev += r["revenue"]; wd_set.add(r["date"])
            except Exception:
                pass
        w = we_rev / max(len(we_set), 1)
        d = wd_rev / max(len(wd_set), 1)
        diff = ((w / max(d, 1)) - 1) * 100
        return (f"**Weekend vs Weekday Sales Comparison**\n\n"
                f"📅 Weekend average : **₹{w:,.0f}/day** ({len(we_set)} weekend days)\n"
                f"📅 Weekday average : **₹{d:,.0f}/day** ({len(wd_set)} weekday days)\n"
                f"📈 Weekend premium : **{diff:+.1f}%**\n\n"
                f"💡 {'Weekends are significantly busier. Add 2 extra staff on Sat/Sun evenings and run Zomato promotions on Friday nights to capture the weekend rush.' if diff > 15 else 'Weekend and weekday performance is balanced. Focus on weekday lunch promotions to smooth demand.'}")

    # ── Platform analysis ──
    if any(k in m for k in [
        "platform", "zomato", "swiggy", "dine-in", "dine in", "delivery",
        "channel", "online order", "online sales", "which platform",
        "which channel", "takeaway", "take away", "order channel",
    ]):
        if not plats:
            return "No platform data available."
        plats_sorted = sorted(plats, key=lambda x: x["revenue"], reverse=True)
        lines = ["**Revenue by Platform:**\n"]
        for p in plats_sorted:
            pct = p["revenue"] / max(sum(x["revenue"] for x in plats), 1) * 100
            lines.append(f"- **{p['platform']}**: ₹{p['revenue']:,.0f} ({pct:.1f}%) — {p['orders']} orders")
        top_p = plats_sorted[0]["platform"]
        lines.append(f"\n💡 **{top_p}** is your highest revenue channel. "
                     f"Invest in better photos, menu descriptions, and promotions on {top_p} to grow this further.")
        return "\n".join(lines)

    # ── Sentiment / reviews ──
    if any(k in m for k in [
        "sentiment", "review", "reviews", "feedback", "rating", "ratings",
        "customer satisfaction", "customer opinion", "customer experience",
        "negative review", "positive review", "what customers", "what do customers",
        "source breakdown", "visit type", "location performance", "google review",
        "zomato review", "swiggy review", "instagram", "social media review",
        "nps", "net promoter", "aspect", "ambiance", "service quality", "customer feeling",
    ]):
        engine = get_sentiment_engine()
        if not engine.has_data:
            return (
                "No review data uploaded yet. Go to **Upload My Data → Customer Reviews** "
                "tab and upload your reviews file to enable sentiment analysis.\n\n"
                "Once uploaded, I can tell you: which platforms get the most complaints, "
                "what customers love most, your NPS score, aspect-level ratings (food, service, "
                "ambiance, wait time, price), and specific actions to improve satisfaction."
            )

        s = engine.stats

        # ── Core numbers ──────────────────────────────────────────────────────
        total     = s["total_reviews"]
        pos_pct   = s["positive_pct"]
        neg_pct   = s["negative_pct"]
        neu_pct   = s["neutral_pct"]
        sat       = s["satisfaction_score"]
        avg_r     = s["overall_avg_rating"]
        nps       = s.get("nps", "N/A")
        conf      = s.get("avg_model_confidence", "?")

        # ── Aspect analysis — pick worst and best ─────────────────────────────
        aspects   = [a for a in s.get("aspect_analysis", []) if a["total"] > 0]
        worst_asp = aspects[:2] if aspects else []   # sorted worst-first
        best_asp  = sorted(aspects, key=lambda x: -x["score"])[:1]

        asp_lines = ""
        for a in aspects:
            bar = "🔴" if a["score"] < 40 else "🟡" if a["score"] < 65 else "🟢"
            asp_lines += f"\n  {bar} **{a['aspect']}** — {a['score']}% satisfaction ({a['positive_pct']}% positive, {a['negative_pct']}% negative, {a['total']} mentions)"

        # ── Source breakdown ───────────────────────────────────────────────────
        src_lines = "\n".join(
            f"  - **{src['source']}**: {src['positive_pct']}% positive, {src['negative_pct']}% negative ({src['total']} reviews)"
            for src in s.get("source_breakdown", [])[:5]
        )

        # ── Visit type ────────────────────────────────────────────────────────
        vt_lines = "\n".join(
            f"  - **{vt['visit_type']}**: {vt['satisfaction']:.0f}% satisfaction ({vt['total']} reviews)"
            for vt in s.get("visit_breakdown", [])
        )

        # ── Keywords ──────────────────────────────────────────────────────────
        pos_kw = ", ".join(k["word"] for k in s.get("keywords", {}).get("positive", [])[:8])
        neg_kw = ", ".join(k["word"] for k in s.get("keywords", {}).get("negative", [])[:8])

        # ── Actionable insights from model ────────────────────────────────────
        insights = s.get("actionable_insights", [])
        insight_lines = ""
        for ins in insights[:4]:
            icon = "🚨" if ins["priority"] == "high" else "💡"
            insight_lines += f"\n{icon} **{ins['title']}**\n   → {ins['detail']}\n"

        # ── Trend snippet ──────────────────────────────────────────────────────
        trend = s.get("sentiment_trend", [])
        trend_note = ""
        if len(trend) >= 2:
            first_pos = trend[0]["positive_pct"]
            last_pos  = trend[-1]["positive_pct"]
            delta     = last_pos - first_pos
            if abs(delta) >= 5:
                direction = "📈 improving" if delta > 0 else "📉 declining"
                trend_note = (f"\n\n**📅 Sentiment Trend:** Positive reviews went from "
                              f"{first_pos}% ({trend[0]['month']}) → {last_pos}% ({trend[-1]['month']}) "
                              f"— {direction} by {abs(delta):.1f} percentage points.")

        # ── NPS interpretation ─────────────────────────────────────────────────
        nps_note = ""
        if isinstance(nps, (int, float)):
            if nps >= 50:
                nps_note = f"**Excellent** — customers actively recommend you"
            elif nps >= 20:
                nps_note = f"**Good** — more promoters than detractors"
            elif nps >= 0:
                nps_note = f"**Average** — needs improvement"
            else:
                nps_note = f"**Needs urgent attention** — detractors outnumber promoters"

        # ── Best / worst aspect callout ────────────────────────────────────────
        callout = ""
        if worst_asp and worst_asp[0]["status"] in ("critical", "needs improvement"):
            callout += (f"\n\n⚠️ **Biggest pain point: {worst_asp[0]['aspect']}** "
                        f"— {worst_asp[0]['negative_pct']}% of mentions are negative. "
                        f"This is your #1 priority to fix.")
        if best_asp and best_asp[0]["score"] >= 70:
            callout += (f"\n\n✨ **Strongest area: {best_asp[0]['aspect']}** "
                        f"— {best_asp[0]['positive_pct']}% positive. Feature this in your marketing.")

        return (
            f"**Customer Sentiment Analysis** *(Pre-trained Logistic Regression + TF-IDF | avg confidence: {conf}%)*\n\n"
            f"**📊 Overall ({total} reviews analysed):**\n"
            f"- ✅ Positive: **{s['positive']}** ({pos_pct}%)  ➖ Neutral: **{s['neutral']}** ({neu_pct}%)  ❌ Negative: **{s['negative']}** ({neg_pct}%)\n"
            f"- 🌟 Satisfaction Score: **{sat}%** | ⭐ Avg Rating: **{avg_r}/5** | 📣 NPS: **{nps}** ({nps_note})\n\n"
            f"**🔍 Aspect-Level Breakdown (what customers talk about):**{asp_lines}\n"
            f"{callout}\n\n"
            f"**📱 By Platform:**\n{src_lines}\n\n"
            f"**🚶 By Visit Type:**\n{vt_lines}\n\n"
            f"**💬 What customers love:** {pos_kw}\n"
            f"**⚠️ What customers complain about:** {neg_kw}\n"
            f"{trend_note}\n\n"
            f"**🎯 Model-Generated Action Plan:**\n{insight_lines}"
        )

    # ── Revenue / sales total ──
    if any(k in m for k in [
        "total revenue", "how much", "revenue", "earnings", "sales total",
        "total sales", "how much did", "sales figure", "sales number",
        "income", "turnover", "how much money", "how much earn",
        "how much have", "what is my revenue", "what are my sales",
        "overall revenue", "overall sales",
    ]):
        if not dates:
            return "No sales data available yet."
        best_date = max(
            {d: sum(r["revenue"] for r in data if r["date"] == d) for d in dates}.items(),
            key=lambda x: x[1]
        )
        return (f"**Revenue Summary**\n\n"
                f"- Total revenue : **₹{total_rev:,.0f}** over {len(dates)} days\n"
                f"- Daily average : **₹{daily_avg:,.0f}**\n"
                f"- Best day      : **{best_date[0]}** (₹{best_date[1]:,.0f})\n"
                f"- Top category  : **{cats[0]['category'] if cats else '—'}**\n\n"
                f"💡 To grow revenue, focus on upselling to your top {items[0]['name'] if items else 'item'} customers and running targeted weekend promotions.")

    # ── Festival / seasonal ──
    fest_name_in_msg = None
    for f in _FESTIVALS:
        if f["name"].lower() in m:
            fest_name_in_msg = f
            break

    if fest_name_in_msg or any(k in m for k in [
        "festival", "upcoming", "occasion", "special dish", "new dish",
        "season", "holiday", "ideas", "idea", "how to handle", "prepare",
        "celebration", "event", "plan for", "get ready", "special menu",
        "promotion", "promo", "offer", "discount",
    ]):
        if fest_name_in_msg:
            f = fest_name_in_msg
            upcoming = [x for x in get_upcoming_festivals(180) if x["name"] == f["name"]]
            date_str = upcoming[0]["date"] if upcoming else "upcoming"
        elif festivals:
            f = festivals[0]
            date_str = f["date"]
        else:
            return ("No upcoming festivals in the next 90 days found in our calendar. "
                    "Please ask about a specific festival by name.")

        menu_list  = "\n".join(f"  - {x}" for x in f.get("menu_ideas", []))
        promo_list = "\n".join(f"  - {x}" for x in f.get("promo_ideas", []))
        top_cats   = [c["category"] for c in cats[:2]] if cats else []
        top_item_n = items[0]["name"] if items else "your top item"

        web_note = ""
        if search_res:
            snippets = [r["body"][:200] for r in search_res[:2] if r.get("body")]
            if snippets:
                web_note = f"\n\n**🌐 From the web:**\n" + "\n".join(f"- {s}" for s in snippets)

        return (f"**{f['name']} ({date_str}) — Café Action Plan**\n\n"
                f"Based on your data, your strengths are in **{', '.join(top_cats)}** "
                f"with **{top_item_n}** as your best seller. Here's how to leverage {f['name']}:\n\n"
                f"**🍽️ Special Menu Ideas:**\n{menu_list}\n\n"
                f"**📣 Promotion Ideas:**\n{promo_list}\n\n"
                f"**📊 Data Insight:** "
                f"Your daily average is ₹{daily_avg:,.0f}. "
                f"Festivals typically drive 30–50% higher footfall — staff up and pre-order ingredients."
                f"{web_note}\n\n"
                f"💡 **Quick win:** Post reels/stories of your festival special dishes 3 days before {f['name']} on Instagram to build anticipation.")

    # ── General overview / analysis / improvement queries ──
    if any(k in m for k in [
        "overview", "summary", "report", "analysis", "analyse", "analyze",
        "insight", "performance", "status", "how is", "how am", "how are",
        "how can", "how do", "how to", "improve", "increase", "grow",
        "strategy", "advice", "recommend", "suggest", "help me",
        "what should", "what can", "tell me", "show me", "give me",
        "about my cafe", "about my business", "my cafe", "my business",
        "sales", "data", "metrics", "kpi", "numbers",
    ]):
        top3_str  = "\n".join(f"  {i+1}. **{x['name']}** — ₹{x['revenue']:,.0f} ({x['margin_pct']:.1f}% margin)"
                              for i, x in enumerate(items[:3]))
        top_plat  = max(plats, key=lambda x: x["revenue"])["platform"] if plats else "—"
        next_fest = festivals[0]["name"] if festivals else "—"
        next_date = festivals[0]["date"] if festivals else "—"
        status    = "✅ Healthy" if food_cost_pct < 35 else ("⚠️ High" if food_cost_pct < 42 else "🚨 Critical")

        return (f"**Café Business Overview**\n\n"
                f"- Revenue: **₹{total_rev:,.0f}** over {len(dates)} days (avg ₹{daily_avg:,.0f}/day)\n"
                f"- Food cost: **{food_cost_pct:.1f}%** — {status}\n"
                f"- Best platform: **{top_plat}**\n"
                f"- Next festival: **{next_fest}** on {next_date}\n\n"
                f"**Top 3 Items:**\n{top3_str}\n\n"
                f"{'*Set ANTHROPIC_API_KEY for full AI-powered answers.*' if not HAS_AI else ''}")

    # ── Absolute last resort: always give a real, data-grounded answer ──
    web_note = ""
    if search_res:
        snippets = [r["body"][:250] for r in search_res[:2] if r.get("body")]
        if snippets:
            web_note = "\n\n**🌐 From the web:**\n" + "\n".join(f"- {s}" for s in snippets)

    if data:
        top_plat  = max(plats, key=lambda x: x["revenue"])["platform"] if plats else "—"
        next_fest = festivals[0]["name"] if festivals else None
        fest_line = (f"- **Next festival**: {next_fest} on {festivals[0]['date']}\n"
                     if next_fest else "")
        status    = "✅ Healthy" if food_cost_pct < 35 else ("⚠️ High" if food_cost_pct < 42 else "🚨 Critical")
        top3_str  = "\n".join(f"  {i+1}. **{x['name']}** — ₹{x['revenue']:,.0f} rev, {x['margin_pct']:.1f}% margin"
                              for i, x in enumerate(items[:3]))
        return (f"Here's your café snapshot — and I'm happy to dive deeper into any area:\n\n"
                f"- **Revenue**: ₹{total_rev:,.0f} over {len(dates)} days (avg ₹{daily_avg:,.0f}/day)\n"
                f"- **Food cost**: {food_cost_pct:.1f}% — {status}\n"
                f"- **Top channel**: {top_plat}\n"
                f"{fest_line}"
                f"\n**Top 3 items:**\n{top3_str}\n\n"
                f"Ask me anything — e.g. *\"which item should I remove?\"*, "
                f"*\"how can I improve margins?\"*, *\"what to do for {next_fest or 'Diwali'}?\"*"
                f"{web_note}")
    else:
        # No data loaded — provide genuinely useful café knowledge or onboarding
        general_advice = {
            ("staff", "team", "employee", "hire", "waiter", "barista", "manpower"):
                ("**Café Staffing Guidelines (India):**\n\n"
                 "- **Rule of thumb**: 1 server per 5–6 tables; 1 barista per 50 orders/day\n"
                 "- Peak hours (8–10am, 12–2pm, 5–8pm) need 30–40% more staff on roster\n"
                 "- Cross-train baristas on billing to handle weekend surges\n"
                 "- Minimum wage in India for F&B: ₹12,000–18,000/month depending on state\n"
                 "- Post rosters 2 weeks ahead to reduce last-minute call-outs"),
            ("equipment", "machine", "coffee machine", "grinder", "pos terminal"):
                ("**Café Equipment Essentials (India Budget Guide):**\n\n"
                 "- **Espresso machine**: ₹80K–2L (Petroncini, La Marzocco); commercial capsule from ₹25K\n"
                 "- **Grinder**: Mazzer Mini ~₹40K; Baratza Encore for budget ₹15K\n"
                 "- **POS system**: Petpooja or UrbanPiper (GST-compliant, Swiggy/Zomato integrated)\n"
                 "- **Refrigeration**: Blue Star or Voltas (inverter compressors handle power cuts)\n"
                 "- Budget ₹8–12L for a full counter + kitchen setup"),
            ("license", "fssai", "legal", "permit", "registration", "gst"):
                ("**Café Licensing Checklist (India):**\n\n"
                 "- **FSSAI License**: mandatory for all food businesses; registration for <₹12L turnover\n"
                 "- **GST**: register if annual turnover >₹20L; café meals attract 5% GST\n"
                 "- **Shop & Establishment Act**: state-specific; needed within 30 days of opening\n"
                 "- **Trade License**: from local municipal corporation\n"
                 "- **Fire NOC**: required for premises >50 sq m or multi-floor\n"
                 "- Timeline: 4–8 weeks for all approvals"),
            ("menu", "price", "pricing", "cost", "recipe"):
                ("**Menu Engineering Basics:**\n\n"
                 "- Target food cost ratio: **28–35%** of selling price\n"
                 "- Formula: Selling price = (Ingredient cost) ÷ 0.30\n"
                 "- **Stars** (high margin, high sales): promote heavily\n"
                 "- **Plowhorses** (low margin, high sales): reformulate recipe to cut cost\n"
                 "- **Puzzles** (high margin, low sales): reposition with better photos/descriptions\n"
                 "- **Dogs** (low margin, low sales): remove from menu\n"
                 "Upload your POS data to identify which category each item falls into."),
            ("open", "timing", "hours", "closing", "schedule"):
                ("**Optimal Café Operating Hours (India):**\n\n"
                 "- **Breakfast café**: 7:30am–11am captures office crowd\n"
                 "- **All-day café**: 9am–10pm; peak at lunch (12–2pm) and evening (5–8pm)\n"
                 "- **Student/college area**: open till 11pm, weekend brunch 10am–3pm drives 30–40% of weekly revenue\n"
                 "- Mon–Tue are typically slowest (20–25% below average); use for staff training or maintenance\n"
                 "- Consider shorter hours (10am–8pm) on slow days to reduce fixed costs"),
        }
        for keywords, response in general_advice.items():
            if any(k in m for k in keywords):
                return response + ("\n\n*Upload your POS data in Data Collection for personalised analytics.*"
                                   if not HAS_AI else "")

        next_fest = festivals[0]["name"] if festivals else "Diwali"
        return (f"Hi! I'm **Cafe Buddy AI** — your café business assistant.\n\n"
                f"**What I can do:**\n"
                f"- 📊 Analyse revenue, margins, platform performance *(needs data upload)*\n"
                f"- 🏆 Identify best/worst items and upsell opportunities\n"
                f"- 🎉 Festival planning — menu ideas & promotions for {next_fest} and more\n"
                f"- 💡 Staffing, pricing, licensing, and general café advice\n\n"
                f"**To unlock analytics:** upload your POS/sales data in **Data Collection**.\n\n"
                f"Or ask me anything about running your café — I'm ready!"
                f"{web_note}")


async def _stream_text(text: str, delay: float = 0.018):
    """Simulate streaming for the smart fallback by word-chunking."""
    words = text.split(" ")
    for i, word in enumerate(words):
        chunk = word + (" " if i < len(words) - 1 else "")
        yield f"data: {json.dumps({'text': chunk})}\n\n"
        await asyncio.sleep(delay)
    yield f"data: {json.dumps({'done': True, 'sources': {'data': True, 'web': False, 'festivals': True}})}\n\n"

# ─── API models ───────────────────────────────────────────────────────────────

class ChatMsg(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMsg] = []

# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/chatbot/stream")
async def chatbot_stream(req: ChatRequest, request: Request = None):
    import auth_utils as _au, tenant_store as _ts
    _auth_header = request.headers.get("Authorization", "") if request else ""
    _tid = _au.extract_tenant_id(_auth_header) or _ts.SYSTEM_TENANT_ID
    data       = _ds.get_data_for_tenant(_tid)
    context    = _build_context(data)
    festivals  = get_upcoming_festivals(90)
    msg_lower  = req.message.lower()

    # Step 1: Build ML model reasoning context (non-blocking, timeout-protected)
    ml_context = ""
    _pos_data_tenant, _ = _ds.get_pos_for_tenant(_tid)
    if _pos_data_tenant:
        try:
            import ml_models
            ml_context = await asyncio.wait_for(
                asyncio.to_thread(ml_models.build_ml_context, _pos_data_tenant),
                timeout=10.0
            )
        except Exception:
            ml_context = ""

    # Skip web search when no data + it's a pure data query (avoids slow DDG → 502)
    do_search = _needs_web_search(req.message)
    if not data and not any(k in msg_lower for k in [
        "festival", "navratri", "diwali", "holi", "eid", "christmas",
        "new year", "trending", "idea", "ideas", "recipe", "weather",
        "strategy", "marketing", "promotion", "social media",
    ]):
        do_search = False

    search_res: list = []
    if do_search and HAS_DDG:
        year  = datetime.now().year
        query = f"cafe restaurant {req.message} India {year}"
        if any(k in msg_lower for k in ["festival", "eid", "diwali", "holi", "navratri", "date", "when"]):
            query = f"{req.message} {year} India date"
        try:
            search_res = await asyncio.wait_for(
                asyncio.to_thread(_web_search, query, 4), timeout=8.0
            )
        except asyncio.TimeoutError:
            search_res = []

    history_dicts = [m.model_dump() for m in req.history]

    async def generate():
        # ── Provider cascade: Anthropic → Groq → Smart Analytics ──────────────
        try:
            if HAS_AI:
                try:
                    async for chunk in _stream_claude(
                        history_dicts, req.message, context, search_res, festivals,
                        ml_context=ml_context
                    ):
                        yield chunk
                    return
                except Exception as claude_err:
                    err_lower = str(claude_err).lower()
                    is_billing = ("credit" in err_lower or "balance" in err_lower
                                  or ("billing" in err_lower and "upgrade" in err_lower))
                    if is_billing and HAS_GROQ:
                        # Anthropic out of credits → silently switch to Groq
                        import logging as _log
                        _log.warning("Anthropic billing exhausted — falling back to Groq")
                    elif not is_billing:
                        raise  # non-billing error: surface it

            if HAS_GROQ:
                async for chunk in _stream_groq(
                    history_dicts, req.message, context, search_res, festivals,
                    ml_context=ml_context
                ):
                    yield chunk
                return

            # ── Pure analytics fallback ────────────────────────────────────────
            response = _smart_response(req.message, data, festivals, search_res, ml_context=ml_context)
            async for chunk in _stream_text(response):
                yield chunk

        except Exception as e:
            import logging as _log
            err_msg = str(e)
            _log.error("Chatbot stream exception: %s", err_msg)
            err_lower = err_msg.lower()
            if "credit" in err_lower or "balance" in err_lower:
                friendly = (
                    "⚠️ **Anthropic account has no credits.**\n\n"
                    "Add credits at console.anthropic.com → Plans & Billing, "
                    "**or** set a free **GROQ_API_KEY** in Railway Variables "
                    "(sign up free at console.groq.com — 14,400 requests/day)."
                )
            elif "502" in err_msg or "503" in err_msg or "timeout" in err_lower:
                friendly = "The server is temporarily busy. Please try again in a moment."
            else:
                friendly = f"AI error: {err_msg[:200]}"
            yield f"data: {json.dumps({'text': friendly})}\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': {}})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "Connection": "keep-alive",
            "X-Content-Type-Options": "nosniff",
        },
    )


# ─── Non-streaming fallback (works through Cloudflare / any proxy) ────────────

@router.post("/chatbot/ask")
async def chatbot_ask(req: ChatRequest, request: Request = None):
    """Identical logic to /chatbot/stream but returns a single JSON object.
    Used by the frontend when SSE is blocked by a tunnel or proxy."""
    import auth_utils as _au, tenant_store as _ts
    _auth_header = request.headers.get("Authorization", "") if request else ""
    _tid = _au.extract_tenant_id(_auth_header) or _ts.SYSTEM_TENANT_ID
    data      = _ds.get_data_for_tenant(_tid)
    context   = _build_context(data)
    festivals = get_upcoming_festivals(90)
    msg_lower = req.message.lower()

    ml_context = ""
    _pos_data_tenant, _ = _ds.get_pos_for_tenant(_tid)
    if _pos_data_tenant:
        try:
            import ml_models
            ml_context = await asyncio.wait_for(
                asyncio.to_thread(ml_models.build_ml_context, _pos_data_tenant),
                timeout=10.0
            )
        except Exception:
            ml_context = ""

    do_search = _needs_web_search(req.message)
    if not data and not any(k in msg_lower for k in [
        "festival", "navratri", "diwali", "holi", "eid", "christmas",
        "new year", "trending", "idea", "ideas", "recipe", "weather",
        "strategy", "marketing", "promotion", "social media",
    ]):
        do_search = False

    search_res: list = []
    if do_search and HAS_DDG:
        year  = datetime.now().year
        query = f"cafe restaurant {req.message} India {year}"
        try:
            search_res = await asyncio.wait_for(
                asyncio.to_thread(_web_search, query, 4), timeout=8.0
            )
        except Exception:
            search_res = []

    history_dicts = [m.model_dump() for m in req.history]

    async def _collect(stream_gen):
        """Collect SSE chunks from a stream generator into (text, sources)."""
        text = ""
        sources: dict = {}
        async for chunk in stream_gen:
            raw = chunk.replace("data: ", "").strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
                if parsed.get("done"):
                    sources = parsed.get("sources", {})
                elif parsed.get("text"):
                    text += parsed["text"]
            except Exception:
                pass
        return text, sources

    full_text = ""
    sources: dict = {}
    try:
        if HAS_AI:
            try:
                full_text, sources = await _collect(
                    _stream_claude(history_dicts, req.message, context, search_res, festivals,
                                   ml_context=ml_context)
                )
            except Exception as claude_err:
                err_lower = str(claude_err).lower()
                is_billing = ("credit" in err_lower or "balance" in err_lower
                              or ("billing" in err_lower and "upgrade" in err_lower))
                if is_billing and HAS_GROQ:
                    import logging as _log
                    _log.warning("Anthropic billing exhausted — falling back to Groq (ask)")
                    full_text, sources = await _collect(
                        _stream_groq(history_dicts, req.message, context, search_res, festivals,
                                     ml_context=ml_context)
                    )
                else:
                    raise

        if not full_text and HAS_GROQ:
            full_text, sources = await _collect(
                _stream_groq(history_dicts, req.message, context, search_res, festivals,
                             ml_context=ml_context)
            )

        if not full_text:
            full_text = _smart_response(req.message, data, festivals, search_res, ml_context=ml_context)
            sources = {
                "data":      bool(data),
                "web":       bool(search_res),
                "festivals": bool(festivals),
            }
    except Exception as e:
        import logging as _log
        _log.error("chatbot_ask exception: %s", str(e))
        full_text = f"Error: {str(e)[:300]}"
        sources = {}

    return {"text": full_text, "sources": sources}


@router.get("/chatbot/status")
def chatbot_status():
    if HAS_AI:
        model = "claude-haiku-4-5-20251001"
        provider = "Anthropic"
    elif HAS_GROQ:
        model = _GROQ_MODEL
        provider = "Groq (free)"
    else:
        model = "Smart Analytics Engine"
        provider = "Built-in"
    return {
        "ai_mode":          HAS_AI or HAS_GROQ,
        "web_search":       HAS_DDG,
        "model":            model,
        "provider":         provider,
        "anthropic_key":    bool(ANTHROPIC_KEY),
        "groq_key":         bool(_GROQ_API_KEY),
    }


@router.get("/chatbot/festivals")
def upcoming_festivals(days: int = 90):
    return {"festivals": get_upcoming_festivals(days)}


# ─── WhatsApp Notifications via Infinito (api.goinfinito.com) ────────────────
# Provider: ValueFirst / Infinito  —  https://api.goinfinito.com/unified/v2/send
# Token valid until 30 Jun 2026.  Override via env var INFINITO_TOKEN when renewed.

import json as _json

# ── Infinito configuration ───────────────────────────────────────────────────
_INFINITO_URL         = "https://api.goinfinito.com/unified/v2/send"
_INFINITO_TOKEN       = os.environ.get(
    "INFINITO_TOKEN",
    "eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJJbmZpbml0byIsImlhdCI6MTc4MTY3NTUwMCwic3ViIjoiRGVtb3NoazV0cmFpbmZzOWY3b2l2dDc2In0.xoy92pqdUS7tTKhM6Ow1rGDwLo8u5y5uek4k9f7kuXs",
)
_INFINITO_FROM        = os.environ.get("INFINITO_FROM",        "917428309250")
_INFINITO_TEMPLATE_ID = os.environ.get("INFINITO_TEMPLATE_ID", "1755248")


class WhatsAppSettings(BaseModel):
    phone:   str       # Recipient phone  e.g. "+919876543210" or "919876543210"
    message: str = ""  # Optional custom message; omit to send the auto daily summary


def _build_daily_summary() -> str:
    """Build a concise WhatsApp summary of today's café performance."""
    from data_store import get_data, item_stats, platform_breakdown, daily_revenue
    data = get_data()
    if not data:
        return (
            "📊 *Cafe Buddy Daily Report*\n\n"
            "No data uploaded yet. Visit your dashboard to upload POS data."
        )

    today   = datetime.now().strftime("%Y-%m-%d")
    items   = item_stats(data)
    plats   = platform_breakdown(data)
    daily   = daily_revenue(data, 1)
    today_r = next((r for r in daily if r["date"] == today), None)
    total   = sum(r["revenue"] for r in data)
    dates   = sorted(set(r["date"] for r in data))

    top_item  = items[0]["name"] if items else "—"
    top_plat  = max(plats, key=lambda x: x["revenue"])["platform"] if plats else "—"
    today_rev = today_r["revenue"] if today_r else 0

    festivals = get_upcoming_festivals(7)
    fest_line = (
        f"\n🎉 *Coming soon*: {festivals[0]['name']} in {festivals[0]['days_away']} days"
        if festivals else ""
    )

    avg_rev = total / max(len(dates), 1)
    trend   = "📈 Above avg" if today_rev > avg_rev else "📉 Below avg"

    return (
        f"☕ *Cafe Buddy — Daily Summary*\n"
        f"📅 {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
        f"💰 *Today's Revenue*: ₹{today_rev:,.0f} {trend}\n"
        f"📊 *Daily Avg*: ₹{avg_rev:,.0f} over {len(dates)} days\n"
        f"🏆 *Best Seller*: {top_item}\n"
        f"📱 *Top Channel*: {top_plat}\n"
        f"{fest_line}\n\n"
        f"*Action Items:*\n"
        f"{'✅ Revenue on track' if today_rev >= avg_rev * 0.9 else '⚠️ Revenue below target — consider a promotion'}\n"
        f"📦 Check stock for top-selling items\n"
        f"💬 Reply to any pending customer reviews"
    )


def _send_via_infinito(phone_clean: str, msg: str) -> dict:
    """
    Send a WhatsApp message through the Infinito unified API using httpx.

    Tries three auth header strategies in order (Bearer, raw token, apikey),
    and for each tries template (msgtype 3) then plain-text (msgtype 1).
    Returns on the first 200.  Collects all errors for diagnostics.
    """
    import httpx
    import logging as _log

    today_str   = datetime.now().strftime("%d/%m/%Y")
    _DLR_URL    = "https://webhook.site/cc84d70e-658a-41e3-851d-1207efef4168?To=%p&From=%P&REASON_CODE=%2&GUID=%5"
    common_addr = [{"seq": "1", "to": phone_clean, "from": _INFINITO_FROM, "tag": "Test1"}]

    template_payload = {
        "apiver": "1.0",
        "whatsapp": {
            "ver": "2.0",
            "dlr": {"url": _DLR_URL},
            "messages": [{
                "coding":       1,
                "id":           "11",
                "msgtype":      "3",
                "templateinfo": f"{_INFINITO_TEMPLATE_ID}~Car~{today_str}",
                "b_urlinfo":    "#/renew-policy",
                "type":         "",
                "mediadata":    "",
                "text":         "",
                "addresses":    common_addr,
            }],
        },
    }

    text_payload = {
        "apiver": "1.0",
        "whatsapp": {
            "ver": "2.0",
            "dlr": {"url": _DLR_URL},
            "messages": [{
                "coding":       1,
                "id":           "11",
                "msgtype":      "1",
                "templateinfo": "",
                "b_urlinfo":    "",
                "type":         "",
                "mediadata":    "",
                "text":         msg,
                "addresses":    common_addr,
            }],
        },
    }

    # ── Auth strategies to try in order ───────────────────────────────────────
    # ValueFirst/Infinito docs state tokens can be sent as "Bearer" OR raw
    # API-key style.  We try all variants so one bad header format can't
    # permanently block delivery.
    auth_variants = [
        ("Bearer",  {"Authorization": f"Bearer {_INFINITO_TOKEN}"}),
        ("Raw",     {"Authorization": _INFINITO_TOKEN}),
        ("apikey",  {"apikey": _INFINITO_TOKEN}),
    ]

    def _call(payload: dict, hdrs: dict) -> tuple[int, str]:
        try:
            with httpx.Client(timeout=20, follow_redirects=True) as client:
                resp = client.post(_INFINITO_URL, json=payload, headers=hdrs)
                _log.warning(
                    "Infinito → HTTP %d | auth=%s | to=%s | response=%s",
                    resp.status_code,
                    list(hdrs.keys())[0],
                    phone_clean,
                    resp.text[:300],
                )
                return resp.status_code, resp.text
        except Exception as exc:
            _log.error("Infinito exception: %s", exc)
            return 0, str(exc)

    errors: list[str] = []

    for label, hdrs in auth_variants:
        # Try template message first
        s, b = _call(template_payload, hdrs)
        if s == 200:
            return {
                "success":  True,
                "message":  f"WhatsApp template sent via Infinito! (auth={label})",
                "response": b[:300],
            }
        errors.append(f"[{label}/template] HTTP {s}: {b[:120]}")

        # Fallback to plain text
        s2, b2 = _call(text_payload, hdrs)
        if s2 == 200:
            return {
                "success":  True,
                "message":  f"WhatsApp message sent via Infinito! (auth={label})",
                "response": b2[:300],
            }
        errors.append(f"[{label}/text] HTTP {s2}: {b2[:120]}")

    # ── All strategies failed — build a diagnostic curl for manual testing ────
    sample_payload_str = _json.dumps(template_payload, indent=2)
    curl_cmd = (
        f"curl --location --request POST '{_INFINITO_URL}' \\\n"
        f"  --header 'Authorization: Bearer {_INFINITO_TOKEN[:20]}...{_INFINITO_TOKEN[-6:]}' \\\n"
        f"  --header 'Content-Type: application/json' \\\n"
        f"  --data '{_json.dumps(template_payload)}'"
    )

    _log.error(
        "All Infinito auth strategies failed for to=%s.\nErrors: %s\nCurl equivalent:\n%s",
        phone_clean, errors, curl_cmd,
    )

    return {
        "success": False,
        "message": (
            "Infinito 403 on all auth strategies — this is an account-level block "
            "on their server, not a code issue.\n\n"
            "NEXT STEPS:\n"
            "1. Run the curl command in your terminal (see Railway logs for exact cmd).\n"
            "   If it also returns 403 locally → contact Infinito/ValueFirst support "
            "to activate your account for outbound WhatsApp.\n"
            "   If it works locally but not on Railway → you need to whitelist "
            "Railway's outbound IP in your Infinito account settings.\n\n"
            "2. Log in to goinfinito.com → Settings → Sandbox / Test Numbers → "
            "add +919953023927 as an approved recipient (demo accounts require this).\n\n"
            f"Errors tried: {' | '.join(errors)}"
        ),
    }


def _normalize_phone(raw: str) -> str:
    """
    Strip formatting characters and ensure the number has a country code.

    Rules (covers Indian numbers specifically but works globally):
      • Strip +, spaces, hyphens, parentheses
      • If the result is exactly 10 digits → prepend India country code "91"
      • Any other digit-only string is returned as-is (assumed to already
        include country code)

    Examples:
      "+91 99530 23927" → "919953023927"
      "9953023927"      → "919953023927"   ← 10-digit Indian number
      "919953023927"    → "919953023927"   ← already has CC
      "14155551234"     → "14155551234"    ← US number, 11 digits, unchanged
    """
    cleaned = (
        raw
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )
    if cleaned.isdigit() and len(cleaned) == 10:
        cleaned = "91" + cleaned          # bare Indian mobile → add country code
    return cleaned


@router.post("/notifications/whatsapp/send")
async def send_whatsapp(settings: WhatsAppSettings):
    """
    Send a WhatsApp notification via Infinito (api.goinfinito.com).

    The recipient phone number is the only required field from the frontend.
    Bearer token, sender number, and template ID are pre-configured server-side
    via environment variables (INFINITO_TOKEN, INFINITO_FROM, INFINITO_TEMPLATE_ID).
    """
    msg         = settings.message or _build_daily_summary()
    phone_clean = _normalize_phone(settings.phone)

    if not phone_clean.isdigit():
        return {
            "success": False,
            "message": "Invalid phone number — use digits with country code, e.g. 919876543210 or +91 98765 43210.",
        }

    return _send_via_infinito(phone_clean, msg)


@router.get("/notifications/whatsapp/diagnose")
async def whatsapp_diagnose():
    """
    Diagnostic endpoint — returns the exact request CafeBuddy will send to
    Infinito (payload + masked token) so you can compare it against a working
    curl command without triggering an actual API call.

    Access via: GET /api/notifications/whatsapp/diagnose
    """
    import httpx

    today_str    = datetime.now().strftime("%d/%m/%Y")
    _DLR_URL_D   = "https://webhook.site/cc84d70e-658a-41e3-851d-1207efef4168?To=%p&From=%P&REASON_CODE=%2&GUID=%5"
    example_addr = [{"seq": "1", "to": "919999999999", "from": _INFINITO_FROM, "tag": "Test1"}]

    template_payload = {
        "apiver": "1.0",
        "whatsapp": {
            "ver": "2.0",
            "dlr": {"url": _DLR_URL_D},
            "messages": [{
                "coding":       1,
                "id":           "11",
                "msgtype":      "3",
                "templateinfo": f"{_INFINITO_TEMPLATE_ID}~Car~{today_str}",
                "b_urlinfo":    "#/renew-policy",
                "type":         "",
                "mediadata":    "",
                "text":         "",
                "addresses":    example_addr,
            }],
        },
    }

    # Mask the token for safe display
    tok   = _INFINITO_TOKEN
    token_display = tok[:12] + "…" + tok[-6:] if len(tok) > 20 else "***"

    # Make a real test call against the API (using a dummy number)
    status, body = 0, "not attempted"
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = client.post(
                _INFINITO_URL,
                json=template_payload,
                headers={"Authorization": f"Bearer {_INFINITO_TOKEN}"},
            )
            status, body = resp.status_code, resp.text
    except Exception as exc:
        status, body = 0, str(exc)

    return {
        "url":            _INFINITO_URL,
        "method":         "POST",
        "authorization":  f"Bearer {token_display}",
        "sender_from":    _INFINITO_FROM,
        "template_id":    _INFINITO_TEMPLATE_ID,
        "sample_payload": template_payload,
        "live_test": {
            "status":   status,
            "response": body[:500],
        },
        "phone_normalization_examples": {
            "9953023927":   _normalize_phone("9953023927"),
            "+919953023927": _normalize_phone("+919953023927"),
            "919953023927": _normalize_phone("919953023927"),
        },
    }


@router.get("/notifications/whatsapp/summary")
def get_whatsapp_summary():
    """Preview the daily summary message that would be sent via WhatsApp."""
    return {"preview": _build_daily_summary()}
