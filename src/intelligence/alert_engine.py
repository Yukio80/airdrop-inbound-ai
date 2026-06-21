"""
Monitors wallet activity and protocol signals.
Generates alerts based on config/scoring.yaml thresholds.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.config_loader import CONFIG
from src.utils.db_manager import DatabaseManager
from src.notifications import NotificationManager
from src.yield_optimizer.apy_feed import APYFeed
from src.yield_optimizer.balance_reader import BalanceReader

logger = logging.getLogger(__name__)


class AlertEngine:
    """
    Checks for alert conditions and persists them to user_alerts table.
    Designed to run at the end of each `ecosystem.py all` cycle.
    """

    def __init__(self, db: Optional[DatabaseManager] = None,
                 notifier: Optional[NotificationManager] = None):
        self.db = db or DatabaseManager()
        self.notifier = notifier or NotificationManager()

    def run_all_checks(self, wallet: str = None, dry_run: bool = False) -> List[dict]:
        """
        Runs all alert checks. Returns list of triggered alerts.
        If dry_run=True, returns alerts without saving to DB.
        """
        alerts = []

        inactivity = self.check_wallet_inactivity(wallet)
        if inactivity:
            alerts.append(inactivity)

        frequency = self.check_activity_frequency(wallet)
        if frequency:
            alerts.append(frequency)

        gas_alert = self.check_gas_reserves(wallet)
        if gas_alert:
            alerts.append(gas_alert)

        if not dry_run:
            for a in alerts:
                self.db.save_alert(
                    alert_type=a["alert_type"],
                    message=a["message"],
                    severity=a["severity"],
                    wallet=a.get("wallet"),
                    protocol=a.get("protocol"),
                    metadata=a.get("metadata"),
                )
                self._send_notification(a)

        return alerts

    def run_all_checks_with_ranked(self, wallet: str = None,
                                    ranked_protocols: List[dict] = None,
                                    dry_run: bool = False) -> List[dict]:
        """
        Runs all alert checks including high-AOI protocol checks.
        """
        alerts = self.run_all_checks(wallet=wallet, dry_run=dry_run)

        if ranked_protocols:
            high_aoi = self.check_high_aoi_protocols(ranked_protocols, wallet)
            alerts.extend(high_aoi)
            if not dry_run:
                for a in high_aoi:
                    self.db.save_alert(
                        alert_type=a["alert_type"],
                        message=a["message"],
                        severity=a["severity"],
                        wallet=a.get("wallet"),
                        protocol=a.get("protocol"),
                        metadata=a.get("metadata"),
                    )
                    self._send_notification(a)

        return alerts

    def _send_notification(self, alert: dict):
        severity = alert["severity"]
        self.notifier.notify("ALERT", {
            "alert_type": alert["alert_type"],
            "severity": severity,
            "severity_icon": {"critical": "🔴", "warning": "⚠️", "info": "ℹ️"}.get(severity, ""),
            "message": alert["message"],
        })

    def check_wallet_inactivity(self, wallet: str = None) -> Optional[dict]:
        """
        Check if wallet has been inactive for configured days.
        """
        if not wallet:
            return None

        last_tx = self.db.get_last_tx_for_wallet(wallet)
        if not last_tx or not last_tx.get("timestamp"):
            return None

        try:
            last_ts = last_tx["timestamp"]
            if isinstance(last_ts, str):
                last_tx_date = datetime.fromisoformat(last_ts)
            else:
                last_tx_date = last_ts
        except (ValueError, TypeError):
            return None

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        days_inactive = (now - last_tx_date).days
        threshold = int(CONFIG.alerts.get("wallet_inactivity_days", 3))

        if days_inactive >= threshold:
            severity = "critical" if days_inactive >= 7 else "warning"
            return {
                "alert_type": "inactivity",
                "wallet": wallet,
                "severity": severity,
                "message": (
                    f"Wallet {wallet[:8]}... inactive for {days_inactive}d. "
                    f"Last tx: {last_tx_date.date()}. Risk: losing eligibility streak."
                ),
                "metadata": {"days_inactive": days_inactive, "last_tx": str(last_tx_date)},
            }
        return None

    def check_high_aoi_protocols(self, ranked_protocols: List[dict],
                                  wallet: str = None) -> List[dict]:
        """
        Alert on high-AOI protocols not interacted with in 30 days.
        """
        threshold = float(CONFIG.alerts.get("high_aoi_threshold", 70))
        alerts = []

        for p in ranked_protocols:
            score = p.get("eligibility_score", 0)
            if score < threshold:
                continue

            name = p.get("protocol", p.get("name", "unknown"))
            if wallet:
                interactions = self.db.get_protocol_interaction_days(wallet, name, days=30)
                if interactions > 0:
                    continue

            alerts.append({
                "alert_type": "high_aoi",
                "protocol": name,
                "severity": "warning",
                "message": (
                    f"{name} AOI={score:.1f} — no interaction in 30d. "
                    f"Urgency: {p.get('window_urgency', 'unknown')}."
                ),
                "metadata": {"aoi": score, "chain": p.get("chain")},
            })

        return alerts

    def check_yield_opportunity(self, wallet: str = None) -> Optional[dict]:
        try:
            feed = APYFeed()
            rates = feed.get_all_rates()
            reader = BalanceReader()
            deposited = reader.get_deposited_balances(wallet) if wallet else []
            cfg = CONFIG.yield_optimizer
            min_improve = cfg.get("min_improvement_pct", 1.5)
            alert_threshold = min_improve * 2

            for dep in deposited:
                asset = dep["token"]
                location = dep["location"]
                if asset not in cfg.get("enabled_assets", ["USDC", "USDT"]):
                    continue
                current_apy = 0.0
                for r in rates:
                    if r["protocol"] == location and r["asset"] == asset:
                        current_apy = r["apy_pct"]
                        break
                best = None
                for r in rates:
                    if r["asset"] == asset and (best is None or r["apy_pct"] > best["apy_pct"]):
                        best = r
                if best and best["protocol"] != location:
                    improvement = best["apy_pct"] - current_apy
                    if improvement >= alert_threshold:
                        return {
                            "alert_type": "yield_opportunity",
                            "severity": "info",
                            "wallet": wallet,
                            "message": (
                                f"Better yield available: {best['protocol']} {best['apy_pct']:.1f}% "
                                f"vs current {current_apy:.1f}% on {location}. "
                                f"Run `ecosystem.py yield` to rebalance."
                            ),
                            "metadata": {
                                "best_protocol": best["protocol"],
                                "best_apy": best["apy_pct"],
                                "current_apy": current_apy,
                                "asset": asset,
                            },
                        }
        except Exception as e:
            logger.warning(f"Yield opportunity check failed: {e}")
        return None

    def check_activity_frequency(self, wallet: str = None) -> Optional[dict]:
        """
        Check if wallet has enough active days per week.
        """
        if not wallet:
            return None

        active_days = self.db.get_active_days_for_wallet(wallet, days=7)
        min_days = int(CONFIG.alerts.get("min_active_days_per_week", 2))

        if active_days < min_days:
            return {
                "alert_type": "low_frequency",
                "wallet": wallet,
                "severity": "info",
                "message": (
                    f"Only {active_days} active day(s) in last 7d. "
                    f"Target: {min_days}d/week for consistent eligibility footprint."
                ),
                "metadata": {"active_days_7d": active_days},
            }
        return None

    def check_gas_reserves(self, wallet: str = None) -> Optional[dict]:
        """Check if wallet has enough native gas for upcoming operations."""
        if not wallet:
            return None
        
        from src.intelligence.chain_registry import get_chain
        from web3 import Web3
        
        alerts = []
        # Check Arbitrum as primary hub
        cfg = get_chain("arbitrum")
        w3 = Web3(Web3.HTTPProvider(cfg.rpc))
        try:
            balance = w3.eth.get_balance(wallet) / 1e18
            min_gas = 0.005 # 0.005 ETH threshold
            if balance < min_gas:
                return {
                    "alert_type": "low_gas",
                    "wallet": wallet,
                    "severity": "critical",
                    "message": f"Critical gas reserve: {balance:.4f} ETH on Arbitrum. Deposit more to avoid paused automation.",
                    "metadata": {"balance": balance, "threshold": min_gas}
                }
        except Exception as e:
            logger.warning(f"Gas check failed: {e}")
            
        return None
