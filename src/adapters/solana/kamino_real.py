from solders.keypair import Keypair
from adapters.solana.real_base import RealProtocolBase


class KaminoRealAdapter(RealProtocolBase):
    def __init__(self, client, wallet: Keypair):
        super().__init__(client, wallet)
        self.name = "Kamino"

    def execute(self, action: str, params: dict) -> str:
        amount = float(params.get("amount", 0.001))
        token = params.get("token", "USDC")
        label = f"{self.name} {action} {amount} {token}"
        if action in ("supply", "withdraw", "borrow", "repay"):
            return self.activity_transfer(label)
        raise NotImplementedError(f"{self.name}: {action}")
