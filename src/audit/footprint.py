"""On-chain footprint auditor for EVM (Arbitrum) and Solana wallets."""

import json
import os
import pathlib
import time
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

import requests

ROOT = pathlib.Path(__file__).parent.parent.parent
DB_PATH = ROOT / "airdrop_bot.db"
SOL_KEYSTORE = ROOT / "wallets" / "solana_real.sol.json"

KNOWN_PROTOCOLS = {
    "0x794a61358D6845594F94dc1DB02A252b5b4814aD": "aave_v3",
    "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45": "uniswap_v3",
    "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506": "sushiswap",
    "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F": "sushiswap",
    "0x4c2Af2Df2a7E567B5155879720619EA06C5BB15D": "curve",
    "0xc3d688B66703497DAA19211EEdff47f25384cdc3": "compound_v3",
    "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84": "lido",
    "0x5979D7b546E38E414F7E9822514be443A4800529": "lido_wsteth",
    "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7": "curve_3pool",
    "0x61fFE014bA17989E743c5F6cB21bF9697530B21e": "uniswap_v3_quoter",
    "0xc00e94Cb662C3520282E6f5717214004A7f26888": "compound",
}


class FootprintAuditor:
    """Audits on-chain footprint for EVM and Solana wallets."""

    def __init__(self):
        self.evm_wallets = [
            "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C",
            "0x15396a785051271e43e687675f11f18143be6512",
        ]
        self.arbiscan_key = os.getenv("ARBISCAN_API_KEY", "")
        self.sol_rpc = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.reports_dir = ROOT / "reports"
        self.reports_dir.mkdir(exist_ok=True)

    # ── EVM ──

    def audit_evm(self, wallet: str) -> dict:
        """Fetch on-chain activity from Arbiscan for a wallet."""
        result = {
            "wallet": wallet,
            "chain": "arbitrum",
            "total_txs": 0,
            "unique_contracts": [],
            "unique_tokens": [],
            "first_tx_date": None,
            "last_tx_date": None,
            "active_days": 0,
            "protocols_detected": [],
            "error": None,
        }

        if not self.arbiscan_key:
            result["error"] = "ARBISCAN_API_KEY not set"
            return result

        base = "https://api.arbiscan.io/api"
        params = {
            "module": "account",
            "address": wallet,
            "sort": "asc",
            "apikey": self.arbiscan_key,
        }

        try:
            # Normal transactions
            tx_params = dict(params, action="txlist")
            resp = requests.get(base, params=tx_params, timeout=30)
            time.sleep(0.25)
            tx_data = resp.json()

            # Token transactions
            tok_params = dict(params, action="tokentx")
            tok_resp = requests.get(base, params=tok_params, timeout=30)
            time.sleep(0.25)
            tok_data = tok_resp.json()

            all_txs = []
            contracts = set()
            tokens = set()
            dates_set = set()

            if tx_data.get("status") == "1" and isinstance(tx_data.get("result"), list):
                for tx in tx_data["result"]:
                    all_txs.append(tx)
                    if tx.get("to"):
                        contracts.add(tx["to"].lower())
                    ts = datetime.fromtimestamp(int(tx["timeStamp"]))
                    dates_set.add(ts.strftime("%Y-%m-%d"))

            if tok_data.get("status") == "1" and isinstance(tok_data.get("result"), list):
                for tx in tok_data["result"]:
                    if tx.get("tokenSymbol"):
                        tokens.add(tx["tokenSymbol"])
                    ts = datetime.fromtimestamp(int(tx["timeStamp"]))
                    dates_set.add(ts.strftime("%Y-%m-%d"))

            # Protocol detection
            protocols = set()
            for addr in contracts:
                if addr in KNOWN_PROTOCOLS:
                    protocols.add(KNOWN_PROTOCOLS[addr])

            dates_sorted = sorted(dates_set)
            result["total_txs"] = len(all_txs)
            result["unique_contracts"] = sorted(contracts)
            result["unique_tokens"] = sorted(tokens)
            result["first_tx_date"] = dates_sorted[0] if dates_sorted else None
            result["last_tx_date"] = dates_sorted[-1] if dates_sorted else None
            result["active_days"] = len(dates_sorted)
            result["protocols_detected"] = sorted(protocols)

        except requests.RequestException as e:
            result["error"] = str(e)

        return result

    # ── Solana ──

    def audit_solana(self, pubkey: Optional[str] = None) -> dict:
        """Fetch Solana activity via public RPC."""
        if not pubkey:
            try:
                with open(SOL_KEYSTORE) as f:
                    d = json.load(f)
                pubkey = d.get("public_key") or d.get("address")
            except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
                return {"wallet": None, "chain": "solana", "error": f"Cannot load keypair: {e}"}

        result = {
            "wallet": pubkey,
            "chain": "solana",
            "total_txs": 0,
            "spl_tokens_held": [],
            "first_tx_date": None,
            "last_tx_date": None,
            "active_days": 0,
            "error": None,
        }

        try:
            # Signatures
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [pubkey, {"limit": 1000}],
            }
            resp = requests.post(self.sol_rpc, json=payload, timeout=30)
            time.sleep(0.25)
            sigs = resp.json().get("result", [])

            dates_set = set()
            for s in sigs:
                if s.get("blockTime"):
                    ts = datetime.fromtimestamp(s["blockTime"])
                    dates_set.add(ts.strftime("%Y-%m-%d"))

            dates_sorted = sorted(dates_set)

            # Token accounts
            tok_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "getTokenAccountsByOwner",
                "params": [pubkey, {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}, {"encoding": "jsonParsed"}],
            }
            tok_resp = requests.post(self.sol_rpc, json=tok_payload, timeout=30)
            time.sleep(0.25)
            tok_result = tok_resp.json().get("result", {}).get("value", [])

            spl_tokens = []
            for acct in tok_result:
                info = acct.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
                mint = info.get("mint")
                if mint and int(info.get("tokenAmount", {}).get("amount", 0)) > 0:
                    spl_tokens.append(mint)

            result["total_txs"] = len(sigs)
            result["spl_tokens_held"] = spl_tokens
            result["first_tx_date"] = dates_sorted[0] if dates_sorted else None
            result["last_tx_date"] = dates_sorted[-1] if dates_sorted else None
            result["active_days"] = len(dates_sorted)

        except requests.RequestException as e:
            result["error"] = str(e)

        return result

    # ── Reconcile ──

    def reconcile(self, wallet: str, chain: str = "arbitrum") -> dict:
        """Cross-reference on-chain data with SQLite transactions table."""
        import sqlite3

        result = {
            "wallet": wallet,
            "chain": chain,
            "matched": 0,
            "missing": 0,
            "untracked": 0,
            "missing_hashes": [],
            "error": None,
        }

        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            db_tx_hashes = set()
            cursor.execute(
                "SELECT tx_hash FROM transactions WHERE wallet = ? AND tx_hash IS NOT NULL AND tx_hash != ''",
                (wallet,),
            )
            for row in cursor.fetchall():
                h = row["tx_hash"].strip()
                if h and not h.startswith("0x_dry_run") and not h.startswith("0x_error") and not h.startswith("0x_sim"):
                    db_tx_hashes.add(h)

            conn.close()
        except Exception as e:
            result["error"] = f"SQLite error: {e}"
            return result

        # Fetch on-chain tx hashes via Arbiscan
        if chain == "arbitrum" and self.arbiscan_key:
            base = "https://api.arbiscan.io/api"
            params = {
                "module": "account",
                "action": "txlist",
                "address": wallet,
                "sort": "asc",
                "apikey": self.arbiscan_key,
            }
            try:
                resp = requests.get(base, params=params, timeout=30)
                onchain_data = resp.json()
                onchain_hashes = set()
                if onchain_data.get("status") == "1" and isinstance(onchain_data.get("result"), list):
                    for tx in onchain_data["result"]:
                        onchain_hashes.add(tx["hash"])

                matched = db_tx_hashes & onchain_hashes
                missing = db_tx_hashes - onchain_hashes
                untracked = onchain_hashes - db_tx_hashes

                result["matched"] = len(matched)
                result["missing"] = len(missing)
                result["untracked"] = len(untracked)
                result["missing_hashes"] = sorted(missing)[:20]
            except requests.RequestException as e:
                result["error"] = f"Arbiscan error: {e}"
        else:
            result["error"] = result.get("error") or "ARBISCAN_API_KEY not set or unsupported chain"

        return result

    # ── Full Report ──

    def full_report(self) -> dict:
        """Run all audits + reconciliation and save to reports/."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "evm": {},
            "solana": None,
            "reconciliation": {},
        }

        for w in self.evm_wallets:
            report["evm"][w] = self.audit_evm(w)
            rep = self.reconcile(w, "arbitrum")
            if "error" not in rep:
                report["reconciliation"][w] = rep
            time.sleep(0.25)

        report["solana"] = self.audit_solana()

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_path = self.reports_dir / f"footprint_{ts}.json"
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        report["_saved_to"] = str(out_path)
        return report
