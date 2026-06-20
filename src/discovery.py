import asyncio
import requests
from datetime import datetime
import concurrent.futures

# Known Solana protocols for airdrop farming
SOLANA_AIRDROP_PROTOCOLS = [
    "Jupiter", "Raydium", "Marinade", "Sanctum", "Kamino",
    "Jito", "Meteora", "Fragmetric", "Drift", "MarginFi",
    "Zeta", "Tensor", "Magic Eden", "Solend", "Orca",
    "Lifinity", "FluxBeam", "Mango Markets", "Pyth Network",
    "Switchboard", "Bonk", "Penguin", "Save", "Solayer",
    "Adrastea", "Parcl", "Helium", "Hivemapper",
]

class OpportunityScanner:
    def __init__(self):
        self.defillama_url = "https://api.llama.fi/protocols"

    def _get_primary_chain(self, protocol):
        chains = protocol.get("chains", []) or []
        chain_tvls = protocol.get("chainTvls", {}) or {}
        name = protocol.get("name", "")

        if not chains and chain_tvls:
            chains = list(chain_tvls.keys())

        chain_str = None
        if isinstance(chains, list):
            chain_str = [c.lower() for c in chains]
        elif isinstance(chains, str):
            chain_str = [chains.lower()]

        if chain_str:
            if "solana" in chain_str:
                return "solana"
            if "arbitrum" in chain_str:
                return "arbitrum"
            if "base" in chain_str:
                return "base"
            if "optimism" in chain_str:
                return "optimism"
            if "polygon" in chain_str:
                return "polygon"
            if "avalanche" in chain_str:
                return "avalanche"
            if "bsc" in chain_str or "binance" in chain_str:
                return "bsc"
            if "ethereum" in chain_str:
                return "arbitrum"

        name_lower = name.lower()
        if "arbitrum" in name_lower: return "arbitrum"
        if "base" in name_lower: return "base"
        if "optimism" in name_lower: return "optimism"
        if "polygon" in name_lower: return "polygon"
        if "avalanche" in name_lower: return "avalanche"
        if "solana" in name_lower: return "solana"

        return "arbitrum"

    async def scan_all(self):
        print("Fetching protocols from DeFiLlama...")

        def sync_fetch():
            try:
                response = requests.get(self.defillama_url, timeout=15)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Error scanning DeFiLlama: {e}")
                return []

        loop = asyncio.get_event_loop()
        try:
            protocols = await loop.run_in_executor(None, sync_fetch)

            signals = []
            solana_count = 0

            for p in protocols:
                name = p.get("name", "")
                if not name:
                    continue
                if any(cex in name.lower() for cex in ["binance", "okx", "bitfinex", "bybit", "coinbase", "kraken", "mexc", "gate.io", "bitget", "htx", "kucoin"]):
                    continue

                chain = self._get_primary_chain(p)
                tvl = p.get("tvl") or 0

                if tvl > 1_000_000:
                    chain_tvls = p.get("chainTvls", {}) or {}
                    raw_chains = p.get("chains", [])
                    if not raw_chains and chain_tvls:
                        raw_chains = list(chain_tvls.keys())

                    signals.append({
                        "protocol": name,
                        "chain": chain,
                        "tvl": tvl,
                        "score": 0,
                        "url": p.get("url"),
                        "createdAt": p.get("createdAt", 0),
                        "audits": p.get("audits", None),
                        "tvl_snapshots": [],
                        "chains": raw_chains or [chain],
                    })

                    if chain == "solana":
                        solana_count += 1

            signals.sort(key=lambda s: s["tvl"], reverse=True)

            solana_signals = [s for s in signals if s["chain"] == "solana"]
            other_signals = [s for s in signals if s["chain"] != "solana"]

            final_signals = []
            final_signals.extend(solana_signals[:5])
            final_signals.extend(other_signals[:8])

            print(f"   Solana protocols found: {solana_count}")
            return final_signals

        except Exception as e:
            print(f"Error in async scan: {e}")
            return []

    async def scan_solana_known(self):
        """Direct scan of known Solana airdrop protocols."""
        print("Scanning known Solana airdrop protocols...")

        def sync_fetch():
            try:
                response = requests.get(self.defillama_url, timeout=15)
                response.raise_for_status()
                data = response.json()
                return {p["name"].lower(): p for p in data}
            except Exception as e:
                print(f"Error fetching protocol details: {e}")
                return {}

        loop = asyncio.get_event_loop()
        protocols_map = await loop.run_in_executor(None, sync_fetch)

        signals = []
        for proto_name in SOLANA_AIRDROP_PROTOCOLS:
            p = protocols_map.get(proto_name.lower())
            if not p:
                continue

            tvl = p.get("tvl") or 0
            chain = self._get_primary_chain(p)
            chain_tvls = p.get("chainTvls", {}) or {}
            raw_chains = p.get("chains", [])
            if not raw_chains and chain_tvls:
                raw_chains = list(chain_tvls.keys())

            signals.append({
                "protocol": p.get("name", proto_name),
                "chain": chain,
                "tvl": tvl,
                "score": 0,
                "url": p.get("url"),
                "createdAt": p.get("createdAt", 0),
                "audits": p.get("audits", None),
                "tvl_snapshots": [],
                "chains": raw_chains or [chain],
            })

        return signals
