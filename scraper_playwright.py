"""
HJ Motors — Playwright HTML Scraper
يفتح المتصفح الحقيقي ويسحب الأسعار من Syarah وHaraj وMotory
"""

import asyncio
import re
import json
from typing import Optional

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

# ── Helpers ────────────────────────────────────────────────────
def _clean_price(text: str) -> int:
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

# ── Syarah Scraper ──────────────────────────────────────────────
async def playwright_syarah(query: str, max_results: int = 15) -> list[dict]:
    """
    يفتح syarah.com/filters?text=QUERY ويسحب بطاقات السيارات
    يتعامل مع الـ JS rendering
    """
    if not PLAYWRIGHT_OK:
        return []

    results = []
    url = f"https://syarah.com/filters?text={query.replace(' ', '%20')}"

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled","--lang=ar-SA"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="ar-SA",
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()

            # منع الصور والخطوط لتسريع التحميل
            await page.route("**/*.{png,jpg,jpeg,gif,webp,woff,woff2,ttf}", lambda r: r.abort())

            print(f"  [Syarah] Opening: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)

            # انتظر ظهور بطاقات السيارات
            try:
                await page.wait_for_selector(
                    "[class*='car-card'], [class*='CarCard'], [class*='listing'], [data-testid*='car']",
                    timeout=10000
                )
            except:
                # حاول انتظار أي محتوى
                await asyncio.sleep(3)

            # اسحب الـ HTML
            html = await page.content()
            await browser.close()

            # استخرج بيانات السيارات من JSON مضمّن في الصفحة
            json_results = _extract_syarah_json(html, query)
            if json_results:
                return json_results[:max_results]

            # fallback: parse HTML مباشرة
            html_results = _parse_syarah_html(html, query)
            return html_results[:max_results]

    except Exception as e:
        print(f"  [Syarah Playwright] Error: {e}")
        return []

def _extract_syarah_json(html: str, query: str) -> list[dict]:
    """يبحث عن JSON مضمّن في الصفحة (Next.js __NEXT_DATA__ أو window.__INITIAL_STATE__)"""
    results = []

    # Next.js data
    patterns = [
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
        r'window\.__DATA__\s*=\s*(\{.*?\});',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            continue
        try:
            data = json.loads(match.group(1))
            # تنقّل في الـ JSON للوصول للسيارات
            cars = _dig_json(data, ["cars","listings","vehicles","results","data","items"])
            if not cars:
                continue
            for car in cars[:15]:
                price = _clean_price(str(car.get("price") or car.get("selling_price") or car.get("cash_price") or ""))
                if not price:
                    continue
                results.append(_L(
                    source="syarah", source_name="Syarah.com",
                    listed_as=_clean_text(car.get("title") or car.get("name") or car.get("car_name") or query),
                    condition="مستعملة" if (car.get("is_used") or car.get("type") == "used") else "جديدة",
                    price=price,
                    mileage=f"{car.get('mileage',0):,} كم" if car.get("mileage") else "0 كم",
                    location=car.get("city") or car.get("region") or "غير محدد",
                    seller_name=car.get("seller_name") or car.get("dealer_name") or "Syarah",
                    seller_type="dealer" if car.get("is_dealer") else "individual",
                    days_ago=0,
                    image=car.get("main_image") or car.get("image") or car.get("thumbnail") or _default_img(query),
                    url=f"https://syarah.com/cars/{car.get('id','')}",
                    note=_clean_text((car.get("description") or ""))[:80],
                    confidence="high", reason="Syarah — بيانات JSON مباشرة",
                ))
            if results:
                break
        except Exception as e:
            print(f"  [Syarah JSON parse] {e}")
            continue

    return results

def _parse_syarah_html(html: str, query: str) -> list[dict]:
    """تحليل HTML مباشرة باستخدام regex — fallback"""
    results = []

    # أسعار الـ cash
    # نمط: سعر الكاش (شامل الضريبة) ﷼ 64,975
    price_blocks = re.findall(
        r'(?:سعر الكاش|cash price)[^\d]*?([\d,]{5,})',
        html, re.IGNORECASE | re.DOTALL
    )

    # أو نمط أرقام بجانب ﷼
    if not price_blocks:
        price_blocks = re.findall(r'﷼\s*([\d,]+)', html)

    # عناوين السيارات
    title_blocks = re.findall(
        r'(?:تويوتا|Toyota|نيسان|هيونداي|كيا)[^"<]{3,60}(?:2023|2024|2025|2026)',
        html, re.IGNORECASE
    )

    seen_prices = set()
    for i, raw_price in enumerate(price_blocks[:15]):
        price = _clean_price(raw_price)
        if not price or price in seen_prices:
            continue
        seen_prices.add(price)

        title = title_blocks[i] if i < len(title_blocks) else query
        results.append(_L(
            source="syarah", source_name="Syarah.com",
            listed_as=_clean_text(title),
            condition="جديدة",
            price=price,
            mileage="غير محدد",
            location="غير محدد",
            seller_name="Syarah",
            seller_type="dealer",
            days_ago=0,
            image=_default_img(query),
            url=f"https://syarah.com/filters?text={query.replace(' ','%20')}",
            note="",
            confidence="medium", reason="Syarah — استخراج HTML",
        ))

    return results

# ── Haraj Scraper ───────────────────────────────────────────────
async def playwright_haraj(query: str, max_results: int = 15) -> list[dict]:
    """
    يفتح haraj.com.sa ويسحب إعلانات السيارات
    """
    if not PLAYWRIGHT_OK:
        return []

    results = []
    # Haraj يستخدم عنوان مختلف للبحث
    url = f"https://haraj.com.sa/search/{query.replace(' ','+')}"

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                locale="ar-SA",
            )
            page = await context.new_page()
            await page.route("**/*.{png,jpg,jpeg,gif,webp,woff,woff2}", lambda r: r.abort())

            print(f"  [Haraj] Opening: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)

            try:
                await page.wait_for_selector(
                    "[class*='post'], [class*='item'], [class*='card'], .result",
                    timeout=10000
                )
            except:
                await asyncio.sleep(3)

            html = await page.content()
            await browser.close()

            # استخرج JSON مضمّن
            json_results = _extract_haraj_json(html, query)
            if json_results:
                return json_results[:max_results]

            # HTML fallback
            html_results = _parse_haraj_html(html, query)
            return html_results[:max_results]

    except Exception as e:
        print(f"  [Haraj Playwright] Error: {e}")
        return []

def _extract_haraj_json(html: str, query: str) -> list[dict]:
    results = []
    patterns = [
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        r'window\.__DATA__\s*=\s*(\{.*?\})\s*;',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if not match:
            continue
        try:
            data = json.loads(match.group(1))
            posts = _dig_json(data, ["posts","items","results","data","listings","search"])
            if not posts:
                continue
            for post in posts[:15]:
                price_raw = str(post.get("price") or post.get("amount") or "")
                price = _clean_price(price_raw)
                if not price:
                    continue
                body = post.get("body") or post.get("content") or post.get("description") or ""
                results.append(_L(
                    source="haraj", source_name="Haraj.com.sa",
                    listed_as=_clean_text(post.get("title") or post.get("subject") or query),
                    condition="مستعملة",
                    price=price,
                    mileage=_extract_mileage(body + " " + (post.get("title") or "")),
                    location=post.get("city") or post.get("region") or "غير محدد",
                    seller_name=post.get("username") or post.get("author") or "بائع",
                    seller_type="individual",
                    days_ago=0,
                    image=((post.get("images") or [_default_img(query)])[0]),
                    url=f"https://haraj.com.sa/{post.get('id','')}",
                    note=_clean_text(body)[:80],
                    confidence="medium", reason="حراج — بيانات JSON",
                ))
            if results:
                break
        except Exception as e:
            print(f"  [Haraj JSON parse] {e}")
    return results

def _parse_haraj_html(html: str, query: str) -> list[dict]:
    results = []
    # أسعار من نص الإعلانات
    price_blocks = re.findall(r'(?:السعر|price|ريال|SAR)[^\d]*([\d,]{5,})', html, re.IGNORECASE)
    if not price_blocks:
        price_blocks = re.findall(r'([\d]{2,3},[\d]{3})', html)

    title_blocks = re.findall(
        r'(?:تويوتا|Toyota|نيسان|Nissan|هيونداي|Hyundai)[^"<]{3,60}(?:2023|2024|2025|2026)',
        html, re.IGNORECASE
    )

    seen = set()
    for i, raw in enumerate(price_blocks[:12]):
        price = _clean_price(raw)
        if not price or price in seen:
            continue
        seen.add(price)
        title = title_blocks[i] if i < len(title_blocks) else query
        results.append(_L(
            source="haraj", source_name="Haraj.com.sa",
            listed_as=_clean_text(title),
            condition="مستعملة", price=price, mileage="غير محدد",
            location="غير محدد", seller_name="بائع حراج", seller_type="individual",
            days_ago=0, image=_default_img(query),
            url=f"https://haraj.com.sa/search/{query.replace(' ','+')}",
            note="", confidence="medium", reason="حراج — استخراج HTML",
        ))
    return results

# ── Toyota.com.sa Scraper ───────────────────────────────────────
async def playwright_toyota_sa(model: str) -> list[dict]:
    """
    يسحب الأسعار الرسمية من صفحة الموديل على toyota.com.sa
    مثال: https://www.toyota.com.sa/en/models/yaris
    """
    if not PLAYWRIGHT_OK:
        return []

    results = []
    slug = model.lower().replace(" ", "-")
    urls = [
        f"https://www.toyota.com.sa/en/models/{slug}",
        f"https://www.toyota.com.sa/ar/models/{slug}",
        f"https://www.toyota.com.sa/en/vehicles/{slug}",
    ]

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            )
            page = await context.new_page()
            await page.route("**/*.{png,jpg,jpeg,gif,webp,woff,woff2,mp4}", lambda r: r.abort())

            for url in urls:
                try:
                    print(f"  [Toyota SA] Opening: {url}")
                    resp = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    if not resp or resp.status >= 400:
                        continue

                    await asyncio.sleep(2)  # انتظر JS
                    html = await page.content()

                    # ابحث عن أسعار الفئات
                    # النمط: Y LIMITED ﷼ 66,700 أو السعر 66,700
                    trim_prices = re.findall(
                        r'([A-Z][A-Z\s\+]{2,20})\s*(?:﷼|SAR|ريال|السعر|Price)\s*([\d,]{5,})',
                        html, re.IGNORECASE
                    )
                    if not trim_prices:
                        trim_prices = re.findall(
                            r'([\w\s\+]{3,25})\s*<[^>]*>\s*([\d,]{5,})\s*(?:﷼|SAR)',
                            html, re.IGNORECASE
                        )

                    if trim_prices:
                        for trim_name, price_str in trim_prices[:8]:
                            price = _clean_price(price_str)
                            if price:
                                results.append(_L(
                                    source="toyota_sa", source_name="Toyota.com.sa (رسمي)",
                                    listed_as=f"Toyota {model} {_clean_text(trim_name)} — سعر رسمي",
                                    condition="جديدة", price=price, mileage="0 كم",
                                    location="المملكة العربية السعودية",
                                    seller_name="هاشم جميل موتورز — المعتمد",
                                    seller_type="official_dealer", days_ago=0,
                                    image=_default_img(model), url=url,
                                    note="سعر رسمي من الوكيل المعتمد",
                                    confidence="high", reason=f"Toyota.com.sa — فئة {_clean_text(trim_name)}",
                                ))
                        break

                    # Fallback: أي أسعار في الصفحة
                    all_prices = re.findall(r'([\d]{2,3}[,،][\d]{3})', html)
                    seen = set()
                    for p_str in all_prices:
                        price = _clean_price(p_str)
                        if price and price not in seen and 40000 < price < 500000:
                            seen.add(price)
                            results.append(_L(
                                source="toyota_sa", source_name="Toyota.com.sa (رسمي)",
                                listed_as=f"Toyota {model} — سعر رسمي",
                                condition="جديدة", price=price, mileage="0 كم",
                                location="المملكة العربية السعودية",
                                seller_name="هاشم جميل موتورز — المعتمد",
                                seller_type="official_dealer", days_ago=0,
                                image=_default_img(model), url=url,
                                note="مستخرج من الصفحة الرسمية",
                                confidence="medium", reason="Toyota.com.sa — HTML regex",
                            ))
                    if results:
                        break

                except Exception as e:
                    print(f"  [Toyota SA] {url}: {e}")
                    continue

            await browser.close()

    except Exception as e:
        print(f"  [Toyota SA Playwright] Error: {e}")

    return results

# ── Motory Scraper ──────────────────────────────────────────────
async def playwright_motory(query: str, max_results: int = 10) -> list[dict]:
    """يسحب من motory.com"""
    if not PLAYWRIGHT_OK:
        return []

    results = []
    url = f"https://motory.com/sa/new-cars/search?q={query.replace(' ', '+')}"

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True, args=["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            )
            page = await context.new_page()
            await page.route("**/*.{png,jpg,jpeg,gif,webp,woff}", lambda r: r.abort())

            print(f"  [Motory] Opening: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)
            html = await page.content()
            await browser.close()

            # استخرج JSON
            match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    cars = _dig_json(data, ["cars","results","data","vehicles","listings"])
                    for car in (cars or [])[:max_results]:
                        price = _clean_price(str(car.get("price") or car.get("min_price") or ""))
                        if price:
                            results.append(_L(
                                source="motory", source_name="Motory.com",
                                listed_as=_clean_text(car.get("name") or car.get("title") or query),
                                condition="جديدة", price=price, mileage="0 كم",
                                location="المملكة العربية السعودية",
                                seller_name=car.get("dealer") or "Motory",
                                seller_type="dealer", days_ago=0,
                                image=car.get("image") or _default_img(query),
                                url=f"https://motory.com/sa/cars/{car.get('slug','')}",
                                note="", confidence="high", reason="Motory — جديد",
                            ))
                except Exception as e:
                    print(f"  [Motory JSON] {e}")

            # HTML fallback
            if not results:
                prices = re.findall(r'(?:SAR|ريال|﷼)\s*([\d,]{5,})', html)
                for p in prices[:max_results]:
                    price = _clean_price(p)
                    if price:
                        results.append(_L(
                            source="motory", source_name="Motory.com",
                            listed_as=query, condition="جديدة", price=price,
                            mileage="0 كم", location="المملكة العربية السعودية",
                            seller_name="Motory", seller_type="dealer", days_ago=0,
                            image=_default_img(query), url=url, note="",
                            confidence="medium", reason="Motory — HTML",
                        ))

    except Exception as e:
        print(f"  [Motory Playwright] Error: {e}")

    return results

# ── Utils ───────────────────────────────────────────────────────
def _dig_json(data, keys: list):
    """ينقّب في JSON متداخل للوصول لأول مفتاح موجود يحتوي list"""
    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        return data
    if isinstance(data, dict):
        for key in keys:
            if key in data and data[key]:
                result = _dig_json(data[key], keys)
                if result:
                    return result
        # بحث أعمق
        for v in data.values():
            if isinstance(v, (dict, list)):
                result = _dig_json(v, keys)
                if result:
                    return result
    return None

def _extract_mileage(text: str) -> str:
    m = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)\s*(?:km|كم|كيلو)', text, re.IGNORECASE)
    return m.group(0).strip() if m else "غير محدد"

# ── Runner للاختبار المباشر ─────────────────────────────────────
async def run_test(query: str = "2026 Toyota Yaris Y Limited"):
    print(f"\n{'='*50}")
    print(f"اختبار Playwright Scraper: {query}")
    print('='*50)

    results_syarah = await playwright_syarah(query)
    print(f"\n✅ Syarah: {len(results_syarah)} نتيجة")
    for r in results_syarah[:3]:
        print(f"   {r['listedAs'][:40]} → SAR {r['price']:,} | {r['condition']} | {r['location']}")

    results_haraj = await playwright_haraj(query)
    print(f"\n✅ Haraj: {len(results_haraj)} نتيجة")
    for r in results_haraj[:3]:
        print(f"   {r['listedAs'][:40]} → SAR {r['price']:,} | {r['location']}")

    model = " ".join(query.split()[2:]) if len(query.split()) > 2 else "Yaris"
    results_toyota = await playwright_toyota_sa(model)
    print(f"\n✅ Toyota.com.sa: {len(results_toyota)} نتيجة")
    for r in results_toyota[:5]:
        print(f"   {r['listedAs'][:50]} → SAR {r['price']:,}")

    print(f"\nإجمالي: {len(results_syarah)+len(results_haraj)+len(results_toyota)} نتيجة")

if __name__ == "__main__":
    asyncio.run(run_test("2026 Toyota Yaris Y Limited"))
