"""
HJ Motors — Trim Classifier Engine
====================================
يصنّف الإعلانات المجموعة من المصادر إلى فئات (trims) صحيحة.

المشكلة الأصلية:
  searchURLAndAI كان يضع جميع الإعلانات في bucket واحد بدون تصنيف.
  مثلاً: كامري E (105k) وكامري لوميير (149k) تظهر تحت نفس الفئة.

الحل:
  1. مطابقة ذكية متعددة الطبقات (keywords → name → price proximity)
  2. فصل واضح حسب الفئة مع confidence scoring
  3. رفض الإعلانات غير المنطقية + حذف المكررات
  4. bucket "Unknown" للإعلانات الغامضة
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from collections import defaultdict
from statistics import median, stdev

# ── استيراد trims_config ────────────────────────────────────────
from trims_config import get_trims, TrimDefinition


# ══════════════════════════════════════════════════════════════════
#  1. TRIM MATCHER — المطابقة الذكية
# ══════════════════════════════════════════════════════════════════

@dataclass
class TrimMatch:
    """نتيجة مطابقة إعلان واحد مع فئة"""
    trim_name: str
    trim_name_ar: str
    trim_id: str
    msrp: int
    engine: str
    confidence: float          # 0.0 → 1.0
    match_method: str          # "keyword" | "name" | "price_proximity" | "fallback"
    match_detail: str          # تفصيل المطابقة

def normalize(text):
    return text.lower().strip()

def classify_listing(listing: dict, brand: str, model: str, year: int,
                     dynamic_trims: list = None) -> TrimMatch:

    title = (listing.get("listedAs") or "").lower().strip()
    price = listing.get("price", 0)

    print(f"\n🔍 Classifying: «{title}» | 💰 {price}")

    trims = _build_trim_list(brand, model, year, dynamic_trims)

    # ── إذا ما فيه trims ────────────────────────────────
    if not trims:
        return TrimMatch(
            trim_name=f"{model} Standard",
            trim_name_ar=f"{model} ستاندرد",
            trim_id="fallback",
            msrp=0,
            engine="",
            confidence=0.35,
            match_method="fallback_no_trims",
            match_detail="لا توجد فئات — تم اختيار الافتراضي"
        )

    scored_trims = []

    # ── تقييم كل Trim ───────────────────────────────────
    for trim in trims:
        score = 0.0
        reasons = []

        # 1️⃣ Keyword Match (أقوى شيء)
        # for kw in trim["keywords"]:
        #     print(f"Checking keyword '{kw}' for trim '{trim['name']}' against title...")
        #     if kw and len(kw) >= 1 and kw in title:
        #         score += 0.9
        #         reasons.append(f"keyword:{kw}")
        #         break  # لا تكرر
        keywords = set(normalize(k) for k in trim["keywords"] if k)
        titleNormalize = normalize(title)
        if titleNormalize in keywords:
            score += 0.9
            reasons.append(f"keyword:{titleNormalize}")

        # 2️⃣ Name Match (مطابقة كاملة للاسم)
        if trim["name"].lower() in title or trim["name_ar"].lower() in title:
            score += 0.8
            reasons.append("name_match")

        # 3️⃣ Word Overlap مع عقوبة على الكلمات الزائدة
        words = trim["name"].lower().split()
        if words:
            hits = sum(1 for w in words if w in title)
            overlap = hits / len(words)

            # عقوبة: كل كلمة في اسم الفئة غير موجودة في العنوان = -0.15
            misses = len(words) - hits
            penalty = misses * 0.15

            net_overlap_score = max(0.0, (overlap * 0.6) - penalty)

            if overlap > 0:
                score += net_overlap_score
                reasons.append(f"overlap:{overlap:.2f} penalty:{penalty:.2f}")

        # 4️⃣ Price Proximity
        if price > 0 and trim["msrp"] > 0:
            diff = abs(trim["msrp"] - price) / trim["msrp"]
            if diff <= 0.30:
                price_score = (1 - diff) * 0.7
                score += price_score
                reasons.append(f"price:{diff:.2f}")

        # 5️⃣ Bias بسيط (عشان ما يكون صفر)
        score += 0.05

        scored_trims.append({
            "trim": trim,
            "score": score,
            "reasons": reasons
        })

    # ── اختيار الأفضل ───────────────────────────────────
    best = max(scored_trims, key=lambda x: x["score"])

    best_trim = best["trim"]
    best_score = best["score"]

    print("📊 Scores:")
    for t in scored_trims:
        print(f" - {t['trim']['name']} → {t['score']:.2f} | {t['reasons']}")

    print(f"🏆 Selected: {best_trim['name']} ({best_score:.2f})")

    # ── Confidence ذكي ──────────────────────────────────
    confidence = min(0.95, max(0.35, best_score))

    # ── تحديد نوع المطابقة ──────────────────────────────
    if any("keyword" in r for r in best["reasons"]):
        method = "keyword"
    elif "name_match" in best["reasons"]:
        method = "name"
    elif any("overlap" in r for r in best["reasons"]):
        method = "word_overlap"
    elif any("price" in r for r in best["reasons"]):
        method = "price_proximity"
    else:
        method = "fallback_best_match"

    return TrimMatch(
        trim_name=best_trim["name"],
        trim_name_ar=best_trim["name_ar"],
        trim_id=best_trim["id"],
        msrp=best_trim["msrp"],
        engine=best_trim["engine"],
        confidence=confidence,
        match_method=method,
        match_detail=" | ".join(best["reasons"]) if best["reasons"] else "default scoring"
    )
# def normalize(text: str) -> str:
#     return (text or "").lower().strip()


# def tokenize(text: str) -> list:
#     return normalize(text).split()


# # ✅ تنظيف الكلمات (إزالة الأكواد مثل 1l5)
# def clean_tokens(text: str) -> list:
#     tokens = tokenize(text)
#     return [
#         t for t in tokens
#         if not t.startswith("(")
#         and not t.endswith(")")
#         and not any(c.isdigit() for c in t)
#     ]


# def classify_listing(listing: dict, brand: str, model: str, year: int,
#                      dynamic_trims: list = None) -> TrimMatch:

#     title = normalize(listing.get("listedAs"))
#     price = listing.get("price", 0)

#     print(f"\n🔍 Classifying: «{title}» | 💰 {price}")

#     trims = _build_trim_list(brand, model, year, dynamic_trims)

#     # ─────────────────────────────────────────────
#     # ✅ fallback إذا ما فيه trims
#     # ─────────────────────────────────────────────
#     if not trims:
#         return TrimMatch(
#             trim_name=f"{model} Standard",
#             trim_name_ar=f"{model} ستاندرد",
#             trim_id="fallback",
#             msrp=0,
#             engine="",
#             confidence=0.35,
#             match_method="fallback_no_trims",
#             match_detail="no trims"
#         )

#     # ─────────────────────────────────────────────
#     # ✅ 1. FILTER قوي
#     # ─────────────────────────────────────────────
#     def contains(word):
#         return word in title

#     strong_filters = ["hybrid", "automatic", "plus"]

#     for f in strong_filters:
#         if contains(f):
#             filtered = [t for t in trims if f in normalize(t["name"])]
#             if filtered:
#                 trims = filtered

#     # ─────────────────────────────────────────────
#     # ✅ 2. ترتيب حسب الأطول
#     # ─────────────────────────────────────────────
#     trims = sorted(trims, key=lambda t: len(t["name"]), reverse=True)

#     scored_trims = []

#     # ✅ استخدام clean tokens
#     title_words = set(clean_tokens(title))

#     # ─────────────────────────────────────────────
#     # ✅ 3. التقييم الذكي
#     # ─────────────────────────────────────────────
#     for trim in trims:
#         score = 0.0
#         reasons = []

#         name = normalize(trim["name"])
#         name_ar = normalize(trim["name_ar"])

#         trim_words = set(clean_tokens(name))
#         word_count = len(trim_words)

#         # 🟢 1. Exact Phrase Match
#         if name in title or name_ar in title:
#             score += 2.0
#             reasons.append("exact_phrase")

#         # 🟢 2. Keyword Match
#         for kw in trim["keywords"]:
#             kw = normalize(kw)
#             if kw and len(kw) >= 2 and kw in title:
#                 score += 1.5
#                 reasons.append(f"keyword:{kw}")
#                 break

#         # 🟢 3. Overlap ذكي
#         if trim_words:
#             intersection = title_words & trim_words
#             overlap = len(intersection) / len(trim_words)

#             if overlap == 1:
#                 score += 1.2
#                 reasons.append("full_overlap")
#             elif overlap > 0:
#                 score += overlap * 0.7
#                 reasons.append(f"overlap:{overlap:.2f}")

#         # 🟢 4. Specificity Boost
#         score += word_count * 0.15

#         # 🔴 5. Penalize الفئات العامة
#         if word_count == 1:
#             score -= 0.4
#             reasons.append("generic_penalty")

#         # 🔴 6. Penalize mismatch
#         if "plus" in title and "plus" not in name:
#             score -= 0.5
#         if "hybrid" in title and "hybrid" not in name:
#             score -= 0.5
#         if "automatic" in title and "automatic" not in name:
#             score -= 0.3

#         # 🔥 7. Penalize الكلمات الزائدة (الحل الأساسي لمشكلتك)
#         extra_words = trim_words - title_words
#         if extra_words:
#             score -= len(extra_words) * 0.15
#             reasons.append(f"extra_penalty:{len(extra_words)}")

#         # 🟢 8. Price Proximity
#         if price > 0 and trim["msrp"] > 0:
#             diff = abs(trim["msrp"] - price) / trim["msrp"]
#             if diff <= 0.30:
#                 score += (1 - diff) * 0.8
#                 reasons.append(f"price:{diff:.2f}")

#         # 🟢 9. Bias بسيط
#         score += 0.05

#         scored_trims.append({
#             "trim": trim,
#             "score": score,
#             "reasons": reasons
#         })

#     # ─────────────────────────────────────────────
#     # ✅ 4. ترتيب النتائج
#     # ─────────────────────────────────────────────
#     scored_trims = sorted(scored_trims, key=lambda x: x["score"], reverse=True)

#     best = scored_trims[0]
#     second = scored_trims[1] if len(scored_trims) > 1 else None

#     best_trim = best["trim"]
#     best_score = best["score"]

#     print("📊 Scores:")
#     for t in scored_trims:
#         print(f" - {t['trim']['name']} → {t['score']:.2f} | {t['reasons']}")

#     print(f"🏆 Selected: {best_trim['name']} ({best_score:.2f})")

#     # ─────────────────────────────────────────────
#     # ✅ 5. Confidence ذكي
#     # ─────────────────────────────────────────────
#     score_gap = 0
#     if second:
#         score_gap = best_score - second["score"]

#     confidence = best_score / 2

#     if score_gap < 0.3:
#         confidence *= 0.7

#     confidence = min(0.95, max(0.35, confidence))

#     # ─────────────────────────────────────────────
#     # ✅ 6. تحديد نوع المطابقة
#     # ─────────────────────────────────────────────
#     if "exact_phrase" in best["reasons"]:
#         method = "exact"
#     elif any("keyword" in r for r in best["reasons"]):
#         method = "keyword"
#     elif "full_overlap" in best["reasons"]:
#         method = "full_overlap"
#     elif any("overlap" in r for r in best["reasons"]):
#         method = "partial_overlap"
#     elif any("price" in r for r in best["reasons"]):
#         method = "price"
#     else:
#         method = "fallback"

#     # ─────────────────────────────────────────────
#     # ✅ 7. تفاصيل
#     # ─────────────────────────────────────────────
#     match_detail = f"gap:{score_gap:.2f} | " + (
#         " | ".join(best["reasons"]) if best["reasons"] else "default scoring"
#     )

#     return TrimMatch(
#         trim_name=best_trim["name"],
#         trim_name_ar=best_trim["name_ar"],
#         trim_id=best_trim["id"],
#         msrp=best_trim["msrp"],
#         engine=best_trim["engine"],
#         confidence=confidence,
#         match_method=method,
#         match_detail=match_detail
#     )

def _build_trim_list(brand: str, model: str, year: int, dynamic_trims: list = None) -> list[dict]:
    """يجمع الفئات من trims_config + dynamic_trims في قائمة موحدة"""
    result = []
    seen_names = set()

    # أولوية 1: trims_config (الأدق — معرّف يدوياً)
    configured = get_trims(brand, model, year)
    for t in configured:
        result.append({
            "id": t.id, "name": t.name.lower(), "name_ar": t.name_ar,
            "msrp": t.msrp, "engine": t.engine,
            "keywords": [k.lower() for k in t.keywords],
            "score": t.match_score,
        })
        seen_names.add(t.name.lower())
    print(f"seen_names after config: {seen_names}")
    print(f"Built trim list for {brand} {model}: {[t['name'] for t in result]}")
    # أولوية 2: dynamic_trims (من AI أو scrape)
    if dynamic_trims:
        for dt in dynamic_trims:
            name = dt.name if hasattr(dt, "name") else dt.get("name", "")
            if name.lower() in seen_names:
                continue
            result.append({
                "id": getattr(dt, "id", "") if hasattr(dt, "id") else dt.get("id", ""),
                "name": name,
                "name_ar": dt.name_ar if hasattr(dt, "name_ar") else dt.get("name_ar", name),
                "msrp": dt.msrp if hasattr(dt, "msrp") else dt.get("msrp", 0),
                "engine": dt.engine if hasattr(dt, "engine") else dt.get("engine", ""),
                "keywords": (dt.keywords if hasattr(dt, "keywords") else dt.get("keywords", [])),
                "score": dt.score if hasattr(dt, "score") else dt.get("score", 0.80),
            })
            seen_names.add(name.lower())

    
    return result


# ══════════════════════════════════════════════════════════════════
#  2. DEDUPLICATION — حذف المكررات
# ══════════════════════════════════════════════════════════════════

def deduplicate_listings(listings: list[dict]) -> list[dict]:
    """
    يحذف الإعلانات المكررة بناءً على:
      1. نفس URL
      2. نفس السعر + نفس العنوان (تقريبياً)
      3. نفس السعر + نفس المصدر + نفس البائع
    يحتفظ بالإعلان الأعلى ثقة.
    """
    seen_urls = set()
    seen_fingerprints = set()
    unique = []

    for l in listings:
        url = l.get("url", "")
        price = l.get("price", 0)
        source = l.get("source", "")
        title = _normalize_title(l.get("listedAs", ""))
        seller = l.get("sellerName", "")

        # فلتر 1: URL مكرر
        if url and url in seen_urls:
            continue

        # فلتر 2: بصمة (سعر + عنوان مختصر + مصدر)
        fp = f"{price}:{title[:30]}:{source}"
        if fp in seen_fingerprints:
            continue

        # فلتر 3: نفس السعر + نفس المصدر + نفس البائع
        fp2 = f"{price}:{source}:{seller}"
        if seller and fp2 in seen_fingerprints:
            continue

        if url:
            seen_urls.add(url)
        seen_fingerprints.add(fp)
        if seller:
            seen_fingerprints.add(fp2)
        unique.append(l)

    return unique


def _normalize_title(title: str) -> str:
    """ينظّف العنوان للمقارنة"""
    return re.sub(r"\s+", " ", (title or "").lower().strip())


# ══════════════════════════════════════════════════════════════════
#  3. OUTLIER REJECTION — رفض الأسعار غير المنطقية
# ══════════════════════════════════════════════════════════════════

def reject_outliers(listings: list[dict], msrp: int = 0,
                    low_pct: float = 0.70, high_pct: float = 1.35) -> list[dict]:
    """
    يرفض الأسعار خارج النطاق المنطقي.

    إذا MSRP معروف: يقبل MSRP × low_pct → MSRP × high_pct
    إذا MSRP=0: يستخدم IQR (interquartile range) لحذف الشاذ
    """
    if not listings:
        return []

    prices = [l["price"] for l in listings if l.get("price", 0) > 0]
    if not prices:
        return listings

    if msrp and msrp > 0:
        lo = int(msrp * low_pct)
        hi = int(msrp * high_pct)
        return [l for l in listings if lo <= l.get("price", 0) <= hi or l.get("price", 0) == 0]

    # IQR-based outlier detection
    if len(prices) < 4:
        return listings  # لا يكفي للتحليل الإحصائي

    sorted_p = sorted(prices)
    q1 = sorted_p[len(sorted_p) // 4]
    q3 = sorted_p[3 * len(sorted_p) // 4]
    iqr = q3 - q1
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr

    return [l for l in listings if lo <= l.get("price", 0) <= hi or l.get("price", 0) == 0]


# ══════════════════════════════════════════════════════════════════
#  4. TRIM BUCKETING — توزيع الإعلانات على الفئات
# ══════════════════════════════════════════════════════════════════
def bucket_listings_by_trim(listings: list[dict], brand: str, model: str, year: int,
                            dynamic_trims: list = None) -> dict:
    """
    يوزّع قائمة الإعلانات على buckets حسب الفئة.
    ✅ يُنشئ bucket لكل فئة من get_trims مسبقاً — حتى لو ما في إعلانات.
    """
    # ── 1. أنشئ buckets فارغة لكل فئة معرّفة مسبقاً ──────────
    configured_trims = get_trims(brand, model, year)
    buckets: dict[str, dict] = {}

    for t in configured_trims:
        buckets[t.name] = {
            "trim_info": {
                "name": t.name,
                "name_ar": t.name_ar,
                "id": t.id,
                "msrp": t.msrp,
                "engine": t.engine,
            },
            "listings": [],
            "match_stats": {},
        }

    match_stats: dict[str, dict] = defaultdict(lambda: defaultdict(int))

    # ── 2. صنّف كل إعلان وأضفه للـ bucket المناسب ────────────
    for listing in listings:
        match = classify_listing(listing, brand, model, year, dynamic_trims)
        print(f"  Matched listing «{listing.get('listedAs', '')}» to trim «{match.trim_name}» "
              f"with confidence {match.confidence:.2f} using {match.match_method}")

        listing["matchedTrim"]     = match.trim_name
        listing["matchReason"]     = match.match_detail
        listing["matchConfidence"] = (
            "high"   if match.confidence > 0.85 else
            "medium" if match.confidence > 0.60 else
            "low"
        )
        listing["matchMethod"] = match.match_method

        trim_key = match.trim_name

        # ── إذا جاءت فئة من dynamic_trims غير موجودة في الـ config أضفها ──
        if trim_key not in buckets:
            buckets[trim_key] = {
                "trim_info": {
                    "name": match.trim_name,
                    "name_ar": match.trim_name_ar,
                    "id": match.trim_id,
                    "msrp": match.msrp,
                    "engine": match.engine,
                },
                "listings": [],
                "match_stats": {},
            }

        buckets[trim_key]["listings"].append(listing)
        match_stats[trim_key][match.match_method] += 1

    # ── 3. أضف إحصائيات المطابقة ─────────────────────────────
    for key in buckets:
        buckets[key]["match_stats"] = dict(match_stats.get(key, {}))

    return buckets

def build_trims_response(buckets: dict, brand: str, model: str, year: int) -> list[dict]:
    """
    يحوّل buckets إلى الشكل النهائي المطلوب من الـ API:
      trims: [{ officialName, officialMSRP, listings, priceAnalysis, ... }]

    مع:
      - الحفاظ على جميع الفئات من get_trims حتى لو فارغة
      - حذف المكررات داخل كل فئة
      - رفض الشاذ (outliers) حسب MSRP
      - حساب priceAnalysis
    """
    trims_out = []

    # ── 1. ابدأ بالفئات الرسمية من get_trims مرتبة حسب MSRP ──
    configured_trims = get_trims(brand, model, year)
    configured_names = [t.name for t in configured_trims]

    # الفئات الرسمية أولاً (مرتبة حسب MSRP تنازلياً)
    official_keys = sorted(
        [k for k in buckets.keys() if k in configured_names],
        key=lambda k: buckets[k]["trim_info"].get("msrp", 0),
        reverse=True
    )

    # الفئات غير الرسمية (dynamic_trims أو Unknown) بعدها
    extra_keys = [k for k in buckets.keys() if k not in configured_names]

    sorted_keys = official_keys + extra_keys

    print(f"Sorted trim keys: {sorted_keys}")

    # ── 2. حساب النطاق السعري من الفئات المعروفة ──────────────
    known_msrps = [
        buckets[k]["trim_info"]["msrp"]
        for k in official_keys
        if buckets[k]["trim_info"].get("msrp", 0) > 0
    ]
    model_price_floor = int(min(known_msrps) * 0.70) if known_msrps else 0
    model_price_ceil  = int(max(known_msrps) * 1.35) if known_msrps else 0

    for trim_key in sorted_keys:
        bucket = buckets[trim_key]
        info   = bucket["trim_info"]
        listings = bucket["listings"]

        # ── حذف المكررات ────────────────────────────────────
        listings = deduplicate_listings(listings)

        # ── رفض الشاذ ───────────────────────────────────────
        listings = reject_outliers(listings, info.get("msrp", 0))

        # ── فلتر إضافي لـ Unknown ────────────────────────────
        if trim_key == "Unknown" and model_price_floor > 0:
            listings = [
                l for l in listings
                if model_price_floor <= l.get("price", 0) <= model_price_ceil
                or l.get("price", 0) == 0
            ]

        # ── حساب priceAnalysis ──────────────────────────────
        prices = [l["price"] for l in listings if l.get("price", 0) > 0]
        msrp   = info.get("msrp", 0)

        if prices:
            market_avg = int(sum(prices) / len(prices))
            vs_pct     = round((market_avg - msrp) / msrp * 100, 1) if msrp else 0
        else:
            market_avg = 0
            vs_pct     = 0

        trim_obj = {
            "officialName":   info["name"],
            "officialNameAr": info.get("name_ar", info["name"]),
            "officialMSRP":   msrp,
            "engine":         info.get("engine", ""),
            "commonAliases":  [],
            "listings":       listings,
            "priceAnalysis": {
                "marketMin":    min(prices) if prices else 0,
                "marketMax":    max(prices) if prices else 0,
                "marketAvg":    market_avg,
                "vsOfficialPct": vs_pct,
                "trend":        "stable",
                "listingCount": len(prices),
            },
            "matchStats": bucket.get("match_stats", {}),
        }

        trims_out.append(trim_obj)

    return trims_out
# ══════════════════════════════════════════════════════════════════
#  5. MAIN ENTRY — الدالة الرئيسية
# ══════════════════════════════════════════════════════════════════

def classify_and_structure(raw_listings: list[dict],
                           brand: str, model: str, year: int,
                           dynamic_trims: list = None,
                           ai_data: dict = None) -> dict:
    """
    الدالة الرئيسية: تأخذ الإعلانات الخام وتُرجع بنية JSON كاملة.

    المنطق:
      1. صنّف كل إعلان حسب الفئة
      2. احذف المكررات
      3. ارفض الشاذ
      4. ادمج مع بيانات AI (إن وجدت)
      5. أرجع البنية النهائية

    Parameters:
      raw_listings: الإعلانات من الـ scrapers
      brand, model, year: معلومات السيارة
      dynamic_trims: فئات من AI أو scrape (اختياري)
      ai_data: بيانات AI fallback (اختياري — للدمج)
    """
    # ── تصنيف وتوزيع ────────────────────────────────────────
    buckets = bucket_listings_by_trim(raw_listings, brand, model, year, dynamic_trims)
    # print(f"buckets data : {buckets} ")
    # ── دمج مع AI (إذا وجد) ─────────────────────────────────
    if ai_data and ai_data.get("trims"):
        _merge_ai_trims(buckets, ai_data, brand, model, year)

    # ── بناء الاستجابة النهائية ──────────────────────────────
    # print(f"buckets data after _merge_ai_trims : {buckets} ")
    trims = build_trims_response(buckets, brand, model, year)
   
    # ✅ الآن: أبقِ جميع الفئات من get_trims حتى لو فارغة
    # احذف فقط Unknown الفارغة (مش فئة رسمية)
    # trims = [t for t in trims if t["listings"] or (t["officialMSRP"] > 0 and t["officialName"] != "Unknown")]
    # print(f"trims after build_trims_response : {trims} ")
    # ── بناء الهيكل النهائي ──────────────────────────────────
    all_prices = []
    for t in trims:
        all_prices.extend(l["price"] for l in t["listings"] if l.get("price", 0) > 0)

    result = {
        "vehicle": f"{year} {brand} {model}",
        "brand": brand, "model": model, "year": year,
        "officialPriceRange": {
            "min": min(all_prices) if all_prices else 0,
            "max": max(all_prices) if all_prices else 0,
        },
        "trims": trims,
    }

    # ── نسخ حقول AI إضافية (إن وجدت) ────────────────────────
    if ai_data:
        for key in ("marketInsight", "priceHistory", "competitorAnalysis"):
            if key in ai_data:
                result[key] = ai_data[key]

    return result


def _merge_ai_trims(buckets: dict, ai_data: dict, brand: str, model: str, year: int):
    """
    يدمج فئات AI في الـ buckets الموجودة.
    يضيف فئات AI جديدة لم تظهر في الإعلانات الحقيقية.
    ينقل الإعلانات المصنّفة AI من فئة لأخرى إذا تطابقت مع فئة scrape.
    """
    for ai_trim in ai_data.get("trims", []):
        ai_name = ai_trim.get("officialName", "")
        if not ai_name:
            continue

        if ai_name in buckets:
            # الفئة موجودة — أضف إعلانات AI التي لم تأت من scrape
            existing_fps = {
                f"{l.get('price',0)}:{l.get('source','')}"
                for l in buckets[ai_name]["listings"]
            }
            for ai_listing in ai_trim.get("listings", []):
                fp = f"{ai_listing.get('price',0)}:{ai_listing.get('source','')}"
                if fp not in existing_fps:
                    ai_listing["matchMethod"] = "ai_fallback"
                    ai_listing["matchConfidence"] = ai_listing.get("matchConfidence", "medium")
                    ai_listing["matchReason"] = "بيانات AI"
                    buckets[ai_name]["listings"].append(ai_listing)
        else:
            # فئة جديدة من AI — أضفها
            buckets[ai_name] = {
                "trim_info": {
                    "name": ai_name,
                    "name_ar": ai_trim.get("officialNameAr", ai_name),
                    "id": "",
                    "msrp": ai_trim.get("officialMSRP", 0),
                    "engine": ai_trim.get("engine", ""),
                },
                "listings": ai_trim.get("listings", []),
                "match_stats": {"ai_fallback": len(ai_trim.get("listings", []))},
            }
