# ── Stage 1: Builder ──
FROM python:3.11-slim AS builder

WORKDIR /app

# COPY requirements.txt riêng một dòng trước pip install
COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy các dependencies đã cài từ builder
COPY --from=builder /install /usr/local

# Copy source code sau khi đã cài dependencies
COPY app ./app
COPY utils ./utils

# Tạo user không phải root để chạy ứng dụng
RUN useradd --create-home --uid 10001 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
