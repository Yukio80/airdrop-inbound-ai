from solders.keypair import Keypair
from adapters.solana.real_base import RealProtocolBase


class MeteoraRealAdapter(RealProtocolBase):
    def __init__(self, client, wallet: Keypair):
        super().__init__(client, wallet)
        self.name = "Meteora"

    def execute(self, action: str, params: dict) -> str:
        amount = float(params.get("amount", 0.001))
        label = f"{self.name} {action} {amount} SOL"
        if action in ("swap", "add_liquidity"):
            return self.activity_transfer(label)
        raise NotImplementedError(f"{self.name}: {action}")
