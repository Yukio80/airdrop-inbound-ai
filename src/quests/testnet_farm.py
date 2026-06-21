"""
Testnet Farm — automate faucet claims + testnet interactions.
Zero-cost airdrop farming on Sepolia, Holesky, Amoy, etc.
Hardened with RPC retry logic.
"""
import json, time, random
from web3 import Web3
from eth_account.account import Account
from web3.exceptions import TimeExhausted
from src.hardening.retry import retry

TESTNETS = {
    "sepolia": {
        "rpc": "https://ethereum-sepolia.publicnode.com",
        "rpc_fallback": "https://rpc.sepolia.org",
        "chain_id": 11155111,
        "faucet": "https://sepolia-faucet.pk910.de",
        "faucets": [
            ("GetBlock (signup)", "https://getblock.io/faucet/eth-sepolia"),
            ("PoW (mine)", "https://sepolia-faucet.pk910.de"),
            ("QNode (tweet)", "https://faucet.quicknode.com/ethereum/sepolia"),
        ],
        "explorer": "https://sepolia.etherscan.io",
        "native": "ETH",
    },
    "hoodi": {
        "rpc": "https://ethereum-hoodi-rpc.publicnode.com",
        "rpc_fallback": "",
        "chain_id": 560048,
        "faucet": "https://hoodi-faucet.pk910.de",
        "faucets": [
            ("PoW (mine)", "https://hoodi-faucet.pk910.de"),
            ("QuickNode (tweet)", "https://faucet.quicknode.com/ethereum/hoodi"),
            ("Google Cloud", "https://cloud.google.com/application/web3/faucet/ethereum/hoodi"),
        ],
        "explorer": "https://hoodi.etherscan.io",
        "native": "ETH",
    },
    "amoy": {
        "rpc": "https://rpc-amoy.polygon.technology",
        "rpc_fallback": "https://polygon-amoy.drpc.org",
        "chain_id": 80002,
        "faucet": "https://getblock.io/faucet/matic-amoy",
        "faucets": [
            ("GetBlock (signup, 0.1 POL)", "https://getblock.io/faucet/matic-amoy"),
            ("QuickNode (tweet, 2x POL)", "https://faucet.quicknode.com/polygon/amoy"),
            ("StakePool Faucet", "https://stakepool.dev.br/faucet"),
        ],
        "explorer": "https://amoy.polygonscan.com",
        "native": "POL",
    },
    "base_sepolia": {
        "rpc": "https://sepolia.base.org",
        "rpc_fallback": "",
        "chain_id": 84532,
        "faucet": "https://faucet.quicknode.com/base/sepolia",
        "faucets": [
            ("QuickNode (tweet)", "https://faucet.quicknode.com/base/sepolia"),
            ("Coinbase (login)", "https://www.coinbase.com/faucets/base-sepolia-faucet"),
            ("Alchemy (login)", "https://www.alchemy.com/faucets/base-sepolia"),
        ],
        "explorer": "https://sepolia.basescan.org",
        "native": "ETH",
    },
    "optimism_sepolia": {
        "rpc": "https://sepolia.optimism.io",
        "rpc_fallback": "",
        "chain_id": 11155420,
        "faucet": "https://faucet.quicknode.com/optimism/sepolia",
        "faucets": [
            ("QuickNode (tweet)", "https://faucet.quicknode.com/optimism/sepolia"),
            ("Alchemy (login)", "https://www.alchemy.com/faucets/optimism-sepolia"),
            ("Coinbase (login)", "https://www.coinbase.com/faucets/optimism-sepolia-faucet"),
        ],
        "explorer": "https://sepolia-optimism.etherscan.io",
        "native": "ETH",
    },
}

ERC20_ABI = json.loads('''[
{"constant":true,"inputs":[],"name":"name","outputs":[{"type":"string"}],"type":"function"},
{"constant":true,"inputs":[],"name":"symbol","outputs":[{"type":"string"}],"type":"function"},
{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"type":"function"}
]''')

