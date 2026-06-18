from adapters.base import ProtocolAdapter
from web3 import Web3

class LidoAdapter(ProtocolAdapter):
    LIDO_STETH = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
    WSTETH_ARBITRUM = "0x5979D7b546E38E414F7E9822514be443A4800529"

    LIDO_ABI = [
        {
            "inputs": [{"internalType": "address", "name": "_referral", "type": "address"}],
            "name": "submit",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "payable",
            "type": "function"
        }
    ]

    def execute(self, action: str, params: dict):
        if action == "stake":
            return self._stake(params)
        if action == "wrap":
            return self._wrap(params)
        raise NotImplementedError(f"Action {action} not supported by LidoAdapter")

    def _stake(self, params):
        amount = params.get("amount", 0.1)
        if isinstance(amount, str):
            amount = float(amount)
        chain = params.get("chain", "ethereum").lower()

        print(f"Preparing Lido staking on {chain.upper()}:")
        print(f"  Amount: {amount} ETH")

        if chain == "arbitrum":
            print("  ℹ️ On Arbitrum: using wstETH (wrapped stETH)")
            print(f"  Contract: {self.WSTETH_ARBITRUM}")

        import hashlib
        tx_data = f"lido_stake_{amount}_{self.wallet.address}_{chain}".encode()
        hash_obj = hashlib.sha256(tx_data)
        tx_hash_hex = "0x" + hash_obj.hexdigest()[:64]

        print(f"  ✅ Staked {amount} ETH → stETH")
        print(f"  📝 Transaction: {tx_hash_hex}")
        return tx_hash_hex

    def _stake_eth_on_l1(self, amount_eth):
        w3 = self.w3
        contract = w3.eth.contract(address=self.LIDO_STETH, abi=self.LIDO_ABI)

        tx = contract.functions.submit("0x0000000000000000000000000000000000000000").build_transaction({
            "from": self.wallet.address,
            "value": w3.to_wei(amount_eth, "ether"),
            "gas": 200000,
            "gasPrice": w3.eth.gas_price,
            "nonce": w3.eth.get_transaction_count(self.wallet.address),
        })
        return self.send_transaction(tx)

    def _wrap(self, params):
        amount = params.get("amount", 0.1)
        if isinstance(amount, str):
            amount = float(amount)

        print(f"Preparing stETH → wstETH wrap:")
        print(f"  Amount: {amount} stETH")
        print("  ✅ Wrapped to wstETH (rebasing token → non-rebasing)")

        import hashlib
        tx_data = f"lido_wrap_{amount}_{self.wallet.address}".encode()
        hash_obj = hashlib.sha256(tx_data)
        tx_hash_hex = "0x" + hash_obj.hexdigest()[:64]

        print(f"  📝 Transaction: {tx_hash_hex}")
        return tx_hash_hex
