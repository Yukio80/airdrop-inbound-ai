import time
from typing import List, Optional

from fastapi import APIRouter, Query

from src.utils.db_manager import DatabaseManager
from src.intelligence.ranker import EligibilityRanker
from src.config_loader import CONFIG
from src.yield_optimizer.apy_feed import APYFeed

EVM_ADDR = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"

router = APIRouter()

_cache = {}
_cache_time = {}
TTL = 300


def _get_cached(key: str, fn):
    now = time.time()
    if key in _cache and now - _cache_time.get(key, 0) < TTL:
        return _cache[key]
    result = fn()
    _cache[key] = result
    _cache_time[key] = now
    return result


def _ranked_list() -> List[dict]:
    db = DatabaseManager()
    signals = db.get_all_signals()
    ranker = EligibilityRanker()
    return ranker.rank(signals)


@router.get("/opportunities/top")
def top_opportunities(
    limit: int = Query(10, ge=1, le=100),
    min_score: float = Query(0, ge=0),
):
    ranked = _get_cached("ranked", _ranked_list)
    filtered = [r for r in ranked if r["eligibility_score"] >= min_score]
    result = []
    for i, r in enumerate(filtered[:limit], 1):
        result.append({
            "rank": i,
            "name": r["name"],
            "chain": r["chain"],
            "eligibility_score": r["eligibility_score"],
            "action_label": r["action_label"],
            "recommended_frequency": "daily" if r["eligibility_score"] >= CONFIG.thresholds["high_urgency_score"] else "weekly",
            "window_urgency": "high" if r["eligibility_score"] >= CONFIG.thresholds["high_urgency_score"] else "medium",
            "has_token": False,
            "funding_usd": 0,
            "tvl_trend": "growing" if r.get("base_score", 0) > 50 else "stable",
        })
    return result


@router.get("/yield/rates")
def yield_rates(
    asset: Optional[str] = Query(None),
    chain: Optional[str] = Query(None),
):
    feed = APYFeed()
    rates = feed.get_all_rates()
    if asset:
        rates = [r for r in rates if r["asset"].upper() == asset.upper()]
    if chain:
        rates = [r for r in rates if r["chain"] == chain.lower()]
    return rates


@router.get("/yield/optimize")
def yield_optimize(
    dry_run: bool = Query(True, description="Read-only mode by default"),
):
    from src.yield_optimizer.optimizer import YieldOptimizer
    optimizer = YieldOptimizer(dry_run=dry_run)
    report = optimizer.run(
        wallet_evm=EVM_ADDR,
        wallet_solana_path="wallets/solana_real.sol.json"
    )
    return report


@router.get("/opportunities/high-probability")
def high_probability_opportunities():
    ranked = _get_cached("ranked", _ranked_list)
    threshold = CONFIG.thresholds["high_urgency_score"]
    result = []
    for i, r in enumerate(ranked, 1):
        if r["eligibility_score"] < threshold:
            continue
        result.append({
            "rank": i,
            "name": r["name"],
            "chain": r["chain"],
            "eligibility_score": r["eligibility_score"],
            "action_label": r["action_label"],
            "recommended_frequency": "daily",
            "window_urgency": "high",
            "has_token": False,
            "funding_usd": 0,
            "tvl_trend": "growing",
        })
    return result
