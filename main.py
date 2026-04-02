"""
HJ Motors — Price Intelligence Backend v3
Playwright HTML Scraper (primary) + httpx API fallback + Redis + AI fallback
"""

import asyncio, json, os, re, time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from trims_config import get_trims, get_all_configured, normalize_from_config, TrimDefinition
from trim_classifier import (
    classify_listing, classify_and_structure,
    bucket_listings_by_trim, build_trims_response,
    deduplicate_listings, reject_outliers,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Playwright scrapers ─────────────────────────────────────────
try:
    from scraper_playwright import (
        playwright_syarah, playwright_haraj,
        playwright_toyota_sa, playwright_lexus_sa, playwright_motory, playwright_yallamotor, PLAYWRIGHT_OK
    )
    #print(f"✅ Playwright scrapers loaded: {PLAYWRIGHT_OK}")
except ImportError as e:
    PLAYWRIGHT_OK = False
    #print(f"⚠️  scraper_playwright not found: {e}")
    async def playwright_syarah(q, **kw): return []
    async def playwright_haraj(q, **kw): return []
    async def playwright_toyota_sa(m, **kw): return []
    async def playwright_lexus_sa(m, **kw): return []
    async def playwright_yallamotor(q, **kw): return []
    async def playwright_motory(q, **kw): return []

# ── Optional: Redis ─────────────────────────────────────────────
try:
    import redis.asyncio as aioredis
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    _redis_client = None
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# ── Config ──────────────────────────────────────────────────────
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
SCRAPE_TIMEOUT    = int(os.getenv("SCRAPE_TIMEOUT", "20"))   # Playwright needs more time
CACHE_TTL         = int(os.getenv("CACHE_TTL", "3600"))
SOURCES_FILE      = Path(os.getenv("SOURCES_FILE", "/app/sources.json"))
_mem_cache: dict  = {}

# ── Default Sources ─────────────────────────────────────────────
DEFAULT_SOURCES = {
    "toyota.com.sa":  {"id":"toyota.com.sa",  "name":"Toyota.com.sa",  "name_ar":"تويوتا السعودية", "url":"https://www.toyota.com.sa",  "color":"#00C49A","enabled":True, "type":"playwright","priority":1,"search_url":"https://www.toyota.com.sa/en/models/{model}", "category":"official"},
    "lexus.com.sa":   {"id":"lexus.com.sa",   "name":"Lexus.com.sa",   "name_ar":"لكسัส",            "url":"https://www.lexus.com.sa",    "color":"#00C49A","enabled":True, "type":"playwright","priority":2,"search_url":"https://www.lexus.com.sa/en/models/{model}", "category":"official"},
    "ksa.Motory.com":     {"id":"ksa.Motory.com",     "name":"ksa.Motory.com",  "name_ar":"موتوري",          "url":"https://ksa.ksa.Motory.com.com",          "color":"#f5a623","enabled":True, "type":"playwright","priority":3,"search_url":"https://ksa.Motory.com.com/sa/new-cars/search?q={query}", "category":"new_cars"},
    "haraj.com.sa":      {"id":"haraj.com.sa",      "name":"Haraj.com.sa",   "name_ar":"حراج",            "url":"https://haraj.com.sa.com.sa",        "color":"#ff8055","enabled":True, "type":"playwright","priority":4,"search_url":"https://haraj.com.sa.com.sa/search/{query}",            "category":"marketplace"},
    "ksa.yallamotor.com": {"id":"ksa.yallamotor.com", "name":"ksa.yallamotor.com",     "name_ar":"يلا موتور",       "url":"https://www.ksa.yallamotor.com.com",  "color":"#a78bfa","enabled":True, "type":"playwright",    "priority":5,"search_url":"https://ksa.ksa.yallamotor.com.com/ar/new-cars?query={query}&country=sa", "category":"new_cars"},
    "syarah.com":     {"id":"syarah.com",     "name":"Syarah.com",     "name_ar":"سيارة",           "url":"https://syarah.com.com",          "color":"#4da6ff","enabled":True, "type":"playwright","priority":6,"search_url":"https://syarah.com.com/filters?text={query}",        "category":"marketplace"},
}

def _load_sources() -> dict:
    if SOURCES_FILE.exists():
        try:
            saved = json.loads(SOURCES_FILE.read_text())
            merged = {**DEFAULT_SOURCES}
            for sid, data in saved.items():
                merged[sid] = {**merged.get(sid, {}), **data}
            return merged
        except Exception as e:
            print(f"⚠️  sources.json: {e}")
    return dict(DEFAULT_SOURCES)

def _save_sources(store):
    try:
        SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        SOURCES_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"⚠️  save sources: {e}")

sources_store: dict = _load_sources()

# ── Redis / cache ───────────────────────────────────────────────
async def _get_redis():
    global _redis_client
    if not REDIS_AVAILABLE: return None
    if _redis_client is None:
        try:
            _redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
            await _redis_client.ping()
        except:
            _redis_client = None
    return _redis_client

async def cache_get(key):
    r = await _get_redis()
    if r:
        try:
            val = await r.get(f"hj:{key}")
            if val: return {**json.loads(val), "fromCache": True}
        except: pass
    if key in _mem_cache:
        ts, data = _mem_cache[key]
        if time.time() - ts < CACHE_TTL:
            return {**data, "fromCache": True, "cacheAge": int(time.time()-ts)}
    return None

async def cache_set(key, data, ttl=CACHE_TTL):
    r = await _get_redis()
    if r:
        try:
            value = json.dumps(data, ensure_ascii=False)
            redis_key = f"hj:{key}"

            if ttl is None:
                await r.set(redis_key, value)  # بدون انتهاء
            else:
                await r.setex(redis_key, ttl, value)  # مع انتهاء
        except:
            pass

    _mem_cache[key] = (time.time(), data)

async def cache_clear():
    r = await _get_redis()
    if r:
        try:
            keys = await r.keys("hj:*")
            if keys: await r.delete(*keys)
        except: pass
    _mem_cache.clear()

# ══════════════════════════════════════════════════════════════════
#  PRICE TREND — weekly snapshots stored in Redis
#  Key pattern:  hj:snap:{brand}:{model}:{year}:{trim_name}:{YYYY-WW}
#  Retention:    13 weeks (≈ 3 months of history)
# ══════════════════════════════════════════════════════════════════

SNAP_RETENTION_WEEKS = 13
SNAP_TTL = 60 * 60 * 24 * 7 * SNAP_RETENTION_WEEKS   # 91 days in seconds

def _week_key() -> str:
    """Returns ISO year-week string e.g. '2026-12'"""
    from datetime import date
    d = date.today().isocalendar()
    return f"{d[0]}-{d[1]:02d}"

def _prev_week_key(n: int = 1) -> str:
    """Returns week key for N weeks ago"""
    from datetime import date, timedelta
    d = (date.today() - timedelta(weeks=n)).isocalendar()
    return f"{d[0]}-{d[1]:02d}"

async def snapshot_save(brand: str, model: str, year: int, trim_name: str,
                         min_p: int, avg_p: int, max_p: int, count: int):
    """Save this week's price snapshot for a trim."""
    r = await _get_redis()
    if not r:
        return
    wk  = _week_key()
    key = f"hj:snap:{brand.lower()}:{model.lower()}:{year}:{trim_name.lower().replace(' ','_')}:{wk}"
    payload = json.dumps({"min": min_p, "avg": avg_p, "max": max_p,
                           "count": count, "week": wk, "saved_at": int(time.time())},
                          ensure_ascii=False)
    try:
        await r.setex(key, SNAP_TTL, payload)
    except Exception as e:
        print(f"snapshot_save error: {e}")


async def snapshot_get_history(brand: str, model: str, year: int,
                                trim_name: str, weeks: int = 6) -> list[dict]:
    """
    Returns up to `weeks` weeks of price history for a trim, newest first.
    Each item: {"week":"2026-12","min":x,"avg":y,"max":z,"count":n}
    """
    r = await _get_redis()
    if not r:
        return []
    results = []
    slug = trim_name.lower().replace(" ", "_")
    prefix = f"hj:snap:{brand.lower()}:{model.lower()}:{year}:{slug}:"
    for n in range(weeks):
        wk  = _prev_week_key(n)
        key = f"{prefix}{wk}"
        try:
            raw = await r.get(key)
            if raw:
                results.append(json.loads(raw))
        except:
            pass
    return results


async def snapshot_calc_trend(history: list[dict]) -> dict:
    """
    Given a list of weekly snapshots (newest first), returns:
    {
      "direction": "up"|"down"|"stable",
      "change_pct": float,          # % change vs 4 weeks ago
      "change_sar": int,            # SAR change vs 4 weeks ago
      "weeks_of_data": int,
      "label": "Arabic text"
    }
    """
    if len(history) < 2:
        return {"direction": "stable", "change_pct": 0.0,
                "change_sar": 0, "weeks_of_data": len(history), "label": "بيانات غير كافية"}

    latest   = history[0]["avg"]
    compare  = history[min(3, len(history)-1)]["avg"]   # ~4 weeks ago
    if compare == 0:
        return {"direction": "stable", "change_pct": 0.0,
                "change_sar": 0, "weeks_of_data": len(history), "label": "بيانات غير كافية"}

    change_sar = latest - compare
    change_pct = round(change_sar / compare * 100, 1)

    if change_pct > 1.5:
        direction, label = "up",   f"↑ ارتفع {abs(change_pct)}% خلال 4 أسابيع"
    elif change_pct < -1.5:
        direction, label = "down", f"↓ انخفض {abs(change_pct)}% خلال 4 أسابيع"
    else:
        direction, label = "stable", "← مستقر خلال 4 أسابيع"

    return {"direction": direction, "change_pct": change_pct,
            "change_sar": change_sar, "weeks_of_data": len(history), "label": label}


# ══════════════════════════════════════════════════════════════════
#  DAYS ON MARKET — track listing first-seen date
#  Key: hj:dom:{source}:{listing_url_hash}
#  Value: {"first_seen": epoch, "url": url, "trim": trim_name}
# ══════════════════════════════════════════════════════════════════

DOM_TTL = 60 * 60 * 24 * 90   # 90 days

async def dom_record(source: str, url: str, trim_name: str):
    """Record first time we see a listing URL. Ignored if already seen."""
    r = await _get_redis()
    if not r or not url:
        return
    import hashlib
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    key = f"hj:dom:{source}:{url_hash}"
    try:
        exists = await r.exists(key)
        if not exists:
            await r.setex(key, DOM_TTL, json.dumps({
                "first_seen": int(time.time()),
                "url": url,
                "trim": trim_name,
                "source": source
            }, ensure_ascii=False))
    except Exception as e:
        print(f"dom_record error: {e}")


async def dom_get_age_days(source: str, url: str) -> int | None:
    """Returns how many days ago we first saw this listing, or None if unknown."""
    r = await _get_redis()
    if not r or not url:
        return None
    import hashlib
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    key = f"hj:dom:{source}:{url_hash}"
    try:
        raw = await r.get(key)
        if raw:
            data = json.loads(raw)
            return max(0, int((time.time() - data["first_seen"]) / 86400))
    except:
        pass
    return None


async def dom_avg_for_trim(brand: str, model: str, trim_name: str,
                            source: str = "") -> dict:
    """
    Returns avg/min/max days on market for a trim across all tracked listings.
    Useful for supply-pressure scoring.
    """
    r = await _get_redis()
    if not r:
        return {"avg": None, "min": None, "max": None, "count": 0}

    pattern = f"hj:dom:{source}:*" if source else "hj:dom:*:*"
    ages = []
    try:
        keys = await r.keys(pattern)
        for k in keys[:200]:   # cap scan
            raw = await r.get(k)
            if not raw:
                continue
            d = json.loads(raw)
            if trim_name.lower() in d.get("trim", "").lower():
                age = max(0, int((time.time() - d["first_seen"]) / 86400))
                ages.append(age)
    except:
        pass

    if not ages:
        return {"avg": None, "min": None, "max": None, "count": 0}

    return {
        "avg":   round(sum(ages) / len(ages), 1),
        "min":   min(ages),
        "max":   max(ages),
        "count": len(ages),
        "label": f"متوسط {round(sum(ages)/len(ages),0):.0f} يوم في السوق"
    }


