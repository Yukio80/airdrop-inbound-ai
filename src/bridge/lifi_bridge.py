import time
import os
import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
import requests
from dotenv import load_dotenv

load_dotenv()

from models import BridgeResult
from src.hardening.retry import retry
from src.hardening.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class LiFiBridge:
    """
    LiFi Bridge integration for automated cross-chain funding.
    Uses retry + circuit breaker for RPC and API resilience.
    """
    
    def __init__(self):
        self.arb_rpc = os.getenv("ARBITRUM_RPC_URL")
        self.bsc_rpc = os.getenv("BSC_RPC_URL")
        self.private_key = os.getenv("PRIVATE_KEY")
        
        if not all([self.arb_rpc, self.bsc_rpc, self.private_key]):
            raise RuntimeError("Missing RPC URLs or Private Key in environment")
            
        self.w3_arb = Web3(Web3.HTTPProvider(self.arb_rpc))
        self.w3_bsc = Web3(Web3.HTTPProvider(self.bsc_rpc))
        self.account = Account.from_key(self.private_key)

        self._rpc_cb = CircuitBreaker(
            name="lifi_rpc", failure_threshold=3, recovery_timeout=60,
        )
        self._api_cb = CircuitBreaker(
            name="lifi_api", failure_threshold=3, recovery_timeout=120,
        )
        self._bridge_cb = CircuitBreaker(
            name="lifi_bridge", failure_threshold=2, recovery_timeout=300,
        )

    @retry(max_attempts=3, delay=2.0, backoff=2.0, exceptions=(ConnectionError, TimeoutError))
    def _get_arb_balance(self) -> Decimal:
        balance = self._rpc_cb.call(
            lambda: self.w3_arb.eth.get_balance(self.account.address)
        )
        return Decimal(balance / 1e18)

    @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(requests.RequestException,))
    def _get_lifi_quote(self, from_chain: str, to_chain: str, from_token: str, to_token: str, amount: Decimal) -> Dict[str, Any]:
        amount_wei = int(amount * Decimal("1000000000000000000"))
        url = (f"https://li.quest/v1/quote?fromChain={from_chain}&toChain={to_chain}"
               f"&fromToken={from_token}&toToken={to_token}&fromAmount={amount_wei}"
               f"&fromAddress={self.account.address}")
        r = self._api_cb.call(lambda: requests.get(url, timeout=15))
        if r.status_code != 200:
            raise RuntimeError(f"LiFi quote failed: {r.text}")
        return r.json()

    def check_and_bridge_if_needed(self, min_eth_balance: float = 0.005, dry_run: bool = False) -> BridgeResult:
        """
        Check Arbitrum balance and bridge from BSC if below threshold.
        Protected by circuit breaker for the full bridge operation.
        """
        def _do_bridge():
            balance_before = self._get_arb_balance()
            
            if balance_before >= Decimal(str(min_eth_balance)):
                return BridgeResult(
                    bridged=False,
                    tx_hash=None,
                    balance_before=balance_before,
                    balance_after=balance_before,
                    status="not_needed"
                )
                
            bridge_amount = Decimal("0.01") 
            quote = self._get_lifi_quote("BSC", "ARB", "BNB", "ETH", bridge_amount)
            tx_data = quote.get("txData")
            if not tx_data:
                raise RuntimeError("No txData returned from LiFi")
                
            tx = {
                "from": self.account.address,
                "to": Web3.to_checksum_address(tx_data["to"]),
                "data": tx_data["data"],
                "value": int(tx_data["value"]),
                "nonce": self.w3_bsc.eth.get_transaction_count(self.account.address),
                "gasPrice": self.w3_bsc.eth.gas_price,
            }
            
            gas = self.w3_bsc.eth.estimate_gas(tx)
            tx["gas"] = gas
            
            if dry_run:
                return BridgeResult(
                    bridged=True,
                    tx_hash=None,
                    balance_before=balance_before,
                    balance_after=balance_before + bridge_amount,
                    status="dry_run"
                )
                
            signed_tx = self.w3_bsc.eth.account.sign_transaction(tx, self.account)
            tx_hash = self.w3_bsc.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            self.w3_bsc.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            time.sleep(30)
            balance_after = self._get_arb_balance()
            
            return BridgeResult(
                bridged=True,
                tx_hash=tx_hash.hex(),
                balance_before=balance_before,
                balance_after=balance_after,
                status="success"
            )

        try:
            return self._bridge_cb.call(_do_bridge)
        except Exception as e:
            logger.error("LiFi bridge circuit breaker open: %s", e)
            return BridgeResult(
                bridged=False, tx_hash=None,
                balance_before=Decimal("0"), balance_after=Decimal("0"),
                status=f"circuit_open: {e}",
            )
