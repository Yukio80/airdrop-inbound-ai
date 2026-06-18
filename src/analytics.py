from datetime import datetime, timedelta
from typing import Optional
import sqlite3

import httpx


class PerformanceAnalyzer:
    def __init__(self, db_path: str = "airdrop_bot.db"):
        self.db_path = db_path

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execution_summary(self, days: int = 7) -> dict:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT status, COUNT(*) as cnt FROM signals WHERE last_updated >= ? GROUP BY status",
            (since,),
        )
        status_counts = {row["status"]: row["cnt"] for row in cursor.fetchall()}

        cursor.execute(
            "SELECT AVG(score) as avg_score FROM signals WHERE last_updated >= ? AND status = 'executed'",
            (since,),
        )
        avg_row = cursor.fetchone()
        avg_score = round(avg_row["avg_score"], 1) if avg_row and avg_row["avg_score"] else 0.0

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM transactions WHERE timestamp >= ?",
            (since,),
        )
        tx_count = cursor.fetchone()["cnt"]

        gas_eth = self._estimate_gas_cost_eth(tx_count)
        gas_usd = self._eth_to_usd(gas_eth)

        conn.close()

        return {
            "period_days": days,
            "executed": status_counts.get("executed", 0),
            "ignored": status_counts.get("ignored", 0),
            "errors": status_counts.get("error", 0),
            "pending": status_counts.get("pending", 0),
            "avg_score_executed": avg_score,
            "total_transactions": tx_count,
            "estimated_gas_eth": round(gas_eth, 6),
            "estimated_gas_usd": round(gas_usd, 2),
        }

    def protocol_roi(self, protocol_name: str, days: int = 30) -> dict:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM transactions WHERE protocol = ? AND timestamp >= ?",
            (protocol_name, since),
        )
        tx_count = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT score FROM signals WHERE protocol = ?",
            (protocol_name,),
        )
        score_row = cursor.fetchone()
        score = score_row["score"] if score_row else 0

        cursor.execute(
            "SELECT status FROM signals WHERE protocol = ?",
            (protocol_name,),
        )
        status_row = cursor.fetchone()
        status = status_row["status"] if status_row else "unknown"

        gas_eth = self._estimate_gas_cost_eth(tx_count)
        gas_usd = self._eth_to_usd(gas_eth)
        token_price = self._fetch_token_price(protocol_name)

        estimated_airdrop_value = 0
        if score >= 30 and token_price:
            estimated_airdrop_value = round(tx_count * 0.5 * token_price, 2)

        conn.close()

        return {
            "protocol": protocol_name,
            "status": status,
            "score": score,
            "transactions": tx_count,
            "estimated_gas_eth": round(gas_eth, 6),
            "estimated_gas_usd": round(gas_usd, 2),
            "estimated_airdrop_value_usd": estimated_airdrop_value,
            "estimated_roi_usd": round(estimated_airdrop_value - gas_usd, 2),
        }

    def best_performing_chains(self, days: int = 30) -> list:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT s.chain,
                      COUNT(*) as total_signals,
                      SUM(CASE WHEN s.status = 'executed' THEN 1 ELSE 0 END) as executed,
                      AVG(s.score) as avg_score,
                      COUNT(t.id) as tx_count
               FROM signals s
               LEFT JOIN transactions t ON s.protocol = t.protocol AND t.timestamp >= ?
               WHERE s.last_updated >= ?
               GROUP BY s.chain
               ORDER BY executed DESC""",
            (since, since),
        )

        results = []
        for row in cursor.fetchall():
            success_rate = round(row["executed"] / row["total_signals"] * 100, 1) if row["total_signals"] > 0 else 0
            results.append({
                "chain": row["chain"],
                "total_signals": row["total_signals"],
                "executed": row["executed"],
                "success_rate": success_rate,
                "avg_score": round(row["avg_score"], 1) if row["avg_score"] else 0,
                "tx_count": row["tx_count"],
            })

        conn.close()
        return results

    def _estimate_gas_cost_eth(self, tx_count: int) -> float:
        avg_gas_per_tx = 150000
        avg_gwei = 25
        return tx_count * avg_gas_per_tx * avg_gwei / 1e9

    def _eth_to_usd(self, eth_amount: float) -> float:
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(
                    "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
                )
                resp.raise_for_status()
                price = resp.json().get("ethereum", {}).get("usd", 2500)
                return eth_amount * price
        except Exception as e:
            print(f"  ⚠️ CoinGecko price fetch failed ({e}), using default $2500/ETH")
            return eth_amount * 2500

    def _fetch_token_price(self, protocol_name: str) -> Optional[float]:
        coin_map = {
            "Lido": "lido-dao",
            "Aave V3": "aave",
            "Uniswap": "uniswap",
            "Compound": "compound-governance-token",
            "Curve": "curve-dao-token",
            "SushiSwap": "sushi",
        }
        coin_id = coin_map.get(protocol_name)
        if not coin_id:
            return None
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(
                    f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
                )
                resp.raise_for_status()
                data = resp.json().get(coin_id, {})
                return data.get("usd")
        except Exception:
            return None