# ══════════════════════════════════════════════════════════════════
#  BUNDLE PRICING — إضافات بدل تخفيض مباشر
# ══════════════════════════════════════════════════════════════════

# تعديل هذا القاموس حسب تكاليف الإضافات الفعلية لديك
BUNDLE_ADDONS = {
    "عازل حراري نانو":          {"cost": 350,  "value": 1500, "label": "عازل حراري نانو سيراميك"},
    "تشميع بدي":                 {"cost": 150,  "value": 700,  "label": "تشميع وحماية البدي"},
    "حماية مقدمة السيارة PPF":  {"cost": 400,  "value": 1800, "label": "حماية PPF المقدمة"},
    "صيانة أولى مجانية":        {"cost": 200,  "value": 800,  "label": "صيانة أولى مجانية"},
    "تأمين السنة الأولى":        {"cost": 800,  "value": 1800, "label": "تأمين شامل السنة الأولى"},
    "أطراف أبواب وبخاخات":      {"cost": 80,   "value": 400,  "label": "حماية أطراف الأبواب"},
    "ريموت إضافي":               {"cost": 120,  "value": 500,  "label": "ريموت بديل إضافي"},
}

def bundle_vs_discount(discount_sar: int,
                        addons: list[str] | None = None) -> dict:
    """
    يقارن بين خفض السعر مباشرة أو تقديم إضافات بنفس القيمة الظاهرية.

    مثال:
        bundle_vs_discount(1500, ["عازل حراري نانو", "تشميع بدي"])
        →  التكلفة الفعلية للإضافات = 500 ريال
        →  وفّرت = 1000 ريال مقارنة بالتخفيض المباشر

    Returns:
        {
          "discount_cost":  1500,   # ما ستخسره لو خفضت السعر
          "bundle_cost":    500,    # تكلفة الإضافات عليك
          "saving":         1000,   # الفرق = ما وفّرته
          "bundle_value":   2200,   # القيمة الظاهرية للعميل
          "addons":         [...],
          "recommendation": "Arabic text"
        }
    """
    if addons is None:
        # اختر أفضل تشكيلة تغطي المبلغ المطلوب بأقل تكلفة
        selected, total_value, total_cost = [], 0, 0
        for name, info in sorted(BUNDLE_ADDONS.items(), key=lambda x: x[1]["value"] / x[1]["cost"], reverse=True):
            if total_value >= discount_sar:
                break
            selected.append(name)
            total_value += info["value"]
            total_cost  += info["cost"]
        addons = selected

    total_cost  = sum(BUNDLE_ADDONS[a]["cost"]  for a in addons if a in BUNDLE_ADDONS)
    total_value = sum(BUNDLE_ADDONS[a]["value"] for a in addons if a in BUNDLE_ADDONS)
    saving      = discount_sar - total_cost
    saving_pct  = round(saving / discount_sar * 100) if discount_sar else 0

    addon_details = [
        {
            "name":  a,
            "label": BUNDLE_ADDONS[a]["label"],
            "cost":  BUNDLE_ADDONS[a]["cost"],
            "value": BUNDLE_ADDONS[a]["value"],
        }
        for a in addons if a in BUNDLE_ADDONS
    ]

    if saving > 0:
        rec = (f"بدل تخفيض {discount_sar:,} ريال مباشرة، قدّم إضافات بقيمة ظاهرية "
               f"{total_value:,} ريال بتكلفة فعلية {total_cost:,} ريال فقط — "
               f"توفير {saving:,} ريال ({saving_pct}%) على هامشك.")
    else:
        rec = f"التخفيض المباشر بـ {discount_sar:,} ريال أفضل في هذه الحالة."

    return {
        "discount_cost":  discount_sar,
        "bundle_cost":    total_cost,
        "bundle_value":   total_value,
        "saving":         saving,
        "saving_pct":     saving_pct,
        "addons":         addon_details,
        "recommendation": rec,
    }


# ══════════════════════════════════════════════════════════════════
#  DEALER PRICING ENGINE
#  يحسب سعر البيع المقترح للوكيل بناءً على:
#  1. أسعار السوق (min / avg / max)
#  2. كمية العرض (supplyStats)  ← هذا ما كان مفقوداً
#  3. نسبة جديد vs مستعمل
#  4. اتجاه السعر (priceTrend)
#  5. السعر الرسمي كمرساة
# ══════════════════════════════════════════════════════════════════

def calc_dealer_price(
    msrp:         int,          # السعر الرسمي من الوكيل ALJ
    market_min:   int,          # أدنى سعر في السوق
    market_avg:   int,          # متوسط السوق
    market_max:   int,          # أعلى سعر في السوق
    total_listings: int,        # إجمالي الإعلانات
    new_listings:   int,        # إعلانات جديدة فقط
    trend_direction: str = "stable",   # "up" | "down" | "stable"
    dom_avg:    float | None = None,   # متوسط أيام الإعلان في السوق
) -> dict:
    """
    يرجع:
    {
      "suggested":     74500,   السعر المقترح (نقطة وسط)
      "range_low":     73000,   أدنى حد معقول
      "range_high":    76000,   أعلى حد معقول
      "supply_score":  "low",   low | medium | high (كمية العرض)
      "pressure":      -1,      -2=ضغط شديد, -1=ضغط, 0=متوازن, +1=فرصة, +2=فرصة ذهبية
      "adjustments":   [...],   قائمة التعديلات المطبّقة ومبررها
      "logic":         "Arabic" شرح القرار
    }
    """
    if not market_avg or not msrp:
        return {"suggested": 0, "range_low": 0, "range_high": 0,
                "supply_score": "unknown", "pressure": 0,
                "adjustments": [], "logic": "بيانات غير كافية"}

    adjustments = []
    base = market_avg   # نبدأ من متوسط السوق

    # ── 1. supply pressure ──────────────────────────────────────
    # نحسب نسبة الجديدة فقط (منافسينا الحقيقيين كوكلاء)
    new_pct = (new_listings / total_listings * 100) if total_listings > 0 else 50

    if total_listings == 0:
        supply_score = "unknown"
        pressure     = 0
    elif new_listings <= 2:
        supply_score = "scarce"   # شحيح جداً
        pressure     = 2
        adj = int(market_avg * 0.025)   # +2.5%
        base += adj
        adjustments.append({
            "factor":  "supply_scarce",
            "label":   f"عرض شحيح جداً (جديدة: {new_listings} فقط) → +{adj:,}",
            "delta":   adj,
        })
    elif new_listings <= 5:
        supply_score = "low"      # منخفض
        pressure     = 1
        adj = int(market_avg * 0.015)   # +1.5%
        base += adj
        adjustments.append({
            "factor":  "supply_low",
            "label":   f"عرض منخفض (جديدة: {new_listings}) → +{adj:,}",
            "delta":   adj,
        })
    elif new_listings <= 12:
        supply_score = "medium"   # متوسط
        pressure     = 0
        adjustments.append({
            "factor":  "supply_medium",
            "label":   f"عرض متوازن (جديدة: {new_listings}) → لا تعديل",
            "delta":   0,
        })
    elif new_listings <= 25:
        supply_score = "high"     # مرتفع
        pressure     = -1
        adj = int(market_avg * 0.015)   # -1.5%
        base -= adj
        adjustments.append({
            "factor":  "supply_high",
            "label":   f"عرض مرتفع (جديدة: {new_listings}) → −{adj:,}",
            "delta":   -adj,
        })
    else:
        supply_score = "very_high"   # مرتفع جداً
        pressure     = -2
        adj = int(market_avg * 0.030)   # -3%
        base -= adj
        adjustments.append({
            "factor":  "supply_very_high",
            "label":   f"عرض مرتفع جداً (جديدة: {new_listings}) → −{adj:,}",
            "delta":   -adj,
        })

    # ── 2. new vs used ratio ────────────────────────────────────
    # إذا غالبية الإعلانات مستعملة، المنافسة الحقيقية أقل
    if total_listings > 0 and new_pct < 30:
        adj = int(market_avg * 0.010)
        base += adj
        adjustments.append({
            "factor":  "mostly_used",
            "label":   f"معظم الإعلانات مستعملة ({new_pct:.0f}% جديدة) → +{adj:,}",
            "delta":   adj,
        })

    # ── 3. price trend ──────────────────────────────────────────
    if trend_direction == "up":
        adj = int(market_avg * 0.010)
        base += adj
        adjustments.append({
            "factor":  "trend_up",
            "label":   f"السوق في ارتفاع → +{adj:,}",
            "delta":   adj,
        })
    elif trend_direction == "down":
        adj = int(market_avg * 0.010)
        base -= adj
        adjustments.append({
            "factor":  "trend_down",
            "label":   f"السوق في انخفاض (سعّر تحسباً) → −{adj:,}",
            "delta":   -adj,
        })

    # ── 4. days on market ───────────────────────────────────────
    # إعلانات تبقى طويلاً = ضغط إضافي على السعر
    if dom_avg is not None:
        if dom_avg <= 7:
            adj = int(market_avg * 0.010)
            base += adj
            adjustments.append({
                "factor":  "dom_fast",
                "label":   f"إعلانات تُباع سريعاً (متوسط {dom_avg:.0f} أيام) → +{adj:,}",
                "delta":   adj,
            })
        elif dom_avg >= 30:
            adj = int(market_avg * 0.015)
            base -= adj
            adjustments.append({
                "factor":  "dom_slow",
                "label":   f"إعلانات تبقى طويلاً (متوسط {dom_avg:.0f} يوم) → −{adj:,}",
                "delta":   -adj,
            })

    # ── 5. floor: لا تبيع أقل من market_min + 500 للجديدة ───────
    floor = market_min + 500
    if base < floor:
        adjustments.append({
            "factor":  "floor",
            "label":   f"لا تبيع أقل من أدنى السوق+500 ({floor:,}) → تعديل للأعلى",
            "delta":   floor - base,
        })
        base = floor

    # ── 6. ceiling: لا تتجاوز market_max كثيراً ─────────────────
    ceiling = int(market_max * 1.03)
    if base > ceiling:
        adjustments.append({
            "factor":  "ceiling",
            "label":   f"أعلى من سقف السوق → ضبط إلى {ceiling:,}",
            "delta":   ceiling - base,
        })
        base = ceiling

    # ── الرنج المقترح ±2% ───────────────────────────────────────
    range_low  = int(base * 0.98)
    range_high = int(base * 1.02)

    # ── شرح القرار بالعربي ──────────────────────────────────────
    supply_labels = {
        "scarce":    "شحيح جداً",
        "low":       "منخفض",
        "medium":    "متوازن",
        "high":      "مرتفع",
        "very_high": "مرتفع جداً",
        "unknown":   "غير محدد",
    }
    pressure_labels = {
        2:  "فرصة ذهبية — الطلب أعلى من العرض",
        1:  "فرصة — العرض منخفض نسبياً",
        0:  "متوازن — سعّر قريب من المتوسط",
        -1: "ضغط تنافسي — العرض مرتفع",
        -2: "ضغط شديد — نافس بالخدمة لا السعر",
    }

    logic = (
        f"متوسط السوق {market_avg:,} ريال | "
        f"عرض الجديدة: {supply_labels[supply_score]} ({new_listings} إعلان) | "
        f"الضغط: {pressure_labels.get(pressure, '')} | "
        f"السعر المقترح: {int(base):,} ريال"
    )

    return {
        "suggested":     int(base),
        "range_low":     range_low,
        "range_high":    range_high,
        "supply_score":  supply_score,
        "pressure":      pressure,
        "new_listings":  new_listings,
        "total_listings": total_listings,
        "new_pct":       round(new_pct, 0),
        "adjustments":   adjustments,
        "logic":         logic,
    }


