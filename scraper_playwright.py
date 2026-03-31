"""
HJ Motors — Playwright HTML Scraper (Fixed v2)
إصلاحات:
  1. Syarah  — URL صحيح /cars/{brand}/{model}?year={year}&type=new
               + تعمّق في NEXT_DATA props.pageProps بمسارات متعددة
  2. Motory  — URL مخصص للموديل + استخراج trims/specs من NEXT_DATA
  3. Toyota  — networkidle بدل domcontentloaded + مسارات grades/trims
  4. Haraj   — regex مقيّد بالسياق (السعر/ريال) لا كل رقم XX,XXX
  5. YallaMotor — URL صحيح + JSON parsing محسّن
  6. _price_in_range — فلتر الأسعار غير المنطقية لكل موديل
  7. _deep_find_list — بحث أعمق في NEXT_DATA JSON
"""
from bs4 import BeautifulSoup
import re
import asyncio
import re
import json
from typing import Optional
import urllib.parse
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False


# ── Helpers ──────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════
#  DYNAMIC PRICE RANGE — بناءً على MSRP الرسمي
#  أدق بكثير من النطاق الثابت — يمنع أسعار مزوّرة
# ══════════════════════════════════════════════════════════════════

# نطاقات ثابتة احتياطية (تُستخدم فقط لو MSRP=0)
_STATIC_RANGES = {
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
    "accent":        (42000,  95000),
    "tucson":        (82000,  175000),
    "sonata":        (82000,  175000),
}

def _price_in_range(price: int, brand: str = "", model: str = "",
                     msrp: int = 0,
                     low_pct: float = 0.85,
                     high_pct: float = 1.20) -> bool:
    """
    يتحقق أن السعر منطقي.

    المنطق:
    - لو MSRP معروف → نطاق ديناميكي: MSRP×0.85 → MSRP×1.20
      (−15% للخصومات الاستثنائية، +20% لشح السوق)
    - لو MSRP=0 → نطاق ثابت حسب الموديل
    - لو الموديل مجهول → 25k → 700k

    مثال:
      YX MSRP=75,670 → 64,319 → 90,804
      سعر 130,000 → مرفوض (مبالغ 72% فوق الرسمي)
      سعر 88,000  → مقبول (+16%)
    """
    if price <= 0:
        return False

    # ── نطاق ديناميكي من MSRP ──────────────────────────────────
    if msrp and msrp > 0:
        lo = int(msrp * low_pct)
        hi = int(msrp * high_pct)
        return lo <= price <= hi

    # ── نطاق ثابت احتياطي ──────────────────────────────────────
    model_l = (model or "").lower()
    for key, (lo, hi) in _STATIC_RANGES.items():
        if key in model_l:
            return lo <= price <= hi

    # ── نطاق عام ───────────────────────────────────────────────
    return 25000 <= price <= 700000


def _matches_model(title: str, brand: str, model: str) -> bool:
    """
    يتحقق أن عنوان الإعلان يطابق الموديل المطلوب بدقة.
    يمنع أسعار موديلات أخرى من الدخول.

    مثال: "Yaris Cross" لا يطابق "Yaris" (لأن cross موديل مختلف)
    """
    if not title or not model:
        return True
    title_l = title.lower()
    model_l  = model.lower()

    # قائمة الموديلات التي تشبه بعضها — يجب التمييز بينها
    # لو الموديل المطلوب "yaris"، نرفض "yaris cross"
    conflicting = {
        "yaris":        ["yaris cross", "يارس كروس"],
        "corolla":      ["corolla cross", "كورولا كروس"],
        "camry":        [],
        "land cruiser": ["land cruiser prado", "prado", "برادو"],  # prado موديل منفصل
    }
    exclusions = conflicting.get(model_l, [])
    for excl in exclusions:
        if excl in title_l:
            return False  # رفض الموديل المتعارض

    # الآن تحقق من وجود الموديل
    if model_l in title_l:
        return True

    # استثناءات: أسماء عربية
    arabic_map = {
        "yaris":        ["يارس", "ياريس"],
        "camry":        ["كامري"],
        "corolla":      ["كورولا"],
        "land cruiser": ["لاند كروزر", "لاندكروزر"],
        "prado":        ["برادو"],
        "patrol":       ["باترول"],
        "fortuner":     ["فورتشنر", "فورتشونر"],
        "rav4":         ["راف4", "rav 4"],
        "hilux":        ["هايلكس", "هيلوكس"],
        "urban cruiser": ["اربن كروزر", "urban"],
        "raize":        ["رايز"],
        "veloz":        ["فيلوز", "فيلوس"],
    }
    ar_names = arabic_map.get(model_l, [])
    return any(ar in title_l for ar in ar_names)


def _matches_year(car: dict, year: int) -> bool:
    """
    يتحقق أن إعلان السيارة يطابق السنة المطلوبة.
    يقبل ±1 سنة (مثلاً 2026 يقبل 2025 لو قريب من الرسمي).
    """
    if not year:
        return True
    for key in ["year", "model_year", "manufacture_year", "yr"]:
        val = car.get(key)
        if val:
            try:
                car_year = int(str(val)[:4])
                # قبل نفس السنة فقط (يمكن تغييرها لـ ±1 لو أردت)
                return car_year == year
            except:
                pass
    # لو ما في سنة في البيانات — اقبل (أفضل من رفض بيانات صحيحة)
    return True


def detect_vat_from_text(text: str) -> str | None:
    """
    يبحث في نص الإعلان عن ذكر صريح للضريبة.
    أدق من أي منطق رياضي — إذا الكاتب صرّح نأخذ تصريحه.
    يرجع: "included" | "excluded" | None
    """
    if not text:
        return None
    t = text.lower().strip()

    included = [
        "شامل الضريبة","شامل ضريبة","شامل vat","شامل الـ vat",
        "شامل قيمة مضافة","including vat","incl vat","inc vat",
        "vat included","with vat","شامل 15%","شامل ال 15",
        "السعر شامل","بالضريبة","ضريبة مضمنة","inclusive",
    ]
    excluded = [
        "بدون ضريبة","بدون الضريبة","قبل الضريبة","بدون vat",
        "excluding vat","excl vat","exc vat","vat excluded",
        "without vat","not including vat","بدون ال 15",
        "السعر قبل","السعر نت","net price","خارج الضريبة","exclusive",
    ]

    for p in included:
        if p in t:
            return "included"
    for p in excluded:
        if p in t:
            return "excluded"
    return None


