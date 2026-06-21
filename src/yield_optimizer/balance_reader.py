import json
import logging
from pathlib import Path

from web3 import Web3
from solders.pubkey import Pubkey
from solana.rpc.api import Client as SolanaClient
from solana.rpc.types import TokenAccountOpts

from src.intelligence.chain_registry import get_chain
from src.adapters import get_token_address

logger = logging.getLogger(__name__)

DUST_THRESHOLDS = {
    "USDC": 1_000_000,
    "USDT": 1_000_000,
    "WETH": 10_000_000_000_000_000,
    "ETH": 10_000_000_000_000_000,
}

ERC20_BALANCE_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    }
]

SOL_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


class BalanceReader:
    def get_evm_idle_balances(self, wallet: str, chain: str) -> list[dict]:
        cfg = get_chain(chain)
        if not cfg:
            logger.warning(f"Unknown chain: {chain}")
            return []
        w3 = Web3(Web3.HTTPProvider(cfg.rpc, request_kwargs={"timeout": 10}))
        if not w3.is_connected():
            logger.warning(f"Cannot connect to {chain} RPC")
            return []

        wallet = Web3.to_checksum_address(wallet)
        results = []

        native_bal = w3.eth.get_balance(wallet)
        if native_bal >= DUST_THRESHOLDS["ETH"]:
            results.append({
                "token": "ETH",
                "balance_raw": native_bal,
                "balance_human": native_bal / 1e18,
                "wallet": wallet,
                "chain": chain,
                "location": "wallet",
            })

        tokens = {"USDC": cfg.usdc, "USDT": cfg.usdt, "WETH": cfg.weth}
        for symbol, addr in tokens.items():
            if not addr:
                continue
            try:
                addr = Web3.to_checksum_address(addr)
                contract = w3.eth.contract(address=addr, abi=ERC20_BALANCE_ABI)
                bal = contract.functions.balanceOf(wallet).call()
                threshold = DUST_THRESHOLDS.get(symbol, 0)
                if bal >= threshold:
                    decimals = 6 if symbol in ("USDC", "USDT") else 18
                    results.append({
                        "token": symbol,
                        "balance_raw": bal,
                        "balance_human": bal / 10 ** decimals,
                        "wallet": wallet,
                        "chain": chain,
                        "location": "wallet",
                    })
            except Exception as e:
                logger.warning(f"Failed to read {symbol} balance on {chain}: {e}")

        return results

    def get_solana_idle_balances(self, wallet_path: str = "wallets/solana_real.sol.json") -> list[dict]:
        path = Path(wallet_path)
        if not path.exists():
            logger.warning(f"Solana wallet not found: {wallet_path}")
            return []
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read Solana wallet: {e}")
            return []

        pubkey_str = data.get("public_key") or data.get("address")
        if not pubkey_str:
            logger.warning("No public key in Solana wallet file")
            return []

        results = []
        client = SolanaClient("https://api.mainnet-beta.solana.com")
        pubkey = Pubkey.from_string(pubkey_str)

        try:
            sol_resp = client.get_balance(pubkey)
            sol_bal = sol_resp.value if hasattr(sol_resp, "value") else 0
            if sol_bal >= DUST_THRESHOLDS.get("SOL", 0):
                results.append({
                    "token": "SOL",
                    "balance_raw": sol_bal,
                    "balance_human": sol_bal / 1e9,
                    "wallet": pubkey_str,
                    "chain": "solana",
                    "location": "wallet",
                })
        except Exception as e:
            logger.warning(f"Failed to read SOL balance: {e}")

        try:
            mint = Pubkey.from_string(SOL_USDC_MINT)
            opts = TokenAccountOpts(mint=mint)
            token_resp = client.get_token_accounts_by_owner(
                pubkey,
                opts,
            )
            accounts = []
            if hasattr(token_resp, "value"):
                accounts = token_resp.value
            elif isinstance(token_resp, dict):
                accounts = token_resp.get("result", {}).get("value", [])
            for acc in accounts:
                amount = 0
                if hasattr(acc, "account") and hasattr(acc.account, "data"):
                    amount = acc.account.data.parsed.get("info", {}).get("tokenAmount", {}).get("uiAmount", 0) or 0
                elif isinstance(acc, dict):
                    amount = (
                        acc.get("account", {})
                        .get("data", {})
                        .get("parsed", {})
                        .get("info", {})
                        .get("tokenAmount", {})
                        .get("uiAmount", 0)
                        or 0
                    )
                if amount >= 1:
                    results.append({
                        "token": "USDC",
                        "balance_raw": int(amount * 1e6),
                        "balance_human": float(amount),
                        "wallet": pubkey_str,
                        "chain": "solana",
                        "location": "wallet",
                    })
        except Exception as e:
            logger.warning(f"Failed to read Solana USDC: {e}")

        return results

    def get_deposited_balances(self, wallet: str) -> list[dict]:
        results = []
        w3 = Web3(Web3.HTTPProvider("https://arb1.arbitrum.io/rpc", request_kwargs={"timeout": 10}))
        if not w3.is_connected():
            logger.warning("Cannot connect to Arbitrum RPC for deposited balance check")
            return results
        wallet = Web3.to_checksum_address(wallet)

        aave_tokens = {
            "USDC": "0x724dc807b04555b71ed48a6896b6F41593b8C637",
        }
        for symbol, a_token_addr in aave_tokens.items():
            try:
                addr = Web3.to_checksum_address(a_token_addr)
                contract = w3.eth.contract(address=addr, abi=ERC20_BALANCE_ABI)
                bal = contract.functions.balanceOf(wallet).call()
                if bal >= DUST_THRESHOLDS.get(symbol, 0):
                    decimals = 6 if symbol in ("USDC", "USDT") else 18
                    results.append({
                        "token": symbol,
                        "balance_raw": bal,
                        "balance_human": bal / 10 ** decimals,
                        "wallet": wallet,
                        "chain": "arbitrum",
                        "location": "aave_v3",
                    })
            except Exception as e:
                logger.warning(f"Failed to read {symbol} aToken balance: {e}")

        compound_tokens = {
            "USDC": "0xA5EDBDD9646f8dFF606d7448e414884C7d905dCA",
        }
        for symbol, c_token_addr in compound_tokens.items():
            try:
                addr = Web3.to_checksum_address(c_token_addr)
                contract = w3.eth.contract(address=addr, abi=ERC20_BALANCE_ABI)
                bal = contract.functions.balanceOf(wallet).call()
                if bal >= DUST_THRESHOLDS.get(symbol, 0):
                    decimals = 6 if symbol in ("USDC", "USDT") else 18
                    results.append({
                        "token": symbol,
                        "balance_raw": bal,
                        "balance_human": bal / 10 ** decimals,
                        "wallet": wallet,
                        "chain": "arbitrum",
                        "location": "compound_v3",
                    })
            except Exception as e:
                logger.warning(f"Failed to read {symbol} cToken balance: {e}")

        return results
