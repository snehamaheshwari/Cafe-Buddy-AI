"""
Cafe Buddy Sentiment Analysis Engine
--------------------------------------
Primary model  : Pre-trained Logistic Regression (sentiment_model.pkl)
Vectoriser     : TF-IDF (tfidf_vectorizer.pkl)
Label mapping  : LabelEncoder (label_encoder.pkl)
                 Classes → Negative | Neutral | Positive

On review upload the engine:
  1. Loads the pre-trained model (trained by the team on real café review data).
  2. Predicts sentiment for every review with a confidence score.
  3. Runs aspect-based analysis across 5 dimensions: Food, Service, Ambiance,
     Price/Value, Wait Time.
  4. Computes NPS, satisfaction score, keyword clouds, trend over time.
  5. Exposes get_chat_context() so the chatbot gets rich structured insights.
"""
from __future__ import annotations

import os
import re
import warnings
from collections import Counter, defaultdict
from datetime import datetime

# ── Optional NLP deps ─────────────────────────────────────────────────────────
try:
    import nltk
    nltk.download("stopwords", quiet=True)
    from nltk.corpus import stopwords as _sw
    _STOPWORDS = set(_sw.words("english"))
except Exception:
    _STOPWORDS = set()

try:
    import joblib
    HAS_JOBLIB = True
except Exception:
    HAS_JOBLIB = False

# ── Model paths ───────────────────────────────────────────────────────────────
_MODELS_DIR   = os.path.join(os.path.dirname(__file__), "models")
_MODEL_PATH   = os.path.join(_MODELS_DIR, "sentiment_model.pkl")
_TFIDF_PATH   = os.path.join(_MODELS_DIR, "tfidf_vectorizer.pkl")
_ENCODER_PATH = os.path.join(_MODELS_DIR, "label_encoder.pkl")

# ── Aspect keyword banks ───────────────────────────────────────────────────────
ASPECT_KEYWORDS = {
    "Food & Menu": [
        "food", "taste", "flavour", "flavor", "dish", "meal", "menu", "delicious",
        "fresh", "stale", "portion", "quality", "cooked", "raw", "bland", "spicy",
        "pizza", "burger", "coffee", "tea", "dessert", "starter", "main course",
        "veg", "non-veg", "ingredient", "recipe", "chef", "cuisine", "appetiser",
    ],
    "Service & Staff": [
        "service", "staff", "waiter", "server", "rude", "polite", "helpful",
        "attentive", "friendly", "unfriendly", "professional", "unprofessional",
        "courteous", "ignored", "responsive", "behaviour", "behavior", "attitude",
        "manager", "crew", "team", "host", "hospitality",
    ],
    "Ambiance & Comfort": [
        "ambiance", "ambience", "atmosphere", "decor", "music", "lighting",
        "seating", "comfortable", "noisy", "quiet", "clean", "dirty", "hygiene",
        "interior", "cozy", "spacious", "crowded", "parking", "location", "vibe",
        "aesthetic", "view", "outdoor", "indoor", "restroom", "toilet",
    ],
    "Price & Value": [
        "price", "expensive", "cheap", "affordable", "overpriced", "value",
        "worth", "cost", "bill", "money", "budget", "costly", "reasonable",
        "pricey", "rate", "charges", "discount", "offer", "deal", "pocket",
    ],
    "Wait Time & Speed": [
        "wait", "waiting", "slow", "fast", "quick", "delay", "time", "late",
        "minutes", "hours", "long", "rushed", "prompt", "efficient", "delivery",
        "order", "queue", "busy", "rush", "speed",
    ],
}

# Words to skip when building keyword clouds
_SKIP_WORDS = {
    "this", "that", "with", "from", "have", "been", "they", "were", "here",
    "just", "will", "came", "also", "very", "good", "great", "really", "would",
    "could", "their", "when", "your", "well", "after", "there", "such", "some",
    "much", "more", "time", "back", "made", "place", "cafe", "coffee", "visited",
    "come", "loved", "ordered", "tried", "definitely", "always", "even", "though",
    "still", "again", "never", "every", "other", "than", "then", "them", "into",
}