def infer_vat_status(price: int, msrp: int = 0, source: str = "",
                      listing_text: str = "") -> dict:
    """
    يستنتج إذا كان السعر شامل VAT أم لا.

    الأولويات:
    1. نص الإعلان (أعلى دقة — إذا صرّح الكاتب)
    2. مصدر رسمي → دائماً شامل
    3. مقارنة مع MSRP الرسمي رياضياً
    4. شكل الرقم (مدوّر أم دقيق)
    """
    # ── 1. النص الصريح في الإعلان (الأولوية القصوى) ────────────
    text_vat = detect_vat_from_text(listing_text)
    if text_vat == "included":
        return {"vat_status":"included","confidence":"high",
                "price_ex_vat":int(price/1.15),"price_inc_vat":price,
                "reason":"نص الإعلان يذكر صراحةً: شامل الضريبة"}
    if text_vat == "excluded":
        return {"vat_status":"excluded","confidence":"high",
                "price_ex_vat":price,"price_inc_vat":int(price*1.15),
                "reason":f"نص الإعلان يذكر صراحةً: بدون ضريبة | شامل VAT: {int(price*1.15):,}"}

    # ── 2. مصدر رسمي → دائماً شامل ─────────────────────────────
    if source in ("toyota_sa","motory","yallamotor","syarah","lexus_sa"):
        return {"vat_status":"included","confidence":"high",
                "price_ex_vat":int(price/1.15),"price_inc_vat":price,
                "reason":"مصدر رسمي — شامل VAT 15%"}

    # ── 3. مقارنة مع MSRP ───────────────────────────────────────
    if msrp and msrp > 0:
        ratio = price / msrp
        if 0.94 <= ratio <= 1.06:
            return {"vat_status":"included","confidence":"high",
                    "price_ex_vat":int(price/1.15),"price_inc_vat":price,
                    "reason":f"قريب من الرسمي {msrp:,} ({abs(ratio-1)*100:.1f}%) → شامل VAT"}
        if abs(int(price*1.15) - msrp) / msrp < 0.03:
            return {"vat_status":"excluded","confidence":"high",
                    "price_ex_vat":price,"price_inc_vat":int(price*1.15),
                    "reason":f"{price:,} × 1.15 ≈ رسمي {msrp:,} → بدون VAT"}
        if 1.06 < ratio <= 1.20:
            return {"vat_status":"included","confidence":"medium",
                    "price_ex_vat":int(price/1.15),"price_inc_vat":price,
                    "reason":f"أعلى من الرسمي {(ratio-1)*100:.0f}% → شامل VAT + علاوة سوق"}

    # ── 4. شكل الرقم ────────────────────────────────────────────
    if price % 100 == 0:
        return {"vat_status":"excluded","confidence":"medium",
                "price_ex_vat":price,"price_inc_vat":int(price*1.15),
                "reason":f"سعر مدوّر → غالباً بدون VAT | شامل VAT: {int(price*1.15):,}"}

    return {"vat_status":"included","confidence":"medium",
            "price_ex_vat":int(price/1.15),"price_inc_vat":price,
            "reason":"رقم دقيق → يشبه سعراً رسمياً شامل VAT"}


# alias للتوافق مع الكود القديم
def _normalize_price_vat(price: int, source: str, include_vat: bool = True) -> dict:
    return infer_vat_status(price, 0, source)

def _is_installment_context(text: str) -> bool:
    """يتحقق أن الرقم في سياق تقسيط أو دفعة — لا سعر بيع كامل"""
    t = (text or "").lower()
    installment_keywords = [
        "تقسيط", "قسط", "شهري", "monthly", "installment",
        "دفعة أولى", "مقدم", "down payment", "downpayment",
        "على", "x ", "× ", "شهر", "سنة", "سنوات",
        "ايجار", "إيجار", "lease", "تأجير",
    ]
    return any(kw in t for kw in installment_keywords)


def _clean_price(text: str, context: str = "") -> int:
    """
    يستخرج السعر من النص.
    يرفض:
    - الأرقام في سياق تقسيط أو دفعة أولى
    - الأرقام خارج نطاق 20k-2M
    """
    if _is_installment_context(context or text or ""):
        return 0
    digits = re.sub(r"[^\d]", "", text or "")
    val = int(digits) if digits else 0
    return val if 20000 < val < 2000000 else 0

def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def _default_img(query: str) -> str:
    q = query.lower()
    if any(x in q for x in ["patrol","prado","land cruiser","fortuner","rav4","tahoe","gx","lx"]):
        return "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=300&q=80"
    if any(x in q for x in ["hilux","f-150","ranger","silverado"]):
        return "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=300&q=80"
    return "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=300&q=80"

def _L(source, source_name, listed_as, condition, price, mileage,
        location, seller_name, seller_type, days_ago, image, url, note,
        confidence, reason):
    return {
        "source": source, "sourceName": source_name, "listedAs": listed_as,
        "condition": condition, "price": price, "mileage": mileage,
        "location": location, "sellerName": seller_name, "sellerType": seller_type,
        "postedDaysAgo": days_ago, "imageUrl": image, "url": url,
        "priceNote": note, "matchConfidence": confidence, "matchReason": reason,
    }

def _deep_find_list(data, keys: list, min_size: int = 1, depth: int = 0):
    """بحث عميق في JSON للوصول لأول قائمة بأحد الأسماء المطلوبة"""
    if depth > 8:
        return None
    if isinstance(data, list) and len(data) >= min_size:
        if all(isinstance(x, dict) for x in data[:3]):
            return data
        return None
    if isinstance(data, dict):
        for key in keys:
            if key in data:
                r = _deep_find_list(data[key], keys, min_size, depth + 1)
                if r:
                    return r
        for v in data.values():
            if isinstance(v, (dict, list)):
                r = _deep_find_list(v, keys, min_size, depth + 1)
                if r:
                    return r
    return None

