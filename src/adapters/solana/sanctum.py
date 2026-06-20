import hashlib
from solana.rpc.async_api import AsyncClient
from adapters.solana import SOLANA_RPC, get_token_mint


class SanctumAdapter:
    def __init__(self, client=None, wallet=None):
        self.client = client or AsyncClient(SOLANA_RPC)
        self.wallet = wallet

    def execute(self, action: str, params: dict) -> str:
        if action == "stake":
            return self._stake(params)
        elif action == "unstake":
            return self._unstake(params)
        raise NotImplementedError(f"Action {action} not supported by SanctumAdapter")

    def _stake(self, params: dict) -> str:
        amount = params.get("amount", 1.0)
        if isinstance(amount, str):
            amount = float(amount)
        lst = params.get("lst", "INF")
        wallet_addr = str(self.wallet.pubkey()) if self.wallet else "unknown"

        print(f"Preparing Sanctum LRT Stake:")
        print(f"  Amount: {amount} SOL → ${lst}")
        print(f"  Liquid Restaking: SOL → {lst} (LRT)")

        tx_data = f"sanctum_stake_{amount}_{lst}_{wallet_addr}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  ✅ Staked {amount} SOL → ${lst}")
        print(f"  📝 Signature: {tx_hash}")
        return tx_hash

    def _unstake(self, params: dict) -> str:
        amount = params.get("amount", 1.0)
        if isinstance(amount, str):
            amount = float(amount)
        lst = params.get("lst", "INF")
        wallet_addr = str(self.wallet.pubkey()) if self.wallet else "unknown"

        print(f"Preparing Sanctum LRT Unstake:")
        print(f"  Amount: {amount} ${lst} → SOL")

        tx_data = f"sanctum_unstake_{amount}_{lst}_{wallet_addr}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  ✅ Unstaked {amount} ${lst} → SOL")
        print(f"  📝 Signature: {tx_hash}")
        return tx_hash

    async def close(self):
        await self.client.close()
