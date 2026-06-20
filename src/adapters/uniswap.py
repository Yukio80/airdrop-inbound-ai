import time
import os
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

from adapters.base import BaseAdapter
from models import SwapResult

class AdapterError(Exception):
    """Custom exception for adapter failures."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}

class UniswapAdapter(BaseAdapter):
    """
    Production-grade Uniswap V3 Adapter for Arbitrum One.
    """
    
    ROUTER_ADDRESS = Web3.to_checksum_address("0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45")
    QUOTER_ADDRESS = Web3.to_checksum_address("0x61fFE014bA17989E743c5F6cB21bF9697530B21e")
    FACTORY_ADDRESS = Web3.to_checksum_address("0x1F98431c8aD98523631C44830bB6A3C0d5D64E43")

    def __init__(self, w3, wallet, config_path: str = "config.yaml"):
        super().__init__(w3, wallet, config_path)
        self.w3 = w3
        self.account = wallet
        
        # ABIs
        self._router_abi = [
            {
                "inputs": [
                    {
                        "components": [
                            {"internalType": "address", "name": "tokenIn", "type": "address"},
                            {"internalType": "address", "name": "tokenOut", "type": "address"},
                            {"internalType": "uint24", "name": "fee", "type": "uint24"},
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                            {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                            {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
                        ],
                        "internalType": "struct ISwapRouter.ExactInputSingleParams",
                        "name": "params",
                        "type": "tuple",
                    }
                ],
                "name": "exactInputSingle",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "payable",
                "type": "function",
            }
        ]
        
        self._quoter_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "tokenIn", "type": "address"},
                    {"internalType": "address", "name": "tokenOut", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                    {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"},
                ],
                "name": "quoteExactInputSingle",
                "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]
        
        self._erc20_abi = [
            {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
            {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
        ]
        
        self._factory_abi = [
            {"inputs": [{"internalType": "address", "name": "tokenA", "type": "address"}, {"internalType": "address", "name": "tokenB", "type": "address"}, {"internalType": "uint24", "name": "fee", "type": "uint24"}], "name": "getPool", "outputs": [{"internalType": "contract Pool", "name": "pool", "type": "address"}], "stateMutability": "view", "type": "function"},
        ]
        
        self._pool_abi = [
            {"inputs": [], "name": "slot0", "outputs": [{"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"}, {"internalType": "int24", "name": "tick", "type": "int24"}, {"internalType": "uint16", "name": "observationIndex", "type": "uint16"}, {"internalType": "uint16", "name": "observation cardinality", "type": "uint16"}, {"internalType": "uint16", "name": "observation liveness", "type": "uint16"}, {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"}], "stateMutability": "view", "type": "function"},
        ]

    def execute(self, action: str, params: dict, dry_run: bool = False) -> str:
        """
        Entry point for Uniswap actions.
        """
        if action == "swap":
            token_in = params.get("token_in")
            token_out = params.get("token_out")
            amount_in = Decimal(str(params.get("amount", 0)))
            
            result = self.swap_exact_input_single(
                token_in=token_in,
                token_out=token_out,
                amount_in=amount_in,
                dry_run=dry_run,
            )
            return result.tx_hash if result.tx_hash else "dry_run"
        
        raise NotImplementedError(f"Action {action} not supported by UniswapAdapter")

    def _retry_call(self, func, *args, **kwargs):
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

    def validate(self, token_in: str, token_out: str, amount_in: Decimal, **kwargs) -> bool:
        """Validate swap parameters against risk rules."""
        # Convert to checksum
        token_in = Web3.to_checksum_address(token_in)
        token_out = Web3.to_checksum_address(token_out)
        
        # Risk: Max position pct (2% of wallet)
        balance = self.w3.eth.get_balance(self.account.address)
        balance_eth = Decimal(balance / 1e18)
        
        # If token_in is ETH
        if token_in == "0xEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE": # Native ETH marker
             if amount_in > balance_eth * Decimal(self.config["risk"]["max_position_pct"] / 100):
                 return False
        
        return True

    def dry_run(self, **kwargs) -> str:
        return "0x_dry_run_uniswap"

    def get_pool_price(self, token_a: str, token_b: str, fee: int = 3000) -> Decimal:
        """
        Fetch the current pool price for two tokens.
        Returns price of token_a in terms of token_b.
        """
        token_a = Web3.to_checksum_address(token_a)
        token_b = Web3.to_checksum_address(token_b)
        
        factory = self.w3.eth.contract(address=self.FACTORY_ADDRESS, abi=self._factory_abi)
        try:
            pool_addr = self._retry_call(factory.functions.getPool, token_a, token_b, fee)
            if pool_addr == "0x0000000000000000000000000000000000000000":
                raise AdapterError(f"No pool found for {token_a}/{token_b} with fee {fee}")
            
            pool = self.w3.eth.contract(address=pool_addr, abi=self._pool_abi)
            slot0 = self._retry_call(pool.functions.slot0().call)
            sqrt_price_x96 = slot0[0]
            
            # Price = (sqrtPriceX96 / 2^96)^2
            price = (Decimal(sqrt_price_x96) / Decimal(2**96))**2
            
            # Adjust for decimals if needed (this function returns the raw ratio)
            return price
            
        except Exception as e:
            if isinstance(e, AdapterError): raise e
            raise AdapterError(f"Failed to get pool price: {str(e)}")

    def swap_exact_input_single(
        self, 
        token_in: str, 
        token_out: str, 
        amount_in: Decimal, 
        slippage_bps: int = 50, 
        dry_run: bool = False
    ) -> SwapResult:
        """
        Execute a swap on Uniswap V3.
        """
        token_in = Web3.to_checksum_address(token_in)
        token_out = Web3.to_checksum_address(token_out)

        amount_in_wei = int(amount_in * Decimal(1e18))

        if dry_run:
            mock_out = int(amount_in_wei * 9900 / 10000)
            return SwapResult(
                tx_hash=None,
                amount_in=amount_in,
                amount_out_min=Decimal(mock_out / 1e18),
                token_in=token_in,
                token_out=token_out,
                gas_estimate=210000,
                status="dry_run",
            )

        quoter = self.w3.eth.contract(address=self.QUOTER_ADDRESS, abi=self._quoter_abi)

        try:
            amount_out_min_wei = self._retry_call(
                quoter.functions.quoteExactInputSingle, 
                token_in, token_out, 3000, amount_in_wei, 0
            ).call()
            amount_out_min = int(amount_out_min_wei * (10000 - slippage_bps) / 10000)
        except Exception as e:
            raise AdapterError(f"Failed to get quote: {str(e)}")

        if token_in != "0xEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE":
            token_contract = self.w3.eth.contract(address=token_in, abi=self._erc20_abi)
            allowance = self._retry_call(token_contract.functions.allowance(self.account.address, self.ROUTER_ADDRESS).call)
            if allowance < amount_in_wei:
                approve_tx = token_contract.functions.approve(self.ROUTER_ADDRESS, amount_in_wei).build_transaction({
                    "from": self.account.address,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                    "gasPrice": self.w3.eth.gas_price,
                })
                signed_approve = self.w3.eth.account.sign_transaction(approve_tx, self.account)
                self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)
                time.sleep(2)

        router = self.w3.eth.contract(address=self.ROUTER_ADDRESS, abi=self._router_abi)
        params = {
            "tokenIn": token_in,
            "tokenOut": token_out,
            "fee": 3000,
            "recipient": self.account.address,
            "amountIn": amount_in_wei,
            "amountOutMinimum": amount_out_min,
            "sqrtPriceLimitX96": 0,
        }

        tx = router.functions.exactInputSingle(params).build_transaction({
            "from": self.account.address,
            "value": amount_in_wei if token_in == "0xEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE" else 0,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gasPrice": self.w3.eth.gas_price,
        })

        gas_estimate = self._retry_call(self.w3.eth.estimate_gas, tx)
        tx["gas"] = gas_estimate

        return SwapResult(
            tx_hash=None,
            amount_in=amount_in,
            amount_out_min=Decimal(amount_out_min / 1e18),
            token_in=token_in,
            token_out=token_out,
            gas_estimate=gas_estimate,
            status="dry_run"
        )
        # 4. Execute
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # 5. Wait for confirmation (2 blocks as per requirements)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        
        # Basic validation (Confirmation check logic would be in execution layer, but we do basic check here)
        if receipt.status != 1:
            raise AdapterError(f"Transaction reverted: {tx_hash.hex()}")
            
        return SwapResult(
            tx_hash=tx_hash.hex(),
            amount_in=amount_in,
            amount_out_min=Decimal(amount_out_min / 1e18),
            token_in=token_in,
            token_out=token_out,
            gas_estimate=gas_estimate,
            status="success"
        )
