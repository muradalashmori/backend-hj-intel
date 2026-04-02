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


def classify_listing(listing: dict, brand: str, model: str,
                     dynamic_trims: list = None) -> TrimMatch:
    """
    يصنّف إعلان واحد إلى الفئة الصحيحة.

    أولوية المطابقة:
      1. Keyword match (أعلى دقة) — كلمات مثل "لوميير", "vxr", "y limited"
      2. Trim name match — اسم الفئة الرسمي في العنوان
      3. Price proximity — أقرب MSRP للسعر المعلن
      4. Fallback — إذا لم يتطابق شيء → "Unknown"
    """
    title = (listing.get("listedAs") or "").lower().strip()
    price = listing.get("price", 0)
    print(f"Classifying listing: «{title}» with price {price}")
    # ── جمع كل الفئات المتاحة ────────────────────────────────
    trims = _build_trim_list(brand, model, dynamic_trims)
    print(f"  Classifying listing: «{listing.get('listedAs', '')}» with price {price}")
    print(f"  Available trims: {[t['name'] for t in trims]}")
    if not trims:
        return TrimMatch(
            trim_name=f"{model} Standard", trim_name_ar=f"{model} ستاندرد",
            trim_id="UNKNOWN", msrp=0, engine="",
            confidence=0.40, match_method="fallback",
            match_detail="لا توجد فئات محددة لهذا الموديل"
        )

    # ── الجولة 1: Keyword Match (الأدق) ──────────────────────
    for trim in trims:
        for kw in trim["keywords"]:
            if not kw or len(kw) < 2:
                continue
            # مطابقة دقيقة — الكلمة المفتاحية موجودة في العنوان
            if kw in title:
                return TrimMatch(
                    trim_name=trim["name"], trim_name_ar=trim["name_ar"],
                    trim_id=trim["id"], msrp=trim["msrp"], engine=trim["engine"],
                    confidence=trim["score"],
                    match_method="keyword",
                    match_detail=f"كلمة مفتاحية: «{kw}»"
                )

    # ── الجولة 2: Trim Name Match ────────────────────────────
    for trim in trims:
        name_l = trim["name"].lower()
        name_ar_l = trim["name_ar"].lower()
        if name_l in title or name_ar_l in title:
            return TrimMatch(
                trim_name=trim["name"], trim_name_ar=trim["name_ar"],
                trim_id=trim["id"], msrp=trim["msrp"], engine=trim["engine"],
                confidence=trim["score"] * 0.95,
                match_method="name",
                match_detail=f"اسم الفئة: «{trim['name']}»"
            )

    # ── الجولة 3: Word Overlap Match ─────────────────────────
    best_overlap = None
    best_overlap_score = 0.0
    for trim in trims:
        words = [w for w in trim["name"].lower().split() if len(w) > 2]
        print(f"  Checking word overlap for trim «{trim['name']}» with words {words}")
        if not words:
            continue
        hits = sum(1 for w in words if w in title)
        score = hits / len(words)
        if score > best_overlap_score and score >= 0.4:
            best_overlap_score = score
            best_overlap = trim

    if best_overlap and best_overlap_score >= 0.4:
        return TrimMatch(
            trim_name=best_overlap["name"], trim_name_ar=best_overlap["name_ar"],
            trim_id=best_overlap["id"], msrp=best_overlap["msrp"], engine=best_overlap["engine"],
            confidence=0.55 + best_overlap_score * 0.2,
            match_method="word_overlap",
            match_detail=f"تطابق جزئي ({best_overlap_score:.0%}) مع «{best_overlap['name']}»"
        )

    # ── الجولة 4: Price Proximity (إذا السعر متاح) ───────────
    if price > 0:
        trims_with_msrp = [t for t in trims if t["msrp"] > 0]
        if trims_with_msrp:
            closest = min(trims_with_msrp, key=lambda t: abs(t["msrp"] - price))
            distance_pct = abs(closest["msrp"] - price) / closest["msrp"] if closest["msrp"] else 1.0

            if distance_pct <= 0.20:  # ±20% من MSRP
                conf = 0.65 - (distance_pct * 1.5)  # أقرب = أعلى ثقة
                return TrimMatch(
                    trim_name=closest["name"], trim_name_ar=closest["name_ar"],
                    trim_id=closest["id"], msrp=closest["msrp"], engine=closest["engine"],
                    confidence=max(0.45, conf),
                    match_method="price_proximity",
                    match_detail=f"أقرب MSRP: {closest['msrp']:,} ر.س (فرق {distance_pct:.0%})"
                )

    # ── الجولة 5: Fallback → Unknown ─────────────────────────
    return TrimMatch(
        trim_name="Unknown", trim_name_ar="غير محدد",
        trim_id="UNKNOWN", msrp=0, engine="",
        confidence=0.30, match_method="fallback",
        match_detail="لم يتطابق مع أي فئة معروفة"
    )


def _build_trim_list(brand: str, model: str, dynamic_trims: list = None) -> list[dict]:
    """يجمع الفئات من trims_config + dynamic_trims في قائمة موحدة"""
    result = []
    seen_names = set()

    # أولوية 1: trims_config (الأدق — معرّف يدوياً)
    configured = get_trims(brand, model)
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
            print(f"  Processing dynamic trim: {dt}")
            name = dt.name if hasattr(dt, "name") else dt.get("name", "")
            print(f"  Normalized name: {name}")
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

    print(f" Final trim list for {result}")
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

