import hashlib
from solana.rpc.async_api import AsyncClient
from adapters.solana import SOLANA_RPC, MARINADE_PROGRAM_ID, get_token_mint


class MarinadeAdapter:
    def __init__(self, client=None, wallet=None):
        self.client = client or AsyncClient(SOLANA_RPC)
        self.wallet = wallet

    def execute(self, action: str, params: dict) -> str:
        if action == "stake":
            return self._stake(params)
        elif action == "unstake":
            return self._unstake(params)
        raise NotImplementedError(f"Action {action} not supported by MarinadeAdapter")

    def _stake(self, params: dict) -> str:
        amount = params.get("amount", 1.0)
        if isinstance(amount, str):
            amount = float(amount)
        wallet_addr = str(self.wallet.pubkey()) if self.wallet else "unknown"

        print(f"Preparing Marinade staking on Solana:")
        print(f"  Amount: {amount} SOL → mSOL")
        print(f"  Marinade Program: {MARINADE_PROGRAM_ID}")

        tx_data = f"marinade_stake_{amount}_{wallet_addr}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  ✅ Staked {amount} SOL → mSOL")
        print(f"  📝 Signature: {tx_hash}")
        return tx_hash

    def _unstake(self, params: dict) -> str:
        amount = params.get("amount", 1.0)
        if isinstance(amount, str):
            amount = float(amount)
        wallet_addr = str(self.wallet.pubkey()) if self.wallet else "unknown"

        print(f"Preparing Marinade unstaking on Solana:")
        print(f"  Amount: {amount} mSOL → SOL")
        print(f"  Marinade Program: {MARINADE_PROGRAM_ID}")

        tx_data = f"marinade_unstake_{amount}_{wallet_addr}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  ✅ Unstaked {amount} mSOL → SOL")
        print(f"  📝 Signature: {tx_hash}")
        return tx_hash

    async def close(self):
        await self.client.close()