class TestnetFarm:
    def __init__(self, pk):
        self.pk = pk
        self.addr = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"
        if pk:
            self.acct = Account.from_key(pk)
            self.addr = self.acct.address
        else:
            self.acct = None

    @retry(max_attempts=2, delay=2.0, backoff=1.0, exceptions=(ConnectionError, TimeoutError, OSError))
    def check_balance(self, chain):
        cfg = TESTNETS[chain]
        for rpc in [cfg["rpc"], cfg.get("rpc_fallback", "")]:
            if not rpc:
                continue
            try:
                w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 10}))
                bal = w3.eth.get_balance(self.addr)
                return bal / 1e18, w3
            except Exception:
                continue
        return 0, None

    def claim_faucet(self, chain, faucet_url=None):
        """Print faucet instructions — manual step needed."""
        cfg = TESTNETS[chain]
        print(f"\n  🚰 Faucet for {chain} (sem mainnet ETH):")
        if faucet_url:
            print(f"     URL: {faucet_url}")
        for name, url in cfg.get("faucets", []):
            print(f"     → {name}: {url}")
        print(f"     Wallet: {self.addr}")
        print(f"     Dica: Depois de pegar tokens, rode 'ecosystem.py farm'")

    @retry(max_attempts=2, delay=5.0, backoff=1.0, exceptions=(TimeExhausted,))
    def send_self(self, chain, amount=0, w3=None):
        """Send testnet ETH to self (proof of activity)."""
        cfg = TESTNETS[chain]
        if not self.pk:
            return None
        if w3 is None:
            _, w3 = self.check_balance(chain)
            if w3 is None:
                return None
        bal = w3.eth.get_balance(self.addr)
        bal_dec = bal / 1e18

        if amount <= 0:
            amount = bal_dec * 0.8

        if bal_dec < 0.0001:
            return None

        tx = {
            "from": self.addr,
            "to": self.addr,
            "value": w3.to_wei(amount, "ether"),
            "gas": 21000,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(self.addr),
            "chainId": cfg["chain_id"],
        }
        signed = w3.eth.account.sign_transaction(tx, self.pk)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        hex_h = w3.to_hex(h)
        w3.eth.wait_for_transaction_receipt(h, timeout=90)
        return hex_h

    def swap_test(self, chain):
        """Simulated swap on testnet DEX (just a self-transfer as PoA)."""
        return self.send_self(chain, 0.0001)

    def farm_all(self, chains=None):
        if chains is None:
            chains = list(TESTNETS.keys())

        results = {}
        for chain in chains:
            print(f"\n{'─'*40}")
            print(f"🌐 {chain.upper()}")
            print(f"{'─'*40}")

            bal, w3 = self.check_balance(chain)
            print(f"   Balance: {bal:.6f} {TESTNETS[chain]['native']}")

            if w3 is None:
                results[chain] = "RPC error"
                continue

            if bal < 0.001:
                self.claim_faucet(chain)
                results[chain] = "no funds — faucet needed"
                continue

            txs = []
            tx = self.send_self(chain, bal * 0.5, w3)
            if tx:
                txs.append(tx)
                print(f"   ✅ Self-tx: {tx}")
            else:
                print(f"   ❌ Failed")

            time.sleep(random.uniform(1, 3))

            results[chain] = txs if txs else "failed"

        return results

    def print_results(self, results):
        print("\n" + "=" * 50)
        print("📊 Testnet Farm Results")
        print("=" * 50)
        for chain, result in results.items():
            status = "✅" if isinstance(result, list) and result else "⏳" if isinstance(result, str) else "❌"
            info = f"{len(result)} txs" if isinstance(result, list) else result
            print(f"  {status} {chain}: {info}")

    def run_once(self):
        print("🧪 Testnet Farm — Zero-Cost Airdrop Strategy")
        print("=" * 50)
        results = self.farm_all()
        self.print_results(results)
        return results
