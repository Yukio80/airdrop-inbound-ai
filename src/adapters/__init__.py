# Token resolver (mock for demo - in prod use DeFiLlama or 0x API)
TOKEN_ADDRESSES = {
    'ethereum': {
        'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
        'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    },
    'arbitrum': {
        'WETH': '0x82aF49447D8a07e3bd95BD0d56f365363aD3160e',
        'USDC': '0xaf88d065e77c8cc2239327a0744cea99e457dc4b',
        'USDT': '0xFd086bC68514b5b0b03Cf118c1e250a1572Fb6b4',
        'ARB': '0x912CE59144191C1204b16AcD8cDFEcacC258E085',
    },
    'base': {
        'WETH': '0x4200000000000000000000000000000000000006',
        'USDC': '0x833589fCD6fE2072CB0D953e5b1b63291cC7408d',
        'OP': '0x4200000000000000000000000000000000000042',
    },
}

UNISWAP_V3_ROUTERS = {
    'ethereum': '0xE592427A0AEce92De3Edee1F18E0157C05861564',
    'arbitrum': '0xE592427A0AEce92De3Edee1F18E0157C05861564',  # Same address on Arbitrum (Universal Router via Uniswap V3 interface)
    'base': '0x3fC91A3afd70395Cd496C647d5a6C2D633e63276',  # Base Uniswap V3 Router
}

# Uniswap V3 Router ABI (simplified - for production use the full ABI)
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
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
        ],
        "stateMutability": "payable",
        "type": "function"
    },
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
        "outputs": [
            {"internalType": "uint256", "name": "amountOut", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Function to get token address based on chain and symbol
def get_token_address(chain: str, symbol: str) -> str:
    return TOKEN_ADDRESSES.get(chain, {}).get(symbol.upper(), f"0x{symbol}" * 10)
