from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Query

from src.utils.db_manager import DatabaseManager
from src.config_loader import CONFIG
from src.audit.footprint import FootprintAuditor
from src.intelligence.chain_registry import SUPPORTED_CHAINS, list_chains
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()


def _detect_chain(address: str) -> str:
    if address.startswith("0x"):
        return "evm"
    if len(address) == 44 and address[0] in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz":
        return "solana"
    return "unknown"


@router.get("/wallet/profile/{address}")
def wallet_profile(address: str):
    db = DatabaseManager()
    chain_type = _detect_chain(address)

    total_txs = 0
    active_days = 0
    first_tx_date = None
    last_tx_date = None
    unique_protocols = []
    unread_alerts = 0

    try:
        total_txs = db.get_count("transactions")
        unique_protocols = db.get_unique_protocols_for_wallet(address)
        last_tx = db.get_last_tx_for_wallet(address)
        if last_tx and last_tx.get("timestamp"):
            last_tx_date = last_tx["timestamp"]
            if isinstance(last_tx_date, str):
                last_tx_date = last_tx_date[:10]
        active_days = db.get_active_days_for_wallet(address, days=30)
        alerts = db.get_alerts_for_wallet(address)
        unread_alerts = len(alerts)
    except Exception:
        pass

    days_since_last_tx = 0
    if last_tx_date:
        try:
            if isinstance(last_tx_date, str) and len(last_tx_date) == 10:
                d = datetime.strptime(last_tx_date, "%Y-%m-%d")
            else:
                d = datetime.fromisoformat(str(last_tx_date))
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            days_since_last_tx = (now - d).days
        except (ValueError, TypeError):
            pass

    inactivity_days = int(CONFIG.alerts.get("wallet_inactivity_days", 3))
    if days_since_last_tx < inactivity_days:
        activity_status = "active"
    elif days_since_last_tx < inactivity_days * 3:
        activity_status = "at_risk"
    else:
        activity_status = "inactive"

    if chain_type == "evm":
        try:
            auditor = FootprintAuditor()
            audit_result = auditor.audit_evm(address)
            if audit_result.get("total_txs", 0) > total_txs:
                total_txs = audit_result["total_txs"]
                unique_protocols = audit_result.get("unique_contracts", unique_protocols)
                first_tx_date = audit_result.get("first_tx_date", first_tx_date)
                last_tx_date = audit_result.get("last_tx_date", last_tx_date)
                active_days = audit_result.get("active_days", active_days)
        except Exception:
            pass

    return {
        "address": address,
        "chain": chain_type,
        "total_txs": total_txs,
        "active_days": active_days,
        "first_tx_date": first_tx_date,
        "last_tx_date": last_tx_date,
        "unique_protocols": unique_protocols,
        "days_since_last_tx": max(0, days_since_last_tx),
        "activity_status": activity_status,
        "unread_alerts": unread_alerts,
    }


@router.get("/wallet/alerts/{address}")
def wallet_alerts(address: str, acknowledged: bool = Query(False)):
    db = DatabaseManager()
    alerts = db.get_alerts_for_wallet(address, acknowledged=acknowledged)
    return [
        {
            "id": a["id"],
            "alert_type": a["alert_type"],
            "severity": a["severity"],
            "message": a["message"],
            "created_at": a["created_at"],
        }
        for a in alerts
    ]


@router.get("/wallet/audit/{address}")
def wallet_audit(address: str):
    """
    Multi-chain audit for a wallet across all supported EVM chains and Solana.
    """
    from src.intelligence.chain_registry import get_chain
    auditor = FootprintAuditor()
    results = {}

    chain_type = _detect_chain(address)
    if chain_type == "evm":
        for chain_name in SUPPORTED_CHAINS:
            if chain_name == "solana":
                continue
            result = auditor.audit_evm_chain(address, chain_name)
            if result["total_txs"] > 0 or result.get("error"):
                results[chain_name] = result
    elif chain_type == "solana":
        results["solana"] = auditor.audit_solana(address)

    return {
        "address": address,
        "chains": results,
        "total_chains_with_activity": len([k for k, v in results.items() if v.get("total_txs", 0) > 0]),
    }


@router.get("/chains")
def chains_list():
    return list_chains()