def _attach_dealer_pricing(data: dict):
    """
    يُضاف بعد _attach_source_stats.
    يضع trim["dealerPricing"] = calc_dealer_price(...)
    """
    for trim in data.get("trims", []):
        pa      = trim.get("priceAnalysis", {})
        ss      = trim.get("supplyStats", {})
        trend   = trim.get("priceTrend",  {})
        dom     = trim.get("daysOnMarket", {})

        msrp         = trim.get("officialMSRP", 0)
        market_min   = pa.get("marketMin", 0)
        market_avg   = pa.get("marketAvg", 0)
        market_max   = pa.get("marketMax", 0)
        total        = ss.get("totalListings", 0)
        new_l        = ss.get("newListings", 0)
        trend_dir    = trend.get("direction", "stable")
        dom_avg      = dom.get("avg", None)

        trim["dealerPricing"] = calc_dealer_price(
            msrp=msrp,
            market_min=market_min,
            market_avg=market_avg,
            market_max=market_max,
            total_listings=total,
            new_listings=new_l,
            trend_direction=trend_dir,
            dom_avg=dom_avg,
        )


# ── Pydantic ────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    brand: str
    model: str
    year: int
    anthropic_key: str
    source_ids: Optional[list[str]] = None
    new_only: bool = True   # افتراضي: جديدة فقط (يستثني المستعملة من Haraj)
    claude_ai: bool = True  # افتراضي: عدم استخدام الذكاء الاصطناعي

class SourceUpdate(BaseModel):
    name: Optional[str] = None
    name_ar: Optional[str] = None
    url: Optional[str] = None
    search_url: Optional[str] = None
    enabled: Optional[bool] = None
    color: Optional[str] = None
    priority: Optional[int] = None

class NewSource(BaseModel):
    id: str
    name: str
    name_ar: str
    url: str
    search_url: str
    color: str = "#6B7280"
    type: str = "httpx"
    priority: int = 99

# ── Car Catalog Models ──────────────────────────────────────────
class Brand(BaseModel):
    BrandID: str = None
    DescriptionAr: Optional[str] = None
    DescriptionEn: Optional[str] = None
    Description: Optional[str] = None

class Group(BaseModel):
    ListTreeGroups: str  = None
    brandID: str = None
    Year: str = None
    DescriptionAr: str = None
    DescriptionEn: str = None
    Description: str = None
    productGroupID: str = None



class ModelType(BaseModel):
    ModelCode: str = None
    guid: str = None
    ProductTypeId: str = None
    Model: str = None
    descriptionAr: str = None
    descriptionEn: str = None
    Description: str = None
    productGroupID: str = None
    Image: Optional[str] = None

class CarCatalog(BaseModel):
    brands: list[Brand]
    groups: list[Group] = []
    modelTypes: list[ModelType] = []

