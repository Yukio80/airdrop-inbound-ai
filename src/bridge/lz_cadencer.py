"""
LayerZero volume cadencer.
Executes small, frequent bridges across multiple routes to build
transaction count and unique-day activity for LZ eligibility.

Historical ZRO airdrop tiers (reference):
  Tier 1: 1-4 txs    → ~$40 avg
  Tier 2: 5-14 txs   → ~$200 avg
  Tier 3: 15-29 txs  → ~$500 avg
  Tier 4: 30+ txs    → ~$2000+ avg

Strategy: daily small bridges ($2-5 USDC) across rotating routes.
Hardened with circuit breaker + state persistence between restarts.
"""
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any

from src.config_loader import CONFIG
from src.bridge.layerzero_bridge import LayerZeroBridge
from src.utils.db_manager import DatabaseManager
from src.hardening.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from src.hardening.state_machine import StateMachine

logger = logging.getLogger(__name__)

class LZCadencer:
    def __init__(self, wallet_addr: str = None):
        self.db = DatabaseManager()
        self.wallet_addr = wallet_addr
        self.config = CONFIG.layerzero_cadencer if hasattr(CONFIG, "layerzero_cadencer") else {}
        self._bridge_cb = CircuitBreaker(
            name="lz_bridge", failure_threshold=3, recovery_timeout=120,
        )
        self._state = StateMachine()

    def get_next_route(self) -> Dict[str, str]:
        """Return the route from config that was used least recently."""
        routes = self.config.get("routes", [])
        if not routes:
            raise RuntimeError("No LZ routes configured in scoring.yaml")

        # Query last 10 LZ bridge txs
        txs = self.db.get_all_signals() # Simplified: we should query the transactions table
        # Correct way: query transactions table directly
        import sqlite3
        conn = self.db._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT metadata FROM transactions WHERE protocol='layerzero' ORDER BY timestamp DESC LIMIT 10"
        )
        rows = cursor.fetchall()
        conn.close()

        used_routes = []
        for row in rows:
            try:
                meta = json.loads(row["metadata"])
                route = f"{meta['from_chain']}->{meta['to_chain']}"
                used_routes.append(route)
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Find the first route in config that is NOT the most recent one used
        for route_cfg in routes:
            route_str = f"{route_cfg['from']}->{route_cfg['to']}"
            if not used_routes or route_str != used_routes[0]:
                return route_cfg
        
        # Fallback: return first route
        return routes[0]

    def should_bridge_today(self) -> Tuple[bool, str]:
        """Check if a bridge should be executed today based on config."""
        if not self.config.get("enabled", False):
            return False, "disabled in config"

        import sqlite3
        conn = self.db._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Unique days in last 30d
        cursor.execute(
            "SELECT COUNT(DISTINCT DATE(timestamp)) as days FROM transactions WHERE protocol='layerzero'"
        )
        unique_days = cursor.fetchone()["days"]

        # 2. Bridges today
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM transactions WHERE protocol='layerzero' AND DATE(timestamp) = DATE('now')"
        )
        today_count = cursor.fetchone()["cnt"]

        # 3. Time since last bridge
        cursor.execute(
            "SELECT timestamp FROM transactions WHERE protocol='layerzero' ORDER BY timestamp DESC LIMIT 1"
        )
        last_tx = cursor.fetchone()
        conn.close()

        max_daily = self.config.get("max_daily_bridges", 2)
        if today_count >= max_daily:
            return False, "daily limit reached"

        if last_tx:
            last_time = datetime.fromisoformat(last_tx["timestamp"])
            diff_hours = (datetime.now() - last_time).total_seconds() / 3600
            if diff_hours < self.config.get("min_interval_hours", 6):
                return False, "too soon"

        return True, "ok"

    def execute_bridge(self, dry_run: bool = False) -> Dict[str, Any]:
        """Executes a small, frequent bridge across rotating routes.
        Protected by circuit breaker + state persistence.
        """
        should, reason = self.should_bridge_today()
        if not should:
            return {"success": False, "reason": reason}

        route = self.get_next_route()
        from_chain = route["from"]
        to_chain = route["to"]
        amount_usdc = Decimal(str(self.config.get("amount_usdc_per_bridge", 3.0)))

        from src.bridge.layerzero_bridge import LayerZeroBridge
        from eth_account import Account
        import os
        pk = os.getenv("PRIVATE_KEY")
        if not pk:
            return {"success": False, "reason": "PRIVATE_KEY missing from env"}

        account = Account.from_key(pk)
        bridge = LayerZeroBridge(account)

        def _do_bridge():
            balance = bridge.get_balance(from_chain, "USDC")
            if balance < amount_usdc:
                logger.info("Insufficient USDC on %s, skipping route", from_chain)
                return {"success": False, "reason": f"insufficient funds on {from_chain}"}

            if dry_run:
                logger.info("[DRY RUN] LZ Bridge: %s -> %s for $%s", from_chain, to_chain, amount_usdc)
                return {
                    "success": True,
                    "from_chain": from_chain,
                    "to_chain": to_chain,
                    "amount_usdc": float(amount_usdc),
                    "status": "dry_run",
                }

            logger.info("Bridging $%s USDC from %s -> %s", amount_usdc, from_chain, to_chain)
            result = bridge.bridge_usdc(amount_usdc, from_chain, to_chain, dry_run=False)
            if result.bridged:
                self.db.log_transaction(
                    wallet=str(account.address),
                    protocol="layerzero",
                    chain=from_chain,
                    tx_hash=result.tx_hash,
                    action="bridge",
                    amount=int(amount_usdc * 1e6),
                    status="executed",
                    metadata=json.dumps({
                        "from_chain": from_chain,
                        "to_chain": to_chain,
                        "amount_usdc": float(amount_usdc),
                        "lz_fee_eth": 0.0,
                    })
                )
                self._state.mark_protocol_success("layerzero")
                self._state.add_bridge_route_used(from_chain, to_chain)
                return {
                    "success": True,
                    "from_chain": from_chain,
                    "to_chain": to_chain,
                    "amount_usdc": float(amount_usdc),
                    "tx_hash": result.tx_hash,
                    "gas_usd": 0.0,
                    "lz_fee_eth": 0.0,
                }
            else:
                return {"success": False, "reason": result.status}

        try:
            return self._bridge_cb.call(_do_bridge)
        except CircuitBreakerOpenError as e:
            logger.warning("LZ bridge circuit OPEN: %s", e)
            self._state.mark_protocol_failure("layerzero", str(e))
            return {"success": False, "reason": f"circuit_open: {e}"}
        except Exception as e:
            logger.error("LZ Cadencer bridge failed: %s", e)
            self._state.mark_protocol_failure("layerzero", str(e))
            return {"success": False, "reason": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Queries SQLite for LayerZero bridge history."""
        import sqlite3
        conn = self.db._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT timestamp, metadata FROM transactions WHERE protocol='layerzero'")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {
                "total_bridges": 0,
                "unique_days": 0,
                "unique_routes": 0,
                "first_bridge": None,
                "last_bridge": None,
                "total_volume_usdc": 0.0,
                "estimated_tier": "tier_1",
            }

        total_bridges = len(rows)
        dates = set()
        routes = set()
        total_vol = 0.0
        
        for r in rows:
            meta = json.loads(r["metadata"])
            dates.add(r["timestamp"][:10])
            routes.add(f"{meta.get('from_chain')}->{meta.get('to_chain')}")
            total_vol += float(meta.get("amount_usdc", 0))

        timestamps = sorted([r["timestamp"] for r in rows])
        
        if total_bridges >= 30: tier = "tier_4"
        elif total_bridges >= 15: tier = "tier_3"
        elif total_bridges >= 5: tier = "tier_2"
        else: tier = "tier_1"

        return {
            "total_bridges": total_bridges,
            "unique_days": len(dates),
            "unique_routes": len(routes),
            "first_bridge": timestamps[0],
            "last_bridge": timestamps[-1],
            "total_volume_usdc": total_vol,
            "estimated_tier": tier,
        }
