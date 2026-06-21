import time
from typing import List, Optional

from fastapi import APIRouter, Query

from src.utils.db_manager import DatabaseManager
from src.intelligence.ranker import EligibilityRanker
from src.adapters.magic_eden_real import MagicEdenRealAdapter
from src.bridge.lz_cadencer import LZCadencer
from solana_wallet import SolanaWalletManager
from solders.keypair import Keypair

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


@router.get("/intel/ranked")
def intel_ranked(
    limit: int = Query(20, ge=1, le=200),
    chain: Optional[str] = Query(None),
):
    ranked = _get_cached("ranked", _ranked_list)
    if chain:
        ranked = [r for r in ranked if r.get("chain", "").lower() == chain.lower()]
    result = []
    for i, r in enumerate(ranked[:limit], 1):
        result.append({
            "rank": i,
            "name": r["name"],
            "eligibility_score": r["eligibility_score"],
            "explain": r["explain"],
            "action_label": r["action_label"],
            "chain": r["chain"],
        })
    return result


@router.get("/intel/explain/{protocol_name}")
def intel_explain(protocol_name: str):
    ranked = _get_cached("ranked", _ranked_list)
    for r in ranked:
        if r["name"].lower() == protocol_name.lower():
            return {
                "name": r["name"],
                "eligibility_score": r["eligibility_score"],
                "explain": r["explain"],
                "action_label": r["action_label"],
                "chain": r["chain"],
            }
    return {"error": f"Protocol '{protocol_name}' not found"}, 404


@router.get("/nft/portfolio/{wallet}")
def nft_portfolio(wallet: str):
    try:
        wm = SolanaWalletManager()
        wallet_obj = wm.load_wallet("solana_real")
        # We use the provided wallet address from URL for the API call, 
        # but the adapter needs a Keypair for some functions.
        # Since get_portfolio only needs the address, we can pass it directly.
        adapter = MagicEdenRealAdapter(None, wallet_obj)
        portfolio = adapter.get_portfolio(wallet)
        return {
            "wallet": wallet,
            "total_nfts": portfolio["total_nfts"],
            "collections": portfolio["collections"],
            "estimated_value_sol": portfolio["estimated_value_sol"],
        }
    except Exception as e:
        return {"error": str(e)}, 500


@router.get("/lz/stats")
def lz_stats():
    try:
        lz = LZCadencer()
        stats = lz.get_stats()
        should, reason = lz.should_bridge_today()
        # next_route requires call to get_next_route()
        next_route = lz.get_next_route()
        return {
            "total_bridges": stats["total_bridges"],
            "unique_days": stats["unique_days"],
            "estimated_tier": stats["estimated_tier"],
            "total_volume_usdc": stats["total_volume_usdc"],
            "next_route": next_route,
            "should_bridge_today": should,
            "reason": reason,
        }
    except Exception as e:
        return {"error": str(e)}, 500
