#!/usr/bin/env python3
"""CLI entrypoint for on-chain footprint audit.

Usage:
  python scripts/run_audit.py            # full report
  python scripts/run_audit.py --evm-only
  python scripts/run_audit.py --solana-only
  python scripts/run_audit.py --reconcile
"""

import argparse
import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

from audit.footprint import FootprintAuditor


def main():
    parser = argparse.ArgumentParser(description="On-chain footprint auditor")
    parser.add_argument("--evm-only", action="store_true", help="Audit EVM wallets only")
    parser.add_argument("--solana-only", action="store_true", help="Audit Solana wallet only")
    parser.add_argument("--reconcile", action="store_true", help="Cross-reference DB with on-chain data only")
    args = parser.parse_args()

    auditor = FootprintAuditor()

    if args.evm_only:
        for w in auditor.evm_wallets:
            result = auditor.audit_evm(w)
            print(json.dumps(result, indent=2, default=str))
    elif args.solana_only:
        result = auditor.audit_solana()
        print(json.dumps(result, indent=2, default=str))
    elif args.reconcile:
        for w in auditor.evm_wallets:
            result = auditor.reconcile(w, "arbitrum")
            print(json.dumps(result, indent=2, default=str))
    else:
        report = auditor.full_report()
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
