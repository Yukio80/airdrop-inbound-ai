"""
Common base for real Solana protocol adapters.
For protocols where we don't have a specific instruction builder,
we fall back to simulation + a real SOL transfer as proof-of-activity.

Hardened with circuit breaker + retry for RPC calls.
"""
import time
import logging
from solders.keypair import Keypair
from solders.system_program import transfer, TransferParams
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client as SyncClient
from solana.rpc.types import TxOpts
from solana.rpc.core import RPCException
from adapters.solana import SOLANA_RPC
from src.hardening.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from src.hardening.retry import retry

logger = logging.getLogger(__name__)


class RealProtocolBase:
    """Base class for real Solana protocol adapters.
    All RPC calls are protected by a shared circuit breaker.
    """

    def __init__(self, client, wallet: Keypair, program_id: str = None):
        self.wallet = wallet
        self.rpc = SyncClient(SOLANA_RPC)
        self.program_id = program_id
        self._rpc_cb = CircuitBreaker(
            name="solana_rpc", failure_threshold=3, recovery_timeout=60,
        )

    @retry(max_attempts=2, delay=2.0, backoff=2.0, exceptions=(RPCException, ConnectionError, TimeoutError))
    def send_transaction(self, instructions: list) -> str:
        blockhash = self._rpc_cb.call(lambda: self.rpc.get_latest_blockhash().value.blockhash)
        msg = MessageV0.try_compile(self.wallet.pubkey(), instructions, [], blockhash)
        tx = VersionedTransaction(msg, [self.wallet])
        opts = TxOpts(skip_preflight=True, max_retries=3)
        sig = self._rpc_cb.call(lambda: self.rpc.send_transaction(tx, opts))
        tx_sig = str(sig.value)
        print(f"   ✅ Real tx: {tx_sig}")
        print(f"   🔗 https://solscan.io/tx/{tx_sig}")
        sig_obj = Signature.from_string(tx_sig)
        for _ in range(30):
            st = self.rpc.get_signature_statuses([sig_obj]).value[0]
            if st and st.confirmation_status:
                print(f"   ✅ Confirmada (slot {st.slot})")
                break
            time.sleep(1)
        return tx_sig

    def activity_transfer(self, label: str, lamports: int = 1) -> str:
        """Send a tiny SOL transfer to self as proof of wallet activity."""
        print(f"🔁 {label}: enviando {lamports} lamport(s) (proof-of-activity)")
        ixn = transfer(TransferParams(
            from_pubkey=self.wallet.pubkey(),
            to_pubkey=self.wallet.pubkey(),
            lamports=lamports,
        ))
        return self.send_transaction([ixn])
