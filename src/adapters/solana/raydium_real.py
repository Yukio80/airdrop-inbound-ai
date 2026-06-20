from solders.keypair import Keypair
from adapters.solana.real_base import RealProtocolBase


class RaydiumRealAdapter(RealProtocolBase):
    def __init__(self, client, wallet: Keypair):
        super().__init__(client, wallet)
        self.name = "Raydium"

    def execute(self, action: str, params: dict) -> str:
        amount = float(params.get("amount", 0.001))
        pool = params.get("pool", "USDC/SOL")
        label = f"{self.name} {action} {amount} {pool}"
        if action in ("add_liquidity", "remove_liquidity", "farm", "unfarm"):
            return self.activity_transfer(label)
        raise NotImplementedError(f"{self.name}: {action}")
