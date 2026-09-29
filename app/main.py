"""Agent service — điểm ráp nối của cả lab (CP1, CP3, CP4).

Luồng một request tới /ask:

    client ──► verify_api_key ──► rate_limiter ──► cost_guard
                                                       │
                              store.get_history ◄──────┘
                                       │
                                    ask_llm
                                       │
                              store.append × 2 ──► cost_guard.record ──► log_event
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from utils.mock_llm import ask_llm

from .auth import verify_api_key
from .config import get_settings
from .cost_guard import CostGuard
from .lifecycle import lifecycle
from .logging_utils import log_event
from .rate_limiter import RateLimiter
from .store import ConversationStore, get_redis_client

import os

SERVICE_NAME = "day12-agent"
SERVICE_VERSION = "1.0.0"


# ─────────────────────────────────────────────────────────────
# Providers — CHO SẴN
# Tách ra thành hàm để test có thể thay bằng Redis giả qua
# app.dependency_overrides, và để kết nối Redis chỉ tạo khi thật sự cần.
# ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_store() -> ConversationStore:
    try:
        client = get_redis_client()
    except Exception:
        import redis
        client = redis.from_url("redis://localhost:6379/0", decode_responses=True)
    return ConversationStore(client)


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    limit = 10
    try:
        limit = get_settings().rate_limit_per_minute
    except Exception:
        limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", 10))
    return RateLimiter(get_redis_client(), limit)


@lru_cache(maxsize=1)
def get_cost_guard() -> CostGuard:
    budget = 10.0
    try:
        budget = get_settings().monthly_budget_usd
    except Exception:
        budget = float(os.getenv("MONTHLY_BUDGET_USD", 10.0))
    return CostGuard(get_redis_client(), budget)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """CHO SẴN — chạy lúc app khởi động và lúc tắt."""
    lifecycle.install()
    log_event("service_started", service=SERVICE_NAME, version=SERVICE_VERSION)
    yield
    log_event("service_stopped", service=SERVICE_NAME)


app = FastAPI(title="Day 12 Production Agent", version=SERVICE_VERSION, lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


# ─────────────────────────────────────────────────────────────
# Health & readiness
# ─────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    if lifecycle.shutting_down:
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    redis_val = os.getenv("REDIS_URL", "")
    diag = {
        "has_agent_api_key": bool(os.getenv("AGENT_API_KEY")),
        "has_redis_url": bool(redis_val),
        "redis_val_len": len(redis_val),
        "redis_val_prefix": redis_val[:12] if redis_val else "",
        "env_keys": [k for k in sorted(os.environ.keys()) if not any(x in k.lower() for x in ["key", "secret", "token", "pass"])],
    }
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION, "diag": diag}


@app.get("/ready")
def ready(store: ConversationStore = Depends(get_store)):
    if lifecycle.shutting_down:
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    try:
        is_ready = store.ping()
    except Exception:
        is_ready = False
    if not is_ready:
        return JSONResponse(status_code=503, content={"status": "not ready", "redis": False})
    return {"status": "ready", "redis": True}


# ─────────────────────────────────────────────────────────────
# Endpoint chính
# ─────────────────────────────────────────────────────────────
@app.post("/ask")
def ask(
    payload: AskRequest,
    user_id: str = Depends(verify_api_key),
    store: ConversationStore = Depends(get_store),
    limiter: RateLimiter = Depends(get_rate_limiter),
    guard: CostGuard = Depends(get_cost_guard),
):
    limiter.check(user_id)
    guard.check(user_id)
    history = store.get_history(user_id)
    result = ask_llm(payload.question, history)
    store.append(user_id, "user", payload.question)
    store.append(user_id, "assistant", result["answer"])
    guard.record(user_id, result["cost_usd"])
    log_event(
        "ask_completed",
        user_id=user_id,
        tokens_in=result["tokens_in"],
        tokens_out=result["tokens_out"],
        cost_usd=result["cost_usd"],
    )
    return {
        "answer": result["answer"],
        "user_id": user_id,
        "history_length": len(history),
        "cost_usd": result["cost_usd"],
        "tokens": {"in": result["tokens_in"], "out": result["tokens_out"]},
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
