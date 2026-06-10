import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import ensure_seeded
from .queries import QuerySpec, dataset_meta, kpis, run_query

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


@app.get("/api/meta")
def meta() -> dict:
    return dataset_meta()


@app.get("/api/kpis")
def get_kpis() -> dict:
    return kpis()


@app.post("/api/query")
def query(spec: QuerySpec) -> dict:
    return run_query(spec)