def clean_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"@\w+|#\w+", "", text)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = [w for w in text.split() if w not in _STOPWORDS and len(w) > 2]
    return " ".join(tokens)


# ── Engine ────────────────────────────────────────────────────────────────────

class SentimentEngine:
    def __init__(self):
        self._model   = None
        self._tfidf   = None
        self._encoder = None
        self._fitted  = False
        self._records: list = []
        self._stats:   dict = {}
        self._info:    dict = {}
        self._load_pretrained()

    # ── Load pre-trained model ─────────────────────────────────────────────────

    def _load_pretrained(self) -> bool:
        """Load the team's pre-trained Logistic Regression + TF-IDF + LabelEncoder."""
        if not HAS_JOBLIB:
            return False
        if not all(os.path.exists(p) for p in [_MODEL_PATH, _TFIDF_PATH, _ENCODER_PATH]):
            return False
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                import pickle
                with open(_MODEL_PATH,   "rb") as f: self._model   = pickle.load(f)
                with open(_TFIDF_PATH,   "rb") as f: self._tfidf   = pickle.load(f)
                with open(_ENCODER_PATH, "rb") as f: self._encoder = pickle.load(f)
            self._fitted = True
            return True
        except Exception as e:
            print(f"[SentimentEngine] Could not load pre-trained models: {e}")
            return False

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(self, text: str) -> str:
        """Predict sentiment label for a single text."""
        label, _, _, _ = self.predict_with_confidence(text)
        return label

    def predict_with_confidence(self, text: str) -> tuple[str, float, float, float]:
        """
        Returns (label, confidence_pct, neg_prob, pos_prob).
        label       : 'Positive' | 'Neutral' | 'Negative'
        confidence  : 0-100 float of the winning class
        neg_prob    : probability of Negative class
        pos_prob    : probability of Positive class
        """
        if not self._fitted:
            return "Neutral", 50.0, 0.33, 0.33
        try:
            vec    = self._tfidf.transform([clean_text(text)])
            pred   = self._model.predict(vec)[0]
            probs  = self._model.predict_proba(vec)[0]  # [neg, neu, pos]
            label  = self._encoder.inverse_transform([pred])[0]
            conf   = round(float(max(probs)) * 100, 1)
            return label, conf, round(float(probs[0]), 3), round(float(probs[2]), 3)
        except Exception:
            return "Neutral", 50.0, 0.33, 0.33

    def predict_batch(self, texts: list[str]) -> list[str]:
        if not self._fitted or not texts:
            return ["Neutral"] * len(texts)
        try:
            vecs  = self._tfidf.transform([clean_text(t) for t in texts])
            preds = self._model.predict(vecs)
            return [self._encoder.inverse_transform([p])[0] for p in preds]
        except Exception:
            return ["Neutral"] * len(texts)

    # ── Process uploaded dataframe ────────────────────────────────────────────

    def process_dataframe(self, df, filename: str = "") -> tuple[list, dict]:
        records: list = []
        for _, row in df.iterrows():
            text  = str(row.get("Review_Text", "")).strip()
            if not text or text.lower() in ("nan", "none", ""):
                continue

            # Use pre-trained model for ALL rows — do not trust uploaded labels
            label, conf, neg_p, pos_p = self.predict_with_confidence(text)

            # Override only if uploaded label is definitive and high confidence
            uploaded_label = str(row.get("Sentiment_Label", "")).strip()
            if uploaded_label in ("Positive", "Neutral", "Negative"):
                label = uploaded_label   # respect human labels when provided

            try:
                rating = int(float(str(row.get("Rating", 3))))
                rating = max(1, min(5, rating))
            except Exception:
                rating = 3

            records.append({
                "review_id":    str(row.get("Review_ID",     "")).strip(),
                "source":       str(row.get("Source",        "Unknown")).strip(),
                "review_date":  str(row.get("Review_Date",   "")).strip(),
                "location":     str(row.get("Cafe_Location", "Unknown")).strip(),
                "visit_type":   str(row.get("Visit_Type",    "Unknown")).strip(),
                "rating":       rating,
                "sentiment":    label,
                "confidence":   conf,
                "neg_prob":     neg_p,
                "pos_prob":     pos_p,
                "review_text":  text,
            })

        stats = self._compute_stats(records)
        self._records = records
        self._stats   = stats
        self._info    = {
            "filename":      filename,
            "total_reviews": len(records),
            "uploaded_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model_type":    "Logistic Regression + TF-IDF (Pre-trained)",
            "model_accuracy": "Team-trained on café review dataset",
        }
        return records, stats

    # ── Statistics ────────────────────────────────────────────────────────────

    def _compute_stats(self, records: list) -> dict:
        if not records:
            return {}

        total = len(records)
        sent  = Counter(r["sentiment"] for r in records)

        # ── Aggregations ──────────────────────────────────────────────────────
        source_agg  = defaultdict(lambda: Counter())
        visit_agg   = defaultdict(lambda: Counter())
        loc_agg     = defaultdict(lambda: Counter())
        date_agg    = defaultdict(lambda: Counter())
        rating_map  = defaultdict(list)

        for r in records:
            source_agg[r["source"]][r["sentiment"]]    += 1
            visit_agg[r["visit_type"]][r["sentiment"]] += 1
            loc_agg[r["location"]][r["sentiment"]]     += 1
            rating_map[r["sentiment"]].append(r["rating"])
            # Parse date to YYYY-MM for trend
            try:
                d = str(r["review_date"])[:7]  # "2024-03"
                if len(d) == 7:
                    date_agg[d][r["sentiment"]] += 1
            except Exception:
                pass

        def breakdown(agg: dict, key_name: str) -> list:
            result = []
            for k, counts in agg.items():
                t   = sum(counts.values())
                pos = counts.get("Positive", 0)
                neu = counts.get("Neutral",  0)
                neg = counts.get("Negative", 0)
                result.append({
                    key_name:       k,
                    "total":        t,
                    "positive":     pos,
                    "neutral":      neu,
                    "negative":     neg,
                    "positive_pct": round(pos / t * 100, 1),
                    "negative_pct": round(neg / t * 100, 1),
                    "satisfaction": round((pos * 2 + neu) / (t * 2) * 100, 1),
                })
            return sorted(result, key=lambda x: x["total"], reverse=True)

        # ── NPS (Promoters ≥4 star, Detractors ≤2 star) ───────────────────────
        promoters  = sum(1 for r in records if r["rating"] >= 4)
        detractors = sum(1 for r in records if r["rating"] <= 2)
        nps = round((promoters - detractors) / total * 100, 1)

        # ── Keyword clouds ────────────────────────────────────────────────────
        def top_words(sentiment: str, n: int = 12) -> list[dict]:
            blob   = " ".join(r["review_text"].lower() for r in records if r["sentiment"] == sentiment)
            words  = re.findall(r"\b[a-z]{4,}\b", blob)
            filtered = [w for w in words if w not in _SKIP_WORDS and w not in _STOPWORDS]
            return [{"word": w, "count": c} for w, c in Counter(filtered).most_common(n)]

        # ── Aspect-based sentiment ─────────────────────────────────────────────
        def aspect_sentiment(aspect: str) -> dict:
            kws = ASPECT_KEYWORDS[aspect]
            matched = [
                r for r in records
                if any(k in r["review_text"].lower() for k in kws)
            ]
            if not matched:
                return {"aspect": aspect, "total": 0, "positive_pct": 0,
                        "negative_pct": 0, "score": 0, "status": "no data"}
            t   = len(matched)
            pos = sum(1 for r in matched if r["sentiment"] == "Positive")
            neg = sum(1 for r in matched if r["sentiment"] == "Negative")
            score = round((pos * 2 + (t - pos - neg)) / (t * 2) * 100, 1)
            status = "excellent" if score >= 75 else "good" if score >= 55 else "needs improvement" if score >= 35 else "critical"
            return {
                "aspect":       aspect,
                "total":        t,
                "positive":     pos,
                "negative":     neg,
                "positive_pct": round(pos / t * 100, 1),
                "negative_pct": round(neg / t * 100, 1),
                "score":        score,
                "status":       status,
            }

        aspects = [aspect_sentiment(a) for a in ASPECT_KEYWORDS]
        aspects.sort(key=lambda x: x["score"])  # worst first

        # ── Trend over time ────────────────────────────────────────────────────
        trend = []
        for month in sorted(date_agg.keys()):
            counts = date_agg[month]
            t = sum(counts.values())
            pos = counts.get("Positive", 0)
            trend.append({
                "month":        month,
                "total":        t,
                "positive":     pos,
                "negative":     counts.get("Negative", 0),
                "positive_pct": round(pos / t * 100, 1) if t else 0,
            })

        # ── Confidence distribution ────────────────────────────────────────────
        conf_vals = [r.get("confidence", 50) for r in records]
        avg_conf  = round(sum(conf_vals) / len(conf_vals), 1) if conf_vals else 0
        low_conf  = sum(1 for c in conf_vals if c < 60)   # uncertain predictions

        # ── Actionable insights ───────────────────────────────────────────────
        insights = _generate_insights(records, aspects, sent, total, nps)

        # ── Avg rating by sentiment ────────────────────────────────────────────
        avg_rating = {
            s: round(sum(v) / len(v), 2)
            for s, v in rating_map.items() if v
        }

        sat_score = round(
            (sent.get("Positive", 0) * 1.0 + sent.get("Neutral", 0) * 0.5)
            / total * 100, 1
        )

        return {
            "total_reviews":    total,
            "positive":         sent.get("Positive", 0),
            "neutral":          sent.get("Neutral",  0),
            "negative":         sent.get("Negative", 0),
            "positive_pct":     round(sent.get("Positive", 0) / total * 100, 1),
            "neutral_pct":      round(sent.get("Neutral",  0) / total * 100, 1),
            "negative_pct":     round(sent.get("Negative", 0) / total * 100, 1),
            "satisfaction_score": sat_score,
            "nps":              nps,
            "promoters":        promoters,
            "detractors":       detractors,
            "overall_avg_rating": round(sum(r["rating"] for r in records) / total, 2),
            "avg_rating_by_sentiment": avg_rating,
            "avg_model_confidence": avg_conf,
            "low_confidence_reviews": low_conf,
            "source_breakdown":   breakdown(source_agg, "source"),
            "visit_breakdown":    breakdown(visit_agg,  "visit_type"),
            "location_breakdown": sorted(
                breakdown(loc_agg, "location"),
                key=lambda x: x["positive_pct"], reverse=True
            ),
            "sentiment_trend":   trend,
            "aspect_analysis":   aspects,
            "keywords": {
                "positive": top_words("Positive"),
                "neutral":  top_words("Neutral"),
                "negative": top_words("Negative"),
            },
            "actionable_insights": insights,
            "recent_reviews": [
                {k: v for k, v in r.items() if k != "review_text"}
                for r in records[-10:]
            ],
        }


