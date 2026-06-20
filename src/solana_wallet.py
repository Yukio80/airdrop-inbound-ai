import json
import base58
from pathlib import Path
from solders.keypair import Keypair
from solders.pubkey import Pubkey


class ReadOnlyWallet:
    """Wallet wrapper for pubkey-only simulation (no private key)."""
    def __init__(self, address: str):
        self._pubkey = Pubkey.from_string(address)

    def pubkey(self):
        return self._pubkey

    def __str__(self):
        return str(self._pubkey)


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

    def load_wallet(self, name: str):
        """Load wallet. Supports both keypair (with secret_key) and pubkey-only."""
        # Try .sol.json first (keypair), then .json (pubkey-only)
        filepath = self.keystore_path / f"{name}.sol.json"
        if not filepath.exists():
            filepath = self.keystore_path / f"{name}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"Solana wallet {name} not found")

        with open(filepath) as f:
            data = json.load(f)

        if "secret_key" in data:
            secret_bytes = base58.b58decode(data["secret_key"])
            return Keypair.from_bytes(secret_bytes)

        # Pubkey-only wallet (read-only simulation)
        addr = data.get("address") or data.get("public_key")
        if not addr:
            raise ValueError(f"No address found in {filepath}")
        print(f"  ℹ️  Read-only wallet {addr} (simulation mode)")
        return ReadOnlyWallet(addr)

    def list_wallets(self):
        sol_files = list(self.keystore_path.glob("*.sol.json"))
        json_files = [f for f in self.keystore_path.glob("*.json") if f.stem != "solana_real"]
        return sorted(
            [p.stem.replace(".sol", "") for p in sol_files] +
            [p.stem for p in json_files]
        )
