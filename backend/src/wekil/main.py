from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import analyst, jobs, merchant
from .config import settings
from .db import Base, engine

Base.metadata.create_all(engine)

app = FastAPI(title="Wekil", description="AI KYB and compliance analyst for payment gateways")
app.add_middleware(CORSMiddleware, allow_origins=[settings().frontend_url, "http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])
for r in (merchant.router, analyst.router, analyst.secured, jobs.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"ok": True}