def _parse_days(date_str: str) -> int:
    if not date_str:
        return 0
    try:
        from datetime import datetime, timezone
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(date_str[:19], fmt).replace(tzinfo=timezone.utc)
                return max(0, (datetime.now(timezone.utc) - dt).days)
            except:
                continue
    except:
        pass
    return 0

def _extract_mileage(text: str) -> str:
    m = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)\s*(?:km|كم|كيلو)", text, re.IGNORECASE)
    return m.group(0).strip() if m else "غير محدد"


def _extract_year_from_text(text: str) -> int | None:
    """
    يستخرج سنة السيارة من العنوان أو النص.
    يبحث عن: 2020-2030
    مفيد لحراج اللي غالباً لا يحفظ السنة كحقل منفصل.
    """
    if not text:
        return None
    matches = re.findall(r"\b(20[2-3][0-9])\b", text)
    if matches:
        # أخذ السنة الأحدث المنطقية
        valid = [int(y) for y in matches if 2018 <= int(y) <= 2030]
        return max(valid) if valid else None
    return None


def _deep_find_all_prices(data, depth: int = 0) -> list[int]:
    """
    يبحث في عمق JSON عن كل الأسعار المنطقية.
    يُستخدم كـ last resort لو كل المسارات المعروفة فشلت.
    """
    if depth > 6:
        return []
    prices = []
    if isinstance(data, dict):
        for k, v in data.items():
            if any(pk in k.lower() for pk in ["price","سعر","cost","amount","value"]):
                try:
                    p = int(str(v).replace(",","").replace(" ",""))
                    if 20000 < p < 700000:
                        prices.append(p)
                except:
                    pass
            prices.extend(_deep_find_all_prices(v, depth+1))
    elif isinstance(data, list):
        for item in data[:20]:
            prices.extend(_deep_find_all_prices(item, depth+1))
    return prices


def _smart_find_cars(data) -> list[dict] | None:
    """
    بحث ذكي شامل في NEXT_DATA.
    يجرّب كل المسارات المعروفة + بحث عميق.
    يرجع أول قائمة فيها dicts تبدو كسيارات.
    """
    # مسارات محددة (الأسرع)
    known_paths = [
        ["props","pageProps","cars"],
        ["props","pageProps","vehicles"],
        ["props","pageProps","listings"],
        ["props","pageProps","data","cars"],
        ["props","pageProps","data","listings"],
        ["props","pageProps","data","vehicles"],
        ["props","pageProps","searchResults","cars"],
        ["props","pageProps","searchResults","listings"],
        ["props","pageProps","initialData","cars"],
        ["props","pageProps","carsData","cars"],
        ["props","pageProps","pageData","cars"],
        ["props","pageProps","models"],
        ["props","pageProps","results"],
        ["props","pageProps","items"],
    ]
    for path in known_paths:
        node = data
        for k in path:
            node = node.get(k) if isinstance(node, dict) else None
            if node is None:
                break
        if isinstance(node, list) and len(node) > 0:
            # تحقق أن القائمة تحتوي سيارات (لا نصوص فقط)
            if any(isinstance(item, dict) and
                   any(pk in item for pk in ["price","cash_price","title","name","year","model"])
                   for item in node[:3]):
                return node

    # بحث عميق كـ last resort
    return _deep_find_list(data, [
        "cars","vehicles","listings","results","items","data",
        "posts","ads","search","models","products"
    ], min_size=1)

async def _make_browser(pw):
    return await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage",
              "--disable-blink-features=AutomationControlled","--lang=ar-SA"]
    )

async def _make_context(browser):
    ctx = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="ar-SA",
        viewport={"width": 1366, "height": 768},
        extra_http_headers={"Accept-Language": "ar-SA,ar;q=0.9,en;q=0.8"},
    )
    await ctx.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    return ctx


# ══════════════════════════════════════════════════════════════════
#  SYARAH SCRAPER
# ══════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════
#  SHARED BROWSER + RETRY UTILITIES
# ══════════════════════════════════════════════════════════════════

_scrape_failures: dict[str, int] = {}   # source_id → failure count

