from abc import ABC, abstractmethod
from web3 import Web3

class ProtocolAdapter(ABC):
    def __init__(self, w3: Web3, wallet):
        self.w3 = w3
        self.wallet = wallet

    @abstractmethod
    async def execute(self, action: str, params: dict):
        pass

    def send_transaction(self, tx):
        # Sign and send transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet.key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return self.w3.to_hex(tx_hash)