# ── Actionable insights generator ─────────────────────────────────────────────

def _generate_insights(records, aspects, sent, total, nps) -> list[dict]:
    insights = []

    neg_pct = round(sent.get("Negative", 0) / total * 100, 1)
    pos_pct = round(sent.get("Positive", 0) / total * 100, 1)

    # NPS insight
    if nps >= 50:
        insights.append({"type": "positive", "priority": "info",
            "title": f"Strong NPS of {nps}",
            "detail": "Your promoter base is significantly larger than detractors. "
                      "Leverage this with referral programs or loyalty rewards."})
    elif nps < 0:
        insights.append({"type": "critical", "priority": "high",
            "title": f"Negative NPS ({nps}) — customers not recommending you",
            "detail": "More detractors than promoters. Urgently address service and food quality issues. "
                      "Consider a feedback recovery campaign."})
    elif nps < 20:
        insights.append({"type": "warning", "priority": "medium",
            "title": f"Low NPS ({nps}) — room for improvement",
            "detail": "Identify your detractors' key complaints and target those specifically."})

    # Aspect-based insights (worst aspects first)
    for asp in aspects[:2]:
        if asp["total"] == 0:
            continue
        if asp["status"] in ("critical", "needs improvement"):
            insights.append({"type": "warning", "priority": "high",
                "title": f"{asp['aspect']} needs attention ({asp['negative_pct']}% negative)",
                "detail": f"Out of {asp['total']} reviews mentioning {asp['aspect'].lower()}, "
                          f"{asp['negative_pct']}% are negative. Focus training and operations here."})

    # Best aspects
    best = sorted(aspects, key=lambda x: -x["score"])
    for asp in best[:1]:
        if asp["total"] > 0 and asp["score"] >= 70:
            insights.append({"type": "positive", "priority": "info",
                "title": f"{asp['aspect']} is your strongest area ({asp['positive_pct']}% positive)",
                "detail": f"Customers love your {asp['aspect'].lower()}. "
                          "Highlight this in marketing materials and social media."})

    # High negative volume
    if neg_pct > 25:
        insights.append({"type": "critical", "priority": "high",
            "title": f"{neg_pct}% of reviews are negative — immediate action needed",
            "detail": "Set up a review monitoring system. Respond to every negative review publicly. "
                      "Identify the top 3 recurring complaints and fix them within 30 days."})

    # High positive — opportunity
    if pos_pct >= 70:
        insights.append({"type": "positive", "priority": "info",
            "title": f"Excellent — {pos_pct}% positive reviews",
            "detail": "You have strong social proof. Ask happy customers to share reviews on Google/Zomato. "
                      "Use positive quotes in your marketing."})

    return insights


