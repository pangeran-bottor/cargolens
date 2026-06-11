import os
from datetime import date

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .db import ensure_seeded
from .orchestrator import answer_question
from .queries import QuerySpec, dataset_meta, kpis, run_query

app = FastAPI(title="CargoLens API")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Simple shared access code for reviewers. Unset = open (local dev).
# /api/health stays open for Railway's healthcheck; OPTIONS passes through
# because CORS preflights never carry custom headers.
ACCESS_CODE = os.environ.get("ACCESS_CODE")


@app.middleware("http")
async def require_access_code(request: Request, call_next):
    if (
        ACCESS_CODE
        and request.method != "OPTIONS"
        and request.url.path.startswith("/api")
        and request.url.path != "/api/health"
        and request.headers.get("x-access-code") != ACCESS_CODE
    ):
        return JSONResponse({"detail": "Invalid or missing access code"}, status_code=401)
    return await call_next(request)

# Global daily cap on LLM calls: the chat endpoint is public and every call
# costs money. In-memory is fine — single instance, resets on redeploy.
DAILY_CHAT_CAP = int(os.environ.get("DAILY_CHAT_CAP", "500"))
_chat_usage = {"day": None, "count": 0}


def _within_daily_cap() -> bool:
    today = date.today().isoformat()
    if _chat_usage["day"] != today:
        _chat_usage["day"] = today
        _chat_usage["count"] = 0
    if _chat_usage["count"] >= DAILY_CHAT_CAP:
        return False
    _chat_usage["count"] += 1
    return True


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.on_event("startup")
def startup() -> None:
    ensure_seeded()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict:
    return dataset_meta()


@app.get("/api/kpis")
def get_kpis() -> dict:
    return kpis()


@app.post("/api/query")
def query(spec: QuerySpec) -> dict:
    return run_query(spec)


@app.post("/api/chat")
@limiter.limit("10/minute")
def chat(request: Request, body: ChatRequest) -> dict:
    if not _within_daily_cap():
        return {
            "answer": None,
            "results": [],
            "error": "The daily question limit for this demo has been reached. "
                     "The dashboard remains fully functional.",
        }
    return answer_question(body.question)
