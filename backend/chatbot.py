"""
Cafe Buddy Chatbot — streaming AI responses with web search + festival calendar.
Works in two modes:
  1. AI mode   — full Claude-powered, if ANTHROPIC_API_KEY env var is set
  2. Smart mode— analytics-based engine (no API key needed)
"""
from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from data_store import (
    get_data, item_stats, platform_breakdown,
    category_breakdown, daily_revenue,
)

router = APIRouter()

# ─── Env / optional deps ─────────────────────────────────────────────────────

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

try:
    import anthropic as _anthropic
    _ai_client = _anthropic.Anthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else None
    HAS_AI = bool(ANTHROPIC_KEY)
except ImportError:
    _ai_client = None
    HAS_AI = False

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

    cutoff_7d   = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    last_7d     = [r for r in data if r["date"] >= cutoff_7d]
    items_7d    = item_stats(last_7d)

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

    return f"""── CAFÉ DATA SUMMARY ──────────────────────────────────────────
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

# ─── Claude streaming ─────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are Cafe Buddy AI — a sharp, data-driven assistant for café owners in India.

You have access to:
1. Real café sales analytics (provided in CONTEXT block)
2. Upcoming Indian festivals with menu and promo ideas (FESTIVALS block)
3. Live web search results (WEB SEARCH block)

Rules:
- Always ground answers in the actual data when available.
- For festival/dish questions, give specific, actionable menu ideas and promotions.
- Format with markdown: **bold** key points, bullet lists, numbered steps.
- Keep responses focused and practical — no filler.
- Currency is always ₹ (Indian Rupees).
- When web results are present, cite insights from them naturally.
"""


async def _stream_claude(history: list, message: str,
                         context: str, search: list, festivals: list):
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

    system_msg = (f"{_SYSTEM_PROMPT}\n\n"
                  f"CONTEXT:\n{context}\n\n"
                  f"{fest_txt}\n{web_txt}")

    msgs = [{"role": m["role"], "content": m["content"]} for m in history[-12:]]
    msgs.append({"role": "user", "content": message})

    with _ai_client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=system_msg,
        messages=msgs,
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'text': text})}\n\n"

    # Send source metadata at end
    sources = {
        "data": bool(context and "no sales data" not in context.lower()),
        "web":  bool(search),
        "festivals": bool(festivals),
    }
    yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

# ─── Smart analytics fallback (no API key needed) ────────────────────────────

def _smart_response(message: str, data: list, festivals: list, search_res: list = []) -> str:
    m      = message.lower()
    items  = item_stats(data)
    plats  = platform_breakdown(data)
    cats   = category_breakdown(data)
    dates  = sorted(set(r["date"] for r in data))
    total_rev   = sum(r["revenue"] for r in data)
    total_cost  = sum(r["cost"]    for r in data)
    daily_avg   = total_rev / max(len(dates), 1)
    food_cost_pct = total_cost / max(total_rev, 1) * 100

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
        if "last week" in m or "past week" in m or "this week" in m:
            cut = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            period_data  = [r for r in data if r["date"] >= cut]
            period_label = "last 7 days"
        elif "last month" in m or "past month" in m:
            cut = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            period_data  = [r for r in data if r["date"] >= cut]
            period_label = "last 30 days"
        elif "today" in m:
            cut = datetime.now().strftime("%Y-%m-%d")
            period_data  = [r for r in data if r["date"] == cut]
            period_label = "today"

        top = item_stats(period_data)
        if not top:
            return f"No data found for {period_label}."
        lines = [f"**Top selling items — {period_label}:**\n"]
        for i, x in enumerate(top[:5]):
            lines.append(f"{i+1}. **{x['name']}** — ₹{x['revenue']:,.0f} revenue, "
                         f"{x['qty']:.0f} units, {x['margin_pct']:.1f}% margin")
        lines.append(f"\n💡 **{top[0]['name']}** is your star product. "
                     "Feature it prominently on Zomato/Swiggy with high-quality photos.")
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
                f"**📊 Revenue**\n"
                f"- Total: **₹{total_rev:,.0f}** over {len(dates)} days\n"
                f"- Daily average: **₹{daily_avg:,.0f}**\n"
                f"- Food cost %: **{food_cost_pct:.1f}%** — {status}\n\n"
                f"**🏆 Top 3 Items:**\n{top3_str}\n\n"
                f"**📱 Best Platform:** {top_plat}\n\n"
                f"**📅 Next Festival:** {next_fest} on {next_date}\n\n"
                f"**💡 Quick Wins:**\n"
                f"- Upsell **{items[0]['name'] if items else 'top items'}** — your highest revenue item\n"
                f"- Boost promotions on **{top_plat}** — your top channel\n"
                f"- Prepare a special menu for **{next_fest}** to capture festival footfall\n"
                f"- Review low-margin items: **{items[-1]['name'] if items else '—'}** needs attention\n\n"
                f"{'💡 *Set ANTHROPIC_API_KEY in backend .env for full AI-powered answers.*' if not HAS_AI else ''}")

    # ── Absolute last resort (greetings / pure meta-questions) ──
    top3 = "\n".join(f"  {i+1}. {x['name']}" for i, x in enumerate(items[:3]))
    return (f"Hi! I'm Cafe Buddy AI. Here's what I can help you with:\n\n"
            f"**Data questions:**\n"
            f"- \"Which was the highest selling item last week?\"\n"
            f"- \"Compare my weekend vs weekday sales\"\n"
            f"- \"Which platform generates the most revenue?\"\n"
            f"- \"What is my lowest margin item?\"\n"
            f"- \"How can I increase my food cost efficiency?\"\n\n"
            f"**Festival / menu planning:**\n"
            f"- \"How should I prepare for Navratri?\"\n"
            f"- \"What special dish should I introduce for Diwali?\"\n"
            f"- \"Give me Holi menu ideas\"\n\n"
            f"Your current top sellers are:\n{top3}\n\n"
            f"{'💡 *Set ANTHROPIC_API_KEY in backend .env for full AI-powered answers.*' if not HAS_AI else ''}")


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
async def chatbot_stream(req: ChatRequest):
    data       = get_data()
    context    = _build_context(data)
    festivals  = get_upcoming_festivals(90)

    do_search  = _needs_web_search(req.message)
    search_res: list = []

    if do_search and HAS_DDG:
        # For festival/event queries, include current year so results are current
        year = datetime.now().year
        query = f"cafe restaurant {req.message} India {year}"
        if any(k in req.message.lower() for k in ["festival", "eid", "diwali", "holi", "navratri", "date", "when"]):
            query = f"{req.message} {year} India date"
        search_res = await asyncio.to_thread(_web_search, query, 4)

    async def generate():
        try:
            if HAS_AI:
                async for chunk in _stream_claude(
                    [m.model_dump() for m in req.history],
                    req.message, context, search_res, festivals
                ):
                    yield chunk
            else:
                response = _smart_response(req.message, data, festivals, search_res)
                async for chunk in _stream_text(response):
                    yield chunk
        except Exception as e:
            yield f"data: {json.dumps({'text': f'\\n\\n*Error: {e}*'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': {}})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no",
                 "Access-Control-Allow-Origin": "*"},
    )


@router.get("/chatbot/status")
def chatbot_status():
    return {
        "ai_mode":     HAS_AI,
        "web_search":  HAS_DDG,
        "model":       "claude-opus-4-7" if HAS_AI else "Smart Analytics Engine",
        "api_key_set": bool(ANTHROPIC_KEY),
    }


@router.get("/chatbot/festivals")
def upcoming_festivals(days: int = 90):
    return {"festivals": get_upcoming_festivals(days)}
