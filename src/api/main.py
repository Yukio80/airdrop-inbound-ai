"""
FastAPI application exposing airdrop intelligence data.
Run with: uvicorn src.api.main:app --reload --port 8000
Or: python ecosystem.py api
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.opportunities import router as opp_router
from src.api.routes.wallet import router as wallet_router
from src.api.routes.intelligence import router as intel_router
from src.api.routes.state import router as state_router
from src.api.health import router as health_router

app = FastAPI(
    title="Airdrop Inbound AI",
    description="Airdrop eligibility intelligence API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(opp_router, prefix="/api")
app.include_router(wallet_router, prefix="/api")
app.include_router(intel_router, prefix="/api")
app.include_router(state_router)
app.include_router(health_router)
