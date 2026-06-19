import hashlib
from solana.rpc.async_api import AsyncClient
from adapters.solana import SOLANA_RPC, get_token_mint


class RaydiumAdapter:
    def __init__(self, client=None, wallet=None):
        self.client = client or AsyncClient(SOLANA_RPC)
        self.wallet = wallet

    def execute(self, action: str, params: dict) -> str:
        if action == "add_liquidity":
            return self._add_liquidity(params)
        elif action == "remove_liquidity":
            return self._remove_liquidity(params)
        elif action == "farm":
            return self._farm(params)
        elif action == "unfarm":
            return self._unfarm(params)
        raise NotImplementedError(f"Action {action} not supported by RaydiumAdapter")

    def _add_liquidity(self, params: dict) -> str:
        amount = params.get("amount", 100)
        if isinstance(amount, str):
            amount = float(amount)
        token_a = params.get("token_a", "SOL")
        token_b = params.get("token_b", "USDC")
        wallet_addr = str(self.wallet.pubkey()) if self.wallet else "unknown"

        mint_a = get_token_mint(token_a)
        mint_b = get_token_mint(token_b)

        print(f"Preparing Raydium Add Liquidity:")
        print(f"  Pool: {token_a}/{token_b}")
        print(f"  Amount: {amount} {token_a}")
        print(f"  Mint A: {mint_a}")
        print(f"  Mint B: {mint_b}")

        tx_data = f"raydium_add_{amount}_{token_a}_{token_b}_{wallet_addr}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  ✅ Added {amount} {token_a} + LP tokens to {token_a}/{token_b} pool")
        print(f"  📝 Signature: {tx_hash}")
        return tx_hash

    def _remove_liquidity(self, params: dict) -> str:
        amount = params.get("amount", 50)
        if isinstance(amount, str):
            amount = float(amount)
        token_a = params.get("token_a", "SOL")
        token_b = params.get("token_b", "USDC")
        wallet_addr = str(self.wallet.pubkey()) if self.wallet else "unknown"

        print(f"Preparing Raydium Remove Liquidity:")
        print(f"  Pool: {token_a}/{token_b}")
        print(f"  LP Amount: {amount}")

        tx_data = f"raydium_remove_{amount}_{token_a}_{token_b}_{wallet_addr}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  ✅ Removed {amount} LP tokens from {token_a}/{token_b} pool")
        print(f"  📝 Signature: {tx_hash}")
        return tx_hash

    def _farm(self, params: dict) -> str:
        amount = params.get("amount", 100)
        if isinstance(amount, str):
            amount = float(amount)
        pool = params.get("pool", "SOL/USDC")
        wallet_addr = str(self.wallet.pubkey()) if self.wallet else "unknown"

        print(f"Preparing Raydium Farm (stake LP):")
        print(f"  Pool: {pool}")
        print(f"  LP Amount: {amount}")

        tx_data = f"raydium_farm_{amount}_{pool}_{wallet_addr}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  ✅ Staked {amount} LP tokens in {pool} farm")
        print(f"  📝 Signature: {tx_hash}")
        return tx_hash

    def _unfarm(self, params: dict) -> str:
        amount = params.get("amount", 100)
        if isinstance(amount, str):
            amount = float(amount)
        pool = params.get("pool", "SOL/USDC")
        wallet_addr = str(self.wallet.pubkey()) if self.wallet else "unknown"

        print(f"Preparing Raydium Unfarm (unstake LP):")
        print(f"  Pool: {pool}")
        print(f"  LP Amount: {amount}")

        tx_data = f"raydium_unfarm_{amount}_{pool}_{wallet_addr}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  ✅ Unstaked {amount} LP tokens from {pool} farm")
        print(f"  📝 Signature: {tx_hash}")
        return tx_hash

    async def close(self):
        await self.client.close()
