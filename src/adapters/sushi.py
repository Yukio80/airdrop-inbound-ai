from decimal import Decimal
from typing import Optional, Dict, Any
from web3 import Web3

from adapters.base import BaseAdapter


class AdapterError(Exception):
    """Custom exception for adapter failures."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


TOKEN_ADDRESSES = {
    "ethereum": {
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    },
    "arbitrum": {
        "WETH": "0x82aF49447D8a07e3bd95BD0d56f365363aAD3160e",
        "USDC": "0xaf88d065e77c8cc2239327a0744cea99e457dc4b",
        "USDT": "0xFd086bC68514b5b0b03Cf118c1e250a1572Fb6b4",
    },
}


class SushiAdapter(BaseAdapter):
    ROUTER_ADDRESSES = {
        "ethereum": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
        "arbitrum": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
    }

    ROUTER_ABI = [
        {
            "inputs": [
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                {"internalType": "address[]", "name": "path", "type": "address[]"},
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            ],
            "name": "swapExactTokensForTokens",
            "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
                {"internalType": "address[]", "name": "path", "type": "address[]"},
                {"internalType": "address", "name": "to", "type": "address"},
                {"internalType": "uint256", "name": "deadline", "type": "uint256"},
            ],
            "name": "swapExactETHForTokens",
            "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
            "stateMutability": "payable",
            "type": "function",
        },
    ]

    ERC20_ABI = [
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    ]

    def __init__(self, w3, wallet, config_path: str = "config.yaml"):
        super().__init__(w3, wallet, config_path)
        self.w3 = w3
        self.wallet = wallet

    def validate(self, **kwargs) -> bool:
        return True

    def dry_run(self, **kwargs) -> str:
        return "0x_dry_run_sushi"

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

    def execute(self, action: str, params: dict, dry_run: bool = False) -> str:
        if action == "swap":
            return self._swap(params, dry_run)
        raise NotImplementedError(f"Action {action} not supported by SushiAdapter")

    def _swap(self, params: dict, dry_run: bool = False) -> str:
        amount = params.get("amount", 0.1)
        if isinstance(amount, str):
            amount = float(amount)
        token_in = params.get("token_in", "WETH")
        token_out = params.get("token_out", "USDC")
        chain = params.get("chain", "arbitrum").lower()
        slippage = params.get("slippage_pct", 0.5)
        gas_limit = params.get("gas_limit", 300000)

        router_addr = self.ROUTER_ADDRESSES.get(chain)
        if not router_addr:
            raise ValueError(f"Unsupported chain for SushiSwap: {chain}")

        tokens = TOKEN_ADDRESSES.get(chain, {})
        token_in_addr = tokens.get(token_in)
        token_out_addr = tokens.get(token_out)

        if dry_run:
            print(f"  [DRY RUN] SushiSwap {token_in}→{token_out} on {chain.upper()}")
            return "0x_dry_run_sushi_swap"

        print(f"Executing real SushiSwap swap on {chain.upper()}...")
        print(f"  Path: {token_in} → {token_out}")
        print(f"  Amount: {amount} {token_in}")

        contract = self.w3.eth.contract(address=router_addr, abi=self.ROUTER_ABI)
        is_eth = token_in in ("WETH", "ETH") or "ETH" in token_in
        amount_in_wei = self.w3.to_wei(amount, "ether") if is_eth else int(amount * 1e6)
        path = [Web3.to_checksum_address(token_in_addr), Web3.to_checksum_address(token_out_addr)]
        amount_out_min = int(int(amount_in_wei) * (1 - slippage / 100))

        # Handle approval for token swaps
        if not is_eth:
            token_contract = self.w3.eth.contract(address=Web3.to_checksum_address(token_in_addr), abi=self.ERC20_ABI)
            allowance = self._retry_call(token_contract.functions.allowance().call, self.wallet.address, router_addr)
            if allowance < amount_in_wei:
                approve_tx = token_contract.functions.approve(router_addr, amount_in_wei).build_transaction({
                    "from": self.wallet.address,
                    "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
                    "gasPrice": self.w3.eth.gas_price,
                })
                signed_approve = self.w3.eth.account.sign_transaction(approve_tx, self.wallet)
                self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)

        deadline = self.w3.eth.get_block("latest")["timestamp"] + 600

        if is_eth:
            tx = contract.functions.swapExactETHForTokens(
                amount_out_min, path, self.wallet.address, deadline
            ).build_transaction({
                "from": self.wallet.address,
                "value": amount_in_wei,
                "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
                "gasPrice": self.w3.eth.gas_price,
            })
        else:
            tx = contract.functions.swapExactTokensForTokens(
                amount_in_wei, amount_out_min, path, self.wallet.address, deadline
            ).build_transaction({
                "from": self.wallet.address,
                "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
                "gasPrice": self.w3.eth.gas_price,
            })

        gas_estimate = self._retry_call(self.w3.eth.estimate_gas, tx)
        tx["gas"] = gas_estimate

        if dry_run:
            print(f"  ⛽ Gas estimate: {gas_estimate}")
            return f"0x_dry_run_sushi_swap"

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  ✅ Swap: {tx_hash.hex()}")
        return tx_hash.hex()
