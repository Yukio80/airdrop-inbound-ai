"""
SolanaRealClient — helper for building, signing, sending, and confirming
real Solana transactions from a Keypair.
"""
import time, base64
from solders.keypair import Keypair
from solders.instruction import Instruction, AccountMeta
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.signature import Signature
from solders.pubkey import Pubkey
from solana.rpc.api import Client as SyncClient
from solana.rpc.types import TxOpts
from adapters.solana import SOLANA_RPC


class SolanaRealClient:
    def __init__(self, wallet: Keypair, rpc: str = SOLANA_RPC):
        self.wallet = wallet
        self.client = SyncClient(rpc)

    def get_blockhash(self) -> str:
        return self.client.get_latest_blockhash().value.blockhash

    def build_and_send(self, instructions: list[Instruction], signers: list[Keypair] | None = None) -> str:
        """Build, sign, send, and confirm a transaction."""
        blockhash = self.get_blockhash()
        msg = MessageV0.try_compile(
            self.wallet.pubkey(),
            instructions,
            [],
            blockhash,
        )
        all_signers = signers or [self.wallet]
        tx = VersionedTransaction(msg, all_signers)

        opts = TxOpts(skip_preflight=True, max_retries=3)
        sig_resp = self.client.send_transaction(tx, opts)
        tx_sig = str(sig_resp.value)

        print(f"   ✅ Real tx: {tx_sig}")
        print(f"   🔗 https://solscan.io/tx/{tx_sig}")

        # Wait for confirmation
        sig_obj = Signature.from_string(tx_sig)
        for _ in range(30):
            st = self.client.get_signature_statuses([sig_obj]).value[0]
            if st and st.confirmation_status:
                print(f"   ✅ Confirmada (slot {st.slot})")
                break
            time.sleep(1)

        return tx_sig

    def simulate(self, instructions: list[Instruction]) -> bool:
        """Dry-run to check if instructions would succeed."""
        blockhash = self.get_blockhash()
        msg = MessageV0.try_compile(self.wallet.pubkey(), instructions, [], blockhash)
        tx = VersionedTransaction(msg, [self.wallet])
        resp = self.client.simulate_transaction(tx)
        err = resp.value.err
        if err:
            print(f"   ⚠️  Simulate error: {err}")
            return False
        return True

    def lamports(self, sol: float) -> int:
        return int(sol * 1e9)
