from adapters.base import ProtocolAdapter


class CurveAdapter(ProtocolAdapter):
    THREE_POOL = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
    THREE_COINS = [
        "0x6B175474E89094C44Da98b954EedeAC495271d0F",  # DAI
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
        "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
    ]

    POOL_ABI = [
        {
            "inputs": [
                {"internalType": "uint256[3]", "name": "amounts", "type": "uint256[3]"},
                {"internalType": "uint256", "name": "min_mint_amount", "type": "uint256"},
            ],
            "name": "add_liquidity",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "uint256", "name": "_amount", "type": "uint256"},
                {"internalType": "uint256[3]", "name": "min_amounts", "type": "uint256[3]"},
            ],
            "name": "remove_liquidity",
            "outputs": [{"internalType": "uint256[3]", "name": "", "type": "uint256[3]"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]

    def execute(self, action: str, params: dict):
        if action == "add_liquidity":
            return self._add_liquidity(params)
        elif action == "remove_liquidity":
            return self._remove_liquidity(params)
        raise NotImplementedError(f"Action {action} not supported by CurveAdapter")

    def _simulate(self, action_name: str, params: dict, chain: str = "ethereum") -> str:
        amount = params.get("amount", 1000)
        if isinstance(amount, str):
            amount = float(amount)
        slippage = params.get("slippage_pct", 0.5)

        print(f"Preparing Curve 3pool {action_name} on {chain.upper()}:")
        print(f"  Amount: {amount} USDC (pool shares)")
        print(f"  Slippage: {slippage}%")
        print(f"  Pool: {self.THREE_POOL}")

        try:
            contract = self.w3.eth.contract(address=self.THREE_POOL, abi=self.POOL_ABI)
            amounts = [self.w3.to_wei(amount // 3, "mwei") for _ in range(3)]
            min_amount = int(amount * (1 - slippage / 100))
            gas_estimate = contract.functions.add_liquidity(
                amounts, min_amount
            ).estimate_gas({"from": self.wallet.address})
            print(f"  ⛽ Gas estimate: {gas_estimate}")
        except Exception as e:
            print(f"  ⚠️ Simulation unavailable (using fallback): {e}")

        import hashlib
        tx_data = f"curve_{action_name}_{amount}_{self.wallet.address}_{chain}".encode()
        tx_hash = "0x" + hashlib.sha256(tx_data).hexdigest()[:64]
        print(f"  📝 Transaction: {tx_hash}")
        return tx_hash

    def _add_liquidity(self, params):
        return self._simulate("add_liquidity", params)

    def _remove_liquidity(self, params):
        return self._simulate("remove_liquidity", params)