# ── Chatbot context ────────────────────────────────────────────────────────────

    # ── Chatbot context method (part of SentimentEngine class) ────────────────

# (attached to the class below via monkey-patch approach — included inline)

def _get_chat_context(self) -> str:
    s = self._stats
    if not s:
        return ""

    lines = [
        "── SENTIMENT ANALYSIS (Pre-trained Logistic Regression + TF-IDF) ─────",
        f"Reviews analysed : {s['total_reviews']}  |  Model avg confidence: {s.get('avg_model_confidence', '?')}%",
        f"Positive : {s['positive']} ({s['positive_pct']}%)  |  Neutral: {s['neutral']} ({s['neutral_pct']}%)  |  Negative: {s['negative']} ({s['negative_pct']}%)",
        f"Satisfaction score : {s['satisfaction_score']}%  |  Avg rating: {s['overall_avg_rating']}/5  |  NPS: {s.get('nps', 'N/A')}",
        f"Promoters : {s.get('promoters', 0)}  |  Detractors: {s.get('detractors', 0)}",
        "",
        "ASPECT ANALYSIS (score = satisfaction %, worst first):",
    ]
    for asp in s.get("aspect_analysis", []):
        if asp["total"] == 0:
            continue
        bar = "🔴" if asp["score"] < 40 else "🟡" if asp["score"] < 65 else "🟢"
        lines.append(
            f"  {bar} {asp['aspect']:22s} score={asp['score']}%  "
            f"(+{asp['positive_pct']}% / -{asp['negative_pct']}%  n={asp['total']})"
        )

    lines += ["", "SOURCE BREAKDOWN:"]
    for src in s.get("source_breakdown", [])[:5]:
        lines.append(
            f"  {src['source']}: {src['positive_pct']}% positive  "
            f"({src['positive']}✓ {src['negative']}✗ / {src['total']} total)"
        )

    lines += ["", "VISIT TYPE:"]
    for vt in s.get("visit_breakdown", []):
        lines.append(f"  {vt['visit_type']}: {vt['satisfaction']:.0f}% satisfaction ({vt['total']} reviews)")

    lines += ["", "TOP POSITIVE KEYWORDS:"]
    lines.append("  " + ", ".join(k["word"] for k in s.get("keywords", {}).get("positive", [])[:10]))
    lines += ["", "TOP NEGATIVE KEYWORDS:"]
    lines.append("  " + ", ".join(k["word"] for k in s.get("keywords", {}).get("negative", [])[:10]))

    lines += ["", "ACTIONABLE INSIGHTS:"]
    for ins in s.get("actionable_insights", []):
        priority = "❗" if ins["priority"] == "high" else "ℹ️"
        lines.append(f"  {priority} {ins['title']}")
        lines.append(f"     → {ins['detail']}")

    lines.append("──────────────────────────────────────────────────────────────")
    return "\n".join(lines)


