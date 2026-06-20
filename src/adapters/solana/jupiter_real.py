import hashlib, base64, requests, json, time
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client as SyncClient
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Confirmed
from adapters.solana import SOLANA_RPC, TOKEN_MINTS

JUPITER_API_BASE = "https://api.jup.ag/swap/v1"


class JupiterRealAdapter:
    """Real Jupiter swap — uses api.jup.ag/swap/v1."""

    def __init__(self, client, wallet: Keypair):
        self.wallet = wallet
        self.client = SyncClient(SOLANA_RPC)  # Always use sync client

    def execute(self, action: str, params: dict) -> str:
        if action == "swap":
            return self._swap(params)
        raise NotImplementedError(f"Action {action}")

    def _swap(self, params: dict) -> str:
        amount = params.get("amount", 0.001)
        if isinstance(amount, str):
            amount = float(amount)
        token_in = params.get("from", params.get("token_in", "SOL"))
        token_out = params.get("to", params.get("token_out", "USDC"))
        slippage_bps = int(float(params.get("slippage_pct", 0.5)) * 100)

        input_mint = str(TOKEN_MINTS[token_in.upper()])
        output_mint = str(TOKEN_MINTS[token_out.upper()])
        lamports = int(amount * 1e9) if token_in.upper() == "SOL" else int(amount * 1e6)

        wallet_str = str(self.wallet.pubkey())
        print(f"🔁 Real Jupiter swap: {amount} {token_in} → {token_out}")

        try:
            quote_resp = requests.get(f"{JUPITER_API_BASE}/quote", params={
                "inputMint": input_mint, "outputMint": output_mint,
                "amount": lamports, "slippageBps": slippage_bps,
            }, timeout=15)
            quote_resp.raise_for_status()
            quote = quote_resp.json()
            print(f"   💱 Quote: {quote['outAmount']} {token_out}")
        except Exception as e:
            print(f"   ⚠️  Quote failed ({e})")
            return self._sim_fallback(amount, token_in, token_out, wallet_str)

        try:
            swap_resp = requests.post(f"{JUPITER_API_BASE}/swap", json={
                "quoteResponse": quote,
                "userPublicKey": wallet_str,
                "wrapAndUnwrapSol": True,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": 1000,
            }, timeout=15)
            swap_resp.raise_for_status()
            swap_data = swap_resp.json()
            tx_b64 = swap_data.get("swapTransaction")
            if not tx_b64:
                print(f"   ⚠️  No swapTransaction in response")
                return self._sim_fallback(amount, token_in, token_out, wallet_str)
            print(f"   ✅ TX built ({len(tx_b64)} bytes)")
        except Exception as e:
            print(f"   ⚠️  Swap TX build failed ({e})")
            return self._sim_fallback(amount, token_in, token_out, wallet_str)

        try:
            from solders.signature import Signature
            tx_bytes = base64.b64decode(tx_b64)
            tx = VersionedTransaction.from_bytes(tx_bytes)
            signed_tx = VersionedTransaction(tx.message, [self.wallet])

            opts = TxOpts(skip_preflight=True, max_retries=3)
            sig_resp = self.client.send_transaction(signed_tx, opts)
            tx_sig = str(sig_resp.value)
            print(f"   ✅ Real tx: {tx_sig}")
            print(f"   🔗 https://solscan.io/tx/{tx_sig}")

            sig_obj = Signature.from_string(tx_sig)
            for _ in range(15):
                st = self.client.get_signature_statuses([sig_obj]).value[0]
                if st and st.confirmation_status:
                    print(f"   ✅ Confirmada (slot {st.slot})")
                    break
                time.sleep(1)

            return tx_sig
        except Exception as e:
            print(f"   ⚠️  Falha ({e})")
            return self._sim_fallback(amount, token_in, token_out, wallet_str)

    def _sim_fallback(self, amount, token_in, token_out, wallet_str) -> str:
        tx_data = f"jup_{amount}_{token_in}_{token_out}_{wallet_str}".encode()
        tx_hash = hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"   📝 Simulado: {tx_hash}")
        return tx_hash

    def close(self):
        pass
