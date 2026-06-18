import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from execution import GasOptimizer


def make_w3_mock(eip1559=True):
    w3 = MagicMock()
    w3.eth.gas_price = 30_000_000_000
    w3.to_wei = lambda val, unit: int(val * 1e9) if unit == "gwei" else int(val)
    if eip1559:
        w3.eth.get_block.return_value = {"baseFeePerGas": 25_000_000_000}
    else:
        w3.eth.get_block.return_value = {}
    return w3


class TestGasOptimizer:
    def test_eip1559_params(self):
        w3 = make_w3_mock(eip1559=True)
        opt = GasOptimizer(w3, "ethereum")
        params = opt.get_gas_params()
        assert "maxFeePerGas" in params
        assert "maxPriorityFeePerGas" in params
        assert params["maxFeePerGas"] == 31_250_000_000

    def test_legacy_fallback(self):
        w3 = make_w3_mock(eip1559=False)
        opt = GasOptimizer(w3, "arbitrum")
        params = opt.get_gas_params()
        assert "gasPrice" in params
        assert params["gasPrice"] == 30_000_000_000

    def test_gas_fetch_failure_returns_safe_default(self):
        w3 = MagicMock()
        w3.eth.get_block.side_effect = Exception("RPC timeout")
        w3.to_wei = lambda val, unit: int(val * 1e9)
        opt = GasOptimizer(w3, "ethereum")
        params = opt.get_gas_params()
        assert "gasPrice" in params
        assert params["gasPrice"] == 30_000_000_000

    def test_chain_id_mapping(self):
        assert GasOptimizer.CHAIN_IDS["ethereum"] == 1
        assert GasOptimizer.CHAIN_IDS["arbitrum"] == 42161
        assert GasOptimizer.CHAIN_IDS["base"] == 8453
