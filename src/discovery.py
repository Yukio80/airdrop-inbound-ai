import asyncio
import requests
from datetime import datetime
import concurrent.futures

class OpportunityScanner:
    def __init__(self):
        self.defillama_url = "https://api.llama.fi/protocols"

    async def scan_all(self):
        print("Fetching protocols from DeFiLlama...")
        
        def sync_fetch():
            try:
                response = requests.get(self.defillama_url, timeout=10)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"Error scanning DeFiLlama: {e}")
                return []
        
        loop = asyncio.get_event_loop()
        try:
            protocols = await loop.run_in_executor(None, sync_fetch)
            
            signals = []
            for p in protocols:
                name = p.get("name", "")
                if any(cex in name.lower() for cex in ["binance", "okx", "bitfinex", "bybit", "coinbase", "kraken"]):
                    continue
                
                tvl = p.get("tvl") or 0
                if tvl > 1_000_000:
                    signals.append({
                        "protocol": name,
                        "chain": self._infer_chain_from_name(name),
                        "tvl": tvl,
                        "score": 0,
                        "url": p.get("url")
                    })
            
            return signals[:5]
            
        except Exception as e:
            print(f"Error in async scan: {e}")
            return []

    def _infer_chain_from_name(self, name):
        name_lower = name.lower()
        if "arbitrum" in name_lower:
            return "arbitrum"
        elif "base" in name_lower:
            return "base"
        elif "optimism" in name_lower:
            return "optimism"
        elif "polygon" in name_lower:
            return "polygon"
        elif "avalanche" in name_lower:
            return "avalanche"
        else:
            return "arbitrum"  # Prefer Arbitrum for farming