# ── App ─────────────────────────────────────────────────────────
app = FastAPI(title="HJ Motors Price Intelligence", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


def transform_catalog(data):
    return {
        "brands": [
            {
                "BrandID": b.get("BrandID") or b.get("brandID") or "",
                "DescriptionAr": b.get("Description") or "",
                "DescriptionEn": b.get("Description") or "",
                "Description": b.get("Description") or ""
            }
            for b in data.get("brands", [])
        ],

        "groups": [
            {
                "ListTreeGroups": g.get("ListTreeGroups") or "",
                "brandID": g.get("BrandId") or "",
                "Year": g.get("Year") or "",
                "DescriptionAr": g.get("DescriptionAr") or "",
                "DescriptionEn": g.get("DescriptionEn") or "",
                "Description": g.get("Description") or g.get("DescriptionEn") or g.get("DescriptionAr") or "",
                "productGroupID": g.get("ProductGroupId") or g.get("productGroupID") or "",
            }
            for g in data.get("groups", [])
        ],

        "modelTypes": [
            {
                "ModelCode": m.get("ModelCode") or "",
                "guid": m.get("guid") or "",
                "ProductTypeId": m.get("ProductTypeId") or "",
                "Model": m.get("Model") or "",
                "descriptionAr": m.get("descriptionAr") or "",
                "descriptionEn": m.get("ShortDescriptionEn") or m.get("ShortDescriptionEn") or "",
                "Description": m.get("Description") or m.get("descriptionEn") or m.get("descriptionAr") or"",
                "productGroupID": m.get("ProductGroupId") or m.get("productGroupID") or "",
                "Image": m.get("Image") or None
            }
            for m in data.get("modelTypes", [])
        ]
    }
# ── Car Catalog Functions ───────────────────────────────────────
async def fetch_car_catalog() -> CarCatalog:
    url = "https://appw.hassanjameelapp.com/en/api/finance/index"
    
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()

        fixed_data = transform_catalog(data)

        return CarCatalog(**fixed_data)

# ── Source endpoints ────────────────────────────────────────────
@app.get("/sources")
def get_sources():
    return sorted(sources_store.values(), key=lambda s: s.get("priority", 99))

@app.post("/sources")
def add_source(source: NewSource):
    if source.id in sources_store:
        raise HTTPException(400, f"Source '{source.id}' already exists")
    sources_store[source.id] = {**source.dict(), "enabled": True}
    _save_sources(sources_store)
    return {"ok": True, "source": sources_store[source.id]}

@app.patch("/sources/{source_id}")
def update_source(source_id: str, update: SourceUpdate):
    if source_id not in sources_store:
        raise HTTPException(404, "Source not found")
    sources_store[source_id].update({k:v for k,v in update.dict().items() if v is not None})
    _save_sources(sources_store)
    return {"ok": True, "source": sources_store[source_id]}

@app.delete("/sources/{source_id}")
def delete_source(source_id: str):
    if source_id not in sources_store:
        raise HTTPException(404, "Source not found")
    if source_id in DEFAULT_SOURCES:
        raise HTTPException(400, "Cannot delete built-in sources")
    del sources_store[source_id]
    _save_sources(sources_store)
    return {"ok": True}

@app.post("/sources/{source_id}/toggle")
def toggle_source(source_id: str):
    if source_id not in sources_store:
        raise HTTPException(404, "Source not found")
    sources_store[source_id]["enabled"] = not sources_store[source_id].get("enabled", True)
    _save_sources(sources_store)
    return {"ok": True, "enabled": sources_store[source_id]["enabled"]}

# ── Trims endpoint ─────────────────────────────────────────────
class TrimsRequest(BaseModel):
    brand: str
    model: str
    year: int
    anthropic_key: str = ""
    force_refresh: bool = False

@app.post("/trims")
async def get_trims_action(req: TrimsRequest):
    """Fetch official trims for any brand/model/year"""
    key = (req.brand.lower(), req.model.lower(), req.year)
    
    # Force refresh clears cache
    if req.force_refresh and key in _trim_cache:
        del _trim_cache[key]
    
    trims = await fetch_official_trims(req.brand, req.model, req.year, req.anthropic_key)
    configured = bool(get_trims(req.brand, req.model))
    return {
        "brand": req.brand, "model": req.model, "year": req.year,
        "source": "config" if configured
                  else "cache" if key in _trim_cache else "fetched",
        "count": len(trims),
        "trims": [{"name":t.name,"name_ar":t.name_ar,"msrp":t.msrp,"engine":t.engine,"keywords":t.keywords} for t in trims]
    }

@app.get("/trims/cache")
def get_trim_cache():
    """View currently cached trims"""
    return {
        f"{k[0]} {k[1]} {k[2]}": {
            "count": len(v["trims"]),
            "names": [t.name for t in v["trims"]],
            "age_hours": round((time.time()-v["ts"])/3600, 1)
        }
        for k, v in _trim_cache.items()
    }

@app.delete("/trims/cache")
def clear_trim_cache():
    _trim_cache.clear()
    return {"ok": True}

@app.post("/bundle")
def bundle_analysis(
    discount: int = 1500,
    addons: list[str] | None = None
):
    """
    يقارن تخفيض سعري مباشر مقابل تقديم إضافات.
    مثال: POST /bundle?discount=1500
    """
    return bundle_vs_discount(discount, addons)

@app.get("/bundle/addons")
def list_addons():
    """عرض كل الإضافات المتاحة وتكاليفها."""
    return [
        {"id": k, "label": v["label"], "cost": v["cost"], "value": v["value"],
         "roi": round(v["value"] / v["cost"], 1)}
        for k, v in sorted(BUNDLE_ADDONS.items(), key=lambda x: -x[1]["value"]/x[1]["cost"])
    ]

@app.get("/trend/{brand}/{model}/{year}/{trim_name}")
async def get_price_trend(brand: str, model: str, year: int, trim_name: str, weeks: int = 6):
    """
    تاريخ أسعار فئة محددة عبر الأسابيع.
    مثال: GET /trend/toyota/yaris/2026/Yaris%20YX?weeks=6
    """
    history = await snapshot_get_history(brand, model, year, trim_name, weeks=weeks)
    trend   = await snapshot_calc_trend(history)
    return {"brand": brand, "model": model, "year": year, "trim": trim_name, **trend, "history": history}

@app.get("/dom/{brand}/{model}/{trim_name}")
async def get_dom(brand: str, model: str, trim_name: str):
    """متوسط أيام الإعلان في السوق لفئة محددة."""
    return await dom_avg_for_trim(brand, model, trim_name)

@app.post("/pricing")
async def get_dealer_pricing(
    brand:   str,
    model:   str,
    year:    int,
    trim:    str,
    msrp:    int = 0,
    market_min: int = 0,
    market_avg: int = 0,
    market_max: int = 0,
    total_listings: int = 0,
    new_listings:   int = 0,
):
    """
    يحسب سعر البيع المقترح للوكيل بناءً على بيانات السوق الحية.

    مثال:
      POST /pricing?brand=toyota&model=yaris&year=2026&trim=Yaris+YX
           &msrp=75000&market_min=69575&market_avg=73073&market_max=79925
           &total_listings=12&new_listings=2
    """
    # جلب trend و DOM من Redis إن وُجدا
    history  = await snapshot_get_history(brand, model, year, trim, weeks=6)
    trend    = await snapshot_calc_trend(history)
    dom      = await dom_avg_for_trim(brand, model, trim)

    result = calc_dealer_price(
        msrp=msrp,
        market_min=market_min,
        market_avg=market_avg,
        market_max=market_max,
        total_listings=total_listings,
        new_listings=new_listings,
        trend_direction=trend.get("direction", "stable"),
        dom_avg=dom.get("avg"),
    )
    return {
        "brand": brand, "model": model, "year": year, "trim": trim,
        "trend": trend,
        "dom":   dom,
        **result,
    }

@app.delete("/trend/cache")
async def clear_trend_cache():
    """مسح كل snapshots الأسعار من Redis."""
    r = await _get_redis()
    if r:
        try:
            keys = await r.keys("hj:snap:*")
            if keys: await r.delete(*keys)
            dom_keys = await r.keys("hj:dom:*")
            if dom_keys: await r.delete(*dom_keys)
        except: pass
    return {"ok": True}

@app.get("/trims/configured")
def get_configured_trims():
    """Returns all brand/models defined in trims_config.py"""
    return get_all_configured()

# ── httpx fallback scrapers ─────────────────────────────────────
def _qenc(s): return s.replace(" ", "+")
def _int(v):
    if v is None: return 0
    try: return int(re.sub(r"[^\d]","",str(v)) or "0")
    except: return 0

def _L(source, source_name, listed_as, condition, price, mileage,
        location, seller_name, seller_type, days_ago, image, url, note, confidence, reason):
    return {"source":source,"sourceName":source_name,"listedAs":listed_as,"condition":condition,
            "price":price,"mileage":mileage,"location":location,"sellerName":seller_name,
            "sellerType":seller_type,"postedDaysAgo":days_ago,"imageUrl":image,"url":url,
            "priceNote":note,"matchConfidence":confidence,"matchReason":reason}

def _img(q):
    q=q.lower()
    if any(x in q for x in ["patrol","prado","land cruiser","fortuner","rav4","lx","gx"]): return "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=300&q=80"
    if any(x in q for x in ["hilux","f-150","ranger"]): return "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=300&q=80"
    return "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=300&q=80"

async def httpx_yallamotor(query, client):
    out = []
    parts = query.split()
    year = parts[0] if parts and parts[0].isdigit() else ""
    brand = parts[1] if len(parts)>1 else ""
    model = " ".join(parts[2:]) if len(parts)>2 else ""
    for url in [f"https://www.ksa.yallamotor.com.com/api/new-cars?brand={brand}&model={model}&year={year}&country=sa&limit=12",
                f"https://www.ksa.yallamotor.com.com/api/v2/listings?q={_qenc(query)}&country=sa&limit=12"]:
        try:
            r = await client.get(url, headers={"Referer":"https://www.ksa.yallamotor.com.com/"}, timeout=SCRAPE_TIMEOUT)
            if r.status_code==200 and "json" in r.headers.get("content-type",""):
                cars = r.json().get("data") or r.json().get("cars") or r.json().get("results") or []
                for c in cars[:10]:
                    p = _int(c.get("price") or c.get("base_price") or c.get("min_price"))
                    if p > 20000:
                        out.append(_L("ksa.yallamotor.com","YallaMotor.com",c.get("name") or query,
                            "جديدة",p,"0 كم",c.get("city") or "السعودية",
                            c.get("dealer_name") or "YallaMotor","dealer",0,
                            c.get("image") or _img(query),c.get("url") or "https://www.ksa.yallamotor.com.com",
                            (c.get("specs") or "")[:80],"high","YallaMotor — جديد"))
                if out: break
        except Exception as e: print(f"YallaMotor: {e}")
    return out

async def httpx_autotrader(query, client):
    out = []
    for url in [f"https://autotrader.sa/api/v1/cars?search={_qenc(query)}&limit=12",
                f"https://autotrader.sa/api/listings?q={_qenc(query)}"]:
        try:
            r = await client.get(url, timeout=SCRAPE_TIMEOUT)
            if r.status_code==200 and "json" in r.headers.get("content-type",""):
                cars = r.json().get("data") or r.json().get("listings") or r.json().get("cars") or []
                for c in cars[:10]:
                    p = _int(c.get("price") or c.get("asking_price"))
                    if p > 20000:
                        out.append(_L("autotrader","AutoTrader.sa",c.get("title") or c.get("name") or query,
                            c.get("condition") or "مستعملة",p,
                            f"{c.get('mileage',0):,} كم" if c.get("mileage") else "غير محدد",
                            c.get("city") or "غير محدد",c.get("seller_name") or "AutoTrader",
                            c.get("seller_type") or "dealer",0,
                            c.get("image") or _img(query),c.get("url") or "https://autotrader.sa",
                            (c.get("description") or "")[:80],"medium","AutoTrader SA"))
                if out: break
        except Exception as e: print(f"AutoTrader: {e}")
    return out


async def httpx_opensooq(query, client):
    """OpenSooq — أكبر سوق خليجي، يعطي أسعار السوق الثانوي بدقة"""
    out = []
    # OpenSooq API - يدعم البحث بالكلمات
    for url in [
        f"https://sa.opensooq.com/api/v2/posts/search?q={_qenc(query)}&category_id=84&limit=20",
        f"https://api.opensooq.com/v3/search?query={_qenc(query)}&country=sa&category=cars&limit=20",
        f"https://sa.opensooq.com/api/v1/listings?keywords={_qenc(query)}&cat=cars&limit=20",
    ]:
        try:
            r = await client.get(url, headers={"Accept":"application/json","Accept-Language":"ar"}, timeout=SCRAPE_TIMEOUT)
            if r.status_code == 200 and "json" in r.headers.get("content-type",""):
                data = r.json()
                items = data.get("data") or data.get("posts") or data.get("listings") or data.get("results") or []
                for item in items[:12]:
                    price_raw = item.get("price") or item.get("asking_price") or item.get("cost") or 0
                    price = _int(price_raw)
                    if price > 20000:
                        out.append(_L(
                            "opensooq", "OpenSooq.com",
                            item.get("title") or item.get("subject") or query,
                            "مستعملة" if item.get("is_used") else item.get("condition","مستعملة"),
                            price,
                            f"{item.get('mileage',0):,} كم" if item.get("mileage") else "غير محدد",
                            item.get("city") or item.get("location") or item.get("area") or "غير محدد",
                            item.get("username") or item.get("seller_name") or "بائع OpenSooq",
                            "individual" if item.get("is_private") else "dealer",
                            0,
                            (item.get("images") or [{"url": _img(query)}])[0].get("url") if isinstance(item.get("images",[{}])[0], dict) else _img(query),
                            item.get("url") or f"https://sa.opensooq.com",
                            (item.get("description") or item.get("body") or "")[:80],
                            "medium", "OpenSooq — سوق خليجي"
                        ))
                if out: break
        except Exception as e:
            print(f"OpenSooq {url}: {e}")
    return out


async def httpx_carswitch(query, client):
    """CarSwitch — سيارات مستعملة معتمدة ومفحوصة"""
    out = []
    parts = query.split()
    year  = parts[0] if parts and parts[0].isdigit() else ""
    brand = parts[1] if len(parts) > 1 else ""
    model = " ".join(parts[2:]) if len(parts) > 2 else ""
    for url in [
        f"https://carswitch.com/api/v2/cars?make={brand}&model={model}&year={year}&country=sa&limit=15",
        f"https://carswitch.com/api/v1/inventory?q={_qenc(query)}&country=sa&limit=15",
        f"https://api.carswitch.com/cars?search={_qenc(query)}&country=sa",
    ]:
        try:
            r = await client.get(url, headers={"Accept":"application/json","Origin":"https://carswitch.com"}, timeout=SCRAPE_TIMEOUT)
            if r.status_code == 200 and "json" in r.headers.get("content-type",""):
                data = r.json()
                cars = data.get("data") or data.get("cars") or data.get("inventory") or data.get("results") or []
                for c in cars[:10]:
                    price = _int(c.get("price") or c.get("selling_price") or c.get("sale_price"))
                    if price > 20000:
                        out.append(_L(
                            "carswitch", "CarSwitch.com",
                            c.get("title") or c.get("name") or f"{c.get('year','')} {c.get('make','')} {c.get('model','')}".strip() or query,
                            "مستعملة معتمدة",
                            price,
                            f"{c.get('mileage',0):,} كم" if c.get("mileage") else "غير محدد",
                            c.get("city") or c.get("location") or "المملكة العربية السعودية",
                            "CarSwitch Certified",
                            "dealer",
                            0,
                            c.get("image") or c.get("main_image") or _img(query),
                            c.get("url") or "https://carswitch.com",
                            f"مفحوصة {c.get('inspection_score','')} نقطة" if c.get("inspection_score") else "سيارة معتمدة",
                            "high", "CarSwitch — مستعملة معتمدة"
                        ))
                if out: break
        except Exception as e:
            print(f"CarSwitch {url}: {e}")
    return out


async def httpx_dubizzle(query, client):
    """Dubizzle Saudi — منصة إعلانات، تعطي نظرة سوق واسعة"""
    out = []
    for url in [
        f"https://api.dubizzle.com/en/classifieds/motors/cars/?keywords={_qenc(query)}&country_abbr=sa&format=json&page_size=15",
        f"https://dubai.dubizzle.com/api/v1/motors/cars/?q={_qenc(query)}&country=sa&format=json&limit=15",
    ]:
        try:
            r = await client.get(url, headers={"Accept":"application/json","Referer":"https://dubai.dubizzle.com/"}, timeout=SCRAPE_TIMEOUT)
            if r.status_code == 200 and "json" in r.headers.get("content-type",""):
                data = r.json()
                items = data.get("results") or data.get("data") or data.get("listings") or []
                for item in items[:10]:
                    price = _int(item.get("price") or item.get("asking_price"))
                    if price > 20000:
                        out.append(_L(
                            "dubizzle_sa", "Dubizzle Saudi",
                            item.get("title") or item.get("subject") or query,
                            "مستعملة",
                            price,
                            f"{item.get('mileage',0):,} كم" if item.get("mileage") else "غير محدد",
                            item.get("city") or item.get("location") or "غير محدد",
                            item.get("username") or "بائع Dubizzle",
                            "individual" if item.get("is_private") else "dealer",
                            0,
                            (item.get("photos") or [{"value": _img(query)}])[0].get("value","") if item.get("photos") else _img(query),
                            item.get("absolute_url") or "https://dubai.dubizzle.com",
                            (item.get("description") or "")[:80],
                            "medium", "Dubizzle Saudi"
                        ))
                if out: break
        except Exception as e:
            print(f"Dubizzle {url}: {e}")
    return out


async def httpx_car_sa(query, client):
    """Car.com.sa — موقع سعودي متخصص"""
    out = []
    for url in [
        f"https://www.car.com.sa/api/cars?search={_qenc(query)}&limit=15",
        f"https://www.car.com.sa/api/v1/listings?q={_qenc(query)}&limit=15",
    ]:
        try:
            r = await client.get(url, headers={"Accept":"application/json"}, timeout=SCRAPE_TIMEOUT)
            if r.status_code == 200 and "json" in r.headers.get("content-type",""):
                data = r.json()
                cars = data.get("data") or data.get("cars") or data.get("results") or []
                for c in cars[:10]:
                    price = _int(c.get("price") or c.get("selling_price"))
                    if price > 20000:
                        out.append(_L(
                            "car_sa", "Car.com.sa",
                            c.get("title") or c.get("name") or query,
                            c.get("condition") or "مستعملة",
                            price,
                            f"{c.get('mileage',0):,} كم" if c.get("mileage") else "غير محدد",
                            c.get("city") or "غير محدد",
                            c.get("seller_name") or "Car.com.sa",
                            c.get("seller_type") or "dealer",
                            0, _img(query),
                            c.get("url") or "https://www.car.com.sa", "",
                            "medium", "Car.com.sa"
                        ))
                if out: break
        except Exception as e:
            print(f"Car.com.sa {url}: {e}")
    return out


async def httpx_petromin(query, client):
    """Petromin Express — وكيل معتمد، سيارات مستعملة مفحوصة"""
    out = []
    parts = query.split()
    brand = parts[1] if len(parts) > 1 else ""
    model_q = " ".join(parts[2:]) if len(parts) > 2 else ""
    for url in [
        f"https://www.petrominexpress.com/api/cars?make={brand}&model={model_q}&limit=12",
        f"https://www.petrominexpress.com/api/v1/new-cars?q={_qenc(query)}&limit=12",
        f"https://petrominexpress.com/api/inventory?search={_qenc(query)}",
    ]:
        try:
            r = await client.get(url, headers={"Accept":"application/json","Referer":"https://www.petrominexpress.com/"}, timeout=SCRAPE_TIMEOUT)
            if r.status_code == 200 and "json" in r.headers.get("content-type",""):
                data = r.json()
                cars = data.get("data") or data.get("cars") or data.get("inventory") or data.get("results") or []
                for c in cars[:10]:
                    price = _int(c.get("price") or c.get("selling_price") or c.get("sale_price"))
                    if price > 20000:
                        out.append(_L(
                            "petromin", "Petromin Express",
                            c.get("title") or c.get("name") or f"{c.get('year','')} {brand} {model_q}".strip() or query,
                            "مستعملة معتمدة",
                            price,
                            f"{c.get('mileage',0):,} كم" if c.get("mileage") else "غير محدد",
                            c.get("branch") or c.get("city") or "المملكة العربية السعودية",
                            "Petromin Express",
                            "official_dealer",
                            0,
                            c.get("image") or c.get("thumbnail") or _img(query),
                            c.get("url") or "https://www.petrominexpress.com",
                            f"مفحوصة {c.get('inspection_points','')} نقطة" if c.get("inspection_points") else "سيارة معتمدة من بترومين",
                            "high", "Petromin Express — وكيل معتمد"
                        ))
                if out: break
        except Exception as e:
            print(f"Petromin {url}: {e}")
    return out


async def httpx_aljazirah(query, client):
    """Al-Jazirah Motors — وكيل نيسان وفورد الرسمي"""
    out = []
    for url in [
        f"https://www.aljazirah-motors.com.sa/api/vehicles?search={_qenc(query)}&limit=10",
        f"https://www.aljazirah-motors.com.sa/api/v1/new-cars?q={_qenc(query)}",
    ]:
        try:
            r = await client.get(url, headers={"Accept":"application/json"}, timeout=SCRAPE_TIMEOUT)
            if r.status_code == 200 and "json" in r.headers.get("content-type",""):
                data = r.json()
                cars = data.get("data") or data.get("vehicles") or data.get("cars") or []
                for c in cars[:8]:
                    price = _int(c.get("price") or c.get("base_price") or c.get("msrp"))
                    if price > 20000:
                        out.append(_L(
                            "aljazirah", "Al-Jazirah Motors",
                            c.get("name") or c.get("title") or query,
                            "جديدة", price, "0 كم",
                            "المملكة العربية السعودية",
                            "الجزيرة للسيارات", "official_dealer",
                            0, c.get("image") or _img(query),
                            c.get("url") or "https://www.aljazirah-motors.com.sa",
                            "سعر رسمي من الجزيرة للسيارات",
                            "high", "Al-Jazirah — وكيل رسمي"
                        ))
                if out: break
        except Exception as e:
            print(f"Al-Jazirah {url}: {e}")
    return out


async def httpx_generic(source, query, client):
    out = []
    base = source.get("url","")
    sid = source.get("id","custom")
    sname = source.get("name","Custom")
    search_url = source.get("search_url","").replace("{query}",_qenc(query))
    for url in ([search_url] if search_url else []) + [f"{base}/api/cars?q={_qenc(query)}"]:
        try:
            r = await client.get(url, timeout=SCRAPE_TIMEOUT)
            if r.status_code==200 and "json" in r.headers.get("content-type",""):
                items = r.json().get("data") or r.json().get("results") or r.json().get("cars") or []
                for item in items[:8]:
                    p = _int(item.get("price") or item.get("selling_price"))
                    if p > 20000:
                        out.append(_L(sid,sname,item.get("title") or item.get("name") or query,
                            item.get("condition") or "مستعملة",p,str(item.get("mileage") or "غير محدد"),
                            item.get("city") or "غير محدد",item.get("seller") or sname,"dealer",0,
                            item.get("image") or _img(query),item.get("url") or base,
                            (item.get("description") or "")[:80],"medium",f"بحث من {sname}"))
                if out: break
        except: continue
    return out

# ── Trim normalizer ─────────────────────────────────────────────
# NOTE: TRIM_RULES is deprecated; the system now uses TRIM_CONFIG from trims_config.py.
# Add/adjust trims in trims_config.py to affect normalization and fetching.

def normalize_trim(title: str, brand: str, model: str) -> tuple[str, str, float]:
    """Primary normalizer — uses trims_config.py (edit that file to add trims).

    If no config exists for the brand/model, returns a generic name.
    """
    configured = get_trims(brand, model)
    if configured:
        return normalize_from_config(title, brand, model)

    # No config found — fall back to a safe generic match.
    return f"{model} Standard", "مطابقة عامة", 0.50

# ── Trim Registry — dynamic cache ──────────────────────────────
# Stores fetched trims per (brand, model, year) for 24h
_trim_cache: dict = {}   # key → {"trims": [...], "ts": timestamp}
TRIM_CACHE_TTL = 86400   # 24 hours

class TrimInfo:
    """Represents one official trim with keywords for matching"""
    def __init__(self, name: str, name_ar: str, msrp: int, engine: str,
                 keywords: list[str], score: float = 0.85):
        self.name      = name
        self.name_ar   = name_ar
        self.msrp      = msrp
        self.engine    = engine
        self.keywords  = [k.lower() for k in keywords]
        self.score     = score


async def fetch_official_trims(brand: str, model: str, year: int,
                                anthropic_key: str) -> list[TrimInfo]:
    """
    Returns official trims for any brand/model/year.
    Priority:
      1. TRIM_CONFIG (from trims_config.py)
      2. In-memory cache (instant if <24h old)
      3. Toyota.com.sa Playwright scrape
      4. Claude AI lookup (fallback for any brand)
    """
    key = (brand.lower(), model.lower(), year)

    # 1. Config-defined trims (fast, explicit)
    configured = get_trims(brand, model)
    if configured:
        return [
            TrimInfo(name=t.name.lower(), name_ar=t.name_ar, msrp=t.msrp, engine=t.engine,
                     keywords=t.keywords, score=t.match_score)
            for t in configured
        ]

    # 2. Cache
    if key in _trim_cache:
        entry = _trim_cache[key]
        if time.time() - entry["ts"] < TRIM_CACHE_TTL:
            return entry["trims"]
    
    # 3. Toyota.com.sa scrape (only for Toyota/Lexus)
    trims = []
    if brand.lower() in ("toyota", "lexus") and PLAYWRIGHT_OK:
        trims = await _scrape_trims_toyota_sa(brand, model, year)
    
    # 4. AI fallback for any brand (or if scrape failed)
    if not trims:
        trims = await _ai_fetch_trims(brand, model, year, anthropic_key)
    
    if trims:
        _trim_cache[key] = {"trims": trims, "ts": time.time()}
    
    return trims


async def _scrape_trims_toyota_sa(brand: str, model: str, year: int) -> list[TrimInfo]:
    """Scrape official trims + prices from toyota.com.sa model page via Playwright"""
    trims = []
    if not PLAYWRIGHT_OK:
        return trims
    
    slug = model.lower().replace(" ", "-")
    urls = [
        f"https://www.toyota.com.sa/en/models/{slug}",
        f"https://www.toyota.com.sa/ar/models/{slug}",
        f"https://www.toyota.com.sa/en/vehicles/{slug}",
    ]
    
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True, args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"]
            )
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
            )
            await page.route("**/*.{png,jpg,jpeg,gif,webp,woff,woff2,mp4}", lambda r: r.abort())
            
            for url in urls:
                try:
                    resp = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    if not resp or resp.status >= 400:
                        continue
                    await page.wait_for_timeout(2000)
                    html = await page.content()
                    
                    # Extract trim cards — toyota.com.sa renders them as JS components
                    # Try JSON-LD first
                    import json as _json, re as _re
                    for ld_str in _re.findall(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', html, _re.DOTALL):
                        try:
                            ld = _json.loads(ld_str)
                            offers = ld.get("offers") or []
                            if isinstance(offers, dict): offers = [offers]
                            for o in offers:
                                price = _int(str(o.get("price") or o.get("lowPrice") or "0"))
                                if 40000 < price < 2000000:
                                    name = o.get("name","") or f"{model} Trim"
                                    trims.append(TrimInfo(
                                        name=name, name_ar=name,
                                        msrp=price, engine="",
                                        keywords=[name.lower(), name.split()[-1].lower()],
                                        score=0.90
                                    ))
                        except: pass
                    
                    # HTML pattern: trim name + price side by side
                    if not trims:
                        # e.g. "Y LIMITED  ﷼ 66,700" or "LE HEV  119,070"
                        pairs = _re.findall(
                            r'([A-Z][A-Z0-9 \+\-]{1,25}?)\s*(?:﷼|SAR|السعر)?\s*([0-9,]{6,})',
                            html, _re.IGNORECASE
                        )
                        seen_prices = set()
                        for trim_name, price_str in pairs[:12]:
                            price = _int(price_str)
                            if 40000 < price < 2000000 and price not in seen_prices:
                                seen_prices.add(price)
                                clean_name = trim_name.strip()
                                trims.append(TrimInfo(
                                    name=f"{model} {clean_name}",
                                    name_ar=f"{model} {clean_name}",
                                    msrp=price, engine="",
                                    keywords=[clean_name.lower()],
                                    score=0.85
                                ))
                    
                    if trims:
                        #print(f"  ✅ toyota.com.sa trims for {model}: {[t.name for t in trims]}")
                        break
                except Exception as e:
                    #print(f"  Toyota SA trim scrape {url}: {e}")
                    continue
            
            await browser.close()
    except Exception as e:
        print(f"  Playwright trim scrape error: {e}")
    
    return trims


async def _ai_fetch_trims(brand: str, model: str, year: int,
                           anthropic_key: str) -> list[TrimInfo]:
    """Ask Claude for official trims of any brand/model in Saudi Arabia"""
    #print(f"  starting AI trim fetch for {year} {brand} {model}...")
    if not anthropic_key:
        return []
   
    prompt = f"""List ALL official trim levels for {year} {brand} {model} sold in Saudi Arabia.
For each trim include: official name, Arabic name, MSRP in SAR (including 15% VAT), engine, and 3-5 common informal names used in Saudi listings.
Return ONLY valid JSON array, no markdown:
[
  {{
    "name": "official trim name in English",
    "name_ar": "اسم الفئة بالعربي",
    "msrp": 120000,
    "engine": "2.5L Hybrid 226hp",
    "keywords": ["informal1", "keyword2", "arabic keyword"],
    "score": 0.90
  }}
]
RULES:
- Saudi Arabia prices only (SAR, includes VAT 15%)
- All trims available at authorized dealers RIGHT NOW ({year} model year)
- keywords = actual words buyers use in listings on Haraj/Syarah
- If model unknown, return empty array []"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                ANTHROPIC_API_URL,
                headers={"Content-Type":"application/json","x-api-key":anthropic_key,"anthropic-version":"2023-06-01"},
                json={"model":"claude-sonnet-4-20250514","max_tokens":1500,
                      "messages":[{"role":"user","content":prompt}]}
            )
        r.raise_for_status()
        raw = r.json()["content"][0]["text"]
        #print(f"response from AI: {raw[:200]}...")  # Log the raw response for debugging
        data = json.loads(re.sub(r"```json|```","",raw).strip())
        trims = []
        for item in data:
            trims.append(TrimInfo(
                name=item.get("name",""),
                name_ar=item.get("name_ar",""),
                msrp=_int(str(item.get("msrp",0))),
                engine=item.get("engine",""),
                keywords=item.get("keywords",[]),
                score=float(item.get("score",0.85))
            ))
        #print(f"  ✅ AI trims for {year} {brand} {model}: {[t.name for t in trims]}")
        return trims
    except Exception as e:
        #print(f"  AI trim fetch error: {e}")
        return []


def normalize_trim_dynamic(title: str, brand: str, model: str,
                             fetched_trims: list) -> tuple[str, str, float]:
    """
    Enhanced normalize_trim that uses dynamically fetched trims.
    Falls back to normalize_trim (which uses TRIM_CONFIG) if no dynamic trims are available.
    """
    if not fetched_trims:
        return normalize_trim(title, brand, model)
    
    t = title.lower()
    best_match = None
    best_score = 0.0
    
    for trim in fetched_trims:
        score = 0.0
        # Exact keyword match
        for kw in trim.keywords:
            if kw and kw in t:
                score = max(score, trim.score)
                break
        # Trim name words match
        name_words = trim.name.lower().split()
        matches = sum(1 for w in name_words if len(w) > 2 and w in t)
        if matches > 0:
            score = max(score, 0.65 + (matches / len(name_words)) * 0.25)
        
        if score > best_score:
            best_score = score
            best_match = trim
    
    if best_match and best_score > 0.5:
        return best_match.name, f"مطابقة ديناميكية ({best_match.keywords[0] if best_match.keywords else ''})", best_score
    
    # Fallback to generic match when no configured trims exist
    return normalize_trim(title, brand, model)

async def get_model_trims_from_catalog(brand: str, model: str, year: int) -> list[str]:
    """
    يجلب أسماء فئات الموديل من الكاتالوج المخزن في الكاش.
    يرجع قائمة بأسماء الفئات أو قائمة فارغة إن لم يوجد.
    """
    cached = await cache_get("car_catalog")
    if not cached:
        return []

    model_types = cached.get("modelTypes", [])
    groups      = cached.get("groups", [])
    brands_list = cached.get("brands", [])

    #print(f"get_model_trims_from_catalog : {brands_list}  ")

    # 1. نجد BrandID من اسم الماركة
    brand_id = None
    for b in brands_list:
        desc = (b.get("DescriptionEn") or b.get("DescriptionAr") or "").lower()
        if brand.lower() in desc:
            brand_id = b.get("BrandID")
            break

    #print(f"get_model_trims_from_catalog brand_id : {brand_id}  ")

    if not brand_id:
        return []

    # 2. نجد ProductGroupId من اسم الموديل + السنة + BrandID
    group_id = None
    for g in groups:
        if g.get("brandID") != brand_id:
            continue
        g_year = str(g.get("Year", ""))
        g_desc = (g.get("DescriptionEn") or g.get("DescriptionAr") or "").lower()
        if model.lower() in g_desc and str(year) in g_year:
            group_id = g.get("productGroupID")
            break

    #print(f"get_model_trims_from_catalog group_id : {group_id}  ")
    # إذا ما لقينا بالسنة، نحاول بدونها
    if not group_id:
        for g in groups:
            if g.get("brandID") != brand_id:
                continue
            g_desc = (g.get("DescriptionEn") or g.get("DescriptionAr") or "").lower()
            if model.lower() in g_desc:
                group_id = g.get("productGroupID")
                break

    #print(f"get_model_trims_from_catalog 22 group_id : {group_id}  ")
    if not group_id:
        return []

   # 3. جمع الفئات مع تنظيف الاسم + منع التكرار
    trim_set = set()

    for mt in model_types:
        mt_model = str(mt.get("Model", ""))
        if mt.get("productGroupID") == group_id and str(year) in mt_model:
            name = mt.get("descriptionEn") or mt.get("descriptionAr") or mt.get("description") or ""
            if not name:
                continue

            clean_name = name.lower()

         # نحذف البراند والموديل والسنة ككلمات مستقلة
            pattern = r'\b(' + re.escape(brand.lower()) + r'|' + re.escape(model.lower()) + r'|' + str(year) + r')\b'
            clean_name = re.sub(pattern, '', clean_name)

            # تنظيف المسافات
            clean_name = " ".join(clean_name.split())

            if clean_name:
                trim_set.add(clean_name)

    unique_list = list(set(trim_set))
    return list(unique_list)[:5]  # نرجع حتى 5 فئات

# ── AI fallback ─────────────────────────────────────────────────
async def ai_fallback(brand, model, year, source_ids, key):
    #print(f"starting AI fallback for {year} {brand} {model} with sources {source_ids}...")
    names = [sources_store[s]["name"] for s in source_ids if s in sources_store]

      # ── جلب أسماء الفئات من الكاتالوج ──
    catalog_trims = await get_model_trims_from_catalog(brand, model, year)
    
    if catalog_trims:
        trims_hint = (
            f"EXACTLY these official trim names :"
            f"{json.dumps(catalog_trims, ensure_ascii=False)} {year} {brand} {model} ."
        )
    else:
        trims_hint = "ALL official trims for {year} {brand} {model} in Saudi"

    prompt = f"""KSA car market pricing expert. Vehicle: {year} {brand} {model}. Date: {datetime.now().strftime('%B %Y')}.
Sources: {', '.join(names)}.
PRICING TIERS (never return 0, always best estimate):
T1=exact known price→confidence:high | T2=adjacent year/trim interpolated→confidence:medium,explain in priceNote | T3=market logic estimate→confidence:low,note it

KSA PRICING RULES: All SAR+15%VAT. Dealer=MSRP±3%, Private(Haraj)=MSRP-4~9%, Syarah/Motory=MSRP-0~5%. YoY increase~3%.

RULES: {trims_hint} | 4+ listings/source/trim | vary location+seller | priceType:exact|interpolated|estimated per listing | NO imageUrl/sellerName/URLs→use "" | priceNote Arabic reasoning | isAIFallback:false if any T1/T2 used

Return ONLY valid JSON no markdown:
{{"vehicle":"{year} {brand} {model}","brand":"{brand}","model":"{model}","year":{year},"searchDate":"{datetime.now().strftime('%B %Y')}","isAIFallback":true,"officialPriceRange":{{"min":0,"max":0}},"marketInsight":"Arabic","trims":[{{"officialName":"","officialNameAr":"","officialMSRP":0,"engine":"","commonAliases":["a1"],"listings":[{{"source":"syarah.com","sourceName":"Syarah.com","listedAs":"Arabic","priceType":"exact|interpolated|estimated","matchConfidence":"high|medium|low","condition":"جديدة","price":0,"mileage":"0 كم","location":"city","priceNote":"Arabic","sellerType":"dealer","sellerName":"","postedDaysAgo":3,"imageUrl":""}}],"priceAnalysis":{{"marketMin":0,"marketMax":0,"marketAvg":0,"vsOfficialPct":0,"trend":"stable"}}}}],"competitorAnalysis":{{"summary":"Arabic","opportunities":["Arabic"],"threats":["Arabic"],"recommendation":"Arabic"}}}}"""
    await cache_set('ai_fallback_prompt', {"content":prompt})  # Cache the prompt for debugging

    
    #print(f"AI prompt: {prompt}")  # Log the prompt for debugging
    try:
        async with httpx.AsyncClient(
                    timeout=180.0,
                    http2=False
                ) as client:
            r = await client.post(
                ANTHROPIC_API_URL,
               headers={
                        "Content-Type": "application/json",
                        "x-api-key": key,
                        "anthropic-version": "2023-06-01",
                        "Connection": "close"
                    },
                  json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 30000,
                    "temperature": 0.2,
                    "system": "You are a Saudi automotive market expert. Return strictly valid JSON only.",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
            )

        r.raise_for_status()

    except Exception as e:
        #print("HTTP request failed:", str(e))
        raise

    # ── معالجة الرد ─────────────────────────────────────────────
    try:
        data = r.json()
        #print(data.get("stop_reason"))
    except Exception as e:
        #print("Failed to parse response as JSON:", str(e))
        #print("Raw response text:", r.text)
        raise

    # ── استخراج النص بشكل آمن ──────────────────────────────────
    text = ""
    if "content" in data and len(data["content"]) > 0:
        text = data["content"][0].get("text", "")
        #print(f"response from AI fallback: {text}...")
    else:
        #print("Unexpected response structure:")
        #print(data)
        raise ValueError("Invalid AI response format")

    # ── تنظيف النص ─────────────────────────────────────────────
    clean_text = re.sub(r"```json|```", "", text).strip()

    # ── تحويل إلى JSON ─────────────────────────────────────────
    try:
        return json.loads(clean_text)

    except Exception as e:
        #print("Failed to parse JSON:", str(e))
        #print("Cleaned response was:")
        #print(clean_text)
        raise

# ── Main search by playwright   ─────────────────────────────────────────────────
@app.post("/searchByURL")
async def searchByURL(req: SearchRequest):
    cache_key = f"searchByURL_{req.brand}:{req.model}:{req.year}:{','.join(sorted(req.source_ids or []))}"
    cached = await cache_get(cache_key)
    if cached: return cached

    active = sorted(
        [s for s in sources_store.values() if s["enabled"] and
         (req.source_ids is None or s["id"] in req.source_ids)],
        key=lambda s: s.get("priority", 99)
    )
    #print(f"active sources for {req.year} {req.brand} {req.model}: {[s['id'] for s in active]}")
    query  = f"{req.year} {req.brand} {req.model}"
    raw: list[dict] = []
    statuses: dict  = {}

    # ── Build task list ──
    # Playwright tasks run sequentially (can't share browser easily)
    # httpx tasks run in parallel
    playwright_tasks = []
    httpx_tasks      = []

    for src in active:
        sid  = src["id"]
        stype = src.get("type","httpx")

        if stype == "playwright" or sid in ("syarah.com","haraj.com.sa","ksa.Motory.com","toyota.com.sa","ksa.yallamotor.com"):
            playwright_tasks.append(sid)
        else:
            httpx_tasks.append(sid)

    # ── Run Playwright scrapers ──
    playwright_enabled = PLAYWRIGHT_OK

    async def run_playwright(sid):
        try:
            # ── تمرير brand/model/year لتفعيل _price_in_range الصحيح ──
            kw = {"brand": req.brand, "model": req.model, "year": req.year}
            used_keywords = ["مستعمل", "مستعملة", "used", "pre-owned"]
            if sid == "syarah.com":
                results = await playwright_syarah(query, max_results=20, **kw)
                # #print(f"  [Syarah]after playwright_syarah results: {len(results)}")
                # فلتر المستعملة — نريد الجديدة فقط لمقارنة الوكلاء
                results = [
                        r for r in results
                        if not any(k in str(r.get("condition", "")).lower() for k in used_keywords)
                    ]
                return sid, results
            elif sid == "haraj.com.sa":
                # حراج يجلب مستعملة — نحتفظ بها كمعلومة لكن نعلّمها
                results = await playwright_haraj(query, max_results=20, **kw)
                # #print(f"  [Haraj]after playwright_haraj results: {results}")
                    # إذا new_only: احذف المستعملة تماماً
                # results = [
                #         r for r in results
                #         if not any(k in str(r.get("condition", "")).lower() for k in used_keywords)
                #     ]
                return sid, results
            elif sid == "ksa.Motory.com":
                results = await playwright_motory(query, max_results=20, **kw)
                results = [r for r in results if "جديد" in str(r.get("condition","")).lower()
                           or r.get("condition","") in ("New","جديدة")]
                return sid, results
            elif sid == "ksa.yallamotor.com":
                results = await playwright_yallamotor(query, max_results=20, **kw)
                # #print(f"  [YallaMotor]after playwright_yallamotor results: {len(results)}")
                 # فلتر المستعملة — نريد الجديدة فقط لمقارنة الوكلاء
                results = [
                        r for r in results
                        if not any(k in str(r.get("condition", "")).lower() for k in used_keywords)
                                       ]
                # #print(f"  [YallaMotor]after filtering used: {len(results)}")
                return sid, results
            if sid == "toyota.com.sa" and req.brand.lower() == "toyota":
                model_name = " ".join(query.split()[2:]) if len(query.split()) > 2 else req.model
                return sid, await playwright_toyota_sa(model_name, year=req.year)
            elif sid == "lexus.com.sa" and req.brand.lower() == "lexus":
                model_name = " ".join(query.split()[2:]) if len(query.split()) > 2 else req.model
                results= await playwright_lexus_sa(model_name, year=req.year)
                # #print(f"  [Lexus SA]after playwright_lexus_sa results: {results}")
                return sid,results 
          
            return sid, []
        except Exception as e:
            return sid, e

    if playwright_enabled and playwright_tasks:
        # Run playwright in parallel (each opens its own browser instance)
        pw_results = await asyncio.gather(
            *[run_playwright(sid) for sid in playwright_tasks],
            return_exceptions=True
        )
        for item in pw_results:
            if isinstance(item, Exception):
                #print(f"Playwright gather error: {item}")
                continue
            sid, result = item
            if isinstance(result, Exception):
                statuses[sid] = {"ok": False, "error": str(result)[:100], "count": 0}
            else:
                statuses[sid] = {"ok": True, "count": len(result), "method": "playwright"}
                raw.extend(result)
                if result:
                    print(f"  ✅ {sid}: {len(result)} results via Playwright")
                else:
                    print(f"  ⚠️  {sid}: 0 results via Playwright")

    # ── Run httpx scrapers ──
    #print(f"Starting httpx tasks for sources: {httpx_tasks}")
    if httpx_tasks:
        hclient = httpx.AsyncClient(
            headers={"User-Agent":"Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36"},
            follow_redirects=True, timeout=SCRAPE_TIMEOUT,
        )
        async with hclient as client:
            htasks = []
            for sid in httpx_tasks:
                src = sources_store.get(sid, {})
                if   sid == "ksa.yallamotor.com":  htasks.append((sid, httpx_yallamotor(query, client)))
                else:                      htasks.append((sid, httpx_generic(src, query, client)))

            hresults = await asyncio.gather(*[t[1] for t in htasks], return_exceptions=True)
            for (sid,_), result in zip(htasks, hresults):
                if isinstance(result, Exception):
                    statuses[sid] = {"ok": False, "error": str(result)[:100], "count": 0}
                else:
                    statuses[sid] = {"ok": True, "count": len(result), "method": "httpx"}
                    raw.extend(result)

    use_ai =False
    data = None

    #print(f"  Total listings collected: {len(raw)} (AI fallback used: {use_ai})")
    #print(f"real data only, no AI fallback — total {len(raw)} listings")

    # ── Classify listings into trims (same engine as searchURLAndAI) ──
    classified = classify_and_structure(
        raw_listings=raw,
        brand=req.brand,
        model=req.model,
        year=req.year,
        dynamic_trims=None,  # searchByURL لا يستخدم AI لجلب الفئات
        ai_data=None,
    )

    data = {
        "vehicle": classified["vehicle"],
        "brand": classified["brand"],
        "model": classified["model"],
        "year": classified["year"],
        "searchDate": datetime.now().strftime("%B %Y"),
        "isAIFallback": False,
        "officialPriceRange": classified["officialPriceRange"],
        "marketInsight": f"تم جمع {len(raw)} إعلان من المصادر الحية — مصنّفة إلى {len(classified['trims'])} فئات",
        "priceHistory": [],
        "competitorAnalysis": {"summary":"","opportunities":[],"threats":[],"recommendation":""},
        "trims": classified["trims"],
    }

    # Log classification summary
    for t in data["trims"]:
        n = len(t.get("listings", []))
        #print(f"  📊 {t['officialName']}: {n} listings")

    # ── حساب إحصائيات كل مصدر لكل فئة ──
    _attach_source_stats(data)
    #print(f"  Source stats attached for {len(data.get('trims', []))} trims")
    data.update({
        "sourceStatuses": statuses,
        "scrapedCount": len(raw),
        "isAIFallback": use_ai,
        "playwrightUsed": playwright_enabled,
    })
    # Save price snapshots + DOM records (only for real scraped data)
    await _post_search_persist(data, req.brand, req.model, req.year)
    # Enrich with historical trend + days-on-market (from Redis)
    await _enrich_with_history(data, req.brand, req.model, req.year)
    # Compute dealer pricing recommendation (uses supply + trend + DOM)
    _attach_dealer_pricing(data)
    # if ai_failed==False:
    #    await cache_set(cache_key, data)
       
    return data

# ── Main search by Ai ─────────────────────────────────────────────────
@app.post("/searchByAI")
async def searchByAI(req: SearchRequest):
    cache_key = f"searchByAI_{req.brand}:{req.model}:{req.year}:{','.join(sorted(req.source_ids or []))}"
    cached = await cache_get(cache_key)
    if cached: return cached

# ✅ تعطيل مصدر معين حسب البراند
    if req.brand and req.brand.lower() != "lexus":
        if "lexus.com.sa" in sources_store:
            sources_store["lexus.com.sa"]["enabled"] = False

    active = sorted(
        [s for s in sources_store.values() if s["enabled"] and
         (req.source_ids is None or s["id"] in req.source_ids)],
        key=lambda s: s.get("priority", 99)
    )
    #print(f"active sources for {req.year} {req.brand} {req.model}: {[s['id'] for s in active]}")
    raw: list[dict] = []
    statuses: dict  = {}


    # ── AI fallback if not enough data ──
    use_ai = len(raw) < 5
    ai_data = None
    ai_failed = False
    if use_ai:
        #print(f"  ⚠️  Only {len(raw)} real listings — using AI fallback")
        try:
            ai_data = await ai_fallback(
                req.brand, req.model, req.year,
                [s["id"] for s in active], req.anthropic_key
            )
        except Exception as e:
            #print(f"AI fallback error: {e}")
            ai_failed = True

    #print(f"  Total listings collected: {len(raw)} (AI fallback used: {use_ai})")
    # ── Classify listings into trims ──
    dyn_trims = await fetch_official_trims(req.brand, req.model, req.year, req.anthropic_key)
    classified = classify_and_structure(
        raw_listings=raw,
        brand=req.brand,
        model=req.model,
        year=req.year,
        dynamic_trims=dyn_trims,
        ai_data=ai_data,
    )

    ai_data = {
        "vehicle": classified["vehicle"],
        "brand": classified["brand"],
        "model": classified["model"],
        "year": classified["year"],
        "searchDate": datetime.now().strftime("%B %Y"),
        "isAIFallback": use_ai,
        "officialPriceRange": classified["officialPriceRange"],
        "marketInsight": classified.get("marketInsight",
            f"تم جمع {len(raw)} إعلان — مصنّفة إلى {len(classified['trims'])} فئات"),
        "priceHistory": classified.get("priceHistory", []),
        "competitorAnalysis": classified.get("competitorAnalysis",
            {"summary":"","opportunities":[],"threats":[],"recommendation":""}),
        "trims": classified["trims"],
    }

    # ── حساب إحصائيات كل مصدر لكل فئة ──
    _attach_source_stats(ai_data)
    #print(f"  Source stats attached for {len(ai_data.get('trims', []))} trims")
    ai_data.update({
        "sourceStatuses": statuses,
        "scrapedCount": len(raw),
        "isAIFallback": use_ai,
        "playwrightUsed": False,
    })
    # Save price snapshots + DOM records (only for real scraped data)
    if not use_ai:
        await _post_search_persist(ai_data, req.brand, req.model, req.year)
    # Enrich with historical trend + days-on-market (from Redis)
    await _enrich_with_history(ai_data, req.brand, req.model, req.year)
    # Compute dealer pricing recommendation (uses supply + trend + DOM)
    _attach_dealer_pricing(ai_data)
    # if ai_failed==False:
    #    await cache_set(cache_key, ai_data)
       
    return ai_data


# ── Main search by URL and AI ─────────────────────────────────────────────────
@app.post("/searchURLAndAI")
async def searchURLAndAI(req: SearchRequest):
    cache_key = f"searchURLAndAI_{req.brand}:{req.model}:{req.year}:{','.join(sorted(req.source_ids or []))}"
    cached = await cache_get(cache_key)
    if cached: return cached

    active = sorted(
        [s for s in sources_store.values() if s["enabled"] and
         (req.source_ids is None or s["id"] in req.source_ids)],
        key=lambda s: s.get("priority", 99)
    )

    query  = f"{req.year} {req.brand} {req.model}"
    raw: list[dict] = []
    statuses: dict  = {}

    # ── Build task list ──
    # Playwright tasks run sequentially (can't share browser easily)
    # httpx tasks run in parallel
    playwright_tasks = []
    httpx_tasks      = []

    for src in active:
        sid  = src["id"]
        stype = src.get("type","httpx")

        if stype == "playwright" or sid in ("syarah.com","haraj.com.sa","ksa.Motory.com","toyota.com.sa"):
            playwright_tasks.append(sid)
        else:
            httpx_tasks.append(sid)

    # ── Run Playwright scrapers ──
    playwright_enabled = PLAYWRIGHT_OK


    async def run_playwright(sid):
        try:
            # ── تمرير brand/model/year لتفعيل _price_in_range الصحيح ──
            kw = {"brand": req.brand, "model": req.model, "year": req.year}
            used_keywords = ["مستعمل", "مستعملة", "used", "pre-owned"]
            if sid == "syarah.com":
                results = await playwright_syarah(query, max_results=20, **kw)
                # #print(f"  [Syarah]after playwright_syarah results: {len(results)}")
                # فلتر المستعملة — نريد الجديدة فقط لمقارنة الوكلاء
                results = [
                        r for r in results
                        if not any(k in str(r.get("condition", "")).lower() for k in used_keywords)
                    ]
                return sid, results
            elif sid == "haraj.com.sa":
                # حراج يجلب مستعملة — نحتفظ بها كمعلومة لكن نعلّمها
                results = await playwright_haraj(query, max_results=20, **kw)
                # #print(f"  [Haraj]after playwright_haraj results: {results}")
                    # إذا new_only: احذف المستعملة تماماً
                # results = [
                #         r for r in results
                #         if not any(k in str(r.get("condition", "")).lower() for k in used_keywords)
                #     ]
                return sid, results
            elif sid == "ksa.Motory.com":
                results = await playwright_motory(query, max_results=20, **kw)
                results = [r for r in results if "جديد" in str(r.get("condition","")).lower()
                           or r.get("condition","") in ("New","جديدة")]
                return sid, results
            elif sid == "ksa.yallamotor.com":
                results = await playwright_yallamotor(query, max_results=20, **kw)
                # #print(f"  [YallaMotor]after playwright_yallamotor results: {len(results)}")
                 # فلتر المستعملة — نريد الجديدة فقط لمقارنة الوكلاء
                results = [
                        r for r in results
                        if not any(k in str(r.get("condition", "")).lower() for k in used_keywords)
                                       ]
                # #print(f"  [YallaMotor]after filtering used: {len(results)}")
                return sid, results
            if sid == "toyota.com.sa" and req.brand.lower() == "toyota":
                model_name = " ".join(query.split()[2:]) if len(query.split()) > 2 else req.model
                return sid, await playwright_toyota_sa(model_name, year=req.year)
            elif sid == "lexus.com.sa" and req.brand.lower() == "lexus":
                model_name = " ".join(query.split()[2:]) if len(query.split()) > 2 else req.model
                results= await playwright_lexus_sa(model_name, year=req.year)
                # #print(f"  [Lexus SA]after playwright_lexus_sa results: {results}")
                return sid,results 
          
            return sid, []
        except Exception as e:
            return sid, e

    if playwright_enabled and playwright_tasks:
        # Run playwright in parallel (each opens its own browser instance)
        pw_results = await asyncio.gather(
            *[run_playwright(sid) for sid in playwright_tasks],
            return_exceptions=True
        )
        for item in pw_results:
            if isinstance(item, Exception):
                #print(f"Playwright gather error: {item}")
                continue
            sid, result = item
            if isinstance(result, Exception):
                statuses[sid] = {"ok": False, "error": str(result)[:100], "count": 0}
            else:
                statuses[sid] = {"ok": True, "count": len(result), "method": "playwright"}
                raw.extend(result)
                if result:
                    print(f"  ✅ {sid}: {len(result)} results via Playwright")
                else:
                    print(f"  ⚠️  {sid}: 0 results via Playwright")

    # ── Run httpx scrapers ──
    #print(f"Starting httpx tasks for sources: {httpx_tasks}")
    if httpx_tasks:
        hclient = httpx.AsyncClient(
            headers={"User-Agent":"Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36"},
            follow_redirects=True, timeout=SCRAPE_TIMEOUT,
        )
        async with hclient as client:
            htasks = []
            for sid in httpx_tasks:
                src = sources_store.get(sid, {})
                if   sid == "ksa.yallamotor.com":  htasks.append((sid, httpx_yallamotor(query, client)))
                else:                      htasks.append((sid, httpx_generic(src, query, client)))

            hresults = await asyncio.gather(*[t[1] for t in htasks], return_exceptions=True)
            for (sid,_), result in zip(htasks, hresults):
                if isinstance(result, Exception):
                    statuses[sid] = {"ok": False, "error": str(result)[:100], "count": 0}
                else:
                    statuses[sid] = {"ok": True, "count": len(result), "method": "httpx"}
                    raw.extend(result)


    # ── AI fallback if not enough data ──
    # use_ai = len(raw) < 5 and req.claude_ai
    use_ai =  req.claude_ai
    ai_data = None
    #print(f"  Raw listings: {raw}")
    if use_ai:
        #print(f"  ⚠️  Only {len(raw)} real listings — using AI fallback")
        try:
            ai_data = await ai_fallback(
                req.brand, req.model, req.year,
                [s["id"] for s in active], req.anthropic_key
            )
        except Exception as e:
            print(f"AI fallback error: {e}")

    # ── Classify listings into trims (NEW — trim_classifier engine) ──
    # بدلاً من رمي كل شيء في bucket واحد، نصنّف كل إعلان حسب الفئة
    dyn_trims = await fetch_official_trims(req.brand, req.model, req.year, req.anthropic_key)
    #print(f"  Fetched {len(dyn_trims)} dynamic trims for classification")

    classified = classify_and_structure(
        raw_listings=raw,
        brand=req.brand,
        model=req.model,
        year=req.year,
        dynamic_trims=dyn_trims,
        ai_data=ai_data,
    )

    # ── بناء الاستجابة النهائية ──
    final_data = {
        "vehicle": classified["vehicle"],
        "brand": classified["brand"],
        "model": classified["model"],
        "year": classified["year"],
        "searchDate": datetime.now().strftime("%B %Y"),
        "isAIFallback": use_ai,
        "officialPriceRange": classified["officialPriceRange"],
        "marketInsight": classified.get("marketInsight",
            f"تم جمع {len(raw)} إعلان من المصادر الحية — مصنّفة إلى {len(classified['trims'])} فئات"),
        "priceHistory": classified.get("priceHistory", []),
        "competitorAnalysis": classified.get("competitorAnalysis",
            {"summary":"","opportunities":[],"threats":[],"recommendation":""}),
        "trims": classified["trims"],
    }

    # Log classification summary
    for t in final_data["trims"]:
        n = len(t.get("listings", []))
        ms = t.get("matchStats", {})
        print(f"  📊 {t['officialName']}: {n} listings "
              f"[keyword={ms.get('keyword',0)}, name={ms.get('name',0)}, "
              f"price={ms.get('price_proximity',0)}, overlap={ms.get('word_overlap',0)}, "
              f"fallback={ms.get('fallback',0)}]")

    # ── حساب إحصائيات كل مصدر لكل فئة ──
    _attach_source_stats(final_data)

    final_data.update({
        "sourceStatuses": statuses,
        "scrapedCount": len(raw),
        "isAIFallback": use_ai,
        "playwrightUsed": playwright_enabled,
    })
    # Save price snapshots + DOM records (only for real scraped data)
    if not use_ai:
        await _post_search_persist(final_data, req.brand, req.model, req.year)
    # Enrich with historical trend + days-on-market (from Redis)
    await _enrich_with_history(final_data, req.brand, req.model, req.year)
    # Compute dealer pricing recommendation (uses supply + trend + DOM)
    _attach_dealer_pricing(final_data)
    await cache_set(cache_key, final_data)
    return final_data



def _attach_source_stats(data: dict):
    """
    لكل trim: يجمّع إعلانات كل مصدر ويحسب min/avg/max/count/spread
    يضيف: trim["sourceStats"] = [
      {"sourceName":"Syarah.com","min":62675,"avg":63800,"max":64975,"count":3,"spread":2300,...},
      {"sourceName":"Haraj.com.sa", ...},
    ]
    """
    brand = data.get("brand", "")
    model = data.get("model", "")

    # نطاقات ثابتة احتياطية (تُستخدم فقط لو MSRP=0 في trims_config)
    _static_ranges = {
        "yaris":         (48000,  95000),
        "yaris cross":   (70000,  150000),
        "urban cruiser":  (70000,  150000),
        "raize":         (58000,  120000),
        "veloz":         (72000,  145000),
        "rush":          (78000,  155000),
        "corolla":       (72000,  160000),
        "camry":         (95000,  175000),
        "rav4":          (90000,  200000),
        "fortuner":      (105000, 260000),
        "hilux":         (82000,  215000),
        "prado":         (145000, 340000),
        "land cruiser":  (250000, 620000),
        "patrol":        (145000, 500000),
    }

    def _in_range(price: int, msrp: int = 0) -> bool:
        """
        فلتر ذكي بناءً على MSRP إذا كان متاحاً:
          - نطاق ديناميكي: MSRP×0.85 → MSRP×1.20
          - سعر 20% فوق الرسمي = شح استثنائي في السوق
          - سعر 15% تحت الرسمي = صفقة استثنائية
        إذا لم يكن MSRP متاحاً → نطاق ثابت احتياطي.
        """
        if price <= 0:
            return False
        # ── نطاق ديناميكي من MSRP (الأدق) ──────────────────────
        if msrp and msrp > 0:
            return int(msrp * 0.85) <= price <= int(msrp * 1.20)
        # ── نطاق ثابت احتياطي ────────────────────────────────────
        model_l = (model or "").lower()
        for key, (lo, hi) in _static_ranges.items():
            if key in model_l:
                return lo <= price <= hi
        return 25000 <= price <= 700000

    for trim in data.get("trims", []):
        listings = trim.get("listings", [])
        # MSRP من trims_config — يُستخدم للفلتر الديناميكي
        trim_msrp = trim.get("officialMSRP", 0) or 0

        # ── فلتر مركزي: احذف أسعار خارج النطاق + حدّد نوع الإعلان ──
        cleaned = []
        for l in listings:
            price = l.get("price", 0)
            # if not price or not _in_range(price, trim_msrp):
            #     continue
            # تصنيف الإعلان: جديدة / مستعملة
            condition = str(l.get("condition", "")).strip()
            src_id = l.get("source", "")
            if not condition:
                if src_id in ("toyota.com.sa", "ksa.Motory.com", "ksa.yallamotor.com"):
                    l["condition"] = "جديدة"
                elif src_id == "haraj.com.sa":
                    l["condition"] = "مستعملة"

            # VAT status — تحليل ذكي بناءً على المصدر + MSRP + شكل الرقم
            if not l.get("vat_status"):
                try:
                    from scraper_playwright import infer_vat_status
                    # مرّر نص الإعلان لاكتشاف ذكر الضريبة صراحةً
                    listing_text = " ".join(filter(None, [
                        l.get("listedAs",""),
                        l.get("priceNote",""),
                        l.get("note",""),
                    ]))
                    vat = infer_vat_status(price, trim_msrp, src_id,
                                           listing_text=listing_text)
                    l["vat_status"]   = vat["vat_status"]
                    l["vat_confidence"] = vat["confidence"]
                    l["price_ex_vat"] = vat["price_ex_vat"]
                    l["price_inc_vat"]= vat["price_inc_vat"]
                    l["priceNote"]    = l.get("priceNote") or vat["reason"]

                except Exception as e:
                    # fallback بسيط
                    if src_id == "haraj.com.sa":
                        l["vat_status"] = "unknown"
                        l["priceNote"]  = l.get("priceNote") or "قد لا يشمل VAT"
                    else:
                        l["vat_status"] = "included"
                        l["priceNote"]  = l.get("priceNote") or "شامل VAT 15%"

            cleaned.append(l)

        trim["listings"] = cleaned
        listings = cleaned

        by_source: dict = {}

        for l in listings:
            price = l.get("price", 0)
            if not price:
                continue
            src_name = l.get("source") or l.get("source") or "غير محدد"
            if src_name not in by_source:
                by_source[src_name] = {
                    "sourceId":   l.get("source", ""),
                    "sourceName": src_name,
                    "color":      _source_color(l.get("source", "")),
                    "prices":     [],
                    "listings":   [],
                }
            by_source[src_name]["prices"].append(price)
            by_source[src_name]["listings"].append(l)

        source_stats = []
        for src_name, info in by_source.items():
            prices = sorted(info["prices"])
            n = len(prices)
            avg = int(sum(prices) / n) if n else 0
            source_stats.append({
                "sourceId":   info["sourceId"],
                "sourceName": src_name,
                "color":      info["color"],
                "count":      n,
                "min":        prices[0]  if prices else 0,
                "avg":        avg,
                "max":        prices[-1] if prices else 0,
                "spread":     prices[-1] - prices[0] if len(prices) > 1 else 0,
                "listings":   info["listings"],
            })

        # رتّب: الأرخص أولاً
        source_stats.sort(key=lambda x: x["min"] if x["min"] else 999999999)
        trim["sourceStats"] = source_stats

        # حدّث priceAnalysis من كل الأسعار الفعلية
        all_prices = [l.get("price", 0) for l in listings if l.get("price")]
        if all_prices:
            msrp = trim.get("officialMSRP", 0)
            market_avg = int(sum(all_prices) / len(all_prices))
            vs_pct = round((market_avg - msrp) / msrp * 100, 1) if msrp else 0
            trim["priceAnalysis"].update({
                "marketMin":    min(all_prices),
                "marketMax":    max(all_prices),
                "marketAvg":    market_avg,
                "vsOfficialPct": vs_pct,
                "listingCount": len(all_prices),
            })

        # ── supply pressure score ───────────────────────────────
        total_new  = sum(1 for l in listings if "جديد" in str(l.get("condition","")).lower() or l.get("condition","") in ("New","جديدة"))
        total_used = len(listings) - total_new
        trim["supplyStats"] = {
            "totalListings": len(listings),
            "newListings":   total_new,
            "usedListings":  total_used,
            "newPct":        round(total_new / len(listings) * 100) if listings else 0,
        }


def _source_color(source_id: str) -> str:
    return {
        "toyota.com.sa":  "#00C49A",
        "ksa.Motory.com":     "#f5a623",
        "haraj.com.sa":      "#ff8055",
        "ksa.yallamotor.com": "#a78bfa",
        "syarah.com":     "#4da6ff",
    }.get(source_id, "#6B7280")


async def _post_search_persist(data: dict, brand: str, model: str, year: int):
    """After a real search, save snapshots and DOM records to Redis."""
    for trim in data.get("trims", []):
        trim_name = trim.get("officialName", "")
        pa = trim.get("priceAnalysis", {})
        # Save weekly price snapshot
        if pa.get("marketMin") and pa.get("marketAvg"):
            await snapshot_save(brand, model, year, trim_name,
                                 pa["marketMin"], pa["marketAvg"],
                                 pa.get("marketMax", 0), pa.get("listingCount", 0))
        # Record DOM for each listing
        for l in trim.get("listings", []):
            url = l.get("url", "")
            src = l.get("source", "")
            if url and src:
                await dom_record(src, url, trim_name)


async def _enrich_with_history(data: dict, brand: str, model: str, year: int):
    """Attach price trend history and DOM stats to each trim."""
    for trim in data.get("trims", []):
        trim_name = trim.get("officialName", "")
        # Price trend
        history = await snapshot_get_history(brand, model, year, trim_name, weeks=6)
        trend   = await snapshot_calc_trend(history)
        trim["priceTrend"] = {**trend, "history": history}
        # Days on Market
        dom = await dom_avg_for_trim(brand, model, trim_name)
        trim["daysOnMarket"] = dom


# ── Car Catalog Endpoints ───────────────────────────────────────
@app.post("/catalog/fetch")
async def fetch_and_cache_catalog():
    try:
        catalog = await fetch_car_catalog()
        await cache_set("car_catalog", catalog.dict(), ttl=None)  # Cache for 24 hours
        return {"status": "success", "message": "Car catalog fetched and cached successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch catalog: {str(e)}")

@app.get("/catalog")
async def get_catalog():
    cached = await cache_get("car_catalog")
    if cached:
        return cached
    else:
        try:
         catalog = await fetch_car_catalog()
         await cache_set("car_catalog", catalog.dict(), ttl=None)  # Cache for 24 hours
         cached = await cache_get("car_catalog")
         if cached:
          return cached
         else:
          raise HTTPException(status_code=404, detail="Catalog not cached. Please fetch first using POST /catalog/fetch")
        except Exception as e:
         raise HTTPException(status_code=404, detail="Catalog not cached. Please fetch first using POST /catalog/fetch")


@app.get("/aiFallbackPrompt")
async def get_ai_fallback_prompt():
    cached = await cache_get("ai_fallback_prompt")
    if cached:
         return {
        "status": "ok",
        "prompt": cached,
       }
    else:
        raise HTTPException(status_code=404, detail="AI fallback prompt not found.")
# ── Health ──────────────────────────────────────────────────────
@app.get("/health")
async def health():
    r = await _get_redis()
    # جلب حالة الـ scrapers
    scrape_health = {}
    try:
        from scraper_playwright import get_scrape_health
        scrape_health = get_scrape_health()
    except:
        pass

    return {
        "status": "ok",
        "sources": len(sources_store),
        "enabled": sum(1 for s in sources_store.values() if s["enabled"]),
        "playwright": PLAYWRIGHT_OK,
        "redis": r is not None,
        "cache_ttl": CACHE_TTL,
        "mem_cache": len(_mem_cache),
        "scrapers": scrape_health,
    }

@app.delete("/cache")
async def clear_cache():
    await cache_clear()
    return {"ok": True}
