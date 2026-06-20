#!/usr/bin/env python3
"""
Airdrop Inbound AI — Ecosystem CLI
Estrategia zero-cost: quests + testnets.

Comandos:
  dashboard   Painel completo com saldos, quests e transacoes
  scan        Escaneia quests (Galxe) + protocolos (DeFiLlama)
  farm        Roda testnet farm + on-chain farm (Solana)
  all         Executa scan + farm (ciclo completo)
  schedule    Agenda cron diario (Linux/macOS)
"""
import argparse
import asyncio
import json
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(ROOT / "src"))

EVM_ADDR = "0x50C905a210E5585B0F0124a0B53195f7Eb3d994C"
KEYSTORE_PASS = "231413"
KEYSTORE = ROOT / "wallets" / "user_real.json"
SOL_SCRIPT = ROOT / "solana_daily_farm.py"


def load_pk():
    from eth_account.account import Account

    with open(KEYSTORE) as f:
        ks = json.load(f)
    return Account.decrypt(ks, KEYSTORE_PASS).hex()


# ── DASHBOARD ──


def cmd_dashboard():
    from dashboard import show_dashboard

    show_dashboard()


# ── SCAN ──


async def cmd_scan():
    from discovery import OpportunityScanner
    from scoring import AirdropPredictor

    print("\n📡 Scan: Quests + Protocolos")
    print("=" * 50)

    print("\n🔍 Galxe Campaigns (persistent scan)...")
    from quests.galxe import run_galxe_scan
    result = run_galxe_scan(EVM_ADDR)
    print(f"   Total ativas:  {result['total']}")
    print(f"   Abertas:       {result['open']}")
    print(f"   Bloqueadas:    {result['blocked']}")
    if result["open_list"]:
        print(f"\n   🔓 Campanhas abertas encontradas:")
        for c in result["open_list"]:
            print(f"      {c['name'][:55]}")
            print(f"      https://galxe.com/campaign/{c['id']}")

    print("\n🔍 DeFiLlama Protocol Scanner...")
    scanner = OpportunityScanner()
    signals = await scanner.scan_all()
    sol_known = await scanner.scan_solana_known()
    merged = {s["protocol"].lower(): s for s in signals}
    for s in sol_known:
        k = s["protocol"].lower()
        if k not in merged:
            merged[k] = s
    merged = list(merged.values())

    pred = AirdropPredictor()
    print(f"\n   Protocolos encontrados: {len(merged)}")
    top = sorted(merged, key=lambda x: pred.calculate_score(x), reverse=True)[:15]
    print(f"\n   {'Protocolo':<25} {'Score':>6} {'Chain':>12}")
    print(f"   {'─' * 45}")
    for s in top:
        sc = pred.calculate_score(s)
        print(f"   {s['protocol'][:24]:<25} {sc:>6} {s.get('chain', '?'):>12}")

    print(f"\n   Total: {len(merged)} | Top 15 exibidos")
    print("\n✅ Scan concluido")
    return merged


# ── FARM ──


