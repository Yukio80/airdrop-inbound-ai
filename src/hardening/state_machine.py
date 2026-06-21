"""
State persistence between restarts.
Saves/loads a JSON state file to track completed steps, last run times,
protocol states, and route usage across bot restarts.
"""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_STATE_PATH = Path(__file__).parent.parent.parent / "state" / "bot_state.json"


class StateMachine:
    """
    Persists bot state to a JSON file so operations resume correctly
    after restarts or crashes.

    State structure:
    {
        "version": 1,
        "last_updated": "2026-06-21T13:00:00",
        "last_run": "2026-06-21T12:00:00",
        "completed_steps": ["galxe_scan", "lz_bridge", "yield_optimizer"],
        "protocol_states": {
            "aave": {"last_run": "...", "status": "ok"},
            "compound": {"last_run": "...", "status": "failed", "failures": 3},
        },
        "bridge_routes_used": [
            {"from": "arbitrum", "to": "base", "timestamp": "..."},
        ],
        "lz_last_route_index": 0,
        "galxe_last_page": 5,
        "solana_protocol_day": 3,
    }
    """

    def __init__(self, state_path: Optional[Path] = None):
        self.path = state_path or DEFAULT_STATE_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Any] = self._load()

    # --- Public API ---

    @property
    def last_run(self) -> Optional[str]:
        return self._data.get("last_run")

    @last_run.setter
    def last_run(self, value: str):
        self._data["last_run"] = value
        self._save()

    @property
    def completed_steps(self) -> List[str]:
        return self._data.get("completed_steps", [])

    def mark_step_complete(self, step: str):
        steps = self._data.setdefault("completed_steps", [])
        if step not in steps:
            steps.append(step)
        self._touch()

    def is_step_complete(self, step: str) -> bool:
        return step in self.completed_steps

    def reset_steps(self):
        self._data["completed_steps"] = []
        self._touch()

    # --- Protocol State ---

    def get_protocol_state(self, protocol: str) -> Dict[str, Any]:
        return self._data.setdefault("protocol_states", {}).get(protocol, {})

    def set_protocol_state(self, protocol: str, state: Dict[str, Any]):
        self._data.setdefault("protocol_states", {})[protocol] = state
        self._touch()

    def mark_protocol_failure(self, protocol: str, error: str):
        pstate = self._data.setdefault("protocol_states", {}).setdefault(protocol, {})
        pstate["last_run"] = datetime.now().isoformat()
        pstate["status"] = "failed"
        pstate["failures"] = pstate.get("failures", 0) + 1
        pstate["last_error"] = str(error)[:200]
        self._touch()

    def mark_protocol_success(self, protocol: str):
        pstate = self._data.setdefault("protocol_states", {}).setdefault(protocol, {})
        pstate["last_run"] = datetime.now().isoformat()
        pstate["status"] = "ok"
        pstate["failures"] = 0
        self._touch()

    def should_skip_protocol(self, protocol: str, max_failures: int = 3) -> bool:
        pstate = self.get_protocol_state(protocol)
        return pstate.get("failures", 0) >= max_failures

    # --- LZ Bridge Routes ---

    def add_bridge_route_used(self, from_chain: str, to_chain: str):
        routes = self._data.setdefault("bridge_routes_used", [])
        routes.append({
            "from": from_chain,
            "to": to_chain,
            "timestamp": datetime.now().isoformat(),
        })
        self._touch()

    @property
    def lz_last_route_index(self) -> int:
        return self._data.get("lz_last_route_index", 0)

    @lz_last_route_index.setter
    def lz_last_route_index(self, value: int):
        self._data["lz_last_route_index"] = value
        self._touch()

    # --- Generic KV ---

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self._touch()

    # --- Reset ---

    def reset(self):
        """Wipe all state (use with caution)."""
        self._data = {
            "version": 1,
            "last_updated": datetime.now().isoformat(),
            "completed_steps": [],
            "protocol_states": {},
            "bridge_routes_used": [],
        }
        self._save()

    # --- Internal ---

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                with open(self.path) as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load state file %s: %s", self.path, e)
        return {
            "version": 1,
            "last_updated": datetime.now().isoformat(),
            "completed_steps": [],
            "protocol_states": {},
            "bridge_routes_used": [],
        }

    def _save(self):
        self._data["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.path, "w") as f:
                json.dump(self._data, f, indent=2)
        except OSError as e:
            logger.error("Failed to save state to %s: %s", self.path, e)

    def _touch(self):
        self._save()
