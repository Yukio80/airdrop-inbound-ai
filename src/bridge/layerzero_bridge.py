"""
Cross-chain bridge via Stargate (LayerZero V1).
Transfers USDC between supported chains.

V1 supported chains: Arbitrum, Optimism, BSC, Polygon, Ethereum
Base not supported via V1 (never deployed) — use LiFi bridge instead.
"""
import os
import time
import logging
from decimal import Decimal
from typing import Optional, Dict
from dataclasses import dataclass

from web3 import Web3
from eth_account.signers.local import LocalAccount
from dotenv import load_dotenv

from src.intelligence.chain_registry import get_chain

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class BridgeResult:
    status: str
    bridged: bool
    tx_hash: Optional[str] = None
    amount: Optional[Decimal] = None
    from_chain: str = ""
    to_chain: str = ""
    error: Optional[str] = None


STARGATE_V1_DEPLOYED = {
    "arbitrum": True,
    "optimism": True,
    "bsc": True,
    "polygon": True,
    "ethereum": True,
}

STARGATE_ROUTERS = {
    "arbitrum": "0x53Bf833A5d6c4ddA888F69c22C88C9f356a41614",
    "optimism": "0xB0D502E938ed5f4df2E681fE6E419ff29631d62b",
    "bsc": "0x4a364f8c717cAAD9A442737Eb7b8A55cc6cf18D8",
    "polygon": "0x45A01E4e04F14f7A4a6702c74187c5F6222033cd",
    "ethereum": "0x8731d54E9D02c286767d56ac03e8037C07e01e98",
}

STARGATE_POOL_IDS = {
    "arbitrum": {"USDC": 1, "USDT": 2},
    "optimism": {"USDC": 1, "USDT": 2},
    "bsc": {"USDC": 1, "USDT": 2},
    "polygon": {"USDC": 1, "USDT": 2},
    "ethereum": {"USDC": 1, "USDT": 2},
}

LAYERZERO_CHAIN_IDS = {
    "arbitrum": 30110,
    "optimism": 30111,
    "bsc": 30102,
    "polygon": 30109,
    "ethereum": 30101,
}

