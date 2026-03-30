# ── Base image (جاهز بكل شيء) ────────────────────────────────
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

# ── تقليل اللوج ──────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── App files ─────────────────────────────────────────────────
COPY . .

# ── Non-root user (موجود مسبقًا لكن نتأكد) ───────────────────
USER pwuser

EXPOSE 8000

# ── Healthcheck ───────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# ── تشغيل السيرفر ────────────────────────────────────────────
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]