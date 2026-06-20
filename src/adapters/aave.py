import time
import os
from decimal import Decimal
from typing import Optional, Dict, Any
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount

from adapters.base import BaseAdapter
from models import SupplyResult, WithdrawResult

class AdapterError(Exception):
    """Custom exception for adapter failures."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}

class AaveAdapter(BaseAdapter):
    """
    Production-grade Aave V3 Adapter for Arbitrum One.
    """
    
    POOL_ADDRESS = Web3.to_checksum_address("0x794a61358D6845594F94dc1DB02A252b5b4814aD")
    
    def __init__(self, w3, wallet, config_path: str = "config.yaml"):
        super().__init__(w3, wallet, config_path)
        self.w3 = w3
        self.account = wallet
        
        # ABIs
        self._pool_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "asset", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"},
                    {"internalType": "address", "name": "onBehalfOf", "type": "address"},
                    {"internalType": "uint16", "name": "referralCode", "type": "uint16"},
                ],
                "name": "supply",
                "outputs": [{"internalType": "uint256", "name": "shares", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "asset", "type": "address"},
                    {"internalType": "uint256", "name": "amount", "type": "uint256"},
                    {"internalType": "address", "name": "to", "type": "address"},
                ],
                "name": "withdraw",
                "outputs": [{"internalType": "uint256", "name": "amount", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
                "name": "getUserAccountData",
                "outputs": [
                    {"internalType": "uint256", "name": "totalCollateralBase", "type": "uint256"},
                    {"internalType": "uint256", "name": "totalDebtBase", "type": "uint256"},
                    {"internalType": "uint256", "name": "availableBorrowsBase", "type": "uint256"},
                    {"internalType": "uint256", "name": "currentLiquidationThreshold", "type": "uint256"},
                    {"internalType": "uint256", "name": "ltv", "type": "uint256"},
                    {"internalType": "uint256", "name": "healthFactor", "type": "uint256"},
                ],
                "stateMutability": "view",
                "type": "function",
            },
        ]
        
        self._erc20_abi = [
            {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
            {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
        ]

    def execute(self, action: str, params: dict, dry_run: bool = False) -> str:
        """
        Entry point for Aave actions.
        """
        if action == "supply":
            token = params.get("token")
            amount = Decimal(str(params.get("amount", 0)))
            result = self.supply(token, amount, dry_run=dry_run)
            return result.tx_hash if result.tx_hash else "dry_run"
        
        if action == "withdraw":
            token = params.get("token")
            amount = Decimal(str(params.get("amount", 0)))
            result = self.withdraw(token, amount, dry_run=dry_run)
            return result.tx_hash if result.tx_hash else "dry_run"
            
        raise NotImplementedError(f"Action {action} not supported by AaveAdapter")

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

    def validate(self, token_address: str, amount: Decimal, **kwargs) -> bool:
        """Validate Aave operation against risk rules."""
        # Check min ETH balance for gas
        balance = self.w3.eth.get_balance(self.account.address)
        balance_eth = Decimal(balance / 1e18)
        
        if balance_eth < Decimal(self.config["risk"]["min_eth_balance"]):
            return False
            
        return True

    def dry_run(self, **kwargs) -> str:
        return "0x_dry_run_aave"

    def get_user_account_data(self, address: str) -> Dict[str, Any]:
        """Fetch account data for a user from Aave Pool."""
        address = Web3.to_checksum_address(address)
        pool = self.w3.eth.contract(address=self.POOL_ADDRESS, abi=self._pool_abi)
        
        try:
            data = self._retry_call(pool.functions.getUserAccountData, address).call()
            
            # Aave returns values in 8 decimals (Ray) for USD values
            return {
                "total_collateral_usd": Decimal(data[0]) / Decimal(10**8),
                "total_debt_usd": Decimal(data[1]) / Decimal(10**8),
                "available_borrow_usd": Decimal(data[2]) / Decimal(10**8),
                "health_factor": Decimal(data[5]) / Decimal(10**18),
            }
        except Exception as e:
            if isinstance(e, AdapterError): raise e
            raise AdapterError(f"Failed to get user account data: {str(e)}")

    def supply(self, token_address: str, amount: Decimal, dry_run: bool = False) -> SupplyResult:
        """
        Supply assets to Aave V3.
        """
        token_address = Web3.to_checksum_address(token_address)
        amount_wei = int(amount * Decimal(1e6))

        if dry_run:
            return SupplyResult(
                tx_hash=None,
                asset=token_address,
                amount=amount,
                atoken_received=None,
                gas_used=0,
                status="dry_run",
            )

        token_contract = self.w3.eth.contract(address=token_address, abi=self._erc20_abi)
        allowance = self._retry_call(token_contract.functions.allowance(self.account.address, self.POOL_ADDRESS).call)

        if allowance < amount_wei:
            approve_tx = token_contract.functions.approve(self.POOL_ADDRESS, amount_wei).build_transaction({
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gasPrice": self.w3.eth.gas_price,
            })
            signed_approve = self.w3.eth.account.sign_transaction(approve_tx, self.account)
            self.w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            time.sleep(2)

        pool = self.w3.eth.contract(address=self.POOL_ADDRESS, abi=self._pool_abi)
        tx = pool.functions.supply(
            token_address, amount_wei, self.account.address, 0
        ).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gasPrice": self.w3.eth.gas_price,
        })

        gas_estimate = self._retry_call(self.w3.eth.estimate_gas, tx)
        tx["gas"] = gas_estimate

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        if receipt.status != 1:
            raise AdapterError(f"Supply transaction reverted: {tx_hash.hex()}")

        return SupplyResult(
            tx_hash=tx_hash.hex(),
            asset=token_address,
            amount=amount,
            atoken_received=None,
            gas_used=receipt.gasUsed,
            status="success"
        )

    def withdraw(self, token_address: str, amount: Decimal, dry_run: bool = False) -> WithdrawResult:
        """
        Withdraw assets from Aave V3.
        """
        token_address = Web3.to_checksum_address(token_address)
        amount_wei = int(amount * 1e6)
        
        pool = self.w3.eth.contract(address=self.POOL_ADDRESS, abi=self._pool_abi)
        tx = pool.functions.withdraw(
            token_address, amount_wei, self.account.address
        ).build_transaction({
            "from": self.account.address,
            "nonce": self.w3.eth.get_transaction_count(self.account.address),
            "gasPrice": self.w3.eth.gas_price,
        })
        
        gas_estimate = self._retry_call(self.w3.eth.estimate_gas, tx)
        tx["gas"] = gas_estimate
        
        if dry_run:
            return WithdrawResult(
                tx_hash=None,
                asset=token_address,
                amount=amount,
                gas_used=gas_estimate,
                status="dry_run"
            )
            
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.account)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
        if receipt.status != 1:
            raise AdapterError(f"Withdraw transaction reverted: {tx_hash.hex()}")
            
        return WithdrawResult(
            tx_hash=tx_hash.hex(),
            asset=token_address,
            amount=amount,
            gas_used=receipt.gasUsed,
            status="success"
        )
