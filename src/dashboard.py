"""Terminal dashboard — painel de controle do Airdrop Inbound AI."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from web3 import Web3
from solana.rpc.api import Client as SolanaClient
from solders.pubkey import Pubkey

ROOT = Path(__file__).parent.parent
DB = ROOT / "airdrop_bot.db"
EVM_ADDR = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"
SOL_KEYSTORE = ROOT / "wallets" / "solana_real.sol.json"

EVM_RPCS = {
    "Arbitrum": ("https://arb1.arbitrum.io/rpc", "ETH"),
    "BSC": ("https://bsc-dataseed.binance.org", "BNB"),
    "Ethereum": ("https://eth.llamarpc.com", "ETH"),
    "Sepolia": ("https://ethereum-sepolia.publicnode.com", "ETH"),
    "Hoodi": ("https://ethereum-hoodi-rpc.publicnode.com", "ETH"),
    "Amoy": ("https://rpc-amoy.polygon.technology", "POL"),
}

TESTNETS = {"Sepolia", "Holesky", "Amoy"}
SOL_RPC = "https://api.mainnet-beta.solana.com"

ERC20_ABI = json.loads(
    '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"type":"uint8"}],"type":"function"}]'
)
USDT_ARB = "0xFd086bC68514b5b0b03Cf118c1e250a1572Fb6b4"


def _sol_addr():
    try:
        with open(SOL_KEYSTORE) as f:
            d = json.load(f)
        return d.get("public_key") or d.get("address")
    except Exception:
        return None


def _evm_bal(rpc, addr, token=None):
    try:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 8}))
        if not w3.is_connected():
            return None, None
        bal = w3.eth.get_balance(addr)
        native = bal / 1e18
        tok = None
        if token:
            c = w3.eth.contract(address=Web3.to_checksum_address(token), abi=ERC20_ABI)
            dec = c.functions.decimals().call()
            tok = c.functions.balanceOf(addr).call() / 10**dec
        return native, tok
    except Exception:
        return None, None


def _sol_bal():
    addr = _sol_addr()
    if not addr:
        return None
    try:
        c = SolanaClient(SOL_RPC)
        resp = c.get_balance(Pubkey.from_string(addr))
        if hasattr(resp, "value"):
            return resp.value / 1e9
        return resp.get("result", {}).get("value", 0) / 1e9
    except Exception:
        return None


def _cron_status():
    try:
        r = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and "ecosystem.py" in r.stdout:
            for line in r.stdout.splitlines():
                if "ecosystem.py" in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        return f"{parts[1]}:{parts[0]}"
            return "agendado"
        return "não agendado"
    except Exception:
        return "n/d"


def _count_eligible(g, camps):
    e = 0
    for c in camps:
        try:
            elig = g.check_eligibility(c["id"], EVM_ADDR)
            camp = elig.get("data", {}).get("campaign")
            if camp and camp.get("credentialGroups"):
                if any(
                    any(cond.get("eligible") for cond in grp.get("conditions", []))
                    for grp in camp["credentialGroups"]
                ):
                    e += 1
        except Exception:
            pass
    return e


def _get_integrity_report():
    """Query SQLite for execution integrity metrics."""
    import datetime as dt
    try:
        conn = sqlite3.connect(str(DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        now = dt.datetime.now()
        cut_7d = (now - dt.timedelta(days=7)).isoformat()
        cut_30d = (now - dt.timedelta(days=30)).isoformat()

        rows_7d = cursor.execute(
            "SELECT tx_hash, protocol, status FROM transactions WHERE timestamp >= ?",
            (cut_7d,)
        ).fetchall()
        rows_30d = cursor.execute(
            "SELECT tx_hash, protocol, status FROM transactions WHERE timestamp >= ?",
            (cut_30d,)
        ).fetchall()

        conn.close()

        def classify(rows):
            real = 0
            sim = 0
            failed = 0
            active_protocols = set()
            for r in rows:
                h = r["tx_hash"] or ""
                if h.startswith("0x_error"):
                    failed += 1
                elif h.startswith("0x_sim") or h == "":
                    sim += 1
                elif h.startswith("0x_"):
                    sim += 1
                else:
                    real += 1
                    if r["protocol"]:
                        active_protocols.add(r["protocol"].lower())
            return real, sim, failed, active_protocols

        real_7d, sim_7d, failed_7d, active_7d = classify(rows_7d)
        real_30d, sim_30d, failed_30d, active_30d = classify(rows_30d)
        total_30d = real_30d + sim_30d + failed_30d

        known_adapters = {"uniswap", "aave", "lido", "compound", "curve", "sushi"}
        no_activity = sorted(known_adapters - active_30d)

        return {
            "real_7d": real_7d,
            "sim_7d": sim_7d,
            "failed_7d": failed_7d,
            "real_30d": real_30d,
            "sim_30d": sim_30d,
            "failed_30d": failed_30d,
            "total_30d": total_30d,
            "rate_7d": (real_7d / (real_7d + sim_7d + failed_7d) * 100) if (real_7d + sim_7d + failed_7d) > 0 else 0,
            "no_activity_30d": no_activity,
        }
    except Exception as e:
        return {"error": str(e)}

def show_dashboard():
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           Airdrop Inbound AI — Painel de Controle           ║")
    print(f"║                     {now:^44}║")
    print("╚══════════════════════════════════════════════════════════════╝")
    
    # ... (Saldos EVM, Solana, Galxe sections) ...
    # (I will insert the integrity section at the end)

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║           Airdrop Inbound AI — Painel de Controle           ║")
    print(f"║                     {now:^44}║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # EVM
    print("\n 📦 Saldos EVM")
    print(" ──────────────────────────────────────────────────────")
    print(f"  Carteira: {EVM_ADDR[:8]}...{EVM_ADDR[-4:]}")
    for chain, (rpc, native) in EVM_RPCS.items():
        bal, tok = _evm_bal(rpc, EVM_ADDR, USDT_ARB if chain == "Arbitrum" else None)
        if bal is None:
            print(f"    {chain:<10} ⚠️  erro de conexão")
        elif bal < 0.0001 and chain in TESTNETS:
            print(f"    {chain:<10} {bal:.6f} {native}  ⛔ sem fundos")
        else:
            parts = [f"    {chain:<10} {bal:.6f} {native}"]
            if tok is not None:
                parts.append(f"  USDT: {tok:.4f}")
            print("".join(parts))

    # Solana
    sol_addr = _sol_addr()
    sol_bal = _sol_bal()
    print("\n 🌞 Saldo Solana")
    print(" ──────────────────────────────────────────────────────")
    if sol_addr:
        print(f"  Carteira: {sol_addr[:8]}...{sol_addr[-4:]}")
        if sol_bal is not None:
            print(f"    SOL      {sol_bal:.6f}")
        else:
            print(f"    SOL      ⚠️  erro de conexão")
    else:
        print("  Carteira não encontrada")

    # Galxe
    print("\n 🎯 Galxe Quests")
    print(" ──────────────────────────────────────────────────────")
    try:
        from utils.db_manager import DatabaseManager
        scan = DatabaseManager(str(DB)).get_last_galxe_scan()
        if scan:
            print(f"  Último scan:       {scan['timestamp'][:19]}")
            print(f"  Campanhas ativas:  {scan['total']}")
            print(f"  Elegíveis (abertas): {scan['open_count']}")
            print(f"  Bloqueadas:        {scan['blocked']}")
            if scan["open_list"]:
                for c in scan["open_list"][:5]:
                    print(f"    🔓 {c['name'][:50]}")
                    print(f"       https://galxe.com/campaign/{c['id']}")
                if len(scan["open_list"]) > 5:
                    print(f"    ... +{len(scan['open_list'])-5} mais")
        else:
            from quests.galxe import GalxeClient
            g = GalxeClient()
            camps = g.active_campaigns(first=50)
            print(f"  Campanhas ativas:  {len(camps)}")
    except Exception as e:
        print(f"  ⚠️  {e}")

    # Transactions
    print("\n 📜 Últimas Transações")
    print(" ──────────────────────────────────────────────────────")
    try:
        conn = sqlite3.connect(str(DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT timestamp, protocol, action, tx_hash FROM transactions ORDER BY timestamp DESC LIMIT 8"
        ).fetchall()
        conn.close()
        if rows:
            for r in rows:
                ts = r["timestamp"][:19] if r["timestamp"] else "?"
                proto = r["protocol"][:12].ljust(12)
                act = r["action"][:10].ljust(10)
                tx = (
                    r["tx_hash"][:10] + "..."
                    if r["tx_hash"] and len(r["tx_hash"]) > 10
                    else r["tx_hash"]
                )
                print(f"  {ts}  {proto} {act} {tx}")
        else:
            print("  Nenhuma transação registrada ainda")
    except Exception as e:
        print(f"  ⚠️  {e}")

    # Status
    print("\n 📊 Status do Farm")
    print(" ──────────────────────────────────────────────────────")
    try:
        conn = sqlite3.connect(str(DB))
        tx_cnt = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        last_tx = conn.execute(
            "SELECT MAX(timestamp) FROM transactions"
        ).fetchone()[0]
        execd = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE status='executed'"
        ).fetchone()[0]
        pend = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE status='pending'"
        ).fetchone()[0]
        conn.close()
        print(f"  Transações totais:     {tx_cnt}")
        print(f"  Protocolos farmados:   {execd}")
        print(f"  Pendentes:             {pend}")
        print(
            f"  Última transação:      {last_tx[:19] if last_tx else 'nunca'}"
        )
    except Exception as e:
        print(f"  ⚠️  {e}")

    # Integrity
    print("\n 🛡️  EXECUTION INTEGRITY")
    print(" ──────────────────────────────────────────────────────")
    report = _get_integrity_report()
    if "error" in report:
        print(f"  ⚠️  Error: {report['error']}")
    else:
        print(f"  Real txs (7d):        {report['real_7d']:>4}   ✅")
        print(f"  Simulated calls (7d): {report['sim_7d']:>4}   ⚠️")
        print(f"  Failed txs (7d):      {report['failed_7d']:>4}   {'🔴' if report['failed_7d'] > 0 else '✅'}")
        print(f"  Real txs (30d):       {report['real_30d']:>4}")
        if report["no_activity_30d"]:
            print(f"  Adapters no real tx (30d): {', '.join(report['no_activity_30d'])}   ⚠️")
        else:
            print(f"  Adapters no real tx (30d): none   ✅")
    
    cr = _cron_status()
    print(f"\n  Cron diário:           {cr}")
    print()
    print(f"  💡 Dica: Rode  python3 ecosystem.py all  para ciclo completo")
    print()


if __name__ == "__main__":
    show_dashboard()
