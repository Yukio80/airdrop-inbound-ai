"""
Central registry for multi-chain configuration.
Provides chain metadata, RPC URLs, token addresses, explorer APIs.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class ChainConfig:
    id: int
    name: str
    rpc: str
    explorer: str
    explorer_api: str
    explorer_key_env: str
    currency: str
    uniswap_v3_router: str
    uniswap_v3_factory: str
    uniswap_v3_quoter: str
    aave_pool: str
    weth: str
    usdc: str
    usdt: str
    native_wrapper: str  # WETH, WBNB, etc.
    testnet_rpc: str = ""
    testnet_explorer: str = ""
    testnet_chain_id: int = 0
    testnet_currency: str = ""
    priotity_tier: int = 1  # 1 = priority_1, 2 = priority_2


REGISTRY: Dict[str, ChainConfig] = {
    "arbitrum": ChainConfig(
        id=42161,
        name="Arbitrum",
        rpc=os.getenv("ARBITRUM_RPC_URL", "https://arb1.arbitrum.io/rpc"),
        explorer="https://arbiscan.io",
        explorer_api="https://api.arbiscan.io/api",
        explorer_key_env="ARBISCAN_API_KEY",
        currency="ETH",
        uniswap_v3_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        uniswap_v3_factory="0x1F98431c8aD98523631C44830bB6A3C0d5D64E43",
        uniswap_v3_quoter="0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
        aave_pool="0x794a61358D6845594F94dc1DB02A252b5b4814aD",
        weth="0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        usdc="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        usdt="0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        native_wrapper="0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        testnet_rpc="https://sepolia-rollup.arbitrum.io/rpc",
        testnet_explorer="https://sepolia.arbiscan.io",
        testnet_chain_id=421614,
        testnet_currency="ETH",
    ),
    "base": ChainConfig(
        id=8453,
        name="Base",
        rpc=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        explorer="https://basescan.org",
        explorer_api="https://api.basescan.org/api",
        explorer_key_env="ARBISCAN_API_KEY",
        currency="ETH",
        uniswap_v3_router="0x3fC91A3afd70395Cd496C647d5a6C2D633e63276",
        uniswap_v3_factory="0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
        uniswap_v3_quoter="0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a",
        aave_pool="0xA238Dd80C259a72e81d7e4664a9801593F98FdFE",
        weth="0x4200000000000000000000000000000000000006",
        usdc="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        usdt="0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
        native_wrapper="0x4200000000000000000000000000000000000006",
        testnet_rpc="https://sepolia.base.org",
        testnet_explorer="https://sepolia.basescan.org",
        testnet_chain_id=84532,
        testnet_currency="ETH",
        priotity_tier=1,
    ),
    "optimism": ChainConfig(
        id=10,
        name="Optimism",
        rpc=os.getenv("OPTIMISM_RPC_URL", "https://mainnet.optimism.io"),
        explorer="https://optimistic.etherscan.io",
        explorer_api="https://api-optimistic.etherscan.io/api",
        explorer_key_env="ARBISCAN_API_KEY",
        currency="ETH",
        uniswap_v3_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        uniswap_v3_factory="0x1F98431c8aD98523631C44830bB6A3C0d5D64E43",
        uniswap_v3_quoter="0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
        aave_pool="0x794a61358D6845594F94dc1DB02A252b5b4814aD",
        weth="0x4200000000000000000000000000000000000006",
        usdc="0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        usdt="0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
        native_wrapper="0x4200000000000000000000000000000000000006",
        testnet_rpc="https://sepolia.optimism.io",
        testnet_explorer="https://sepolia-optimism.etherscan.io",
        testnet_chain_id=11155420,
        testnet_currency="ETH",
        priotity_tier=2,
    ),
    "bsc": ChainConfig(
        id=56,
        name="BSC",
        rpc=os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org"),
        explorer="https://bscscan.com",
        explorer_api="https://api.bscscan.com/api",
        explorer_key_env="ARBISCAN_API_KEY",
        currency="BNB",
        uniswap_v3_router="",
        uniswap_v3_factory="",
        uniswap_v3_quoter="",
        aave_pool="",
        weth="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        usdc="0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        usdt="0x55d398326f99059fF775485246999027B3197955",
        native_wrapper="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        priotity_tier=2,
    ),
    "polygon": ChainConfig(
        id=137,
        name="Polygon",
        rpc=os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
        explorer="https://polygonscan.com",
        explorer_api="https://api.polygonscan.com/api",
        explorer_key_env="ARBISCAN_API_KEY",
        currency="POL",
        uniswap_v3_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        uniswap_v3_factory="0x1F98431c8aD98523631C44830bB6A3C0d5D64E43",
        uniswap_v3_quoter="0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
        aave_pool="0x794a61358D6845594F94dc1DB02A252b5b4814aD",
        weth="0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        usdc="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        usdt="0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        native_wrapper="0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        priotity_tier=2,
    ),
    "ethereum": ChainConfig(
        id=1,
        name="Ethereum",
        rpc=os.getenv("ETH_RPC_URL", "https://eth.llamarpc.com"),
        explorer="https://etherscan.io",
        explorer_api="https://api.etherscan.io/api",
        explorer_key_env="ARBISCAN_API_KEY",
        currency="ETH",
        uniswap_v3_router="0xE592427A0AEce92De3Edee1F18E0157C05861564",
        uniswap_v3_factory="0x1F98431c8aD98523631C44830bB6A3C0d5D64E43",
        uniswap_v3_quoter="0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
        aave_pool="0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
        weth="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        usdc="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        usdt="0xdAC17F958D2ee523a2206206994597C13D831ec7",
        native_wrapper="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        priotity_tier=1,
    ),
}

SUPPORTED_CHAINS = list(REGISTRY.keys())


def get_chain(name: str) -> Optional[ChainConfig]:
    return REGISTRY.get(name.lower())


def get_explorer_api_url(chain: str, module: str, action: str, **params) -> str:
    cfg = get_chain(chain)
    if not cfg:
        return ""
    api_key = os.getenv(cfg.explorer_key_env, "")
    url = f"{cfg.explorer_api}?module={module}&action={action}"
    for k, v in params.items():
        url += f"&{k}={v}"
    if api_key:
        url += f"&apikey={api_key}"
    return url


def list_chains() -> List[dict]:
    return [
        {
            "name": c.name,
            "id": c.id,
            "currency": c.currency,
            "explorer": c.explorer,
            "has_testnet": bool(c.testnet_rpc),
            "tier": c.priotity_tier,
        }
        for c in REGISTRY.values()
    ]
