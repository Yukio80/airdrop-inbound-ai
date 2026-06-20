import pytest
from unittest.mock import Mock, patch
from web3 import Web3
from eth_account import Account

from adapters.compound import CompoundAdapter
from adapters.curve import CurveAdapter
from adapters.sushi import SushiAdapter


@pytest.fixture
def w3():
    return Web3(Web3.HTTPProvider("https://eth.llamarpc.com"))


@pytest.fixture
def wallet():
    return Account.create()


class TestCompoundAdapter:
    def test_supply_returns_tx_hash(self, w3, wallet):
        adapter = CompoundAdapter(w3, wallet)
        tx = adapter.execute("supply", {"amount": 100}, dry_run=True)
        assert tx.startswith("0x")

    def test_withdraw_returns_tx_hash(self, w3, wallet):
        adapter = CompoundAdapter(w3, wallet)
        tx = adapter.execute("withdraw", {"amount": 50}, dry_run=True)
        assert tx.startswith("0x")

    def test_claim_returns_tx_hash(self, w3, wallet):
        adapter = CompoundAdapter(w3, wallet)
        tx = adapter.execute("claim", {}, dry_run=True)
        assert tx.startswith("0x")

    def test_unsupported_action_raises(self, w3, wallet):
        adapter = CompoundAdapter(w3, wallet)
        with pytest.raises(NotImplementedError):
            adapter.execute("stake", {})


class TestCurveAdapter:
    def test_add_liquidity_returns_tx_hash(self, w3, wallet):
        adapter = CurveAdapter(w3, wallet)
        tx = adapter.execute("add_liquidity", {"amount": 1000, "slippage_pct": 0.5}, dry_run=True)
        assert tx.startswith("0x")

    def test_remove_liquidity_returns_tx_hash(self, w3, wallet):
        adapter = CurveAdapter(w3, wallet)
        tx = adapter.execute("remove_liquidity", {"amount": 500}, dry_run=True)
        assert tx.startswith("0x")

    def test_unsupported_action_raises(self, w3, wallet):
        adapter = CurveAdapter(w3, wallet)
        with pytest.raises(NotImplementedError):
            adapter.execute("swap", {})


class TestSushiAdapter:
    def test_swap_ethereum_returns_tx_hash(self, w3, wallet):
        adapter = SushiAdapter(w3, wallet)
        tx = adapter.execute("swap", {
            "amount": 0.1, "token_in": "WETH", "token_out": "USDC",
            "chain": "ethereum", "slippage_pct": 0.5, "gas_limit": 300000,
        }, dry_run=True)
        assert tx.startswith("0x")

    def test_swap_arbitrum_returns_tx_hash(self, w3, wallet):
        adapter = SushiAdapter(w3, wallet)
        tx = adapter.execute("swap", {
            "amount": 0.1, "token_in": "WETH", "token_out": "USDC",
            "chain": "arbitrum",
        }, dry_run=True)
        assert tx.startswith("0x")

    def test_unsupported_chain_raises(self, w3, wallet):
        adapter = SushiAdapter(w3, wallet)
        with pytest.raises(ValueError, match="Unsupported chain"):
            adapter.execute("swap", {
                "amount": 0.1, "token_in": "WETH", "token_out": "USDC",
                "chain": "invalid",
            })

    def test_unsupported_action_raises(self, w3, wallet):
        adapter = SushiAdapter(w3, wallet)
        with pytest.raises(NotImplementedError):
            adapter.execute("stake", {})
