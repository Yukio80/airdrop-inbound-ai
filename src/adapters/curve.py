from decimal import Decimal
from typing import Optional, Dict, Any
from web3 import Web3

from adapters.base import BaseAdapter


class AdapterError(Exception):
    """Custom exception for adapter failures."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


class CurveAdapter(BaseAdapter):
    THREE_POOL = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
    THREE_COINS = [
        "0x6B175474E89094C44Da98b954EedeAC495271d0F",  # DAI
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
        "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
    ]

    POOL_ABI = [
        {
            "inputs": [
                {"internalType": "uint256[3]", "name": "amounts", "type": "uint256[3]"},
                {"internalType": "uint256", "name": "min_mint_amount", "type": "uint256"},
            ],
            "name": "add_liquidity",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "_amount", "type": "uint256"},
                {"internalType": "uint256[3]", "name": "min_amounts", "type": "uint256[3]"},
            ],
            "name": "remove_liquidity",
            "outputs": [{"internalType": "uint256[3]", "name": "", "type": "uint256[3]"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]

    def __init__(self, w3, wallet, config_path: str = "config.yaml"):
        super().__init__(w3, wallet, config_path)
        self.w3 = w3
        self.wallet = wallet

    def validate(self, **kwargs) -> bool:
        return True

    def dry_run(self, **kwargs) -> str:
        return "0x_dry_run_curve"

    def _retry_call(self, func, *args, **kwargs):
        import time
        max_attempts = 3
        backoff = [1, 2, 4]
        last_err = None
        for i in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_err = e
                if i < max_attempts - 1:
                    time.sleep(backoff[i])
        raise AdapterError(f"RPC call failed after {max_attempts} attempts: {str(last_err)}", context={"func": func.__name__})

    def execute(self, action: str, params: dict, dry_run: bool = False):
        if action == "add_liquidity":
            return self._add_liquidity(params, dry_run)
        elif action == "remove_liquidity":
            return self._remove_liquidity(params, dry_run)
        raise NotImplementedError(f"Action {action} not supported by CurveAdapter")

    def _add_liquidity(self, params: dict, dry_run: bool = False) -> str:
        amount = params.get("amount", 1000)
        if isinstance(amount, str):
            amount = float(amount)
        slippage = params.get("slippage_pct", 0.5)

        if dry_run:
            print(f"  [DRY RUN] Curve 3pool add_liquidity: {amount} USDC")
            return "0x_dry_run_curve_add_liquidity"

        print(f"Executing real Curve 3pool add_liquidity...")
        contract = self.w3.eth.contract(address=self.THREE_POOL, abi=self.POOL_ABI)

        amount_per_coin = int(amount * 1e6 / 3)
        amounts = [amount_per_coin for _ in range(3)]
        min_mint = int(amount * (1 - slippage / 100) * 1e18)

        tx = contract.functions.add_liquidity(amounts, min_mint).build_transaction({
            "from": self.wallet.address,
            "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
            "gasPrice": self.w3.eth.gas_price,
        })
        gas_estimate = self._retry_call(self.w3.eth.estimate_gas, tx)
        tx["gas"] = gas_estimate

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  ✅ add_liquidity: {tx_hash.hex()}")
        return tx_hash.hex()

    def _remove_liquidity(self, params: dict, dry_run: bool = False) -> str:
        amount = params.get("amount", 1000)
        if isinstance(amount, str):
            amount = float(amount)
        slippage = params.get("slippage_pct", 0.5)

        if dry_run:
            print(f"  [DRY RUN] Curve 3pool remove_liquidity: {amount}")
            return "0x_dry_run_curve_remove_liquidity"

        print(f"Executing real Curve 3pool remove_liquidity...")
        contract = self.w3.eth.contract(address=self.THREE_POOL, abi=self.POOL_ABI)

        lp_amount = int(amount * 1e18)
        min_amounts = [int(amount * (1 - slippage / 100) * 1e6 / 3) for _ in range(3)]

        tx = contract.functions.remove_liquidity(lp_amount, min_amounts).build_transaction({
            "from": self.wallet.address,
            "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
            "gasPrice": self.w3.eth.gas_price,
        })
        gas_estimate = self._retry_call(self.w3.eth.estimate_gas, tx)
        tx["gas"] = gas_estimate

        if dry_run:
            print(f"  ⛽ Gas estimate: {gas_estimate}")
            return f"0x_dry_run_curve_remove_liquidity"

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  ✅ remove_liquidity: {tx_hash.hex()}")
        return tx_hash.hex()
