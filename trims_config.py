"""
HJ Motors — Trim Configuration
================================
هذا الملف هو المكان الوحيد لتعريف فئات السيارات.

كيفية الاستخدام:
----------------
لكل موديل، أضف مدخلاً في TRIM_CONFIG بالشكل التالي:

    ("brand", "model"): [
        TrimDefinition(
            id          = "TRIM_CODE",      # كود الفئة من نظامك
            name        = "Official Name",
            name_ar     = "الاسم بالعربي",
            msrp        = 120000,           # SAR شامل VAT 15%
            engine      = "2.5L HEV 226hp",
            keywords    = ["keyword1", "كلمة2"],  # ما يكتبه البائع في الإعلان
            match_score = 0.90,
        ),
    ],

بعد الإضافة: أعد تشغيل Docker أو اضغط DELETE /trims/cache
"""

from dataclasses import dataclass, field


@dataclass
class TrimDefinition:
    id:          str
    name:        str
    name_ar:     str
    msrp:        int          # SAR شامل VAT — 0 = غير محدد بعد
    engine:      str
    keywords:    list[str]
    match_score: float = 0.85


# ════════════════════════════════════════════════════════════════
#  TRIM_CONFIG  ← أضف / عدّل هنا
# ════════════════════════════════════════════════════════════════

TRIM_CONFIG: dict[tuple, list[TrimDefinition]] = {

    # ─── Toyota Camry 2026 ───────────────────────────────────────
    ("toyota", "camry"): [
        TrimDefinition("CAM26-LUMIERE-HEV", "Camry Lumiere HEV",  "كامري لوميير هايبرد",  149500, "2.5L HEV 226hp E-CVT", ["lumiere","لوميير","فل كامل","platinum","بلاتينيوم","فل اوبشن"], 0.95),
        TrimDefinition("CAM26-GRANDE",      "Camry Grande",        "كامري جراندي",          140990, "2.5L 201hp 8AT",       ["grande","جراندي","grand"], 0.95),
        TrimDefinition("CAM26-LE-HEV",      "Camry LE HEV",        "كامري LE هايبرد",       120060, "2.5L HEV 226hp E-CVT", ["le hev","le هايبرد","ال اي هايبرد","le hybrid"], 0.92),
        TrimDefinition("CAM26-LE",          "Camry LE",            "كامري LE",               117070, "2.5L 201hp 8AT",       ["camry le ","كامري ال اي","le بنزين"], 0.90),
        TrimDefinition("CAM26-EPLUS-HEV",   "Camry E Plus HEV",    "كامري E بلس هايبرد",    111550, "2.5L HEV 226hp E-CVT", ["e plus hev","e plus","e بلس","e+"], 0.92),
        TrimDefinition("CAM26-E-HEV",       "Camry E HEV",         "كامري E هايبرد",         106605, "2.5L HEV 226hp E-CVT", ["e hev","e هايبرد","هايبرد عادي","كامري هايبرد"], 0.88),
        TrimDefinition("CAM26-E",           "Camry E",             "كامري E",                105340, "2.5L 201hp 8AT",       ["camry e ","كامري عادي","ستاندرد","e بنزين"], 0.85),
    ],

    # ─── Toyota Yaris 2026 ───────────────────────────────────────
    ("toyota", "yaris"): [
        TrimDefinition("YAR26-YLIMITED", "Yaris Y Limited", "يارس Y ليمتد", 69690, "1.5L 107hp CVT", ["y limited","y ليمتد","ليمتد","limited","يارس فل"], 0.95),
        TrimDefinition("YAR26-YPLUS",   "Yaris Y Plus",    "يارس Y بلس",   66700, "1.5L 107hp CVT", ["y plus","y بلاس","بلاس","plus","نص فل"], 0.92),
        TrimDefinition("YAR26-Y",       "Yaris Y",         "يارس Y",        57500, "1.5L 107hp CVT", ["yaris y ","يارس واي","يارس عادي","ستاندرد"], 0.85),
    ],

    # ─── Toyota Land Cruiser 2026 ────────────────────────────────
    ("toyota", "land cruiser"): [
        TrimDefinition("LC300-VXR", "Land Cruiser VXR", "لاند كروزر VXR", 0, "3.5L TT-V6 409hp", ["vxr","في اكس ار","فل كامل","platinum"], 0.95),
        TrimDefinition("LC300-GXR", "Land Cruiser GXR", "لاند كروزر GXR", 0, "3.5L TT-V6 409hp", ["gxr","جي اكس ار","full","فل"], 0.90),
        TrimDefinition("LC300-GX",  "Land Cruiser GX",  "لاند كروزر GX",  0, "3.5L TT-V6 409hp", ["gx ","جي اكس","عادي"], 0.85),
    ],

    # ─── Toyota Prado 2026 ───────────────────────────────────────
    ("toyota", "prado"): [
        TrimDefinition("PRA26-TXL", "Prado TXL", "برادو TXL", 0, "2.7L 163hp 6AT", ["txl","تي اكس ال","فل"], 0.92),
        TrimDefinition("PRA26-VX",  "Prado VX",  "برادو VX",  0, "2.7L 163hp 6AT", ["vx ","في اكس","نص فل"], 0.88),
        TrimDefinition("PRA26-TX",  "Prado TX",  "برادو TX",  0, "2.7L 163hp 6AT", ["tx ","تي اكس","عادي"], 0.85),
    ],

    # ─── Toyota RAV4 2026 ────────────────────────────────────────
    ("toyota", "rav4"): [
        TrimDefinition("RAV26-ADV", "RAV4 Adventure", "راف4 أدفنتشر", 0, "2.5L 203hp CVT",     ["adventure","أدفنتشر"], 0.92),
        TrimDefinition("RAV26-HYB", "RAV4 Hybrid",    "راف4 هايبرد",  0, "2.5L HEV 219hp E-CVT", ["hybrid","هايبرد","هجين"], 0.90),
        TrimDefinition("RAV26-XLE", "RAV4 XLE",       "راف4 XLE",     0, "2.5L 203hp CVT",     ["xle","نص فل"], 0.88),
        TrimDefinition("RAV26-LE",  "RAV4 LE",        "راف4 LE",      0, "2.5L 203hp CVT",     ["le ","عادي"], 0.85),
    ],

    # ─── Nissan Patrol 2026 ──────────────────────────────────────
    ("nissan", "patrol"): [
        TrimDefinition("PAT26-PLAT", "Patrol Platinum", "باترول بلاتينيوم", 0, "5.6L V8 400hp 7AT", ["platinum","بلاتينيوم","titanium","تيتانيوم","فل كامل"], 0.95),
        TrimDefinition("PAT26-SL",   "Patrol SL",       "باترول SL",         0, "5.6L V8 400hp 7AT", ["sl ","اس ال","نص فل"], 0.88),
        TrimDefinition("PAT26-SV",   "Patrol SV",       "باترول SV",         0, "5.6L V8 400hp 7AT", ["sv ","اس في"], 0.88),
        TrimDefinition("PAT26-SE",   "Patrol SE",       "باترول SE",         0, "5.6L V8 400hp 7AT", ["se ","اس اي","عادي"], 0.82),
    ],

    # ════════════════════════════════════════════════════════════
    #  أضف موديلات إضافية هنا — نفس الشكل أعلاه
    # ════════════════════════════════════════════════════════════

    # مثال:
    # ("toyota", "fortuner"): [
    #     TrimDefinition("FOR26-VXR", "Fortuner VXR", "فورتشنر VXR", 0, "2.7L 166hp 6AT", ["vxr","فل"], 0.92),
    #     TrimDefinition("FOR26-GXR", "Fortuner GXR", "فورتشنر GXR", 0, "2.7L 166hp 6AT", ["gxr","نص فل"], 0.88),
    # ],

}


