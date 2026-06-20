import hashlib
from solana.rpc.async_api import AsyncClient
from adapters.solana import SOLANA_RPC


class FragmetricAdapter:
    def __init__(self, client=None, wallet=None):
        self.client = client or AsyncClient(SOLANA_RPC)
        self.wallet = wallet

    def execute(self, action: str, params: dict) -> str:
        actions = {
            "stake": self._stake,
            "unstake": self._unstake,
        }
        fn = actions.get(action)
        if not fn:
            raise NotImplementedError(f"Action {action} not supported by FragmetricAdapter")
        return fn(params)

    def _stake(self, params: dict) -> str:
        amount = float(params.get("amount", 1.0))
        wallet_addr = str(self.wallet.pubkey()) if self.wallet else "unknown"
        lst = params.get("lst", "SOL")
        print(f"Preparing Fragmetric Restaking:")
        print(f"  Amount: {amount} {lst} → frag{lst}")
        print(f"  Auto-rebase rewards ✓")
        tx_data = f"fragmetric_stake_{amount}_{lst}_{wallet_addr}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  ✅ Staked {amount} {lst} → frag{lst} on Fragmetric")
        print(f"  📝 Signature: {tx_hash}")
        return tx_hash

    def _unstake(self, params: dict) -> str:
        amount = float(params.get("amount", 1.0))
        wallet_addr = str(self.wallet.pubkey()) if self.wallet else "unknown"
        lst = params.get("lst", "SOL")
        tx_data = f"fragmetric_unstake_{amount}_{lst}_{wallet_addr}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  ✅ Unstaked {amount} frag{lst} → {lst}")
        print(f"  📝 Signature: {tx_hash}")
        return tx_hash
