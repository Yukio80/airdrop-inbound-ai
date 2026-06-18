from adapters.base import ProtocolAdapter
from web3 import Web3
import json
from pathlib import Path

# Token resolver (mock for demo - in prod use DeFiLlama or 0x API)
TOKEN_ADDRESSES = {
    'ethereum': {
        'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
        'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    },
    'arbitrum': {
        'WETH': '0x82aF49447D8a07e3bd95BD0d56f365363aAD3160e',
        'USDC': '0xaf88d065e77c8cc2239327a0744cea99e457dc4b',
        'USDT': '0xFd086bC68514b5b0b03Cf118c1e250a1572Fb6b4',
        'ARB': '0x912CE59144191C1204b16AcD8cDFEcacC258E085',
        'WBTC': '0x2f2a67c06109e0a2c6e7a08f3adc9e3a3ae7bc8a',
    },
    'base': {
        'WETH': '0x4200000000000000000000000000000000000006',
        'USDC': '0x833589fCD6fE2072CB0D953e5b1b63291cC7408d',
        'OP': '0x4200000000000000000000000000000000000042',
    },
}

# Load Uniswap V3 Router ABI
UNISWAP_V3_ROUTER_ABI_PATH = Path(__file__).parent / "uniswap_v3_router_abi.json"
if UNISWAP_V3_ROUTER_ABI_PATH.exists():
    with open(UNISWAP_V3_ROUTER_ABI_PATH) as f:
        UNISWAP_V3_ROUTER_ABI = json.load(f)
else:
    # Fallback to minimal ABI
    UNISWAP_V3_ROUTER_ABI = [
        {
            "inputs": [
                {"internalType": "address", "name": "tokenIn", "type": "address"},
                {"internalType": "address", "name": "tokenOut", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"},
                {"internalType": "address", "name": "recipient", "type": "address"},
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "uint256", "name": "amountOutMinimum", "type": "uint256"},
                {"internalType": "uint160", "name": "sqrtPriceLimitX96", "type": "uint160"}
            ],
            "name": "exactInputSingle",
            "outputs": [{"internalType": "uint256", "name": "amountOut", "type": "uint256"}],
            "stateMutability": "payable",
            "type": "function"
        }
    ]

# Function to get token address based on chain and symbol
def get_token_address(chain: str, symbol: str) -> str:
    return TOKEN_ADDRESSES.get(chain, {}).get(symbol.upper(), f"0x{symbol}" * 10)

class UniswapAdapter(ProtocolAdapter):
    # Uniswap V3 Router Address - in production, this should be configurable per chain
    # Defaulting to Arbitrum (common choice for farming)
    ROUTER_ADDRESS = "0xE592427A0AEce92De3Edee1F18E0157C05861564"

    # Token resolution - in production, use a more robust mapping
    # Source: https://www.uniswap.org/docs/v3/guides/tokens/
    TOKENS = {
        'arbitrum': {
            'WETH': '0x82aF49447D8a07e3bd95BD0d56f365363aAD3160e',
            'USDC': '0xaf88d065e77c8cc2239327a0744cea99e457dc4b',
            'USDT': '0xFd086bC68514b5b0b03Cf118c1e250a1572Fb6b4',
            'ARB': '0x912CE59144191C1204b16AcD8cDFEcacC258E085',
            'WBTC': '0x2f2a67c06109e0a2c6e7a08f3adc9e3a3ae7bc8a',
        }
    }

    def execute(self, action: str, params: dict):
        if action == "swap":
            return self._swap(params)
        raise NotImplementedError(f"Action {action} not supported by UniswapAdapter")

    def _swap(self, params):
        # Extract parameters
        amount_in = params.get("amount", 0.1)
        if isinstance(amount_in, str):
            amount_in = float(amount_in)
        
        token_in_symbol = params.get("token_in", "WETH")
        token_out_symbol = params.get("token_out", "USDC")
        chain = params.get("chain", "arbitrum")
        
        print(f"Preparing Uniswap V3 swap on {chain.upper()}:")
        print(f"  Path: {token_in_symbol} → {token_out_symbol}")
        print(f"  Amount: {amount_in} tokens")
        
        # Create a simulated transaction hash instead of actually calling the contract
        import hashlib
        
        # Create a deterministic transaction hash based on the parameters
        tx_data = f"{token_in_symbol}_{token_out_symbol}_{amount_in}_{self.wallet.address}".encode()
        hash_obj = hashlib.sha256(tx_data)
        tx_hash_hex = "0x" + hash_obj.hexdigest()[:64]
        
        print(f"  📝 Simulated transaction submitted: {tx_hash_hex}")
        print(f"  🔍 View on Arbiscan: https://arbiscan.io/tx/{tx_hash_hex}")
        
        return tx_hash_hex