async def _with_retry(coro_fn, source_id: str, max_retries: int = 0):
    """
    يجرّب scrape مرتين قبل الاستسلام.
    يسجّل الفشل للـ alerting.
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            result = await coro_fn()
            if result:
                _scrape_failures.pop(source_id, None)  # reset على النجاح
                return result
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait = (attempt + 1) * 2
                #print(f"  [{source_id}] محاولة {attempt+1} فشلت ({e}) — انتظر {wait}ث")
                import asyncio
                await asyncio.sleep(wait)

    # سجّل الفشل
    _scrape_failures[source_id] = _scrape_failures.get(source_id, 0) + 1
    count = _scrape_failures[source_id]
    if count >= 3:
        print(f"  🚨 [{source_id}] فشل {count} مرة متتالية — يحتاج مراجعة")
    return []


def get_scrape_health() -> dict:
    """
    يرجع حالة كل مصدر للـ /health endpoint.
    """
    return {
        "failures": dict(_scrape_failures),
        "healthy":  [s for s in ["syarah","haraj","motory","toyota_sa","yallamotor"]
                     if _scrape_failures.get(s, 0) < 3],
        "degraded": [s for s, c in _scrape_failures.items() if c >= 3],
    }


async def _open_shared_browser(pw):
    """
    يفتح browser مشترك لاستخدامه في عدة صفحات بدل فتح browser جديد لكل مصدر.
    يوفّر 60-70% من وقت التحميل.
    """
    return await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage",
              "--disable-blink-features=AutomationControlled","--lang=ar-SA",
              "--disable-extensions","--disable-plugins",
              "--blink-settings=imagesEnabled=false"]  # لا صور = أسرع
    )


async def _new_page_from_browser(browser):
    """يفتح صفحة جديدة من browser مشترك."""
    ctx = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="ar-SA",
        viewport={"width": 1366, "height": 768},
        extra_http_headers={"Accept-Language": "ar-SA,ar;q=0.9,en;q=0.8"},
    )
    await ctx.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )
    page = await ctx.new_page()
    await page.route("**/*.{png,jpg,jpeg,gif,webp,woff,woff2,ttf,svg,mp4}", lambda r: r.abort())
    return page, ctx


async def playwright_syarah(query: str, max_results: int = 15,
                              brand: str = "", model: str = "", year: int = 0) -> list[dict]:
    if not PLAYWRIGHT_OK:
        return []

    parts = query.split()
    brand_slug = brand.lower().replace(" ", "-") if brand else (parts[2].lower() if len(parts) > 2 else "toyota")
    model_slug = model.lower().replace(" ", "-") if model else (parts[3].lower() if len(parts) > 3 else parts[-1].lower())
    year_val   = year or (int(parts[0]) if parts and parts[0].isdigit() else 2026)

    urls_to_try = [
        f"https://syarah.com/filters?text={query.replace(' ', '%20')}&fromRecentSearch=1",
    ]

    async def _do_syarah():
        async with async_playwright() as pw:
            browser = await _make_browser(pw)
            ctx     = await _make_context(browser)

            api_data = []
            async def capture(response):
                if any(x in response.url for x in ["/api/","/v1/","/v2/","cars","vehicles"]):
                    ct = response.headers.get("content-type","")
                    if "json" in ct:
                        try: api_data.append((response.url, await response.json()))
                        except: pass

            page = await ctx.new_page()
            await page.route("**/*.{png,jpg,jpeg,gif,webp,woff,woff2,ttf,svg}", lambda r: r.abort())
            page.on("response", capture)

            found = []
            for url in urls_to_try:
                try:
                    #print(f"  [Syarah] {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    # try:
                    #     await page.wait_for_load_state("networkidle", timeout=30000)
                    # except:
                    #     await asyncio.sleep(3)

      
                    try:
                        await page.wait_for_selector(
                            "[class*='posts-card'][class*='posts-card-body'][class*='car-card'],[class*='CarCard'],[class*='listing-card'],article,[data-car-id]",
                            timeout=30000)
                    except:
                        await asyncio.sleep(3)
                  
                    

                      # 🔥 أهم سطر
                    html = await page.evaluate("""
                    () => {
                        document.querySelectorAll('script').forEach(e => e.remove());
                        document.querySelectorAll('style').forEach(e => e.remove());
                        return document.body.innerHTML;
                    }
                    """)
                    # html = await page.content()
                    #print(f"  [Syarah] html: {html}")
                    found = _syarah_from_next_data(html, brand, model, year_val)
                    #print(f" _syarah_from_next_data: {len(found)} results")
                    if found: break
                    for _, body in api_data:
                        found.extend(_syarah_from_api(body, brand, model))

                    #print(f" _syarah_from_api: {len(found)} results")    
                    if found: break
                    found = _syarah_from_html(html, brand, model)
                    #print(f" _syarah_from_html: {len(found)} results") 
                    if found: break
                except Exception as e:
                    print(f"  [Syarah] url error: {e}")
            await browser.close()
            return found

    results = await _with_retry(_do_syarah, "syarah")
    #print(f"  [Syarah]_do_syarah results: {results}")
    return [r for r in results if _price_in_range(r["price"], brand, model)][:max_results]


def _syarah_from_next_data(html, brand, model, year):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m: return []
    try: data = json.loads(m.group(1))
    except: return []

    paths = [
        ["props","pageProps","cars"],
        ["props","pageProps","vehicles"],
        ["props","pageProps","listings"],
        ["props","pageProps","data","cars"],
        ["props","pageProps","data","listings"],
        ["props","pageProps","initialData","cars"],
        ["props","pageProps","carsData","cars"],
        ["props","pageProps","searchResults"],
    ]
    cars = _smart_find_cars(data)
    if not cars: return []

    out = []
    for car in cars[:20]:
        if not isinstance(car,dict): continue
        # ── فلتر السنة ────────────────────────────────────────
        if not _matches_year(car, year): continue
        # ── فلتر الموديل ──────────────────────────────────────
        title_check = car.get("title") or car.get("name") or car.get("car_name") or ""
        if not _matches_model(title_check, brand, model): continue

        price = 0
        for pk in ["price","cash_price","selling_price","salePrice","cashPrice","amount"]:
            raw = car.get(pk)
            if raw:
                price = _clean_price(str(raw))
                if price: break
        if not price: continue
        vat = _normalize_price_vat(price, "syarah")
        is_new = car.get("is_new") or car.get("type")=="new" or not car.get("mileage")
        out.append(_L("syarah","Syarah.com",
            _clean_text(car.get("title") or car.get("name") or f"{brand} {model}"),
            "جديدة" if is_new else "مستعملة", price,
            f"{car.get('mileage',0):,} كم" if car.get("mileage") else "0 كم",
            car.get("city") or car.get("region") or "غير محدد",
            car.get("seller_name") or "Syarah",
            "dealer" if car.get("is_dealer") else "individual",
            _parse_days(car.get("created_at") or ""),
            car.get("main_image") or car.get("image") or _default_img(f"{brand} {model}"),
            f"https://syarah.com/filters?text={car.get('id','')}",
            "", "high", "Syarah — NEXT_DATA JSON"))
    return out


def _syarah_from_api(data, brand, model):
    cars = _smart_find_cars(data)
    if not cars: return []
    out = []
    for car in cars[:15]:
        if not isinstance(car,dict): continue
        price = 0
        for pk in ["price","cash_price","selling_price","salePrice"]:
            if car.get(pk):
                price = _clean_price(str(car[pk]))
                if price: break
        if not price: continue
        out.append(_L("syarah","Syarah.com",
            _clean_text(car.get("title") or car.get("name") or f"{brand} {model}"),
            "جديدة" if not car.get("mileage") else "مستعملة", price,
            "0 كم", car.get("city") or "غير محدد",
            car.get("seller_name") or "Syarah", "dealer", 0,
            _default_img(f"{brand} {model}"),
            f"https://syarah.com/cars/{car.get('id','')}",
            "", "high", "Syarah — API"))
    return out



def _syarah_from_html(html, brand, model):
    out = []
    seen = set()

    soup = BeautifulSoup(html, "html.parser")
    #print(f" [Syarah] Parsed HTML, looking for price blocks...")
    # =========================
    # 1️⃣ PRIMARY: CSS SELECTOR
    # =========================
    price_blocks = soup.select('[id^="posts-card-cash-price"]')
    
    #print(f" [Syarah] Found {price_blocks} price blocks with CSS selector")
    for block in price_blocks:
        #print(f" [Syarah] Processing price block: {block}")
        try:
            price_tag = block.select_one('.font-bold')
            #print(f" [Syarah] Found price tag: {price_tag}")
            if not price_tag:
                continue

            raw_price = price_tag.get_text(strip=True)
            #print(f" [Syarah] Raw price: {raw_price}")
            price = _clean_price(raw_price)
            #print(f" [Syarah] Cleaned price: {price}")
            if not price:
                continue

            # ❌ فلترة التقسيط (حماية قوية)
            full_text = block.get_text(" ", strip=True)
            if "التقسيط" in full_text or "شهري" in full_text:
                continue

            if price < 10000:
                continue

            if price in seen:
                continue

            if not _price_in_range(price, brand, model):
                continue

            seen.add(price)

            card = block.find_parent("a")

            title = f"{brand} {model}"
            url = ""
            mileage = "غير محدد"

            if card:
                url = card.get("href", "")

                title_tag = card.select_one("h2")
                if title_tag:
                    title = title_tag.get_text(strip=True)

                mileage_tag = card.select_one('#posts-card-tag-odometer span:last-child')
                if mileage_tag:
                    mileage = mileage_tag.get_text(strip=True)

            out.append(_L(
                "syarah",
                "Syarah.com",
                title.strip(),
                "مستعملة",
                price,
                mileage,
                "غير محدد",
                "Syarah",
                "dealer",
                0,
                _default_img(f"{brand} {model}"),
                f"https://syarah.com{url}" if url else "",
                "",
                "low",
                "Syarah — HYBRID CSS"
            ))

        except Exception:
            continue

    # =========================
    # 2️⃣ FALLBACK: REGEX (ONLY IF EMPTY)
    # =========================
    if not out:
        patterns = [
            r'سعر الكاش[^\d]{0,30}([\d,]{5,8})',
            r'cash price[^\d]{0,30}([\d,]{5,8})',
            r'(?:﷼|SAR)\s*([\d,]{5,8})',
        ]

        for pat in patterns:
            for raw in re.findall(pat, html, re.IGNORECASE):

                context_match = re.search(r'.{0,80}' + re.escape(str(raw)) + r'.{0,80}', html)
                context = context_match.group() if context_match else ""

                # ❌ فلترة التقسيط
                if re.search(r'شهري|التقسيط', context):
                    continue

                price = _clean_price(str(raw), context=context)

                if not price or price < 10000:
                    continue

                if price in seen:
                    continue

                if not _price_in_range(price, brand, model):
                    continue

                seen.add(price)

                out.append(_L(
                    "syarah",
                    "Syarah.com",
                    f"{brand} {model}".strip(),
                    "مستعملة",
                    price,
                    "غير محدد",
                    "غير محدد",
                    "Syarah",
                    "dealer",
                    0,
                    _default_img(f"{brand} {model}"),
                    f"https://syarah.com/search?q={brand}+{model}",
                    "",
                    "low",
                    "Syarah — HYBRID REGEX"
                ))

    return out
# ══════════════════════════════════════════════════════════════════
#  HARAJ SCRAPER
# ══════════════════════════════════════════════════════════════════

async def playwright_haraj(query: str, max_results: int = 15,
                             brand: str = "", model: str = "", year: int = 0) -> list[dict]:
    if not PLAYWRIGHT_OK:
        return []

    year_str = str(year) if year else ""
    query_ar = f"{brand} {model} {year_str}".strip()
    urls_to_try = [
        f"https://haraj.com.sa/search/{query.replace(' ','%20')}",
    ]
    async def _do_haraj():
        async with async_playwright() as pw:
            browser = await _make_browser(pw)
            ctx     = await _make_context(browser)
            page    = await ctx.new_page()
            # 🚀 تسريع (إلغاء الصور والخطوط)
            await page.route(
                "**/*.{png,jpg,jpeg,gif,webp,woff,woff2,ttf,svg}",
                lambda r: r.abort()
            )
            found = []
            for url in urls_to_try:
                try:
                    #print(f"  [Haraj] {url}")
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    try:
                        await page.wait_for_selector(
                            "[class*='post'],[class*='item'],[class*='card'],.post-title",
                            timeout=8000)
                    except:
                        await asyncio.sleep(3)

                    html = await page.evaluate("""
                    () => {
                        document.querySelectorAll('script').forEach(e => e.remove());
                        document.querySelectorAll('style').forEach(e => e.remove());
                        return document.body.innerHTML;
                    }
                    """)
                    # html = await page.content()
                    #print(f"  [Haraj] html: {html}")
                    found = _haraj_from_next_data(html, brand, model, year)
                    if found: break
                    found = _haraj_from_html(html, brand, model)
                    if found: break
                except Exception as e:
                    print(f"  [Haraj] url error: {e}")
            await browser.close()
            return found

    results = await _with_retry(_do_haraj, "haraj")

    return [r for r in results if _price_in_range(r["price"], brand, model)][:max_results]


# =========================================
# 🔥 استخراج NEXT_DATA (الأساسي)
# =========================================
def _haraj_from_next_data(html, brand, model, year):
    m = re.search(
        r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE
    )
    if not m:
        return []

    try:
        data = json.loads(m.group(1))
    except:
        return []

    posts = _haraj_smart_find_cars(data)
    if not posts:
        return []

    out = []
    seen = set()

    for post in posts[:30]:
        if not isinstance(post, dict):
            continue

        title = _clean_text(post.get("title") or post.get("subject") or "")

        # ── فلترة الموديل ─────────────────────
        if not _matches_model(title, brand, model):
            continue

        # ── السنة ───────────────────────────
        post_year = (
            post.get("year")
            or post.get("model_year")
            or _extract_year_from_text(title)
        )
        if post_year and year and int(str(post_year)[:4]) != year:
            continue

        # ── السعر ───────────────────────────
        price = 0
        for pk in ["price", "amount", "value", "salePrice"]:
            raw = post.get(pk)
            if raw:
                price = _clean_price(str(raw))
                if price:
                    break

        if not price:
            body = " ".join(str(post.get(k) or "") for k in ["title","body","content","description"])
            price = _extract_price_from_text(body, brand, model)

        if not price or not _price_in_range(price, brand, model):
            continue

        if price in seen:
            continue
        seen.add(price)

        # ── النص ────────────────────────────
        body_txt = _clean_text(
            post.get("body")
            or post.get("content")
            or post.get("description")
            or title
        )

        vat = infer_vat_status(price, 0, "haraj", listing_text=body_txt)

        # ── الصورة ──────────────────────────
        imgs = post.get("images")
        if isinstance(imgs, list) and imgs:
            img = imgs[0]
        else:
            img = _default_img(title)

        # ── الرابط ──────────────────────────
        url = post.get("url") or f"https://haraj.com.sa/{post.get('id','')}"

        out.append(_L(
            "haraj", "Haraj.com.sa",
            title or f"{brand} {model}",
            "مستعملة",
            price,
            _extract_mileage(body_txt),
            post.get("city") or "غير محدد",
            post.get("username") or "بائع",
            "individual",
            _parse_days(post.get("created_at") or ""),
            img,
            url,
            body_txt[:80],
            "medium",
            "حراج — NEXT_DATA"
        ))

    return out


# =========================================
# 🔥 fallback HTML (عند فشل NEXT_DATA)
# =========================================
def _haraj_from_html(html, brand, model):
    out = []
    seen = set()

    patterns = [
        r'(?:السعر|بسعر|Price|يباع)[^\d]{0,20}([\d,،]{5,8})',
        r'([\d,،]{5,8})\s*(?:ريال|SAR|﷼)',
        r'(?:ريال|SAR|﷼)\s*([\d,،]{5,8})',
        r'(\d{2,3}(?:,\d{3})+)',  # 🔥 جديد
    ]

    for pat in patterns:
        for raw in re.findall(pat, html, re.IGNORECASE):
            price = _clean_price(str(raw))

            if not price or price in seen:
                continue

            if not _price_in_range(price, brand, model):
                continue

            seen.add(price)

            out.append(_L(
                "haraj",
                "Haraj.com.sa",
                f"{brand} {model}".strip(),
                "مستعملة",
                price,
                "غير محدد",
                "غير محدد",
                "بائع حراج",
                "individual",
                0,
                _default_img(f"{brand} {model}"),
                f"https://haraj.com.sa/search/{brand}+{model}",
                "لا يمكن التحقق من الضريبة",
                "low",
                "حراج — HTML"
            ))

    return out


# =========================================
# 🔥 استخراج السعر من النص
# =========================================
def _extract_price_from_text(text, brand="", model=""):
    for pat in [
        r'(?:السعر|بسعر|يباع)[^\d]{0,20}([0-9,،]+)',
        r'([0-9,،]{5,8})\s*(?:ريال|SAR|﷼)',
        r'(\d{2,3}(?:,\d{3})+)',  # 🔥 قوي
    ]:
        for raw in re.findall(pat, text, re.IGNORECASE):
            p = _clean_price(raw)
            if p and _price_in_range(p, brand, model):
                return p
    return 0


# =========================================
# 🔥 استخراج السيارات من JSON (ذكي جدًا)
# =========================================
def _haraj_smart_find_cars(data):
    # المسار الشائع
    try:
        return data["props"]["pageProps"]["posts"]
    except:
        pass

    # fallback ذكي
    stack = [data]
    while stack:
        item = stack.pop()

        if isinstance(item, dict):
            for k, v in item.items():
                if isinstance(v, list) and v:
                    if isinstance(v[0], dict):
                        keys = v[0].keys()
                        if any(x in keys for x in ["price","title","subject"]):
                            return v
                stack.append(v)

        elif isinstance(item, list):
            stack.extend(item)

    return []
# ══════════════════════════════════════════════════════════════════
#  TOYOTA.COM.SA SCRAPER
# ══════════════════════════════════════════════════════════════════

async def playwright_toyota_sa(model: str, year: int = 0) -> list[dict]:
    if not PLAYWRIGHT_OK:
        return []

    slug = model.lower().replace(" ","-")
    urls = [
         f"https://www.toyota.com.sa/en/vehicles/passenger/{slug}",
         f"https://www.toyota.com.sa/en/vehicles/commercial/{slug}",
         f"https://www.toyota.com.sa/en/vehicles/suv/{slug}",
    ]
    async def _do_toyota():
        async with async_playwright() as pw:
            browser = await _make_browser(pw)
            ctx     = await _make_context(browser)
            page    = await ctx.new_page()
            await page.route("**/*.{png,jpg,jpeg,gif,webp,woff,woff2,mp4,svg}", lambda r: r.abort())
            found = []
            for url in urls:
                try:
                    #print(f"  [Toyota SA] {url}")
                    resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    if not resp or resp.status >= 400: continue
                    try:
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    except:
                        await asyncio.sleep(3)
                    # html = await page.content()
                    html = await page.evaluate("""
                    () => {
                        document.querySelectorAll('script').forEach(e => e.remove());
                        document.querySelectorAll('style').forEach(e => e.remove());
                        return document.body.innerHTML;
                    }
                    """)
                    #print(f"  [Toyota SA] html: {html}")
                    found = _toyota_from_next_data(html, model)
                    #print(f" _toyota_from_next_data: {len(found)} results")
                    if found: break
                    found = _toyota_from_html(html, model)
                    #print(f" _toyota_from_html: {len(found)} results")
                    if found: break
                except Exception as e:
                    print(f"  [Toyota SA] url error: {e}")
            await browser.close()
            return found

    results = await _with_retry(_do_toyota, "toyota_sa")
    return results


def _toyota_from_next_data(html, model):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m: return []
    try: data = json.loads(m.group(1))
    except: return []

    paths = [
        ["props","pageProps","grades"],
        ["props","pageProps","trims"],
        ["props","pageProps","variants"],
        ["props","pageProps","model","grades"],
        ["props","pageProps","data","grades"],
        ["props","pageProps","modelData","grades"],
        ["props","pageProps","pageData","grades"],
    ]
    trims = None
    for path in paths:
        node = data
        for k in path:
            node = node.get(k) if isinstance(node,dict) else None
            if node is None: break
        if isinstance(node,list) and len(node) > 0:
            trims = node; break
    if not trims:
        trims = _smart_find_cars(data)
    if not trims: return []

    out = []
    for trim in trims[:12]:
        if not isinstance(trim,dict): continue
        price = 0
        for pk in ["price","cashPrice","msrp","startingPrice","listPrice","selling_price","base_price","amount"]:
            raw = trim.get(pk)
            if raw:
                price = _clean_price(str(raw))
                if price: break
        if not price: continue
        name = _clean_text(trim.get("name") or trim.get("gradeName") or trim.get("grade") or
                           trim.get("trimName") or trim.get("title") or model)
        out.append(_L("toyota_sa","Toyota.com.sa (رسمي)",
            f"Toyota {model} {name} — سعر رسمي",
            "جديدة", price, "0 كم", "المملكة العربية السعودية",
            "هاشم جميل موتورز — المعتمد","official_dealer", 0,
            _default_img(model),
            f"https://www.toyota.com.sa/en/models/{model.lower().replace(' ','-')}",
            "سعر رسمي من الوكيل المعتمد",
            "high", f"Toyota.com.sa — فئة {name}"))
    return out


def _toyota_from_html(html, model):
 
    out = []

    # 🔥 تنظيف HTML أولًا
    seen_prices = set()

    # 🔥 تنظيف HTML (إزالة السكربتات والستايل)
    html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 🔥 قائمة التريمات
    TRIMS = [
        "Y Limited","Y Plus","Y","YX","SE","LE","XLE",
        "Grande","Lumiere","GXR","VXR","TXL","VX",
        "Platinum","SL","SV"
    ]

    seen = set()

    # ✅ البحث بالـ HTML الجديد (pricing div)
    soup = BeautifulSoup(html, "html.parser")

    # 🔥 رابط الموديل
    model_url = f"https://www.toyota.com.sa/en/models/{model.lower().replace(' ','-')}"

    # 🔥 البحث فقط داخل pricing div
     # 🔥 المرور على كل كرت سيارة
    for card in soup.find_all("div", class_="tt-car-item"):

        try:
            # ✅ اسم الفئة (Trim)
            title_tag = card.find("div", class_="title")
            trim_name = ""
            if title_tag:
                h3 = title_tag.find("h3")
                if h3:
                    trim_name = _clean_text(h3.get_text())

            # ✅ السعر
            pricing_div = card.find("div", class_="pricing")
            if not pricing_div:
                continue

            price_tag = pricing_div.find("div", class_="price-tag")
            if not price_tag:
                continue

            h4 = price_tag.find("h4")
            if not h4:
                continue

            price_match = re.search(r'([\d,]{5,8})', h4.get_text())
            if not price_match:
                continue

            price = _clean_price(price_match.group(1))

            if not price or not _price_in_range(price, "toyota", model):
                continue

            # ✅ الصورة
            img_url = None
            img_tag = card.find("img", class_="front")
            if img_tag and img_tag.get("src"):
                src = img_tag.get("src")
                if src.startswith("/"):
                    img_url = "https://www.toyota.com.sa" + src
                else:
                    img_url = src

            if not img_url:
                img_url = _default_img(model)

            # منع التكرار
            key = (trim_name.lower(), price)
            if key in seen:
                continue
            seen.add(key)

            # label (اختياري)
            label_tag = pricing_div.find("span", class_="label")
            label_text = label_tag.get_text(strip=True) if label_tag else ""

            # بناء العنوان
            title = f"Toyota {model} {trim_name} — سعر رسمي"
            if label_text:
                title = f"Toyota {model} {trim_name} — {label_text} — سعر رسمي"

            out.append(_L(
                "toyota_sa",
                "Toyota.com.sa (رسمي)",
                title,
                "جديدة",
                price,
                "0 كم",
                "المملكة العربية السعودية",
                "عبداللطيف جميل — المعتمد",
                "official_dealer",
                0,
                img_url,
                model_url,
                "مستخرج من HTML (card)",
                "high",
                "Toyota.com.sa — HTML"
            ))

            if len(out) >= 10:
                break

        except Exception as e:
            #print(f"[Toyota card parsing error] {e}")
            continue
    return out

# ══════════════════════════════════════════════════════════════════
#  MOTORY SCRAPER
# ══════════════════════════════════════════════════════════════════

async def playwright_motory(query: str, max_results: int = 10,
                             brand: str = "", model: str = "", year: int = 0) -> list[dict]:
    if not PLAYWRIGHT_OK:
        return []

    b = brand.lower().replace(" ","-") if brand else "toyota"
    mo = model.lower().replace(" ","-") if model else "yaris"
    yr = year or 2026

    urls_to_try = [
        f"https://ksa.motory.com/en/new-cars/{b}/{mo}/{yr}"
        # f"https://motory.com/sa/new-cars/{b}/{mo}/{yr}",
        # f"https://motory.com/sa/new-cars/{b}/{mo}?year={yr}",
        # f"https://motory.com/sa/new-cars/{b}/{mo}",
        # f"https://motory.com/sa/new-cars/search?q={b}+{mo}+{yr}",
    ]
    async def _do_motory():
        async with async_playwright() as pw:
            browser = await _make_browser(pw)
            ctx     = await _make_context(browser)
            page    = await ctx.new_page()
            await page.route("**/*.{png,jpg,jpeg,gif,webp,woff}", lambda r: r.abort())
            found = []
            for url in urls_to_try:
                try:
                    #print(f"  [Motory] {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=8000)
                    except:
                        await asyncio.sleep(3)
                    html = await page.content()
                    found = _motory_from_next_data(html, brand, model, yr)
                    if found: break
                    found = _motory_from_html(html, brand, model)
                    if found: break
                except Exception as e:
                    print(f"  [Motory] url error: {e}")
            await browser.close()
            return found

    results = await _with_retry(_do_motory, "motory")

    return [r for r in results if _price_in_range(r["price"], brand, model)][:max_results]


def _motory_from_next_data(html, brand, model, year):
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m: return []
    try: data = json.loads(m.group(1))
    except: return []

    paths = [
        ["props","pageProps","trims"],
        ["props","pageProps","specs"],
        ["props","pageProps","variants"],
        ["props","pageProps","cars"],
        ["props","pageProps","data","trims"],
        ["props","pageProps","data","cars"],
        ["props","pageProps","searchResults","cars"],
    ]
    items = _smart_find_cars(data)
    if not items: return []

    out = []
    for item in items[:15]:
        if not isinstance(item,dict): continue
        # ── فلتر السنة والموديل ───────────────────────────────
        if not _matches_year(item, year): continue
        title_check = item.get("name") or item.get("title") or ""
        if not _matches_model(title_check, brand, model): continue

        price = 0
        for pk in ["price","min_price","starting_price","startingPrice","list_price","msrp","cash_price"]:
            raw = item.get(pk)
            if raw:
                price = _clean_price(str(raw))
                if price: break
        if not price: continue
        vat = _normalize_price_vat(price, "motory")
        name = _clean_text(item.get("name") or item.get("title") or item.get("trim_name") or
                           item.get("grade") or f"{brand} {model}")
        out.append(_L("motory","Motory.com",
            name, "جديدة", price, "0 كم",
            "المملكة العربية السعودية",
            item.get("dealer") or item.get("seller") or "Motory",
            "dealer", 0,
            item.get("image") or item.get("thumbnail") or _default_img(f"{brand} {model}"),
            f"https://motory.com/sa/cars/{item.get('slug','')}",
            "", "high", "Motory — NEXT_DATA"))
    return out


def _motory_from_html(html, brand, model):
    out = []
    seen = set()
    for pat in [
        r'(?:SAR|ريال|﷼)\s*([\d,]{5,8})',
        r'([\d,]{5,8})\s*(?:SAR|ريال|﷼)',
        r'"price":\s*(\d{5,7})',
    ]:
        for raw in re.findall(pat, html, re.IGNORECASE):
            price = _clean_price(str(raw))
            if not price or price in seen: continue
            if not _price_in_range(price, brand, model): continue
            seen.add(price)
            out.append(_L("motory","Motory.com",
                f"{brand} {model}".strip(),"جديدة",price,"0 كم",
                "المملكة العربية السعودية","Motory","dealer",0,
                _default_img(f"{brand} {model}"),
                f"https://motory.com/sa/new-cars/{brand.lower()}/{model.lower()}",
                "","medium","Motory — HTML"))
    return out


# ══════════════════════════════════════════════════════════════════
#  YALLAMOTOR SCRAPER
# ══════════════════════════════════════════════════════════════════

async def playwright_yallamotor(query: str, max_results: int = 10,
                                  brand: str = "", model: str = "", year: int = 0) -> list[dict]:
    import httpx
    b = brand.lower() if brand else "toyota"
    mo = model.lower().replace(" ","-") if model else "yaris"
    yr = year or 2026

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept": "application/json, text/html, */*",
        "Referer": "https://www.yallamotor.com",
        "Accept-Language": "ar,en;q=0.9",
    }
    urls = [
        f"https://ksa.yallamotor.com/ar/new-cars?query={query.replace(' ','+')}",
    ]
    results = []
    async with httpx.AsyncClient(timeout=20, headers=headers, follow_redirects=True) as client:
        for url in urls:
            try:
                r = await client.get(url)
                ct = r.headers.get("content-type","")
                #print(f"  [YallaMotor] {url.split('yallamotor.com')[1][:50]} → {r.status_code}")
                if r.status_code != 200: continue

                if "json" in ct:
                    data = r.json()
                    items = _smart_find_cars(data)
                    for item in (items or [])[:max_results]:
                        if not isinstance(item,dict): continue
                        price = 0
                        for pk in ["price","min_price","starting_price","cashPrice"]:
                            raw = item.get(pk)
                            if raw:
                                price = _clean_price(str(raw))
                                if price: break
                        if not price or not _price_in_range(price, brand, model): continue
                        results.append(_L("yallamotor","YallaMotor",
                            _clean_text(item.get("name") or item.get("title") or f"{brand} {model}"),
                            "جديدة",price,"0 كم","المملكة العربية السعودية",
                            item.get("dealer") or "YallaMotor","dealer",0,
                            item.get("image") or _default_img(f"{brand} {model}"),
                            f"https://www.yallamotor.com{item.get('url','') or '/new-cars/'+b+'/'+mo}",
                            "","high","YallaMotor — API"))
                    if results: break
                else:
                    html = r.text
                    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
                    if m:
                        try:
                            data = json.loads(m.group(1))
                            items = _deep_find_list(data, ["cars","trims","variants","results"])
                            for item in (items or [])[:max_results]:
                                if not isinstance(item,dict): continue
                                for pk in ["price","min_price","starting_price"]:
                                    raw = item.get(pk)
                                    if raw:
                                        price = _clean_price(str(raw))
                                        if price and _price_in_range(price, brand, model):
                                            results.append(_L("yallamotor","YallaMotor",
                                                _clean_text(item.get("name") or f"{brand} {model}"),
                                                "جديدة",price,"0 كم",
                                                "المملكة العربية السعودية",
                                                "YallaMotor","dealer",0,
                                                _default_img(f"{brand} {model}"),
                                                url,"","high","YallaMotor — NEXT_DATA"))
                                            break
                            if results: break
                        except: pass
            except Exception as e:
                print(f"  [YallaMotor] {e}")
    return results[:max_results]


# ── Runner للاختبار ──────────────────────────────────────────────

async def run_test(query: str = "2026 Toyota Yaris"):
    brand, model, year = "Toyota", "Yaris", 2026
    #print(f"\n{'='*55}\nاختبار: {query}\n{'='*55}")
    for name, coro in [
        ("Syarah",     playwright_syarah(query, brand=brand, model=model, year=year)),
        ("Haraj",      playwright_haraj(query, brand=brand, model=model, year=year)),
        ("Toyota SA",  playwright_toyota_sa(model, year=year)),
        ("Motory",     playwright_motory(query, brand=brand, model=model, year=year)),
    ]:
        results = await coro
        print(f"\n[{name}] {len(results)} نتيجة")
        for r in results[:3]:
            print(f"   {r['listedAs'][:40]} → {r['price']:,} | {r['matchReason']}")

if __name__ == "__main__":
    asyncio.run(run_test("2026 Toyota Yaris"))
