import logging
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

_feed_cache = {}
_feed_cache_time = {}
FEED_TTL = 600


class APYFeed:
    def __init__(self):
        self.session = requests.Session()

    def get_all_rates(self) -> list[dict]:
        now = time.time()
        if "all_rates" in _feed_cache and now - _feed_cache_time.get("all_rates", 0) < FEED_TTL:
            return _feed_cache["all_rates"]
        results = []
        sources = [
            self._fetch_defillama,
            self._fetch_kamino,
            self._fetch_marinade,
            self._fetch_lido,
        ]
        for fn in sources:
            try:
                data = fn()
                results.extend(data)
                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"APY source {fn.__name__} failed: {e}")
        fetched_at = datetime.now(timezone.utc).isoformat()
        for r in results:
            r["fetched_at"] = fetched_at
        results.sort(key=lambda x: x["apy_pct"], reverse=True)
        _feed_cache["all_rates"] = results
        _feed_cache_time["all_rates"] = now
        return results

    def _fetch_defillama(self) -> list[dict]:
        url = "https://yields.llama.fi/pools"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        out = []

        aave_targets = {
            "USDC": "aave_v3",
            "USD₮0": "aave_v3",
            "WETH": "aave_v3",
        }
        for pool in data:
            project = pool.get("project", "")
            chain = pool.get("chain", "")
            symbol = pool.get("symbol", "")
            apy = pool.get("apy", 0) or 0
            tvl = pool.get("tvlUsd", 0) or 0

            if project == "aave-v3" and chain == "Arbitrum":
                asset = None
                for sym, mapped in aave_targets.items():
                    if symbol == sym:
                        asset = "USDT" if sym == "USD₮0" else sym
                        break
                if asset and asset in ("USDC", "USDT", "WETH"):
                    out.append({
                        "protocol": "aave_v3",
                        "chain": "arbitrum",
                        "asset": asset,
                        "apy_pct": round(float(apy), 4),
                        "tvl_usd": int(float(tvl)),
                        "source": "defillama",
                    })

            if project == "compound-v3" and chain == "Arbitrum" and symbol == "USDC":
                out.append({
                    "protocol": "compound_v3",
                    "chain": "arbitrum",
                    "asset": "USDC",
                    "apy_pct": round(float(apy), 4),
                    "tvl_usd": int(float(tvl)),
                    "source": "defillama",
                })

        return out

    def _fetch_kamino(self) -> list[dict]:
        url = "https://api.kamino.finance/strategies/metrics"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        out = {}
        targets = {"USDC", "USDT", "SOL"}
        for item in data:
            symbol = item.get("tokenA", "") or item.get("tokenB", "")
            if symbol not in targets:
                continue
            apy_obj = item.get("apy", item.get("kaminoApy", {}))
            if isinstance(apy_obj, dict):
                total_apy_str = apy_obj.get("totalApy", "0")
                try:
                    total_apy = float(total_apy_str)
                except (ValueError, TypeError):
                    total_apy = 0
            else:
                total_apy = 0
            tvl_str = item.get("totalValueLocked", "0")
            try:
                tvl = int(float(tvl_str))
            except (ValueError, TypeError):
                tvl = 0
            key = (symbol,)
            existing = out.get(key)
            if existing is None or total_apy > existing["apy_pct"]:
                out[key] = {
                    "protocol": "kamino",
                    "chain": "solana",
                    "asset": symbol,
                    "apy_pct": round(total_apy, 4),
                    "tvl_usd": tvl,
                    "source": "kamino_api",
                }
        return list(out.values())

    def _fetch_marinade(self) -> list[dict]:
        url = "https://api.marinade.finance/msol/apy/1y"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        apy = float(data.get("value", 0)) * 100
        return [{
            "protocol": "marinade",
            "chain": "solana",
            "asset": "SOL",
            "apy_pct": round(apy, 4),
            "tvl_usd": 0,
            "source": "marinade_api",
        }]

    def _fetch_lido(self) -> list[dict]:
        url = "https://eth-api.lido.fi/v1/protocol/steth/apr/last"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        apr = float(data.get("data", {}).get("apr", 0))
        return [{
            "protocol": "lido",
            "chain": "ethereum",
            "asset": "ETH",
            "apy_pct": round(apr, 4),
            "tvl_usd": 0,
            "source": "lido_api",
        }]