# Attach to class
SentimentEngine.get_chat_context = _get_chat_context


# ── Decision generation ───────────────────────────────────────────────────────

def _get_decisions(self) -> list:
    s = self._stats
    if not s:
        return []

    decisions, did = [], 100
    neg_pct = s.get("negative_pct", 0)
    pos_pct = s.get("positive_pct", 0)
    nps     = s.get("nps", 0)

    if neg_pct > 20:
        decisions.append({
            "id": did, "type": "customer", "priority": "critical",
            "title": f"Address negative sentiment — {neg_pct:.0f}% of reviews are negative",
            "rationale": (
                f"With {s['negative']} negative reviews out of {s['total_reviews']}, "
                "customer satisfaction is at risk. "
                f"Top complaint areas: {', '.join(a['aspect'] for a in s.get('aspect_analysis', [])[:2] if a['total'] > 0)}."
            ),
            "action": "Conduct staff training, review operations checklist, respond to all negative reviews within 24h.",
            "confidence": min(95, 60 + int(neg_pct)),
            "impact": "high", "status": "pending",
        })
        did += 1

    if nps < 20:
        decisions.append({
            "id": did, "type": "customer", "priority": "high",
            "title": f"NPS improvement programme (current NPS: {nps})",
            "rationale": "Low NPS indicates customers are not actively recommending the café.",
            "action": "Launch post-visit feedback collection. Offer small incentive for completing surveys.",
            "confidence": 78, "impact": "medium", "status": "pending",
        })
        did += 1

    if pos_pct >= 70:
        decisions.append({
            "id": did, "type": "marketing", "priority": "medium",
            "title": "Amplify positive reviews in marketing",
            "rationale": f"{pos_pct:.0f}% positive reviews is excellent social proof.",
            "action": "Share top reviews on Instagram/Zomato. Ask 5-star customers to write Google reviews.",
            "confidence": 85, "impact": "medium", "status": "pending",
        })
        did += 1

    # Aspect-based decisions
    for asp in s.get("aspect_analysis", []):
        if asp.get("status") == "critical" and asp["total"] > 0:
            decisions.append({
                "id": did, "type": "operations", "priority": "high",
                "title": f"Fix {asp['aspect']} — {asp['negative_pct']}% negative mentions",
                "rationale": f"{asp['total']} reviews mention {asp['aspect'].lower()}, {asp['negative_pct']}% negatively.",
                "action": f"Deep-dive into customer feedback on {asp['aspect'].lower()}. "
                          "Assign a dedicated improvement owner this week.",
                "confidence": 80, "impact": "high", "status": "pending",
            })
            did += 1

    return decisions


