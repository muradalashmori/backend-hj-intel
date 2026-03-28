FROM python:3.12-slim

# ── System deps for Playwright Chromium ────────────────────────
RUN apt-get update && apt-get install -y \
    wget curl ca-certificates gnupg \
    # Chromium runtime deps
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libx11-6 libx11-xcb1 \
    libxcb1 libxext6 libxfont-dev fonts-freefont-ttf \
    # Arabic font support
    fonts-noto-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ─────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Playwright: install Chromium only ──────────────────────────
RUN python -m playwright install chromium

# ── App files ──────────────────────────────────────────────────
COPY main.py .
COPY scraper_playwright.py .
COPY trims_config.py .

# ── Security: non-root user ─────────────────────────────────────
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30m --timeout=15s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 1 worker فقط لأن Playwright يستهلك ذاكرة
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