async def cmd_farm(dry_run=False):
    print("\n🧪 Testnet Farm")
    print("=" * 40)
    pk = load_pk()
    from quests.testnet_farm import TestnetFarm

    farm = TestnetFarm(pk)
    results = farm.farm_all()
    farm.print_results(results)

    # faucet guide
    from quests.faucet import check_and_guide

    check_and_guide()

    print("\n🌞 Solana Daily Farm")
    print("=" * 40)
    try:
        result = subprocess.run(
            [sys.executable, str(SOL_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(ROOT),
        )
        print(result.stdout)
        if result.stderr:
            print(f"   stderr: {result.stderr}")
    except FileNotFoundError:
        print("   ⚠️  solana_daily_farm.py nao encontrado")
    except subprocess.TimeoutExpired:
        print("   ⚠️  Solana farm excedeu tempo limite")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

    print("\n✅ Farm concluido")


# ── ALL ──


async def cmd_all(dry_run=False):
    print()
    print("=" * 55)
    print(f"🌱 Airdrop Inbound AI — Ciclo Completo {'(DRY RUN)' if dry_run else ''}")
    print("=" * 55)
    
    # 1. Balance Check & Bridge
    print("\n🌉 Checking Balance & Bridge...")
    try:
        from bridge.lifi_bridge import LiFiBridge
        bridge = LiFiBridge()
        bridge_res = bridge.check_and_bridge_if_needed(min_eth_balance=0.005, dry_run=dry_run)
        print(f"   Status: {bridge_res.status} | Bridged: {bridge_res.bridged}")
        if bridge_res.bridged:
            print(f"   Tx: {bridge_res.tx_hash}")
    except Exception as e:
        print(f"   ⚠️  Bridge skipped: {e}")
    
    await cmd_scan()

    # 2. Quest Farm
    print("\n🎯 Quest On-chain Tasks...")
    try:
        from quest_farm import run_quest_farm
        quest_results = await run_quest_farm(dry_run=dry_run)
        print(f"   Attempted: {quest_results['attempted']} | Completed: {quest_results['completed']} | Skipped: {quest_results['skipped']}")
    except Exception as e:
        print(f"   ⚠️  Quest farm error: {e}")

    await cmd_farm(dry_run=dry_run)
    print()
    print("=" * 55)
    print("✅ Ciclo completo executado com sucesso!")
    print("=" * 55)


# ── SCHEDULE ──


def cmd_schedule():
    cron_cmd = (
        f"0 8 * * * cd {ROOT} && {sys.executable} "
        f"{ROOT / 'ecosystem.py'} all >> {ROOT / 'logs' / 'daily.log'} 2>&1"
    )
    try:
        r = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=10
        )
        current = r.stdout if r.returncode == 0 else ""
        if cron_cmd in current or "ecosystem.py" in current:
            print("✅ Cron ja agendado para 08:00 diario")
            return
        new_cron = current.strip() + "\n" + cron_cmd + "\n"
        p = subprocess.Popen(
            ["crontab"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p.communicate(input=new_cron.encode(), timeout=10)
        print("✅ Cron agendado: 08:00 todos os dias")
        print(f"   Comando: {cron_cmd}")
    except FileNotFoundError:
        print("⚠️  crontab nao encontrado (SO nao suportado?)")
        print("   Adicione manualmente ao crontab:")
        print(f"   {cron_cmd}")
    except Exception as e:
        print(f"⚠️  Erro ao agendar cron: {e}")


# ── MAIN ──


def main():
    parser = argparse.ArgumentParser(
        description="🌱 Airdrop Inbound AI — Ecosystem CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Exemplos:
              python3 ecosystem.py dashboard
              python3 ecosystem.py scan
              python3 ecosystem.py farm
              python3 ecosystem.py all
              python3 ecosystem.py schedule
              python3 ecosystem.py audit
              python3 ecosystem.py dryrun
        """),
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["dashboard", "scan", "farm", "all", "schedule", "audit", "dryrun"],
        help="Comando a executar",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate transactions without broadcasting",
    )
    args, remaining = parser.parse_known_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    (ROOT / "logs").mkdir(exist_ok=True)

    if args.command == "dashboard":
        cmd_dashboard()
    elif args.command == "schedule":
        cmd_schedule()
    elif args.command == "scan":
        asyncio.run(cmd_scan())
    elif args.command == "farm":
        asyncio.run(cmd_farm(dry_run=args.dry_run))
    elif args.command == "all":
        asyncio.run(cmd_all(dry_run=args.dry_run))
    elif args.command == "audit":
        from scripts.run_audit import main as audit_main
        sys.argv = [sys.argv[0]] + remaining
        audit_main()
    elif args.command == "dryrun":
        from scripts.stress_test_dryrun import main as dryrun_main
        dryrun_main()


if __name__ == "__main__":
    main()