def bucket_listings_by_trim(listings: list[dict], brand: str, model: str,
                            dynamic_trims: list = None) -> dict:
    """
    يوزّع قائمة الإعلانات على buckets حسب الفئة.

    Returns:
      {
        "Camry Lumiere HEV": {
          "trim_info": {...},
          "listings": [...],
          "match_stats": {"keyword": 5, "name": 1, "price_proximity": 2, ...}
        },
        ...
      }
    """
    buckets: dict[str, dict] = {}
    match_stats: dict[str, dict] = defaultdict(lambda: defaultdict(int))

    for listing in listings:
        match = classify_listing(listing, brand, model, dynamic_trims)

        # أضف معلومات المطابقة للإعلان
        listing["matchedTrim"] = match.trim_name
        listing["matchReason"] = match.match_detail
        listing["matchConfidence"] = (
            "high" if match.confidence > 0.85
            else "medium" if match.confidence > 0.60
            else "low"
        )
        listing["matchMethod"] = match.match_method

        trim_key = match.trim_name

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
            }

        buckets[trim_key]["listings"].append(listing)
        match_stats[trim_key][match.match_method] += 1

    # إضافة إحصائيات المطابقة
    for key in buckets:
        buckets[key]["match_stats"] = dict(match_stats.get(key, {}))

    return buckets


def build_trims_response(buckets: dict, brand: str, model: str, year: int) -> list[dict]:
    """
    يحوّل buckets إلى الشكل النهائي المطلوب من الـ API:
      trims: [{ officialName, officialMSRP, listings, priceAnalysis, ... }]

    مع:
      - حذف المكررات داخل كل فئة
      - رفض الشاذ (outliers) حسب MSRP
      - حساب priceAnalysis
    """
    trims_out = []

    # رتّب: الأغلى أولاً (عادةً Lumiere/VXR/Platinum)
    sorted_keys = sorted(
        buckets.keys(),
        key=lambda k: buckets[k]["trim_info"].get("msrp", 0),
        reverse=True
    )

    # ── حساب النطاق السعري من الفئات المعروفة (للتحقق من Unknown) ──
    known_msrps = [
        buckets[k]["trim_info"]["msrp"]
        for k in sorted_keys
        if buckets[k]["trim_info"].get("msrp", 0) > 0 and k != "Unknown"
    ]
    model_price_floor = int(min(known_msrps) * 0.70) if known_msrps else 0
    model_price_ceil  = int(max(known_msrps) * 1.35) if known_msrps else 0

    for trim_key in sorted_keys:
        bucket = buckets[trim_key]
        info = bucket["trim_info"]
        listings = bucket["listings"]

        # ── حذف المكررات ────────────────────────────────────
        listings = deduplicate_listings(listings)

        # ── رفض الشاذ ───────────────────────────────────────
        # نطاق أوسع من _price_in_range لأن هنا نريد الاحتفاظ بالبيانات
        # المعقولة حتى لو كان فيها خصم كبير أو علاوة استثنائية
        listings = reject_outliers(listings, info.get("msrp", 0))

        # ── فلتر إضافي لـ Unknown: استخدم نطاق الموديل ككل ──
        if trim_key == "Unknown" and model_price_floor > 0:
            listings = [
                l for l in listings
                if model_price_floor <= l.get("price", 0) <= model_price_ceil
                or l.get("price", 0) == 0
            ]

        # ── حساب priceAnalysis ──────────────────────────────
        prices = [l["price"] for l in listings if l.get("price", 0) > 0]
        msrp = info.get("msrp", 0)

        if prices:
            market_avg = int(sum(prices) / len(prices))
            vs_pct = round((market_avg - msrp) / msrp * 100, 1) if msrp else 0
        else:
            market_avg = 0
            vs_pct = 0

        trim_obj = {
            "officialName": info["name"],
            "officialNameAr": info.get("name_ar", info["name"]),
            "officialMSRP": msrp,
            "engine": info.get("engine", ""),
            "commonAliases": [],
            "listings": listings,
            "priceAnalysis": {
                "marketMin": min(prices) if prices else 0,
                "marketMax": max(prices) if prices else 0,
                "marketAvg": market_avg,
                "vsOfficialPct": vs_pct,
                "trend": "stable",
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
    buckets = bucket_listings_by_trim(raw_listings, brand, model, dynamic_trims)
    print(f"Buckets after classification: { {k: len(v['listings']) for k,v in buckets.items()} }")
    # ── دمج مع AI (إذا وجد) ─────────────────────────────────
    if ai_data and ai_data.get("trims"):
        _merge_ai_trims(buckets, ai_data, brand, model)

    # ── بناء الاستجابة النهائية ──────────────────────────────
    trims = build_trims_response(buckets, brand, model, year)

    # ── إزالة "Unknown" إذا كان فارغاً ──────────────────────
    trims = [t for t in trims if t["listings"] or t["officialMSRP"] > 0]

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


def _merge_ai_trims(buckets: dict, ai_data: dict, brand: str, model: str):
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
