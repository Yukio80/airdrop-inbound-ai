import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import requests
from web3 import Web3
from eth_account import Account

from src.config_loader import CONFIG
from src.yield_optimizer.apy_feed import APYFeed
from src.yield_optimizer.balance_reader import BalanceReader
from src.intelligence.chain_registry import get_chain
from src.utils.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent
KEYSTORE = ROOT / "wallets" / "user_real.json"
KEYSTORE_PASS = "231413"


class YieldOptimizer:
    def __init__(self, dry_run: bool = False):
        self.apy_feed = APYFeed()
        self.balance_reader = BalanceReader()
        self.db = DatabaseManager()
        self.dry_run = dry_run

    def get_best_rate(self, asset: str, chain_preference: list[str] = None) -> dict | None:
        rates = self.apy_feed.get_all_rates()
        filtered = [r for r in rates if r["asset"] == asset.upper()]
        if chain_preference:
            preferred = [r for r in filtered if r["chain"] in chain_preference]
            if preferred:
                filtered = preferred
        if not filtered:
            return None
        return max(filtered, key=lambda r: r["apy_pct"])

    def should_rebalance(self, current_location: str, current_apy: float, best_rate: dict) -> bool:
        cfg = CONFIG.yield_optimizer
        improvement = best_rate["apy_pct"] - current_apy
        min_improve = cfg.get("min_improvement_pct", 1.5)
        min_tvl = cfg.get("min_tvl_usd", 5_000_000)
        return (
            improvement >= min_improve
            and best_rate["protocol"] != current_location
            and best_rate["tvl_usd"] >= min_tvl
        )

    def estimate_gas_cost_usd(self, chain: str) -> float:
        cfg = get_chain(chain)
        if not cfg:
            return 999
        try:
            w3 = Web3(Web3.HTTPProvider(cfg.rpc, request_kwargs={"timeout": 10}))
            gas_price = w3.eth.gas_price
            gas_units = 170_000
            gas_cost_eth = (gas_price * gas_units) / 1e18
            url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            eth_price = resp.json().get("ethereum", {}).get("usd", 0)
            return gas_cost_eth * eth_price
        except Exception as e:
            logger.warning(f"Gas estimation failed for {chain}: {e}")
            return 999

    def run(self, wallet_evm: str, wallet_solana_path: str = "wallets/solana_real.sol.json") -> dict:
        cfg = CONFIG.yield_optimizer
        enabled_assets = cfg.get("enabled_assets", ["USDC", "USDT"])
        enabled_chains = cfg.get("enabled_chains", ["arbitrum", "solana"])
        reserve_eth_pct = cfg.get("reserve_eth_pct", 0.2)

        results = {
            "checked": [],
            "rebalanced": [],
            "skipped": [],
            "total_apy_before": 0.0,
            "total_apy_after": 0.0,
            "estimated_annual_gain_usd": 0.0,
        }

        all_rates = self.apy_feed.get_all_rates()

        for chain in enabled_chains:
            if chain == "arbitrum":
                idle = self.balance_reader.get_evm_idle_balances(wallet_evm, chain)
                deposited = self.balance_reader.get_deposited_balances(wallet_evm)
                balances = idle + deposited
            elif chain == "solana":
                balances = self.balance_reader.get_solana_idle_balances(wallet_solana_path)
            else:
                continue

            for bal in balances:
                asset = bal["token"]
                if asset not in enabled_assets:
                    continue
                if bal["balance_human"] < 1:
                    results["skipped"].append({**bal, "reason": "dust"})
                    continue

                location = bal["location"]
                current_apy = self._get_current_apy(all_rates, location, asset)

                best_rate = self.get_best_rate(asset, chain_preference=[chain])

                checked_entry = {
                    "token": asset,
                    "chain": chain,
                    "balance_human": bal["balance_human"],
                    "location": location,
                    "current_apy": current_apy,
                    "best_apy": best_rate["apy_pct"] if best_rate else current_apy,
                    "best_protocol": best_rate["protocol"] if best_rate else location,
                }
                results["checked"].append(checked_entry)

                if not best_rate:
                    results["skipped"].append({**bal, "reason": "no_rate_found"})
                    continue

                if location == "wallet":
                    deploy_result = self._deploy_to_protocol(
                        asset=asset,
                        amount_raw=bal["balance_raw"],
                        amount_human=bal["balance_human"],
                        target_protocol=best_rate["protocol"],
                        chain=chain,
                        wallet_evm=wallet_evm,
                    )
                    if deploy_result:
                        results["rebalanced"].append(deploy_result)
                        annual_gain = bal["balance_human"] * best_rate["apy_pct"] / 100
                        results["estimated_annual_gain_usd"] += annual_gain
                else:
                    if self.should_rebalance(location, current_apy, best_rate):
                        gas_usd = self.estimate_gas_cost_usd(chain)
                        improvement = best_rate["apy_pct"] - current_apy
                        annual_gain = bal["balance_human"] * improvement / 100
                        if gas_usd > annual_gain / 12:
                            results["skipped"].append({**bal, "reason": "gas_too_high", "location": location})
                            continue
                        rebal_result = self.run_evm_rebalance(
                            asset=asset,
                            amount_raw=bal["balance_raw"],
                            amount_human=bal["balance_human"],
                            from_protocol=location,
                            to_protocol=best_rate["protocol"],
                            chain=chain,
                            wallet_evm=wallet_evm,
                        )
                        if rebal_result:
                            results["rebalanced"].append(rebal_result)
                            results["estimated_annual_gain_usd"] += annual_gain
                    else:
                        results["skipped"].append({**bal, "reason": "already_optimal", "location": location})

        results["total_apy_after"] = self._calc_avg_apy(results["rebalanced"], all_rates)
        return results

    def _get_current_apy(self, rates: list[dict], location: str, asset: str) -> float:
        for r in rates:
            if r["protocol"] == location and r["asset"] == asset:
                return r["apy_pct"]
        return 0.0

    def _calc_avg_apy(self, rebalanced: list[dict], rates: list[dict]) -> float:
        if not rebalanced:
            return 0.0
        total = 0.0
        for r in rebalanced:
            best = next(
                (x for x in rates if x["protocol"] == r.get("to_protocol") and x["asset"] == r.get("asset")),
                None,
            )
            total += best["apy_pct"] if best else 0
        return total / len(rebalanced)

    def _deploy_to_protocol(self, asset: str, amount_raw: int, amount_human: float,
                             target_protocol: str, chain: str,
                             wallet_evm: str) -> dict | None:
        if self.dry_run:
            logger.info(f"[DRY RUN] Deploy {amount_human} {asset} to {target_protocol} on {chain}")
            return {
                "asset": asset,
                "amount_human": amount_human,
                "from_protocol": "wallet",
                "to_protocol": target_protocol,
                "chain": chain,
                "action": "deploy",
                "status": "dry_run",
                "withdraw_tx": None,
                "supply_tx": None,
            }

        if chain == "solana":
            logger.warning(f"Solana deploy not yet implemented for {target_protocol}")
            return None

        try:
            with open(KEYSTORE) as f:
                ks = json.load(f)
            pk = Account.decrypt(ks, KEYSTORE_PASS).hex()
            account = Account.from_key(pk)
            cfg = get_chain(chain)
            w3 = Web3(Web3.HTTPProvider(cfg.rpc, request_kwargs={"timeout": 10}))

            if target_protocol == "aave_v3":
                from adapters.aave import AaveAdapter
                adapter = AaveAdapter(w3, account)
                token_addr = cfg.usdc if asset == "USDC" else (cfg.usdt if asset == "USDT" else cfg.weth)
                result = adapter.supply(token_addr, Decimal(str(amount_human)), dry_run=False)
                tx_hash = result.tx_hash
            elif target_protocol == "compound_v3":
                from adapters.compound import CompoundAdapter
                adapter = CompoundAdapter(w3, account)
                tx_hash = adapter.execute("supply", {"amount": amount_human}, dry_run=False)
            else:
                logger.warning(f"Unknown protocol: {target_protocol}")
                return None

            self.db.log_transaction(wallet_evm, target_protocol, f"yield_supply_{asset}", tx_hash)
            return {
                "asset": asset,
                "amount_human": amount_human,
                "from_protocol": "wallet",
                "to_protocol": target_protocol,
                "chain": chain,
                "action": "deploy",
                "status": "success",
                "supply_tx": tx_hash,
            }
        except Exception as e:
            logger.error(f"Deploy failed: {e}")
            return None

    def run_evm_rebalance(self, asset: str, amount_raw: int, amount_human: float,
                           from_protocol: str, to_protocol: str, chain: str,
                           wallet_evm: str) -> dict | None:
        if self.dry_run:
            logger.info(
                f"[DRY RUN] Rebalance {amount_human} {asset} from {from_protocol} → {to_protocol} on {chain}"
            )
            return {
                "asset": asset,
                "amount_human": amount_human,
                "from_protocol": from_protocol,
                "to_protocol": to_protocol,
                "chain": chain,
                "action": "rebalance",
                "status": "dry_run",
                "withdraw_tx": None,
                "supply_tx": None,
            }

        try:
            with open(KEYSTORE) as f:
                ks = json.load(f)
            pk = Account.decrypt(ks, KEYSTORE_PASS).hex()
            account = Account.from_key(pk)
            cfg = get_chain(chain)
            if not cfg:
                return None
            w3 = Web3(Web3.HTTPProvider(cfg.rpc, request_kwargs={"timeout": 10}))
            token_addr = cfg.usdc if asset == "USDC" else (cfg.usdt if asset == "USDT" else cfg.weth)

            withdraw_tx = None
            if from_protocol == "aave_v3":
                from adapters.aave import AaveAdapter
                adapter = AaveAdapter(w3, account)
                result = adapter.withdraw(token_addr, Decimal(str(amount_human)), dry_run=False)
                withdraw_tx = result.tx_hash
            elif from_protocol == "compound_v3":
                from adapters.compound import CompoundAdapter
                adapter = CompoundAdapter(w3, account)
                withdraw_tx = adapter.execute("withdraw", {"amount": amount_human}, dry_run=False)
            else:
                logger.warning(f"Unknown from_protocol: {from_protocol}")
                return None

            self.db.log_transaction(wallet_evm, from_protocol, f"yield_withdraw_{asset}", withdraw_tx)

            supply_tx = None
            if to_protocol == "aave_v3":
                from adapters.aave import AaveAdapter
                adapter = AaveAdapter(w3, account)
                result = adapter.supply(token_addr, Decimal(str(amount_human)), dry_run=False)
                supply_tx = result.tx_hash
            elif to_protocol == "compound_v3":
                from adapters.compound import CompoundAdapter
                adapter = CompoundAdapter(w3, account)
                supply_tx = adapter.execute("supply", {"amount": amount_human}, dry_run=False)
            else:
                logger.warning(f"Unknown to_protocol: {to_protocol}")
                return None

            self.db.log_transaction(wallet_evm, to_protocol, f"yield_supply_{asset}", supply_tx)

            return {
                "asset": asset,
                "amount_human": amount_human,
                "from_protocol": from_protocol,
                "to_protocol": to_protocol,
                "chain": chain,
                "action": "rebalance",
                "status": "success",
                "withdraw_tx": withdraw_tx,
                "supply_tx": supply_tx,
            }
        except Exception as e:
            logger.error(f"Rebalance failed: {e}")
            return None
