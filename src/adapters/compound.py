from adapters.base import BaseAdapter
from web3 import Web3

class CompoundAdapter(BaseAdapter):
    COMET_USDC = "0xc3d688B66703497DAA19211EEdff47f25384cdc3"
    COMP_TOKEN = "0xc00e94Cb662C3520282E6f5717214004A7f26888"

    COMET_ABI = [
        {
            "inputs": [
                {"internalType": "address", "name": "asset", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
            ],
            "name": "supply",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "asset", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
            ],
            "name": "withdraw",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [{"internalType": "address", "name": "src", "type": "address"}],
            "name": "claim",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]

    USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    def __init__(self, w3, wallet, config_path: str = "config.yaml"):
        super().__init__(w3, wallet, config_path)
        self.w3 = w3
        self.wallet = wallet

    def validate(self, **kwargs) -> bool:
        return True

    def dry_run(self, **kwargs) -> str:
        return "0x_dry_run_compound"

    def execute(self, action: str, params: dict, dry_run: bool = False):
        if action == "supply":
            return self._supply(params, dry_run)
        elif action == "withdraw":
            return self._withdraw(params, dry_run)
        elif action == "claim":
            return self._claim(params, dry_run)
        raise NotImplementedError(f"Action {action} not supported by CompoundAdapter")

    def _supply(self, params, dry_run: bool = False):
        amount = params.get("amount", 100)
        if isinstance(amount, str):
            amount = float(amount)

        if dry_run:
            print(f"  [DRY RUN] Compound V3 supply: {amount} USDC")
            return "0x_dry_run_compound_supply"

        print(f"Executing real Compound V3 supply...")
        contract = self.w3.eth.contract(address=self.COMET_USDC, abi=self.COMET_ABI)
        
        tx = contract.functions.supply(
            self.USDC_ADDRESS, self.w3.to_wei(amount, "mwei")
        ).build_transaction({
            "from": self.wallet.address,
            "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
            "gasPrice": self.w3.eth.gas_price,
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return tx_hash.hex()

    def _withdraw(self, params, dry_run: bool = False):
        amount = params.get("amount", 100)
        if isinstance(amount, str):
            amount = float(amount)
        
        if dry_run:
            print(f"  [DRY RUN] Compound V3 withdraw: {amount} USDC")
            return "0x_dry_run_compound_withdraw"

        print(f"Executing real Compound V3 withdraw...")
        contract = self.w3.eth.contract(address=self.COMET_USDC, abi=self.COMET_ABI)
        
        tx = contract.functions.withdraw(
            self.USDC_ADDRESS, self.w3.to_wei(amount, "mwei")
        ).build_transaction({
            "from": self.wallet.address,
            "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
            "gasPrice": self.w3.eth.gas_price,
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return tx_hash.hex()

    def _claim(self, params, dry_run: bool = False):
        if dry_run:
            print(f"  [DRY RUN] Compound V3 claim")
            return "0x_dry_run_compound_claim"

        print(f"Executing real Compound V3 COMP claim for {self.wallet.address[:8]}...")
        contract = self.w3.eth.contract(address=self.COMET_USDC, abi=self.COMET_ABI)

        tx = contract.functions.claim(
            self.wallet.address
        ).build_transaction({
            "from": self.wallet.address,
            "nonce": self.w3.eth.get_transaction_count(self.wallet.address),
            "gasPrice": self.w3.eth.gas_price,
        })
        gas_estimate = self.w3.eth.estimate_gas(tx)
        tx["gas"] = gas_estimate

        signed_tx = self.w3.eth.account.sign_transaction(tx, self.wallet)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"  ✅ Claim: {tx_hash.hex()}")
        return tx_hash.hex()