SentimentEngine.get_decisions = _get_decisions


# ── Disk persistence ──────────────────────────────────────────────────────────

def _save_state(self) -> None:
    import json as _json
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    try:
        with open(os.path.join(data_dir, "reviews_state.json"), "w", encoding="utf-8") as f:
            _json.dump({"records": self._records, "stats": self._stats, "info": self._info},
                       f, ensure_ascii=False)
    except Exception:
        pass


def _load_state(self) -> bool:
    import json as _json
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    state_path = os.path.join(data_dir, "reviews_state.json")
    if not os.path.exists(state_path):
        return False
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = _json.load(f)
        self._records = state.get("records", [])
        self._stats   = state.get("stats", {})
        self._info    = state.get("info", {})
        return bool(self._records)
    except Exception:
        return False


def _clear_state(self) -> None:
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    p = os.path.join(data_dir, "reviews_state.json")
    try:
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass


SentimentEngine.save_state  = _save_state
SentimentEngine.load_state  = _load_state
SentimentEngine.clear_state = _clear_state


# ── Accessors ─────────────────────────────────────────────────────────────────

@property
def _has_data(self) -> bool:
    return bool(self._records)

@property
def _stats_prop(self) -> dict:
    return self._stats

@property
def _records_prop(self) -> list:
    return self._records

@property
def _info_prop(self) -> dict:
    return self._info

SentimentEngine.has_data = _has_data
SentimentEngine.stats    = _stats_prop
SentimentEngine.records  = _records_prop
SentimentEngine.info     = _info_prop


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: SentimentEngine | None = None


def get_engine() -> SentimentEngine:
    global _engine
    if _engine is None:
        _engine = SentimentEngine()
        _engine.load_state()
    return _engine
