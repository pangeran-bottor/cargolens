import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import ensure_seeded

app = FastAPI(title="CargoLens API")

frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    ensure_seeded()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
