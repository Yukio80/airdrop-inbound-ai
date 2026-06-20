from adapters.base import BaseAdapter
from web3 import Web3

class LidoAdapter(BaseAdapter):
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

    WSTETH_ABI = [
        {
            "inputs": [{"internalType": "uint256", "name": "_amount", "type": "uint256"}],
            "name": "wrap",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

    def __init__(self, w3, wallet, config_path: str = "config.yaml"):
        super().__init__(w3, wallet, config_path)
        self.w3 = w3
        self.wallet = wallet

    def validate(self, **kwargs) -> bool:
        return True

    def dry_run(self, **kwargs) -> str:
        return "0x_dry_run_lido"

    def execute(self, action: str, params: dict, dry_run: bool = False):
        if action == "stake":
            return self._stake(params, dry_run)
        if action == "wrap":
            return self._wrap(params, dry_run)
        raise NotImplementedError(f"Action {action} not supported by LidoAdapter")

    def _stake(self, params, dry_run: bool = False):
        amount = params.get("amount", 0.1)
        if isinstance(amount, str):
            amount = float(amount)
        chain = params.get("chain", "ethereum").lower()

        if dry_run:
            print(f"  [DRY RUN] Lido stake {amount} ETH on {chain.upper()}")
            return "0x_dry_run_lido_stake"

        print(f"Executing real Lido staking on {chain.upper()}...")
        
        # For L1 stake
        contract = self.w3.eth.contract(address=self.LIDO_STETH, abi=self.LIDO_ABI)
        tx = contract.functions.submit("0x0000000000000000000000000000000000000000").build_transaction({
            "from": self.wallet.address,
            "value": self.w3.to_wei(amount, "ether"),
            "gas": 200000,
            "gasPrice": self.w3.eth.gas_price,
            "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"  ✅ Staked {amount} ETH → stETH")
        print(f"  📝 Transaction: {tx_hash.hex()}")
        return tx_hash.hex()

    def _wrap(self, params, dry_run: bool = False):
        amount = params.get("amount", 0.1)
        if isinstance(amount, str):
            amount = float(amount)

        if dry_run:
            print(f"  [DRY RUN] Lido wrap {amount} stETH → wstETH")
            return "0x_dry_run_lido_wrap"

        print(f"Executing real stETH → wstETH wrap on Arbitrum...")
        wsteth = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.WSTETH_ARBITRUM),
            abi=self.WSTETH_ABI
        )
        amount_wei = self.w3.to_wei(amount, "ether")

        tx = wsteth.functions.wrap(amount_wei).build_transaction({
            "from": self.wallet.address,
            "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
            "gasPrice": self.w3.eth.gas_price,
        })
        gas_estimate = self.w3.eth.estimate_gas(tx)
        tx["gas"] = gas_estimate

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f"  ✅ Wrapped {amount} stETH to wstETH")
        print(f"  📝 Transaction: {tx_hash.hex()}")
        return tx_hash.hex()
