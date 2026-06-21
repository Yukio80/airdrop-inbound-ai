"""API route exposing bot state machine data."""
from fastapi import APIRouter
from src.hardening.state_machine import StateMachine

router = APIRouter(tags=["state"])


@router.get("/api/state")
def get_state():
    sm = StateMachine()
    data = sm._data
    return {
        "last_run": data.get("last_run"),
        "cycle_date": data.get("cycle_date"),
        "cycle_count": data.get("cycle_count", 0),
        "completed_steps": data.get("completed_steps", []),
        "protocol_states": {
            k: {
                "status": v.get("status"),
                "failures": v.get("failures", 0),
                "last_run": v.get("last_run"),
                "last_error": v.get("last_error"),
            }
            for k, v in data.get("protocol_states", {}).items()
        },
        "recent_routes": data.get("bridge_routes_used", [])[-5:],
        "lz_route_index": data.get("lz_last_route_index", 0),
        "last_solana_farm": data.get("last_solana_farm"),
    }


@router.post("/api/state/reset")
def reset_state():
    sm = StateMachine()
    sm.reset()
    return {"status": "reset"}
