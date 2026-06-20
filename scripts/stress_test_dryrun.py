#!/usr/bin/env python3
"""
Stress test: runs all EVM adapters with dry_run=True and reports:
- Which adapters produced valid calldata / execution path
- Which raised exceptions
- Which returned empty/null calldata (silent failure)

Usage: python scripts/stress_test_dryrun.py
Output: reports/dryrun_{timestamp}.json
"""

import json
import os
import pathlib
import sys
import time
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from web3 import Web3
from eth_account import Account

ROOT = pathlib.Path(__file__).parent.parent
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Arbitrum token addresses
USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
WETH = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"

TEST_PARAMS = {
    "uniswap":  {"action": "swap", "token_in": WETH, "token_out": USDC, "amount": Decimal("0.0001")},
    "aave":     {"action": "supply", "token": USDC, "amount": Decimal("1.0")},
    "lido":     {"action": "stake", "amount": Decimal("0.001")},
    "compound": {"action": "supply", "amount": Decimal("1.0")},
    "curve":    {"action": "add_liquidity", "amount": 1000},
    "sushi":    {"action": "swap", "token_in": "WETH", "token_out": "USDC", "amount": Decimal("0.001"), "chain": "arbitrum"},
}


def _init_w3() -> tuple:
    """Create a disposable Web3 instance + random wallet for testing."""
    rpc = os.getenv("ARBITRUM_RPC_URL")
    if not rpc:
        return None, None
    w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
    wallet = Account.create()
    return w3, wallet


def _test_adapter(name: str, adapter_cls, params: dict) -> dict:
    """Run a single adapter dry-run and return the result."""
    w3, wallet = _init_w3()
    if w3 is None:
        return {"adapter": name, "status": "exception", "error": "ARBITRUM_RPC_URL not set", "duration_ms": 0}

    start = time.perf_counter()
    try:
        adapter = adapter_cls(w3, wallet)
        # Each adapter.execute accepts (action, params, dry_run=True)
        action = params.pop("action", name)
        result = adapter.execute(action, params, dry_run=True)
        elapsed = int((time.perf_counter() - start) * 1000)

        if result is None or result == "":
            return {
                "adapter": name,
                "status": "empty_calldata",
                "calldata_preview": None,
                "estimated_gas": None,
                "error": "empty calldata",
                "duration_ms": elapsed,
            }

        return {
            "adapter": name,
            "status": "ok",
            "calldata_preview": str(result)[:100],
            "estimated_gas": None,
            "error": None,
            "duration_ms": elapsed,
        }

    except Exception as e:
        elapsed = int((time.perf_counter() - start) * 1000)
        err_str = str(e)[:200]
        # Distinguish connection errors from adapter logic errors
        if "Connection" in err_str or "timeout" in err_str or "RPC" in err_str:
            status = "connection_error"
        else:
            status = "exception"
        return {
            "adapter": name,
            "status": status,
            "calldata_preview": None,
            "estimated_gas": None,
            "error": err_str,
            "duration_ms": elapsed,
        }


def _print_table(results: list):
    """Print a summary table in ASCII."""
    sep = "╠══════════╬══════════════╬══════════════╬════════════════════════════╣"
    top = "╔══════════════════════════════════════════════════════════════════════╗"
    header = "║              DRY-RUN STRESS TEST RESULTS                         ║"
    hline = "╠══════════╦══════════════╦══════════════╦════════════════════════════╣"
    col_h = "║ Adapter  ║ Status       ║ Duration(ms) ║ Error                      ║"
    bot = "╚══════════╩══════════════╩══════════════╩════════════════════════════╝"

    print()
    print(top)
    print(header)
    print(hline)
    print(col_h)
    print(hline)

    for r in results:
        status_icon = {
            "ok": "✅ ok",
            "exception": "❌ exception",
            "empty_calldata": "⚠️ empty",
            "connection_error": "🔴 conn_err",
        }.get(r["status"], r["status"])

        dur = str(r["duration_ms"]) if r["duration_ms"] is not None else "—"
        err = (r["error"] or "—")[:24]
        print(f"║ {r['adapter']:<8} ║ {status_icon:<12} ║ {dur:<12} ║ {err:<26} ║")

    print(bot)

    any_fail = any(r["status"] != "ok" for r in results)
    if any_fail:
        print("\n⚠️  Some adapters did not complete successfully.")
    else:
        print("\n✅ All adapters completed successfully.")
    print()


def main():
    results = []

    # Import adapters
    from adapters.uniswap import UniswapAdapter
    from adapters.aave import AaveAdapter
    from adapters.lido import LidoAdapter
    from adapters.compound import CompoundAdapter
    from adapters.curve import CurveAdapter
    from adapters.sushi import SushiAdapter

    ADAPTERS = [
        ("uniswap", UniswapAdapter),
        ("aave", AaveAdapter),
        ("lido", LidoAdapter),
        ("compound", CompoundAdapter),
        ("curve", CurveAdapter),
        ("sushi", SushiAdapter),
    ]

    for name, cls in ADAPTERS:
        params = dict(TEST_PARAMS[name])
        result = _test_adapter(name, cls, params)
        results.append(result)
        # Rate-limit between tests
        time.sleep(0.1)

    _print_table(results)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = REPORTS_DIR / f"dryrun_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"📝 Results saved to {out_path}")

    # Exit 1 if any adapter is not ok
    if any(r["status"] != "ok" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
