import asyncio
import random
import json
import os
from datetime import datetime
from pathlib import Path
from eth_account import Account
from web3 import Web3
from adapters.uniswap import UniswapAdapter
from adapters.aave import AaveAdapter
from adapters.lido import LidoAdapter
from utils.behavior import HumanBehaviorSimulator

class SecureWalletManager:
    def __init__(self, keystore_path="wallets"):
        self.keystore_path = Path(keystore_path)
        self.keystore_path.mkdir(exist_ok=True)
        self.w3_connections = {
            'ethereum': Web3(Web3.HTTPProvider('https://eth.llamarpc.com')),
            'arbitrum': Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc')),
            'base': Web3(Web3.HTTPProvider('https://mainnet.base.org')),
        }

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

class TaskExecutor:
    def __init__(self, wallet_manager=None):
        self.wm = wallet_manager or SecureWalletManager()
        self.task_history = []
        self.behavior = HumanBehaviorSimulator()
        self.adapters = {
            "uniswap": UniswapAdapter,
            "aave": AaveAdapter,
            "lido": LidoAdapter
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

