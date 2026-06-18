import asyncio
import random
import json
import os
import sqlite3
from datetime import datetime, date
from pathlib import Path
from eth_account import Account
from web3 import Web3
from adapters.uniswap import UniswapAdapter
from adapters.aave import AaveAdapter
from adapters.lido import LidoAdapter
from adapters.compound import CompoundAdapter
from adapters.curve import CurveAdapter
from adapters.sushi import SushiAdapter
from utils.behavior import HumanBehaviorSimulator


class GasOptimizer:
    EIP1559_CHAINS = {1, 42161, 8453}
    CHAIN_IDS = {"ethereum": 1, "arbitrum": 42161, "base": 8453}

    def __init__(self, w3: Web3, chain_name: str = "arbitrum"):
        self.w3 = w3
        self.chain_name = chain_name.lower()
        self.chain_id = self.CHAIN_IDS.get(self.chain_name, 1)
        self._supports_eip1559 = self.chain_id in self.EIP1559_CHAINS
        self._tip_gwei = 1.5

    def get_gas_params(self) -> dict:
        try:
            if self._supports_eip1559:
                block = self.w3.eth.get_block("latest")
                base_fee = block.get("baseFeePerGas", None)
                if base_fee:
                    max_fee = int(base_fee * 1.25)
                    max_priority = self.w3.to_wei(self._tip_gwei, "gwei")
                    return {
                        "maxFeePerGas": max_fee,
                        "maxPriorityFeePerGas": max_priority,
                    }
            legacy_gas = self.w3.eth.gas_price
            return {"gasPrice": legacy_gas}
        except Exception as e:
            print(f"  ⚠️ Gas fetch failed ({e}), using defaults")
            return {}


class SecureWalletManager:
    def __init__(self, keystore_path="wallets"):
        self.keystore_path = Path(keystore_path)
        self.keystore_path.mkdir(exist_ok=True)
        self.w3_connections = {
            'ethereum': Web3(Web3.HTTPProvider('https://eth.llamarpc.com')),
            'arbitrum': Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc')),
            'base': Web3(Web3.HTTPProvider('https://mainnet.base.org')),
        }
        self._round_robin_index = 0

    def create_wallet(self, name, password):
        account = Account.create()
        keystore_json = Account.encrypt(account.key, password)
        
        filepath = self.keystore_path / f"{name}.json"
        with open(filepath, 'w') as f:
            json.dump(keystore_json, f)
        
        return account.address

    def load_wallet(self, name, password):
        filepath = self.keystore_path / f"{name}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Wallet {name} not found")
            
        with open(filepath) as f:
            keystore_json = json.load(f)
        
        private_key = Account.decrypt(keystore_json, password)
        return Account.from_key(private_key)

    def list_wallets(self):
        return sorted([p.stem for p in self.keystore_path.glob("*.json")])

    def get_next_wallet(self, strategy: str = "round_robin", db=None) -> tuple:
        """Return (wallet_name, wallet_account) based on strategy."""
        wallets = self.list_wallets()
        if not wallets:
            raise FileNotFoundError("No wallets available")

        if strategy == "round_robin":
            name = wallets[self._round_robin_index % len(wallets)]
            self._round_robin_index += 1
        elif strategy == "least_used" and db:
            name = self._least_used_wallet(wallets, db)
        else:
            name = wallets[self._round_robin_index % len(wallets)]
            self._round_robin_index += 1

        wallet = self.load_wallet(name, "default_password")
        return name, wallet

    def _least_used_wallet(self, wallets, db) -> str:
        today = date.today().isoformat()
        conn = db._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        counts = {}
        for w in wallets:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM transactions WHERE wallet = ? AND DATE(timestamp) = ?",
                (w, today),
            )
            counts[w] = cursor.fetchone()["cnt"]
        conn.close()
        return min(counts, key=counts.get)

class TaskExecutor:
    def __init__(self, wallet_manager=None):
        self.wm = wallet_manager or SecureWalletManager()
        self.task_history = []
        self.behavior = HumanBehaviorSimulator()
        self.adapters = {
            "uniswap": UniswapAdapter,
            "aave": AaveAdapter,
            "lido": LidoAdapter,
            "compound": CompoundAdapter,
            "curve": CurveAdapter,
            "sushi": SushiAdapter,
        }

    async def execute_strategy(self, wallet_name, strategy, db=None):
        print(f"Starting execution for wallet {wallet_name}")
        try:
            wallet = self.wm.load_wallet(wallet_name, "default_password")
        except Exception as e:
            print(f"Wallet error: {e}. Creating a new one for demo...")
            self.wm.create_wallet(wallet_name, "default_password")
            wallet = self.wm.load_wallet(wallet_name, "default_password")

        w3 = self.wm.w3_connections['arbitrum']

        for task in strategy:
            protocol_name = task['protocol'].lower()
            action = task['action']
            
            print(f"Executing {action} on {protocol_name}...")
            
            adapter_class = self.adapters.get(protocol_name)
            if adapter_class:
                adapter = adapter_class(w3, wallet)
                try:
                    # Execute adapter - this might be async or sync
                    result = adapter.execute(action, task)
                    if asyncio.iscoroutine(result):
                        tx_hash = await result
                    else:
                        tx_hash = result
                    print(f"Success: {tx_hash}")
                except Exception as e:
                    print(f"Adapter error: {e}")
                    tx_hash = f"0x_error_{protocol_name}"
            else:
                print(f"No adapter found for {protocol_name}, simulating...")
                tx_hash = f"0x_sim_{protocol_name}_{random.getrandbits(128):x}"
                print(f"Simulated success: {tx_hash}")
            
            if db:
                db.log_transaction(wallet_name, protocol_name, action, tx_hash)
            
            # Simple delay instead of human behavior (to avoid hanging)
            await asyncio.sleep(0.5)
            
            self.task_history.append({
                'timestamp': datetime.now(),
                'wallet': wallet_name,
                'task': task,
                'tx_hash': tx_hash
            })

