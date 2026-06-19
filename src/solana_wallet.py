import json
import base58
from pathlib import Path
from solders.keypair import Keypair


class SolanaWalletManager:
    def __init__(self, keystore_path="wallets"):
        self.keystore_path = Path(keystore_path)
        self.keystore_path.mkdir(exist_ok=True)

    def create_wallet(self, name: str) -> tuple:
        keypair = Keypair()
        wallet_data = {
            "secret_key": base58.b58encode(bytes(keypair)).decode(),
            "public_key": str(keypair.pubkey()),
        }
        filepath = self.keystore_path / f"{name}.sol.json"
        with open(filepath, "w") as f:
            json.dump(wallet_data, f)
        return keypair.pubkey(), keypair

    def load_wallet(self, name: str) -> Keypair:
        filepath = self.keystore_path / f"{name}.sol.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Solana wallet {name} not found")
        with open(filepath) as f:
            data = json.load(f)
        secret_bytes = base58.b58decode(data["secret_key"])
        return Keypair.from_bytes(secret_bytes)

    def list_wallets(self):
        return sorted([p.stem.replace(".sol", "") for p in self.keystore_path.glob("*.sol.json")])
