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

# ─── TRIM_CONFIG ─────────────────────────────────────────────────────────────
# Generated from modelTypes + groups data
# Each key: (brand, model_group) → list of TrimDefinition
    # ─── Toyota Yaris 2026 ───────────────────────────────────────
    ("toyota", "yaris"): [
        TrimDefinition("YAR26-YLIMITED", "Y Limited", "واي ليمتد", 0, "1.3L CVT",
                       ["y limited","y ليمتد","ليمتد","limited","يارس فل",
                        "full option","فل اوبشن","واي ليمتد","y lim","ylimited"], 0.95),
        TrimDefinition("YAR26-YPLUS", "Y Plus", "واي بلس", 0, "1.3L CVT",
                       ["y plus","y بلاس","واي بلس","بلاس","plus","نص فل",
                        "y+","yplus","half option","نص اوبشن"], 0.92),
        TrimDefinition("YAR26-YX", "YX", "واي اكس", 0, "1.3L CVT",
                       ["yx","y x","واي اكس","yaris yx","يارس yx",
                        "yx trim","فئة yx","y اكس","واي x"], 0.90),
        TrimDefinition("YAR26-Y", "Y", "واي", 0, "1.3L CVT",
                       ["yaris y","يارس واي","يارس عادي","ستاندرد",
                        "standard","base","بيس","عادي","واي عادي"], 0.85),
    ],

    # ─── Toyota Camry 2025 / 2026 ───────────────────────────────
    ("toyota", "camry"): [
        TrimDefinition("CAM-LUMIERE-HEV-1L5", "Lumiere Hybrid (1L5)", "لومير هايبرد (1L5)", 0, "2.5L HEV CVT",
                       ["lumiere hybrid 1l5","لومير هايبرد 1l5","lumiere 1l5","لومير 1l5"], 0.97),
        TrimDefinition("CAM-LUMIERE-HEV", "Lumiere Hybrid", "لومير هايبرد", 0, "2.5L HEV CVT",
                       ["lumiere hybrid","لومير هايبرد","lumiere","لومير","كامري لومير"], 0.96),
        TrimDefinition("CAM-GRANDE-1L5", "Grande Automatic (1L5)", "جراندي اتوماتيك (1L5)", 0, "2.5L Petrol AT",
                       ["grande automatic 1l5","جراندي 1l5","grande 1l5"], 0.95),
        TrimDefinition("CAM-GRANDE", "Grande Automatic", "جراندي اتوماتيك", 0, "2.5L Petrol AT",
                       ["grande","جراندي","grande automatic","كامري جراندي","camry grande"], 0.94),
        TrimDefinition("CAM-LE-HEV-1L5", "LE Hybrid (1L5)", "ال اي هايبرد (1L5)", 0, "2.5L HEV CVT",
                       ["le hybrid 1l5","ال اي هايبرد 1l5","le hev 1l5"], 0.93),
        TrimDefinition("CAM-LE-HEV", "LE Hybrid", "ال اي هايبرد", 0, "2.5L HEV CVT",
                       ["le hybrid","ال اي هايبرد","le hev","كامري ال اي هايبرد"], 0.92),
        TrimDefinition("CAM-EPLUS-HEV-1L5", "E Plus Hybrid (1L5)", "اي بلس هايبرد (1L5)", 0, "2.5L HEV CVT",
                       ["e plus hybrid 1l5","اي بلس هايبرد 1l5","e plus 1l5"], 0.91),
        TrimDefinition("CAM-EPLUS-HEV", "E Plus Hybrid", "اي بلس هايبرد", 0, "2.5L HEV CVT",
                       ["e plus hybrid","اي بلس هايبرد","e plus","eplus hybrid","كامري اي بلس"], 0.90),
        TrimDefinition("CAM-E-HEV-1L5", "E Hybrid (1L5)", "اي هايبرد (1L5)", 0, "2.5L HEV CVT",
                       ["e hybrid 1l5","اي هايبرد 1l5","e hev 1l5"], 0.89),
        TrimDefinition("CAM-E-HEV", "E Hybrid", "اي هايبرد", 0, "2.5L HEV CVT",
                       ["e hybrid","اي هايبرد","e hev","camry e hybrid","كامري هايبرد"], 0.88),
        TrimDefinition("CAM-LE-1L5", "LE Automatic (1L5)", "ال اي اتوماتيك (1L5)", 0, "2.5L Petrol AT",
                       ["le automatic 1l5","ال اي اتوماتيك 1l5","le 1l5"], 0.87),
        TrimDefinition("CAM-LE", "LE Automatic", "ال اي اتوماتيك", 0, "2.5L Petrol AT",
                       ["le automatic","ال اي اتوماتيك","camry le","كامري ال اي","le at"], 0.86),
        TrimDefinition("CAM-E-1L5", "E Automatic (1L5)", "اي اتوماتيك (1L5)", 0, "2.5L Petrol AT",
                       ["e automatic 1l5","اي اتوماتيك 1l5","e 1l5"], 0.85),
        TrimDefinition("CAM-E", "E Automatic", "اي اتوماتيك", 0, "2.5L Petrol AT",
                       ["e automatic","اي اتوماتيك","camry e","كامري اي","base camry","كامري عادي"], 0.84),
    ],

    # ─── Toyota Corolla 2025 / 2026 ─────────────────────────────
    ("toyota", "corolla"): [
        TrimDefinition("COR-XLI-EXE-MR-HEV", "XLI EXE M/R HEV", "اكس ال اي مطور فتحة سقف هايبرد", 0, "1.8L HEV CVT",
                       ["xli exe mr hev","xli executive moonroof hybrid","اكس ال اي مطور فتحة سقف هايبرد",
                        "xli exe hev moonroof","كورولا هايبرد فتحة سقف مطور"], 0.97),
        TrimDefinition("COR-XLI-EXE-MR-2L", "XLI EXE M/R 2.0", "اكس ال اي مطور فتحة سقف 2.0", 0, "2.0L Petrol CVT",
                       ["xli exe mr 2.0","xli executive moonroof 2.0","اكس ال اي مطور فتحة سقف 2.0",
                        "2.0 moonroof executive","كورولا 2.0 مطور فتحة سقف"], 0.96),
        TrimDefinition("COR-XLI-HEV", "XLI HEV", "اكس ال اي هايبرد", 0, "1.8L HEV CVT",
                       ["xli hev","xli hybrid","اكس ال اي هايبرد","كورولا هايبرد","corolla hybrid",
                        "xli hev 1.8","هايبرد كورولا"], 0.95),
        TrimDefinition("COR-GLI-MR-2L", "GLI M/R 2.0", "جي ال اي فتحة سقف 2.0", 0, "2.0L Petrol CVT",
                       ["gli mr","gli moonroof","جي ال اي فتحة سقف","gli 2.0 mr",
                        "corolla gli moonroof","كورولا جي ال اي فتحة سقف"], 0.94),
        TrimDefinition("COR-XLI-EXE-2L", "XLI EXE 2.0", "اكس ال اي مطور 2.0", 0, "2.0L Petrol CVT",
                       ["xli exe 2.0","xli executive 2.0","اكس ال اي مطور 2.0","xli executive",
                        "corolla executive 2.0","كورولا مطور 2.0"], 0.93),
        TrimDefinition("COR-XLI-EXE-15L", "XLI EXE 1.5", "اكس ال اي مطور 1.5", 0, "1.5L Petrol CVT",
                       ["xli exe 1.5","xli executive 1.5","اكس ال اي مطور 1.5",
                        "corolla executive 1.5","كورولا مطور 1.5"], 0.92),
        TrimDefinition("COR-XLI-2L", "XLI 2.0", "اكس ال اي 2.0", 0, "2.0L Petrol CVT",
                       ["xli 2.0","اكس ال اي 2.0","corolla 2.0 xli","كورولا 2.0 xli",
                        "xli 2000","corolla 2.0"], 0.90),
        TrimDefinition("COR-XLI-15L", "XLI 1.5", "اكس ال اي 1.5", 0, "1.5L Petrol CVT",
                       ["xli 1.5","اكس ال اي 1.5","corolla 1.5 xli","كورولا 1.5 xli",
                        "xli 1500","corolla 1.5"], 0.88),
        TrimDefinition("COR-GLI-2L", "GLI 2.0", "جي ال اي 2.0", 0, "2.0L Petrol CVT",
                       ["gli 2.0","جي ال اي 2.0","corolla gli","كورولا جي ال اي",
                        "gli","gli base"], 0.86),
    ],

    # ─── Toyota Corolla Cross 2025 ───────────────────────────────
    ("toyota", "corolla cross"): [
        TrimDefinition("CC-LTD-HEV-2TONE", "LTD HEV 2Tone", "ليميتد هايبرد لونين", 0, "1.8L HEV AT",
                       ["ltd hev 2tone","limited hybrid 2 tone","ليميتد هايبرد لونين",
                        "corolla cross limited 2tone","كروس ليميتد لونين","2tone ltd hev"], 0.97),
        TrimDefinition("CC-LTD-HEV", "LTD HEV", "ليميتد هايبرد", 0, "1.8L HEV AT",
                       ["ltd hev","limited hybrid","ليميتد هايبرد","corolla cross limited",
                        "كروس ليميتد","corolla cross hev ltd","فل اوبشن كروس"], 0.95),
        TrimDefinition("CC-XLE-HEV", "XLE HEV", "اكس ال اي هايبرد", 0, "1.8L HEV AT",
                       ["xle hev","xle hybrid","اكس ال اي هايبرد","corolla cross xle",
                        "كروس xle هايبرد","xle corolla cross"], 0.92),
        TrimDefinition("CC-LE-HEV", "LE HEV", "ال اي هايبرد", 0, "1.8L HEV AT",
                       ["le hev","le hybrid","ال اي هايبرد","corolla cross le",
                        "كروس ال اي","le hev 1.8"], 0.88),
    ],

    # ─── Toyota Fortuner 2025 / 2026 ────────────────────────────
    ("toyota", "fortuner"): [
        TrimDefinition("FOR-VX3S-4X4", "VX3-S 4X4", "في اكس 3 اس دفع رباعي", 0, "4.0L V6 Petrol AT",
                       ["vx3-s","vx3s","vx3 s","في اكس 3 اس","fortuner vx3s",
                        "vx3 4x4","فورتشنر في اكس 3","top fortuner","فل فورتشنر"], 0.97),
        TrimDefinition("FOR-VX3-4X4", "VX3 4X4", "في اكس 3 دفع رباعي", 0, "4.0L V6 Petrol AT",
                       ["vx3","في اكس 3","fortuner vx3","vx3 4x4 petrol",
                        "فورتشنر في اكس3"], 0.95),
        TrimDefinition("FOR-VX2PLUS-4X4-DSL", "VX2 Plus 4X4 DSL", "في اكس 2 بلس ديزل", 0, "2.8L Diesel AT",
                       ["vx2 plus","vx2plus","في اكس 2 بلس","fortuner vx2 plus",
                        "فورتشنر في اكس 2 بلس","vx2+ diesel"], 0.94),
        TrimDefinition("FOR-VX1-4X4", "VX1 4X4", "في اكس 1 دفع رباعي", 0, "4.0L V6 Petrol AT",
                       ["vx1","في اكس 1","fortuner vx1","vx1 4x4",
                        "فورتشنر في اكس 1"], 0.92),
        TrimDefinition("FOR-GX2-4X4-DSL", "GX2 4X4 DSL", "جي اكس 2 ديزل رباعي", 0, "2.4L Diesel AT",
                       ["gx2 4x4 dsl","gx2 diesel 4x4","جي اكس 2 ديزل رباعي",
                        "fortuner gx2 diesel","فورتشنر جي اكس 2 ديزل"], 0.91),
        TrimDefinition("FOR-GX2-4X4", "GX2 4X4", "جي اكس 2 رباعي", 0, "2.7L Petrol AT",
                       ["gx2 4x4","gx2 petrol 4x4","جي اكس 2 رباعي",
                        "fortuner gx2 4x4","فورتشنر جي اكس 2 رباعي"], 0.90),
        TrimDefinition("FOR-GX2-4X2", "GX2 4X2", "جي اكس 2 ثنائي", 0, "2.7L Petrol AT",
                       ["gx2 4x2","gx2 2wd","gx2 petrol 4x2","جي اكس 2 ثنائي",
                        "fortuner gx2 4x2","فورتشنر جي اكس 2 ثنائي","fortuner base"], 0.87),
    ],

    # ─── Toyota Hilux Double Cab 2025 / 2026 ────────────────────
    ("toyota", "hilux double cab"): [
        TrimDefinition("HIL-DC-GRS-RE-4X4", "GR-S Rally Edition 4X4", "جي ار اس اصدار رالي", 0, "4.0L V6 Petrol AT",
                       ["gr-s rally edition","gr-s re","grs rally","جي ار اس رالي",
                        "hilux grs rally","هايلكس جي ار اس رالي","rally edition"], 0.98),
        TrimDefinition("HIL-DC-GRS-4X4", "GR-S 4X4", "جي ار اس رباعي", 0, "4.0L V6 Petrol AT",
                       ["gr-s 4x4","grs 4x4","جي ار اس رباعي","hilux grs",
                        "هايلكس جي ار اس","grs hilux"], 0.96),
        TrimDefinition("HIL-DC-ADV-4X4", "Adventure 4X4", "ادفنشر رباعي", 0, "4.0L V6 Petrol AT",
                       ["adventure 4x4","adventure dc","ادفنشر رباعي","hilux adventure",
                        "هايلكس ادفنشر","hilux adv"], 0.95),
        TrimDefinition("HIL-DC-SGLX-28-4X4-DSL", "SGLX 2.8 4X4 DSL AT", "سوبر جي ال اكس 2.8 ديزل رباعي اتوماتيك", 0, "2.8L Diesel AT",
                       ["sglx 2.8 4x4 dsl","sglx 2.8 diesel","سوبر جي ال اكس 2.8 ديزل",
                        "hilux sglx 2.8","هايلكس سوبر جي ال اكس 2.8"], 0.94),
        TrimDefinition("HIL-DC-SGLX-24-4X4-DSL-AT", "SGLX 2.4 4X4 DSL AT", "سوبر جي ال اكس 2.4 ديزل رباعي اتوماتيك", 0, "2.4L Diesel AT",
                       ["sglx 2.4 4x4 dsl at","sglx 2.4 dsl","سوبر جي ال اكس 2.4 ديزل اتوماتيك",
                        "hilux sglx 2.4 diesel at","هايلكس سوبر 2.4 ديزل اوتو"], 0.93),
        TrimDefinition("HIL-DC-SGLX-27-4X4-AT", "SGLX 2.7 4X4 AT", "سوبر جي ال اكس 2.7 رباعي اتوماتيك", 0, "2.7L Petrol AT",
                       ["sglx 2.7 4x4 at","sglx 2.7 auto","سوبر جي ال اكس 2.7 اتوماتيك",
                        "hilux sglx 2.7 at"], 0.92),
        TrimDefinition("HIL-DC-SGLX-27-4X4-MT", "SGLX 2.7 4X4 MT", "سوبر جي ال اكس 2.7 رباعي يدوي", 0, "2.7L Petrol MT",
                       ["sglx 2.7 4x4 mt","sglx 2.7 manual","سوبر جي ال اكس 2.7 يدوي",
                        "hilux sglx 2.7 mt"], 0.91),
        TrimDefinition("HIL-DC-GLX1-4X2", "GLX1 4X2", "جي ال اكس1 ثنائي", 0, "2.7L Petrol AT",
                       ["glx1 4x2","glx1 2wd","جي ال اكس1 ثنائي","hilux glx1",
                        "هايلكس جي ال اكس 1"], 0.90),
        TrimDefinition("HIL-DC-GL2-24-4X4-DSL-MT", "GL2 2.4 4X4 DSL MT", "جي ال 2 ديزل رباعي يدوي", 0, "2.4L Diesel MT",
                       ["gl2 2.4 4x4 dsl mt","gl2 diesel 4x4","جي ال 2 ديزل رباعي",
                        "hilux gl2 4x4 diesel"], 0.89),
        TrimDefinition("HIL-DC-GL-24-4X2-DSL-MT", "GL 2.4 4X2 DSL MT", "جي ال 2.4 ثنائي ديزل يدوي", 0, "2.4L Diesel MT",
                       ["gl 2.4 4x2 dsl mt","gl diesel 4x2","جي ال ثنائي ديزل",
                        "hilux gl 4x2 diesel","هايلكس جي ال ديزل ثنائي"], 0.87),
        TrimDefinition("HIL-DC-GLX2-27-4X2-MT", "GLX2 2.7 4X2 MT", "جي ال اكس2 ثنائي يدوي", 0, "2.7L Petrol MT",
                       ["glx2 2.7 4x2 mt","glx2 manual","جي ال اكس 2 يدوي ثنائي",
                        "hilux glx2 4x2"], 0.86),
        TrimDefinition("HIL-DC-GLX-27-4X2-MT", "GLX 2.7 4X2 MT", "جي ال اكس ثنائي يدوي", 0, "2.7L Petrol MT",
                       ["glx 2.7 4x2 mt","glx manual 2wd","جي ال اكس يدوي ثنائي",
                        "hilux glx 4x2","هايلكس جي ال اكس يدوي"], 0.85),
    ],

    # ─── Toyota Hilux Single Cab 2026 ────────────────────────────
    ("toyota", "hilux single cab"): [
        TrimDefinition("HIL-SC-GLX-28-4X4-DSL-AT", "GLX 4X4 DSL AT", "جي ال اكس ديزل رباعي اتوماتيك", 0, "2.8L Diesel AT",
                       ["sc glx 4x4 dsl at","glx diesel 4x4 auto","جي ال اكس ديزل رباعي اوتو",
                        "hilux sc glx 2.8 at"], 0.95),
        TrimDefinition("HIL-SC-GLX-28-4X4-DSL-MT", "GLX 4X4 DSL MT", "جي ال اكس ديزل رباعي يدوي", 0, "2.8L Diesel MT",
                       ["sc glx 4x4 dsl mt","glx diesel 4x4 manual","جي ال اكس ديزل رباعي يدوي",
                        "hilux sc glx 2.8 mt"], 0.93),
        TrimDefinition("HIL-SC-GLX-24-4X4-DSL-MT", "GLX 4X4 DSL MT 2.4", "جي ال اكس 2.4 ديزل رباعي يدوي", 0, "2.4L Diesel MT",
                       ["sc glx 2.4 4x4 dsl mt","glx 2.4 diesel 4x4","هايلكس غماره 2.4 ديزل رباعي",
                        "hilux sc 2.4 glx"], 0.92),
        TrimDefinition("HIL-SC-GLX-27-4X4-MT", "GLX 4X4 Petrol MT", "جي ال اكس بنزين رباعي يدوي", 0, "2.7L Petrol MT",
                       ["sc glx 4x4 petrol mt","glx petrol 4x4 manual","جي ال اكس بنزين رباعي يدوي",
                        "hilux sc glx 2.7 4x4"], 0.91),
        TrimDefinition("HIL-SC-GLX-27-4X2-MT", "GLX 4X2 Petrol MT", "جي ال اكس بنزين ثنائي يدوي", 0, "2.7L Petrol MT",
                       ["sc glx 4x2 petrol mt","glx petrol 4x2 manual","جي ال اكس بنزين ثنائي",
                        "hilux sc glx 2.7 4x2"], 0.90),
        TrimDefinition("HIL-SC-GL-28-4X2-DSL-MT", "GL 4X2 DSL MT 2.8", "جي ال ديزل ثنائي يدوي", 0, "2.8L Diesel MT",
                       ["sc gl 2.8 4x2 dsl mt","gl diesel 4x2 sc 2.8","جي ال ديزل ثنائي 2.8",
                        "hilux sc gl 2.8 4x2"], 0.89),
        TrimDefinition("HIL-SC-GL-24-4X2-DSL-MT", "GL 4X2 DSL MT 2.4", "جي ال ديزل ثنائي يدوي 2.4", 0, "2.4L Diesel MT",
                       ["sc gl 2.4 4x2 dsl mt","gl diesel 4x2 sc 2.4","جي ال ديزل ثنائي 2.4",
                        "hilux sc gl 2.4 4x2","hilux sc base"], 0.87),
        TrimDefinition("HIL-SC-DECKLESS-24-4X2-DSL-MT", "SC Deckless 2.4 4X2 DSL MT", "غماره واحدة بدون حوض ديزل", 0, "2.4L Diesel MT",
                       ["deckless","sc deckless","بدون حوض","hilux deckless",
                        "هايلكس بدون حوض","no deck"], 0.85),
    ],

    # ─── Toyota LandCruiser Wagon (LC300) 2025 / 2026 ──────────
    ("toyota", "landcruiser wagon"): [
        TrimDefinition("LC300-GRS-35-DSL", "GRS 3.3 V6 DSL AT", "جي ار اس ديزل", 0, "3.3L V6 Diesel AT",
                       ["grs dsl","grs diesel","جي ار اس ديزل","lc300 grs diesel",
                        "لاندكروزر جي ار اس ديزل","grs 3.3 dsl"], 0.97),
        TrimDefinition("LC300-VXR-HEV", "VXR HEV", "في اكس ار هايبرد", 0, "3.5L V6 HEV AT",
                       ["vxr hev","vxr hybrid","في اكس ار هايبرد","lc300 vxr hev",
                        "لاندكروزر في اكس ار هايبرد","vxr hev at"], 0.97),
        TrimDefinition("LC300-GRS-HEV", "GR-S HEV", "جي ار اس هايبرد", 0, "3.5L V6 HEV AT",
                       ["gr-s hev","grs hev","grs hybrid","جي ار اس هايبرد","lc300 grs hev",
                        "لاندكروزر جي ار اس هايبرد"], 0.97),
        TrimDefinition("LC300-VXR", "VXR 3.5 Petrol AT", "في اكس ار بنزين", 0, "3.5L V6 Petrol AT",
                       ["vxr","في اكس ار","lc300 vxr","لاندكروزر في اكس ار",
                        "vxr at","vxr 3.5"], 0.96),
        TrimDefinition("LC300-VX-HEV", "VX HEV", "في اكس هايبرد", 0, "3.5L V6 HEV AT",
                       ["vx hev","vx hybrid","في اكس هايبرد","lc300 vx hev",
                        "لاندكروزر في اكس هايبرد"], 0.95),
        TrimDefinition("LC300-GXR4-35", "GXR4 3.5 Petrol AT", "جي اكس ار4 بنزين", 0, "3.5L V6 Petrol AT",
                       ["gxr4 3.5","gxr4 petrol","جي اكس ار 4 بنزين","lc300 gxr4",
                        "لاندكروزر جي اكس ار4"], 0.95),
        TrimDefinition("LC300-GXR4-DSL", "GXR4 3.3 V6 DSL AT", "جي اكس ار4 ديزل", 0, "3.3L V6 Diesel AT",
                       ["gxr4 dsl","gxr4 diesel","جي اكس ار4 ديزل","lc300 gxr4 diesel",
                        "لاندكروزر جي اكس ار4 ديزل"], 0.94),
        TrimDefinition("LC300-GXR3-35", "GXR3 3.5 Petrol AT", "جي اكس ار3 بنزين", 0, "3.5L V6 Petrol AT",
                       ["gxr3 3.5","gxr3 petrol","جي اكس ار 3 بنزين","lc300 gxr3",
                        "لاندكروزر جي اكس ار3"], 0.93),
        TrimDefinition("LC300-GXR3-DSL", "GXR3 3.3 V6 DSL AT", "جي اكس ار3 ديزل", 0, "3.3L V6 Diesel AT",
                       ["gxr3 dsl","gxr3 diesel","جي اكس ار3 ديزل","lc300 gxr3 diesel",
                        "لاندكروزر جي اكس ار3 ديزل"], 0.92),
        TrimDefinition("LC300-GXR-S", "GXR-S 3.5 Petrol AT", "جي اكس ار اس", 0, "3.5L V6 Petrol AT",
                       ["gxr-s","gxrs","جي اكس ار اس","lc300 gxr-s",
                        "لاندكروزر جي اكس ار اس"], 0.92),
        TrimDefinition("LC300-GXR2-35", "GXR2 3.5 Petrol AT", "جي اكس ار2 بنزين", 0, "3.5L V6 Petrol AT",
                       ["gxr2 3.5","gxr2 petrol","جي اكس ار 2 بنزين","lc300 gxr2",
                        "لاندكروزر جي اكس ار2 بنزين"], 0.91),
        TrimDefinition("LC300-GXR2-DSL", "GXR2 3.3 V6 DSL AT", "جي اكس ار2 ديزل", 0, "3.3L V6 Diesel AT",
                       ["gxr2 dsl","gxr2 diesel","جي اكس ار2 ديزل","lc300 gxr2 diesel",
                        "لاندكروزر جي اكس ار2 ديزل"], 0.90),
        TrimDefinition("LC300-GXR1-35", "GXR1 3.5 Petrol AT", "جي اكس ار1 بنزين", 0, "3.5L V6 Petrol AT",
                       ["gxr1 3.5","gxr1 petrol","جي اكس ار 1 بنزين","lc300 gxr1",
                        "لاندكروزر جي اكس ار1"], 0.90),
        TrimDefinition("LC300-VX-35", "VX 3.5 Petrol AT", "في اكس بنزين", 0, "3.5L V6 Petrol AT",
                       ["vx 3.5","vx petrol","في اكس بنزين","lc300 vx",
                        "لاندكروزر في اكس","vx at"], 0.89),
        TrimDefinition("LC300-GX-40-GOV", "GX 4.0 Petrol AT (Gov)", "جي اكس بنزين حكومي", 0, "4.0L V6 Petrol AT",
                       ["gx 4.0","gx at","gx v6","جي اكس بنزين","lc300 gx",
                        "لاندكروزر جي اكس","government gx"], 0.88),
        TrimDefinition("LC300-GX-DSL", "GX 3.3 V6 DSL AT", "جي اكس ديزل", 0, "3.3L V6 Diesel AT",
                       ["gx dsl","gx diesel","جي اكس ديزل","lc300 gx diesel",
                        "لاندكروزر جي اكس ديزل"], 0.87),
    ],

    # ─── Toyota Prado 2025 / 2026 ───────────────────────────────
    ("toyota", "prado"): [
        TrimDefinition("PRA-VXL3-24", "VXL-3 2.4 Petrol AT", "في اكس ال 3 بنزين", 0, "2.4L Petrol AT",
                       ["vxl-3","vxl3","vxl 3","في اكس ال 3","prado vxl3",
                        "برادو في اكس ال 3","prado top"], 0.97),
        TrimDefinition("PRA-ADV2-2TONE", "ADV-2 2Tone 2.4 Petrol AT", "ادفنشر 2 لونين", 0, "2.4L Petrol AT",
                       ["adv-2 2tone","adv2 2tone","ادفنشر 2 لونين","prado adv2 2tone",
                        "برادو ادفنشر لونين"], 0.96),
        TrimDefinition("PRA-ADV2-24", "ADV-2 2.4 Petrol AT", "ادفنشر 2 بنزين", 0, "2.4L Petrol AT",
                       ["adv-2","adv2","ادفنشر 2","prado adv2",
                        "برادو ادفنشر 2"], 0.95),
        TrimDefinition("PRA-ADV1-DSL", "ADV-1 2.8 Diesel AT", "ادفنشر 1 ديزل", 0, "2.8L Diesel AT",
                       ["adv-1 dsl","adv1 diesel","ادفنشر 1 ديزل","prado adv-1 diesel",
                        "برادو ادفنشر ديزل"], 0.94),
        TrimDefinition("PRA-TXL3-24", "TXL-3 2.4 Petrol AT", "تي اكس ال 3 بنزين", 0, "2.4L Petrol AT",
                       ["txl-3","txl3","تي اكس ال 3","prado txl3",
                        "برادو تي اكس ال 3"], 0.93),
        TrimDefinition("PRA-TXL2-DSL", "TXL-2 2.8 Diesel AT", "تي اكس ال 2 ديزل", 0, "2.8L Diesel AT",
                       ["txl-2 dsl","txl2 diesel","تي اكس ال 2 ديزل","prado txl2 diesel",
                        "برادو تي اكس ال 2 ديزل"], 0.92),
        TrimDefinition("PRA-TX2-DSL", "TX-2 2.8 Diesel AT", "تي اكس 2 ديزل", 0, "2.8L Diesel AT",
                       ["tx-2 dsl","tx2 diesel","تي اكس 2 ديزل","prado tx2 diesel",
                        "برادو تي اكس 2 ديزل"], 0.91),
        TrimDefinition("PRA-ADV-2TONE-24", "ADV 2 Tone 2.4 Petrol AT", "ادفنشر لونين 2.4", 0, "2.4L Petrol AT",
                       ["adv 2 tone","adv 2tone","ادفنشر لونين","prado adv 2tone",
                        "برادو ادفنشر لونين 2.4"], 0.91),
        TrimDefinition("PRA-TXL2-24", "TXL2 2.4 Petrol AT", "تي اكس ال 2 بنزين", 0, "2.4L Petrol AT",
                       ["txl2 petrol","txl2 2.4","تي اكس ال 2 بنزين","prado txl2 petrol",
                        "برادو تي اكس ال 2 بنزين"], 0.90),
        TrimDefinition("PRA-TXL1-24", "TXL1 2.4 Petrol AT", "تي اكس ال 1 بنزين", 0, "2.4L Petrol AT",
                       ["txl1","txl 1","تي اكس ال 1","prado txl1",
                        "برادو تي اكس ال 1"], 0.89),
        TrimDefinition("PRA-ADV-24", "ADV 2.4 Petrol AT", "ادفنشر بنزين", 0, "2.4L Petrol AT",
                       ["adv","ادفنشر","prado adv","برادو ادفنشر",
                        "prado adventure"], 0.88),
        TrimDefinition("PRA-TX2-24", "TX-2 2.4 Petrol AT", "تي اكس 2 بنزين", 0, "2.4L Petrol AT",
                       ["tx-2","tx2 petrol","تي اكس 2 بنزين","prado tx2",
                        "برادو تي اكس 2"], 0.87),
        TrimDefinition("PRA-TX1-24", "TX1 2.4 Petrol AT", "تي اكس 1 بنزين", 0, "2.4L Petrol AT",
                       ["tx1","تي اكس 1","prado tx1","برادو تي اكس 1",
                        "prado base"], 0.85),
    ],

    # ─── Toyota RAV4 2025 / 2026 ────────────────────────────────
    ("toyota", "rav 4"): [
        TrimDefinition("RAV4-LTD-4X4-HEV", "LTD 4x4 HEV", "ليميتد هايبرد رباعي", 0, "2.5L HEV AT",
                       ["ltd 4x4 hev","limited hybrid 4x4","ليميتد هايبرد رباعي","rav4 limited hev",
                        "راف فور ليميتد هايبرد","ltd hev 4x4"], 0.97),
        TrimDefinition("RAV4-XSE-4X4-HEV", "XSE 4x4 HEV", "اكس اس اي هايبرد رباعي", 0, "2.5L HEV AT",
                       ["xse 4x4 hev","xse hybrid 4x4","اكس اس اي هايبرد رباعي",
                        "rav4 xse hev","راف فور xse هايبرد"], 0.96),
        TrimDefinition("RAV4-XLE-4X4-HEV", "XLE 4x4 HEV", "اكس ال اي هايبرد رباعي", 0, "2.5L HEV AT",
                       ["xle 4x4 hev","xle hybrid 4x4","اكس ال اي هايبرد رباعي","rav4 xle hev",
                        "راف فور xle هايبرد"], 0.95),
        TrimDefinition("RAV4-LE-4X4-HEV", "LE 4x4 HEV", "ال اي هايبرد رباعي", 0, "2.5L HEV AT",
                       ["le 4x4 hev","le hybrid 4x4","ال اي هايبرد رباعي","rav4 le hev 4x4",
                        "راف فور ال اي هايبرد رباعي"], 0.94),
        TrimDefinition("RAV4-LE-4X2-HEV", "LE 4x2 HEV", "ال اي هايبرد ثنائي", 0, "2.5L HEV AT",
                       ["le 4x2 hev","le hybrid 4x2","ال اي هايبرد ثنائي","rav4 le hev 4x2",
                        "راف فور ال اي هايبرد ثنائي"], 0.93),
        TrimDefinition("RAV4-ADV-4X4", "ADV 4x4 2.5 Petrol AT", "ادفنشر رباعي", 0, "2.5L Petrol AT",
                       ["adv 4x4","adventure 4x4","ادفنشر رباعي","rav4 adventure",
                        "راف فور ادفنشر"], 0.92),
        TrimDefinition("RAV4-XLE-4X4", "XLE 4x4 2.0 Petrol AT", "اكس ال اي رباعي 2.0", 0, "2.0L Petrol AT",
                       ["xle 4x4 2.0","xle petrol 4x4","اكس ال اي رباعي 2.0","rav4 xle 4x4",
                        "راف فور xle رباعي"], 0.91),
        TrimDefinition("RAV4-LE-4X4-20", "LE 4x4 2.0 Petrol AT", "ال اي رباعي 2.0", 0, "2.0L Petrol AT",
                       ["le 4x4 2.0","le petrol 4x4","ال اي رباعي 2.0","rav4 le 4x4",
                        "راف فور ال اي رباعي"], 0.90),
        TrimDefinition("RAV4-LE-4X2-20", "LE 4x2 2.0 Petrol AT", "ال اي ثنائي 2.0", 0, "2.0L Petrol AT",
                       ["le 4x2 2.0","le petrol 4x2","ال اي ثنائي 2.0","rav4 le 4x2",
                        "راف فور ال اي ثنائي","rav4 base"], 0.87),
    ],

    # ─── Toyota Highlander 2025 / 2026 ──────────────────────────
    ("toyota", "highlander"): [
        TrimDefinition("HIG-LTD-4X4-HEV", "LIMITED HEV 4X4", "ليميتد هايبرد رباعي", 0, "2.5L HEV AT",
                       ["limited hev 4x4","ltd hev 4x4","ليميتد هايبرد رباعي","highlander limited hev",
                        "هايلاندر ليميتد هايبرد","highlander top"], 0.97),
        TrimDefinition("HIG-GLE-4X4-HEV-BLACK", "GLE HEV 4X4 Black Edition", "جي ال اي هايبرد رباعي اسود", 0, "2.5L HEV AT",
                       ["gle hev black edition","gle black","جي ال اي هايبرد اصدار اسود",
                        "highlander gle black","هايلاندر اسود"], 0.96),
        TrimDefinition("HIG-GLE-4X4-HEV", "GLE HEV 4X4", "جي ال اي هايبرد رباعي", 0, "2.5L HEV AT",
                       ["gle hev 4x4","gle hybrid 4x4","جي ال اي هايبرد رباعي","highlander gle",
                        "هايلاندر جي ال اي","gle 4x4"], 0.94),
        TrimDefinition("HIG-LE-4X4-HEV", "LE HEV 4X4", "ال اي هايبرد رباعي", 0, "2.5L HEV AT",
                       ["le hev 4x4","le hybrid 4x4","ال اي هايبرد رباعي","highlander le 4x4",
                        "هايلاندر ال اي رباعي"], 0.91),
        TrimDefinition("HIG-LE-4X2-HEV", "LE HEV 4X2", "ال اي هايبرد ثنائي", 0, "2.5L HEV AT",
                       ["le hev 4x2","le hybrid 4x2","ال اي هايبرد ثنائي","highlander le 4x2",
                        "هايلاندر ال اي ثنائي","highlander base"], 0.88),
    ],

    # ─── Toyota Crown 2023 / 2026 ───────────────────────────────
    ("toyota", "crown"): [
        TrimDefinition("CRW-MAJESTA-HEV-MAX", "Majesta HEV Max AWD", "ماجيستا هايبرد ماكس", 0, "2.4L HEV AT AWD",
                       ["majesta hev","majesta hybrid","ماجيستا هايبرد","crown majesta",
                        "كراون ماجيستا","majesta max","ماجيستا"], 0.97),
        TrimDefinition("CRW-PREMIUM-HEV", "Premium HEV FWD", "بريميوم هايبرد", 0, "2.5L HEV CVT FWD",
                       ["premium hev","premium hybrid","بريميوم هايبرد","crown premium",
                        "كراون بريميوم"], 0.93),
        TrimDefinition("CRW-PRESTIGE-HEV", "Prestige HEV FWD", "بريستيج هايبرد", 0, "2.5L HEV CVT FWD",
                       ["prestige hev","prestige hybrid","بريستيج هايبرد","crown prestige",
                        "كراون بريستيج","crown base hev"], 0.90),
    ],

    # ─── Toyota LandCruiser Pick-up (LC70 Pick-up) 2026 ─────────
    ("toyota", "landcruiser pick-up"): [
        TrimDefinition("LC70PU-SDLX-40-DC-AT", "S-DLX Gas DC 4x4 AT", "سوبر ديلوكس غمارتين بنزين اتوماتيك", 0, "4.0L Petrol AT",
                       ["sdlx dc at","s-dlx dc 4x4 at","سوبر ديلوكس غمارتين اتوماتيك",
                        "lc70 sdlx dc at","lc70 s-dlx double cab at"], 0.97),
        TrimDefinition("LC70PU-SDLX-40-SC-AT", "S-DLX Gas SC 4x4 AT", "سوبر ديلوكس غماره بنزين اتوماتيك", 0, "4.0L Petrol AT",
                       ["sdlx sc at","s-dlx sc 4x4 at","سوبر ديلوكس غماره اتوماتيك",
                        "lc70 sdlx sc at"], 0.96),
        TrimDefinition("LC70PU-SDLX-28-SC-AT", "S-DLX DSL SC 4x4 AT", "سوبر ديلوكس ديزل اتوماتيك", 0, "2.8L Diesel AT",
                       ["sdlx dsl sc at","s-dlx dsl at","سوبر ديلوكس ديزل اتوماتيك",
                        "lc70 sdlx dsl at"], 0.95),
        TrimDefinition("LC70PU-DLX3-28-SC-MT", "DLX3 DSL SC 4x4 MT", "ديلوكس3 ديزل يدوي", 0, "2.8L Diesel MT",
                       ["dlx3 dsl sc mt","dlx3 diesel manual","ديلوكس3 ديزل يدوي",
                        "lc70 dlx3 sc mt"], 0.93),
        TrimDefinition("LC70PU-DLX2-28-SC-AT", "DLX2 DSL SC 4x4 AT", "ديلوكس2 ديزل اتوماتيك", 0, "2.8L Diesel AT",
                       ["dlx2 dsl sc at","dlx2 diesel auto","ديلوكس2 ديزل اتوماتيك",
                        "lc70 dlx2 sc at"], 0.92),
        TrimDefinition("LC70PU-DX-28-SC-AT", "DX DSL SC 4x4 AT", "دي اكس ديزل اتوماتيك", 0, "2.8L Diesel AT",
                       ["dx dsl sc at","dx diesel auto","دي اكس ديزل اتوماتيك",
                        "lc70 dx sc at"], 0.91),
        TrimDefinition("LC70PU-DX-28-SC-MT", "DX DSL SC 4x4 MT", "دي اكس ديزل يدوي", 0, "2.8L Diesel MT",
                       ["dx dsl sc mt","dx diesel manual","دي اكس ديزل يدوي",
                        "lc70 dx sc mt"], 0.90),
        TrimDefinition("LC70PU-STD-40-DC-MT", "STD Gas DC 4x4 MT", "ستاندر غمارتين بنزين يدوي", 0, "4.0L Petrol MT",
                       ["std dc mt","std gas dc","ستاندر غمارتين بنزين يدوي",
                        "lc70 std dc mt"], 0.89),
        TrimDefinition("LC70PU-STD-40-SC-MT", "STD Gas SC 4x4 MT", "ستاندر غماره بنزين يدوي", 0, "4.0L Petrol MT",
                       ["std sc mt","std gas sc","ستاندر غماره بنزين يدوي",
                        "lc70 std sc mt","lc70 base"], 0.87),
    ],

    # ─── Toyota LandCruiser Hard-Top (LC70 Hard-Top) 2026 ───────
    ("toyota", "landcruiser hard-top"): [
        TrimDefinition("LC70HT-SDLX-40-5DR-AT", "S-DLX Gas 5 Doors 4x4 AT", "سوبر ديلوكس بنزين 5 أبواب اتوماتيك", 0, "4.0L Petrol AT",
                       ["s-dlx 5dr at","sdlx 5 doors at","سوبر ديلوكس 5 أبواب اتوماتيك",
                        "lc70 ht sdlx at","lc70 s-dlx at"], 0.97),
        TrimDefinition("LC70HT-DLX3-40-5DR-AT", "DLX3 Gas 5 Doors 4x4 AT", "ديلوكس3 بنزين 5 أبواب اتوماتيك", 0, "4.0L Petrol AT",
                       ["dlx3 5dr at","dlx3 5 doors at gas","ديلوكس3 5 أبواب اتوماتيك",
                        "lc70 ht dlx3 at","dlx3 gas at"], 0.95),
        TrimDefinition("LC70HT-DX-40-5DR-AT", "DX Gas 5 Doors 4x4 AT", "دي اكس بنزين 5 أبواب اتوماتيك", 0, "4.0L Petrol AT",
                       ["dx 5dr at","dx 5 doors at gas","دي اكس 5 أبواب اتوماتيك",
                        "lc70 ht dx at"], 0.93),
        TrimDefinition("LC70HT-SDLX-28-5DR-AT", "S-DLX DSL 5 Doors 4x4 AT", "سوبر ديلوكس ديزل 5 أبواب اتوماتيك", 0, "2.8L Diesel AT",
                       ["s-dlx dsl 5dr at","sdlx diesel 5 doors","سوبر ديلوكس ديزل 5 أبواب",
                        "lc70 ht sdlx dsl at"], 0.93),
        TrimDefinition("LC70HT-DLX2-28-5DR-AT", "DLX2 DSL 5 Doors 4x4 AT", "ديلوكس2 ديزل 5 أبواب اتوماتيك", 0, "2.8L Diesel AT",
                       ["dlx2 dsl 5dr at","dlx2 diesel 5 doors","ديلوكس2 ديزل 5 أبواب",
                        "lc70 ht dlx2 dsl at"], 0.91),
        TrimDefinition("LC70HT-DX-40-5DR-MT", "DX Gas 5 Doors 4x4 MT", "دي اكس بنزين 5 أبواب يدوي", 0, "4.0L Petrol MT",
                       ["dx 5dr mt","dx 5 doors mt gas","دي اكس 5 أبواب يدوي",
                        "lc70 ht dx mt","lc70 ht base"], 0.88),
    ],

    # ─── Toyota Hiace Bus 2025 / 2026 ───────────────────────────
    ("toyota", "hiace bus"): [
        TrimDefinition("HIB-28-DSL-AT", "Bus 2.8 DSL AT RWD", "باص 2.8 ديزل اتوماتيك", 0, "2.8L Diesel AT",
                       ["hiace bus dsl at","bus 2.8 diesel auto","باص ديزل اتوماتيك",
                        "hiace bus at","هاي اس باص ديزل اوتو"], 0.95),
        TrimDefinition("HIB-28-DSL-MT", "Bus 2.8 DSL MT RWD", "باص 2.8 ديزل يدوي", 0, "2.8L Diesel MT",
                       ["hiace bus dsl mt","bus 2.8 diesel manual","باص ديزل يدوي",
                        "hiace bus mt","هاي اس باص ديزل يدوي"], 0.92),
        TrimDefinition("HIB-35-GAS-MT", "Bus 3.5 Petrol MT RWD", "باص 3.5 بنزين يدوي", 0, "3.5L Petrol MT",
                       ["hiace bus petrol","bus 3.5 petrol","bus 3.5 mt","باص بنزين",
                        "هاي اس باص بنزين","bus petrol manual"], 0.90),
    ],

    # ─── Toyota Hiace Van 2026 ───────────────────────────────────
    ("toyota", "hiace van"): [
        TrimDefinition("HIV-28-DSL-AT-HR", "Van 2.8 DSL AT H/R", "فان 2.8 ديزل اتوماتيك سقف عالي", 0, "2.8L Diesel AT",
                       ["van dsl at high roof","van 2.8 diesel auto hr","فان ديزل اتوماتيك سقف عالي",
                        "hiace van dsl at hr","هاي اس فان سقف عالي اوتو"], 0.95),
        TrimDefinition("HIV-28-DSL-MT-HR", "Van 2.8 DSL MT H/R", "فان 2.8 ديزل يدوي سقف عالي", 0, "2.8L Diesel MT",
                       ["van dsl mt high roof","van 2.8 diesel manual hr","فان ديزل يدوي سقف عالي",
                        "hiace van dsl mt hr"], 0.93),
        TrimDefinition("HIV-28-DSL-AT-STD", "Van 2.8 DSL AT STD", "فان 2.8 ديزل اتوماتيك ستاندرد", 0, "2.8L Diesel AT",
                       ["van dsl at std","van 2.8 diesel auto standard","فان ديزل اتوماتيك ستاندرد",
                        "hiace van std at"], 0.92),
        TrimDefinition("HIV-28-DSL-MT-STD", "Van 2.8 DSL MT STD", "فان 2.8 ديزل يدوي ستاندرد", 0, "2.8L Diesel MT",
                       ["van dsl mt std","van 2.8 diesel manual standard","فان ديزل يدوي ستاندرد",
                        "hiace van std mt"], 0.90),
        TrimDefinition("HIV-35-GAS-MT-HR", "Van 3.5 Petrol MT H/R", "فان 3.5 بنزين يدوي سقف عالي", 0, "3.5L Petrol MT",
                       ["van petrol mt hr","van 3.5 petrol high roof","فان بنزين سقف عالي",
                        "hiace van petrol hr"], 0.89),
        TrimDefinition("HIV-35-GAS-MT-STD", "Van 3.5 Petrol MT STD", "فان 3.5 بنزين يدوي ستاندرد", 0, "3.5L Petrol MT",
                       ["van petrol mt std","van 3.5 petrol standard","فان بنزين ستاندرد",
                        "hiace van petrol std","hiace van base"], 0.87),
    ],

    # ─── Toyota Coaster 2025 ─────────────────────────────────────
    ("toyota", "coaster"): [
        TrimDefinition("COA-28-DSL-AT-20S", "Bus 20 Seater 2.8 DSL AT", "باص 20 راكب ديزل اتوماتيك", 0, "2.8L Diesel AT",
                       ["coaster 2.8 dsl at","coaster diesel auto","كوستر ديزل اتوماتيك",
                        "bus 20 seater dsl at","باص 20 ديزل اوتو"], 0.95),
        TrimDefinition("COA-27-GAS-MT-20S", "Bus 20 Seater 2.7 Petrol MT", "باص 20 راكب بنزين يدوي", 0, "2.7L Petrol MT",
                       ["coaster 2.7 petrol mt","coaster petrol manual","كوستر بنزين يدوي",
                        "bus 20 seater petrol","باص 20 بنزين يدوي"], 0.90),
    ],

    # ─── Toyota Innova 2026 ──────────────────────────────────────
    ("toyota", "innova"): [
        TrimDefinition("INN-VIP7-HEV", "VIP7 HEV 2.0 AT", "في اي بي 7 هايبرد", 0, "2.0L HEV AT",
                       ["vip7 hev","vip 7 hybrid","في اي بي 7 هايبرد","innova vip7",
                        "انوفا في اي بي 7","innova top"], 0.97),
        TrimDefinition("INN-GL-HEV", "GL HEV 2.0 AT", "جي ال هايبرد", 0, "2.0L HEV AT",
                       ["gl hev","gl hybrid","جي ال هايبرد","innova gl hev",
                        "انوفا جي ال هايبرد"], 0.93),
        TrimDefinition("INN-GL", "GL 2.0 AT", "جي ال بنزين", 0, "2.0L Petrol AT",
                       ["innova gl","gl petrol","جي ال بنزين","انوفا جي ال",
                        "innova base","انوفا عادي"], 0.88),
    ],

    # ─── Toyota Liteace 2026 ─────────────────────────────────────
    ("toyota", "liteace"): [
        TrimDefinition("LIT-15-AT", "Van 1.5 AT RWD", "فان 1.5 اتوماتيك", 0, "1.5L Petrol AT",
                       ["liteace at","van 1.5 at","فان 1.5 اتوماتيك","لايت اس اتوماتيك",
                        "liteace auto"], 0.93),
        TrimDefinition("LIT-15-MT", "Van 1.5 MT RWD", "فان 1.5 يدوي", 0, "1.5L Petrol MT",
                       ["liteace mt","van 1.5 mt","فان 1.5 يدوي","لايت اس يدوي",
                        "liteace manual","liteace base"], 0.88),
    ],

    # ─── Toyota Urban Cruiser 2025 / 2026 ───────────────────────
    ("toyota", "urban cruiser"): [
        TrimDefinition("UC-GLX-4X2", "GLX 1.5 4X2 AT", "جي ال اكس ثنائي", 0, "1.5L Petrol AT",
                       ["urban cruiser glx","glx 1.5 4x2","جي ال اكس ثنائي","أوربان كروزر جي ال اكس",
                        "urban cruiser top","اوربان كروزر جي ال اكس"], 0.95),
        TrimDefinition("UC-GL-4X2", "GL 1.5 4X2 AT", "جي ال ثنائي", 0, "1.5L Petrol AT",
                       ["urban cruiser gl","gl 1.5 4x2","جي ال ثنائي","أوربان كروزر جي ال",
                        "urban cruiser base","اوربان كروزر جي ال"], 0.88),
    ],

    # ─── Toyota Raize 2024 / 2026 ───────────────────────────────
    ("toyota", "raize"): [
        TrimDefinition("RAI-LIMITED-10T", "LIMITED 1.0 Turbo AT 4X2", "ليمتد تيربو", 0, "1.0L Turbo Petrol AT",
                       ["raize limited","limited 1.0 turbo","ليمتد تيربو","رايز ليمتد",
                        "raize top","full option raize","رايز فل"], 0.95),
        TrimDefinition("RAI-XLE-12", "XLE 1.2 AT 4X2", "اكس ال اي 1.2", 0, "1.2L Petrol AT",
                       ["raize xle","xle 1.2","اكس ال اي 1.2","رايز xle",
                        "raize base","رايز عادي"], 0.88),
    ],

    # ─── Toyota Veloz 2025 ───────────────────────────────────────
    ("toyota", "veloz"): [
        TrimDefinition("VEL-GLX-15", "GLX 1.5 AT 4X2", "جي ال اكس", 0, "1.5L Petrol AT",
                       ["veloz glx","glx 1.5","جي ال اكس فيلوز","فيلوز",
                        "veloz","veloz base"], 0.90),
    ],

    # ─── Toyota GR86 2026 ───────────────────────────────────────
    ("toyota", "gr86"): [
        TrimDefinition("GR86-YSE-AT", "YSE Sport AT 2.4", "واي اس اي اتوماتيك", 0, "2.4L Petrol AT",
                       ["gr86 yse at","yse automatic","واي اس اي اتوماتيك","gr86 auto yse",
                        "جي ار 86 اتوماتيك yse"], 0.96),
        TrimDefinition("GR86-YSE-MT", "YSE Sport MT 2.4", "واي اس اي يدوي", 0, "2.4L Petrol MT",
                       ["gr86 yse mt","yse manual","واي اس اي يدوي","gr86 manual yse",
                        "جي ار 86 يدوي yse"], 0.95),
        TrimDefinition("GR86-AT", "Sport AT 2.4", "اتوماتيك", 0, "2.4L Petrol AT",
                       ["gr86 at","gr86 auto","sport at","اتوماتيك 86","جي ار 86 اتوماتيك",
                        "gr86 automatic"], 0.92),
        TrimDefinition("GR86-MT", "Sport MT 2.4 RS", "يدوي ار اس", 0, "2.4L Petrol MT",
                       ["gr86 mt","gr86 manual","sport mt","يدوي 86","جي ار 86 يدوي",
                        "gr86 rs","gr86 base"], 0.90),
    ],

    # ─── Toyota Supra 2026 ───────────────────────────────────────
    ("toyota", "supra"): [
        TrimDefinition("SUP-TRACK-AT", "GR Track Edition AT", "تراك ايديشن اتوماتيك", 0, "3.0L Petrol AT",
                       ["supra track at","track edition auto","تراك ايديشن اتوماتيك",
                        "gr supra at","سوبرا اتوماتيك"], 0.95),
        TrimDefinition("SUP-TRACK-MT", "GR Track Edition MT", "تراك ايديشن يدوي", 0, "3.0L Petrol MT",
                       ["supra track mt","track edition manual","تراك ايديشن يدوي",
                        "gr supra mt","سوبرا يدوي","supra base"], 0.92),
    ],

    # ─── Lexus LX 2025 / 2026 ───────────────────────────────────
    ("lexus", "lx"): [
        TrimDefinition("LX-VIP-BLACK-VP", "LX600 VIP Black Edition VP", "في اي بي بلاك ايديشن", 0, "V8 AT",
                       ["vip black edition vp","vip black","في اي بي بلاك","lx600 vip black",
                        "lx vip black","lx top"], 0.98),
        TrimDefinition("LX-VIP-VR", "LX600 VIP VR", "في اي بي في ار", 0, "V8 AT",
                       ["vip vr","lx600 vip vr","في اي بي في ار","lx vip vr"], 0.96),
        TrimDefinition("LX-ELITE-BB", "LX600 Elite BB", "اليت بي بي", 0, "V8 AT",
                       ["elite bb","lx600 elite bb","اليت بي بي","lx elite bb"], 0.95),
        TrimDefinition("LX-ELITE-BA", "LX600 Elite BA", "اليت بي ايه", 0, "V8 AT",
                       ["elite ba","lx600 elite ba","اليت بي ايه","lx elite ba"], 0.94),
        TrimDefinition("LX-FSPORT-FF", "LX600 F-Sport FF", "اف سبورت", 0, "V8 AT",
                       ["f-sport ff","lx600 f-sport","اف سبورت","lx f-sport","lx fsport"], 0.93),
        TrimDefinition("LX-OVERTRAIL-OT", "LX600 Overtrail OT", "اوفرتريل", 0, "V8 AT",
                       ["overtrail ot","lx600 overtrail","اوفرتريل","lx overtrail"], 0.92),
        TrimDefinition("LX700H-OVERTRAIL-OH", "LX700h Hybrid Overtrail OH", "لكزس 700 اوفرتريل هايبرد", 0, "3.5L HEV AT",
                       ["lx700h overtrail","lx700 overtrail oh","700h overtrail",
                        "لكزس 700 اوفرتريل"], 0.95),
        TrimDefinition("LX700H-ELITE-BH", "LX700h Hybrid Elite BH", "لكزس 700 اليت هايبرد", 0, "3.5L HEV AT",
                       ["lx700h elite bh","lx700 elite","700h elite","لكزس 700 اليت"], 0.93),
    ],

    # ─── Lexus NX 2025 / 2026 ───────────────────────────────────
    ("lexus", "nx"): [
        TrimDefinition("NX-350H-EXCEL-BH", "NX350h Hybrid Excellence BH", "اكسيلانس بي اتش هايبرد", 0, "2.5L HEV AT",
                       ["nx350h excellence bh","nx excellence bh hev","اكسيلانس بي اتش",
                        "nx350h bh","نكس اكسيلانس هايبرد"], 0.97),
        TrimDefinition("NX-350H-EXEC-HH", "NX350h Hybrid Executive HH", "اكسيكيوتف هايبرد", 0, "2.5L HEV AT",
                       ["nx350h executive hh","executive hev hh","اكسيكيوتف هايبرد هه",
                        "nx350h hh","نكس اكسيكيوتف هايبرد"], 0.95),
        TrimDefinition("NX-350H-AH", "NX350h Hybrid AH", "ايه اتش هايبرد", 0, "2.5L HEV AT",
                       ["nx350h ah","ah hev nx","ايه اتش هايبرد","نكس 350h ايه اتش"], 0.93),
        TrimDefinition("NX-350-EXCEL-PLUS-CC", "NX350 Excellence Plus CC", "اكسيلانس بلس سي سي", 0, "2.4L Turbo AT",
                       ["nx350 excellence plus cc","excellence plus cc","اكسيلانس بلس سي سي",
                        "nx350 cc","نكس 350 اكسيلانس بلس"], 0.95),
        TrimDefinition("NX-350-FSPORT-FF", "NX350 F-Sport FF", "اف سبورت اف اف", 0, "2.4L Turbo AT",
                       ["nx350 f-sport ff","nx f-sport","اف سبورت اف اف","نكس f-sport",
                        "nx350 fsport"], 0.93),
        TrimDefinition("NX-350-ELEGANT-AA", "NX350 Elegant AA", "ايليجنت ايه ايه", 0, "2.4L Turbo AT",
                       ["nx350 elegant aa","elegant aa","ايليجنت ايه ايه","نكس 350 ايليجنت",
                        "nx base","نكس عادي"], 0.88),
    ],

    # ─── Lexus RX 2025 / 2026 ───────────────────────────────────
    ("lexus", "rx"): [
        TrimDefinition("RX500H-FSPORT-FH", "RX500h F-Sport FH", "500h اف سبورت", 0, "2.4L HEV AT",
                       ["rx500h f-sport fh","rx500h fsport","500h f-sport","ار اكس 500 اف سبورت",
                        "rx500h top"], 0.97),
        TrimDefinition("RX500H-SPECIAL-SH", "RX500h Special Edition SH", "500h سبيشل ايديشن", 0, "2.4L HEV AT",
                       ["rx500h special edition sh","rx500h special","500h special","ار اكس 500 سبيشل",
                        "rx500h se"], 0.95),
        TrimDefinition("RX350H-HYBRID-BH", "RX350h Hybrid BH", "350h هايبرد بي اتش", 0, "2.5L HEV AT",
                       ["rx350h bh","rx350h hybrid bh","350h bh","ار اكس 350h بي اتش",
                        "rx350h"], 0.93),
        TrimDefinition("RX350-EXCEL-BB", "RX350 Excellence BB", "350 اكسلنس بي بي", 0, "2.4L Turbo AT",
                       ["rx350 excellence bb","excellence bb","اكسلنس بي بي","ار اكس 350 اكسلنس",
                        "rx350 bb"], 0.92),
        TrimDefinition("RX350-FSPORT-FF", "RX350 F-Sport FF", "350 اف سبورت اف اف", 0, "2.4L Turbo AT",
                       ["rx350 f-sport ff","rx350 fsport","350 f-sport","ار اكس 350 اف سبورت",
                        "rx350 fsport ff"], 0.91),
    ],

    # ─── Lexus ES 2025 ──────────────────────────────────────────
    ("lexus", "es"): [
        TrimDefinition("ES350-FSPORT-FF", "ES350 F-Sport FF", "350 اف سبورت اف اف", 0, "3.5L V6 AT",
                       ["es350 f-sport ff","es350 fsport","اف سبورت es350","ايه اس 350 اف سبورت"], 0.97),
        TrimDefinition("ES350-EXEC-DD", "ES350 Executive DD", "350 اكسيكيوتف دي دي", 0, "3.5L V6 AT",
                       ["es350 executive dd","es350 exec","اكسيكيوتف es350","ايه اس 350 اكسيكيوتف"], 0.95),
        TrimDefinition("ES350-ELITE-CC", "ES350 Elite CC", "350 اليت سي سي", 0, "3.5L V6 AT",
                       ["es350 elite cc","es elite","اليت es350","ايه اس 350 اليت"], 0.93),
        TrimDefinition("ES300H-PLUS-BH", "ES300h Hybrid Plus BH", "300h بلس بي اتش", 0, "2.5L HEV CVT",
                       ["es300h plus bh","es300h plus","300h plus","ايه اس 300h بلس"], 0.92),
        TrimDefinition("ES300H-AH", "ES300h Hybrid AH", "300h ايه اتش", 0, "2.5L HEV CVT",
                       ["es300h ah","300h ah","ايه اس 300h ايه اتش","es300h base"], 0.90),
        TrimDefinition("ES250-EXCEL-PLUS-BD", "ES250 Excellence Plus BD", "250 اكسيلانس بلس بي دي", 0, "2.5L AT",
                       ["es250 excellence plus bd","es250 plus","250 excellence plus","ايه اس 250 اكسيلانس بلس"], 0.92),
        TrimDefinition("ES250-ELEGANT-AA", "ES250 Elegant AA", "250 ايليجنت ايه ايه", 0, "2.5L AT",
                       ["es250 elegant aa","es250 elegant","250 elegant","ايه اس 250 ايليجنت","es250 base"], 0.88),
    ],

    # ─── Lexus IS 2026 ──────────────────────────────────────────
    ("lexus", "is"): [
        TrimDefinition("IS350-FSPORT-FF", "IS350 F-Sport FF", "350 اف سبورت اف اف", 0, "3.5L V6 AT",
                       ["is350 f-sport ff","is350 fsport","is f-sport","آي اس 350 اف سبورت"], 0.97),
        TrimDefinition("IS350-EXCEL-CC", "IS350 Excellence CC", "350 اكسلنس سي سي", 0, "3.5L V6 AT",
                       ["is350 excellence cc","is350 excellence","is excellence","آي اس 350 اكسلنس"], 0.93),
        TrimDefinition("IS350-ELITE-DD", "IS350 Elite DD", "350 اليت دي دي", 0, "3.5L V6 AT",
                       ["is350 elite dd","is elite","is350 elite","آي اس 350 اليت","is base"], 0.90),
    ],

    # ─── Lexus LS 2026 ──────────────────────────────────────────
    ("lexus", "ls"): [
        TrimDefinition("LS500H-HYBRID-AH", "LS500h Hybrid Elegant AH", "500h هايبرد ايليجنت", 0, "3.5L V6 HEV AT",
                       ["ls500h elegant ah","ls500h hybrid","500h elegant","ال اس 500h ايليجنت"], 0.96),
        TrimDefinition("LS500H-HYBRID-PLUS-HH", "LS500h Hybrid Plus HH", "500h بلس هه", 0, "3.5L V6 HEV AT",
                       ["ls500h plus hh","ls500h plus hybrid","500h plus","ال اس 500h بلس"], 0.94),
        TrimDefinition("LS500-ELEGANT-AA", "LS350 Elegant AA", "350 ايليجنت ايه ايه", 0, "3.5L V6 AT",
                       ["ls350 elegant aa","ls elegant","ls350 base","ال اس 350 ايليجنت",
                        "ls base","ال اس عادي"], 0.90),
        TrimDefinition("LS500-ELITE-CC", "LS500 Elite CC", "500 اليت سي سي", 0, "3.5L V6 AT",
                       ["ls500 elite cc","ls500 elite","500 elite","ال اس 500 اليت"], 0.93),
    ],

    # ─── Lexus LC 2026 ──────────────────────────────────────────
    ("lexus", "lc"): [
        TrimDefinition("LC500-ELITE-AA", "LC500 Elite AA", "500 اليت ايه ايه", 0, "5.0L V8 AT",
                       ["lc500 elite aa","lc500 elite","500 elite aa","ال سي 500 اليت"], 0.95),
        TrimDefinition("LC500-CONVERTIBLE-WB", "LC500 Convertible White & Blue WB", "500 كونفرتبل", 0, "5.0L V8 AT",
                       ["lc500 convertible","lc500 white blue","convertible wb","ال سي 500 كونفرتبل",
                        "lc convertible"], 0.97),
    ],

    # ─── Lexus UX 2025 ──────────────────────────────────────────
    ("lexus", "ux"): [
        TrimDefinition("UX300H-AH", "UX300H AH", "300h ايه اتش", 0, "2.0L HEV AT",
                       ["ux300h ah","ux300h","ux hybrid","يو اكس 300h","ux300h base"], 0.90),
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
    يطابق عنوان الإعلان مع الفئة الرسمية.
    محسّن لدعم:
    - الكلمات المفتاحية الدقيقة (عربي + إنجليزي)
    - الاختصارات الشائعة (YX, Y+, ...)
    - المطابقة الجزئية كـ fallback
    """
    trims = get_trims(brand, model)
    if not trims:
        return f"{model} Standard", "لا توجد فئات محددة", 0.50

    t = title.lower().strip()

    # الجولة الأولى: مطابقة keywords دقيقة
    for trim in trims:
        for kw in trim.keywords:
            if kw and len(kw) >= 2 and kw in t:
                return trim.name, f"كلمة مفتاحية: «{kw}»", trim.match_score

    # الجولة الثانية: مطابقة اسم الفئة مباشرة
    for trim in trims:
        trim_name_l = trim.name.lower()
        trim_ar_l   = trim.name_ar.lower()
        if trim_name_l in t or trim_ar_l in t:
            return trim.name, f"اسم الفئة: «{trim.name}»", trim.match_score

    # الجولة الثالثة: أبحث عن الفئة باستخدام السعر
    # (لو ما في نص كافٍ للتطابق، استخدم السعر القريب من MSRP)
    # هذا يُطبّق في _price_in_range مسبقاً

    # الجولة الرابعة: Word overlap
    best, best_score = trims[-1], 0.0
    for trim in trims:
        words = [w for w in trim.name.lower().split() if len(w) > 2]
        hits = sum(1 for w in words if w in t)
        score = (hits / len(words) * 0.4) if words else 0
        if score > best_score:
            best_score, best = score, trim

    # لو ما في تطابق واضح → أرجع الفئة الأقل ثقة (الأرخص عادة)
    if best_score < 0.2:
        return trims[-1].name, "لا تطابق — افتراضي", 0.40

    return best.name, "مطابقة جزئية", max(0.45, best_score)