# ════════════════════════════════════════════════════════════════
#  Helper functions — لا تعدل هنا
# ════════════════════════════════════════════════════════════════

def get_trims(brand: str, model: str) -> list[TrimDefinition]:
    """Returns trims for brand/model or empty list."""
    return TRIM_CONFIG.get((brand.lower(), model.lower()), [])


def get_all_configured() -> list[dict]:
    """Summary of all configured brand/models."""
    return [
        {
            "brand": k[0], "model": k[1],
            "trim_count": len(v),
            "trims": [{"id": t.id, "name": t.name, "msrp": t.msrp} for t in v],
        }
        for k, v in TRIM_CONFIG.items()
    ]


def normalize_from_config(title: str, brand: str, model: str) -> tuple[str, str, float]:
    """
    Match a marketplace listing title to official trim using TRIM_CONFIG.
    Returns: (official_name, match_reason, confidence_score)
    """
    trims = get_trims(brand, model)
    if not trims:
        return f"{model} Standard", "لا توجد فئات محددة", 0.50

    t = title.lower()
    for trim in trims:
        for kw in trim.keywords:
            if kw and kw in t:
                return trim.name, f"كلمة مفتاحية: «{kw}»", trim.match_score

    # Word overlap fallback
    best, best_score = trims[-1], 0.0
    for trim in trims:
        words = [w for w in trim.name.lower().split() if len(w) > 2]
        hits = sum(1 for w in words if w in t)
        score = (hits / len(words) * 0.3) if words else 0
        if score > best_score:
            best_score, best = score, trim

    return best.name, "مطابقة جزئية", max(0.50, best_score)