ROUTER_ABI = [
    {
        "inputs": [
            {"type": "uint16", "name": "_dstChainId"},
            {"type": "uint256", "name": "_srcPoolId"},
            {"type": "uint256", "name": "_dstPoolId"},
            {"type": "address", "name": "_refundAddress"},
            {"type": "uint256", "name": "_amountLD"},
            {"type": "uint256", "name": "_minAmountLD"},
            {"type": "bytes", "name": "_lzTxParams"},
            {"type": "bytes", "name": "_to"},
            {"type": "bytes", "name": "_payload"},
        ],
        "name": "swap",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "inputs": [
            {"type": "uint16", "name": "_dstChainId"},
            {"type": "uint8", "name": "_functionType"},
            {"type": "address", "name": "_receiver"},
            {"type": "uint256", "name": "_amount"},
            {"type": "uint256", "name": "_minAmount"},
            {"type": "bytes", "name": "_payload"},
        ],
        "name": "quoteLayerZeroFee",
        "outputs": [{"type": "uint256"}, {"type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
]


class LayerZeroBridge:
    """
    Cross-chain bridge via Stargate (LayerZero V1).
    """

    def __init__(self, account: Optional[LocalAccount] = None):
        self.account = account
        self._w3_cache: Dict[str, Web3] = {}

    def _w3(self, chain: str) -> Web3:
        if chain not in self._w3_cache:
            cfg = get_chain(chain)
            if not cfg:
                raise ValueError(f"Unknown chain: {chain}")
            self._w3_cache[chain] = Web3(Web3.HTTPProvider(cfg.rpc))
        return self._w3_cache[chain]

    def _check_v1_supported(self, chain: str):
        if not STARGATE_V1_DEPLOYED.get(chain):
            raise ValueError(
                f"Stargate V1 not deployed on {chain}. "
                f"Use LiFi bridge instead (ecosystem.py lfbridge ...)"
            )

    def get_balance(self, chain: str, token: str = "USDC") -> Decimal:
        cfg = get_chain(chain)
        if not cfg:
            raise ValueError(f"Unknown chain: {chain}")
        w3 = self._w3(chain)
        token_addr = getattr(cfg, token.lower())
        if not token_addr:
            raise ValueError(f"Token {token} not configured on {chain}")
        contract = w3.eth.contract(address=Web3.to_checksum_address(token_addr), abi=ERC20_ABI)
        bal = contract.functions.balanceOf(self.account.address).call()
        return Decimal(bal) / Decimal(10 ** 6)

    def bridge_usdc(
        self,
        from_chain: str,
        to_chain: str,
        amount: Decimal,
        dry_run: bool = False,
    ) -> BridgeResult:
        self._check_v1_supported(from_chain)
        self._check_v1_supported(to_chain)

        from_cfg = get_chain(from_chain)
        to_cfg = get_chain(to_chain)
        if not from_cfg or not to_cfg:
            return BridgeResult(status="error", bridged=False, error="Unknown chain")

        amount_ld = int(amount * Decimal(1e6))
        dst_chain_id = LAYERZERO_CHAIN_IDS.get(to_chain)
        if not dst_chain_id:
            return BridgeResult(status="error", bridged=False, error=f"Unknown LayerZero chain ID for {to_chain}")

        if dry_run:
            return BridgeResult(
                status="dry_run",
                bridged=False,
                amount=amount,
                from_chain=from_chain,
                to_chain=to_chain,
            )

        w3 = self._w3(from_chain)
        router_addr = Web3.to_checksum_address(STARGATE_ROUTERS[from_chain])
        router = w3.eth.contract(address=router_addr, abi=ROUTER_ABI)

        src_pool_id = STARGATE_POOL_IDS[from_chain]["USDC"]
        dst_pool_id = STARGATE_POOL_IDS[to_chain]["USDC"]

        dst_address_bytes = Web3.to_bytes(hexstr=self.account.address)
        empty_params = b""
        empty_payload = b""

        try:
            quote = router.functions.quoteLayerZeroFee(
                dst_chain_id,
                1,
                self.account.address,
                amount_ld,
                amount_ld,
                empty_payload,
            ).call()
            native_fee = int(quote[0] * 1.1)
        except Exception as e:
            logger.warning(f"quoteLayerZeroFee failed, using fallback: {e}")
            native_fee = Web3.to_wei(0.0005, "ether")

        token_addr = Web3.to_checksum_address(from_cfg.usdc)
        token_contract = w3.eth.contract(address=token_addr, abi=ERC20_ABI)
        allowance = token_contract.functions.allowance(self.account.address, router_addr).call()
        if allowance < amount_ld:
            approve_tx = token_contract.functions.approve(router_addr, amount_ld).build_transaction({
                "from": self.account.address,
                "nonce": w3.eth.get_transaction_count(self.account.address),
                "gasPrice": w3.eth.gas_price,
            })
            signed_approve = w3.eth.account.sign_transaction(approve_tx, self.account)
            w3.eth.send_raw_transaction(signed_approve.raw_transaction)
            time.sleep(2)

        tx = router.functions.swap(
            dst_chain_id,
            src_pool_id,
            dst_pool_id,
            self.account.address,
            amount_ld,
            amount_ld,
            empty_params,
            dst_address_bytes,
            empty_payload,
        ).build_transaction({
            "from": self.account.address,
            "value": native_fee,
            "nonce": w3.eth.get_transaction_count(self.account.address),
            "gasPrice": w3.eth.gas_price,
        })

        signed = w3.eth.account.sign_transaction(tx, self.account)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

        if receipt.status != 1:
            return BridgeResult(
                status="failed", bridged=False,
                error=f"Transaction reverted: {tx_hash.hex()}",
                from_chain=from_chain, to_chain=to_chain,
            )

        return BridgeResult(
            status="success",
            bridged=True,
            tx_hash=tx_hash.hex(),
            amount=amount,
            from_chain=from_chain,
            to_chain=to_chain,
        )


def bridge_route(from_chain: str, to_chain: str, amount: Decimal = Decimal("10"),
                 dry_run: bool = False) -> BridgeResult:
    from eth_account.account import Account
    import json
    from pathlib import Path

    ROOT = Path(__file__).parent.parent.parent
    KEYSTORE = ROOT / "wallets" / "user_real.json"
    KEYSTORE_PASS = "231413"

    with open(KEYSTORE) as f:
        ks = json.load(f)
    pk = Account.decrypt(ks, KEYSTORE_PASS).hex()
    account = Account.from_key(pk)

    bridge = LayerZeroBridge(account)
    return bridge.bridge_usdc(from_chain, to_chain, amount, dry_run=dry_run)
