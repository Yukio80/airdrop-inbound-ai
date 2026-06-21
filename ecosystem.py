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
import logging
import subprocess
import sys
import textwrap
from pathlib import Path
from solders.keypair import Keypair

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

    # 0. Yield Optimizer
    if not dry_run:
        print("\n💰 Yield Optimizer...")
        try:
            from src.yield_optimizer.optimizer import YieldOptimizer
            yield_report = YieldOptimizer(dry_run=False).run(
                wallet_evm=EVM_ADDR,
                wallet_solana_path="wallets/solana_real.sol.json"
            )
            log = logging.getLogger("ecosystem")
            log.info(f"Yield optimizer: {len(yield_report['rebalanced'])} rebalance(s), "
                     f"est. annual gain ${yield_report['estimated_annual_gain_usd']:.2f}")
            if yield_report["rebalanced"]:
                for r in yield_report["rebalanced"]:
                    print(f"   {r['asset']}: {r['from_protocol']} → {r['to_protocol']}  ({r['status']})")
            else:
                print("   No rebalances needed")
        except Exception as e:
            print(f"   ⚠️  Yield optimizer skipped: {e}")

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

    # State tracking for restart resilience
    from src.hardening.state_machine import StateMachine
    state = StateMachine()
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("cycle_date") != today:
        state.reset_steps()
        state.set("cycle_date", today)
        state.set("cycle_count", state.get("cycle_count", 0) + 1)
    state.last_run = datetime.now().isoformat()
    
    # 1. Balance Check & Bridge
    if not state.is_step_complete("bridge_check"):
        print("\n🌉 Checking Balance & Bridge...")
        try:
            from src.bridge.lifi_bridge import LiFiBridge
            bridge = LiFiBridge()
            bridge_res = bridge.check_and_bridge_if_needed(min_eth_balance=0.005, dry_run=dry_run)
            print(f"   Status: {bridge_res.status} | Bridged: {bridge_res.bridged}")
            if bridge_res.bridged:
                print(f"   Tx: {bridge_res.tx_hash}")
        except Exception as e:
            print(f"   ⚠️  Bridge skipped: {e}")
        if not dry_run:
            state.mark_step_complete("bridge_check")

    # LZ Volume Cadencer
    if not state.is_step_complete("lz_bridge"):
        try:
            from src.bridge.lz_cadencer import LZCadencer
            lz = LZCadencer()
            lz_result = lz.execute_bridge(dry_run=dry_run)
            if lz_result.get("success"):
                import logging
                log = logging.getLogger("ecosystem")
                log.info(f"LZ bridge: {lz_result['from_chain']} → {lz_result['to_chain']} ${lz_result['amount_usdc']:.2f}")
                print(f"   ✅ LZ Bridge: {lz_result['from_chain']} → {lz_result['to_chain']} ${lz_result['amount_usdc']:.2f}")
            else:
                print(f"   ⏸ LZ bridge skipped: {lz_result.get('reason', 'unknown')}")
        except Exception as e:
            print(f"   ⚠️  LZ Cadencer error: {e}")
        if not dry_run:
            state.mark_step_complete("lz_bridge")

    if not state.is_step_complete("scan"):
        await cmd_scan()
        if not dry_run:
            state.mark_step_complete("scan")

    # 2. Quest Farm
    if not state.is_step_complete("quest_farm"):
        print("\n🎯 Quest On-chain Tasks...")
        try:
            from quest_farm import run_quest_farm
            quest_results = await run_quest_farm(dry_run=dry_run)
            print(f"   Attempted: {quest_results['attempted']} | Completed: {quest_results['completed']} | Skipped: {quest_results['skipped']}")
        except Exception as e:
            print(f"   ⚠️  Quest farm error: {e}")
        if not dry_run:
            state.mark_step_complete("quest_farm")

    if not state.is_step_complete("farm"):
        await cmd_farm(dry_run=dry_run)
        if not dry_run:
            state.mark_step_complete("farm")

    # 3. Alert Checks
    if not state.is_step_complete("alerts"):
        print("\n\U0001f514 Alert Checks...")
        try:
            from src.intelligence.alert_engine import AlertEngine
            alert_engine = AlertEngine()
            signals_list = []
            from src.utils.db_manager import DatabaseManager
            db = DatabaseManager()
            try:
                signals_list = db.get_all_signals()
            except Exception:
                pass
            from src.intelligence.ranker import EligibilityRanker
            ranker = EligibilityRanker()
            ranked = ranker.rank(signals_list) if signals_list else []
            alerts = alert_engine.run_all_checks_with_ranked(
                wallet=EVM_ADDR, ranked_protocols=ranked, dry_run=dry_run
            )
            if alerts:
                import logging
                logger = logging.getLogger("ecosystem")
                logger.warning(f"{len(alerts)} alert(s) triggered:")
                for a in alerts:
                    logger.warning(f"  [{a['severity'].upper()}] {a['message']}")
                    print(f"  [{a['severity'].upper()}] {a['message']}")
            else:
                print("  Alert check: no issues detected")
        except Exception as e:
            print(f"  \u26a0\ufe0f Alert check skipped: {e}")
        if not dry_run:
            state.mark_step_complete("alerts")

    print()
    print("=" * 55)
    print("\u2705 Ciclo completo executado com sucesso!")
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


# ── YIELD OPTIMIZER ──


def _print_yield_report(report: dict):
    print()
    print("╔════════════════════════════════════════════════╗")
    print("║           YIELD OPTIMIZER REPORT              ║")
    print("╠════════════════════════════════════════════════╣")
    print(f"║ Assets checked:     {len(report['checked']):<4}                       ║")
    rebalanced_str = ", ".join(
        f"{r['asset']} → {r['to_protocol']}" for r in report["rebalanced"]
    )
    skipped_str = ", ".join(
        set(r.get("reason", "?") for r in report["skipped"])
    )
    print(f"║ Rebalanced:         {len(report['rebalanced']):<4}  {rebalanced_str:<23} ║")
    print(f"║ Skipped:            {len(report['skipped']):<4}  ({skipped_str})           ║")
    print(f"║ Est. annual gain:   ${report['estimated_annual_gain_usd']:<7.2f}                 ║")
    print("╠════════════════════════════════════════════════╣")
    for r in report["checked"]:
        best = r.get("best_protocol", "—")
        loc = r.get("location", "?")
        curr = r.get("current_apy", 0)
        bapy = r.get("best_apy", 0)
        if loc == "wallet":
            print(f"║ {r['token']:<4}  {curr:>5.1f}% idle → {best:<12} {bapy:>5.1f}%  💰 deploy     ║")
        elif r.get("best_protocol") == loc:
            print(f"║ {r['token']:<4}  {curr:>5.1f}% at {loc:<12} ✅ already optimal      ║")
        else:
            print(f"║ {r['token']:<4}  {curr:>5.1f}% at {loc:<12} → {best:<12} {bapy:>5.1f}%  🔄 rebalance  ║")
    print("╚════════════════════════════════════════════════╝")
    print()


def cmd_yield(dry_run=False):
    from src.yield_optimizer.optimizer import YieldOptimizer
    optimizer = YieldOptimizer(dry_run=dry_run)
    report = optimizer.run(
        wallet_evm=EVM_ADDR,
        wallet_solana_path="wallets/solana_real.sol.json"
    )
    _print_yield_report(report)


def cmd_nft():
    # Use the same wallet logic as the rest of the app
    from solana_wallet import SolanaWalletManager
    wm = SolanaWalletManager()
    wallet = wm.load_wallet("solana_real")
    
    if not isinstance(wallet, Keypair):
        print("❌ Error: Solana wallet is not a Keypair")
        return

    from src.adapters.magic_eden_real import MagicEdenRealAdapter
    adapter = MagicEdenRealAdapter(None, wallet)
    
    # parse args
    import sys
    args = sys.argv
    dry_run = "--dry-run" in args
    do_buy = "--buy" in args

    portfolio = adapter.get_portfolio(str(wallet.pubkey()))
    print("\n🎨 MAGIC EDEN PORTFOLIO")
    print("=" * 40)
    print(f"  Wallet: {str(wallet.pubkey())[:10]}...{str(wallet.pubkey())[-10:]}")
    print(f"  Total NFTs: {portfolio['total_nfts']}")
    print(f"  Collections: {len(portfolio['collections'])}")
    print(f"  Est. Value: {portfolio['estimated_value_sol']:.4f} SOL")
    print("=" * 40)
    
    if do_buy:
        print("🚀 Attempting to buy NFT...")
        result = adapter.execute(dry_run=dry_run)
        if result.get("success"):
            print(f"✅ Purchase successful! Tx: {result['tx_hash']}")
        elif result.get("dry_run"):
            print(f"🔍 [DRY RUN] Would buy {result['intended_mint']} for {result['price_sol']} SOL")
        else:
            print(f"❌ Purchase failed: {result.get('reason', 'unknown')}")

def cmd_lz():
    from src.bridge.lz_cadencer import LZCadencer
    import json
    import sys
    lz = LZCadencer()
    args = sys.argv
    
    if "--stats" in args:
        stats = lz.get_stats()
        print(f"Total LZ bridges:  {stats['total_bridges']}")
        print(f"Unique days:       {stats['unique_days']}")
        print(f"Unique routes:     {stats['unique_routes']}")
        print(f"Total volume:      ${stats['total_volume_usdc']:.2f} USDC")
        print(f"Estimated tier:    {stats['estimated_tier'].upper()}")
        print(f"First bridge:      {stats['first_bridge']}")
        print(f"Last bridge:       {stats['last_bridge']}")
    elif "--bridge" in args:
        dry_run = "--dry-run" in args
        result = lz.execute_bridge(dry_run=dry_run)
        print(json.dumps(result, indent=2))
    else:
        stats = lz.get_stats()
        should, reason = lz.should_bridge_today()
        print(f"Status: {'✅ ready to bridge' if should else f'⏸ {reason}'}")
        print(f"Tier: {stats['estimated_tier'].upper()} ({stats['total_bridges']} bridges, {stats['unique_days']} days)")


def cmd_state():
    """Display persisted bot state."""
    from src.hardening.state_machine import StateMachine
    sm = StateMachine()
    data = sm._data

    print("\n📦 Bot State")
    print(f"{'─' * 50}")
    print(f"  Last run:         {data.get('last_run', 'never')}")
    print(f"  Cycle date:       {data.get('cycle_date', '—')}")
    print(f"  Cycle count:      {data.get('cycle_count', 0)}")
    print(f"  Completed steps:  {', '.join(data.get('completed_steps', [])) or 'none'}")

    proto_states = data.get("protocol_states", {})
    if proto_states:
        print(f"\n  Protocol States:")
        for name, ps in sorted(proto_states.items()):
            status_icon = "✅" if ps.get("status") == "ok" else "🔴"
            fails = ps.get("failures", 0)
            last = ps.get("last_run", "—")[:16]
            print(f"    {status_icon} {name:<15} fails={fails} last={last}")

    routes = data.get("bridge_routes_used", [])
    if routes:
        print(f"\n  Last LZ routes used:")
        for r in routes[-3:]:
            print(f"    {r['from']} → {r['to']} @ {r['timestamp'][:16]}")

    lz_idx = data.get("lz_last_route_index", 0)
    print(f"  LZ route index:   {lz_idx}")
    print(f"  Last Solana farm: {data.get('last_solana_farm', '—')}")
    print()


# ── MAIN ──


def main():
    parser = argparse.ArgumentParser(
        description="\U0001f331 Airdrop Inbound AI \u2014 Ecosystem CLI",
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
              python3 ecosystem.py alerts
              python3 ecosystem.py intel
              python3 ecosystem.py explain kamino
              python3 ecosystem.py api
              python3 ecosystem.py chains
               python3 ecosystem.py bridge --from arbitrum --to base --amount 10
               python3 ecosystem.py yield
               python3 ecosystem.py state
        """),
    )
    parser.add_argument(
        "command",
        choices=[
            "dashboard", "scan", "farm", "all", "schedule",
            "audit", "dryrun", "alerts", "intel", "explain",
            "api", "chains", "bridge", "yield", "nft", "lz", "state",
        ],
        nargs="?",
        help="Command to execute",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate transactions without broadcasting",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=15,
        help="Limit results (used by intel command)",
    )
    parser.add_argument(
        "--from",
        dest="from_chain",
        default="arbitrum",
        help="Source chain for bridge (default: arbitrum)",
    )
    parser.add_argument(
        "--to",
        dest="to_chain",
        default="base",
        help="Target chain for bridge (default: base)",
    )
    parser.add_argument(
        "--amount",
        type=float,
        default=10.0,
        help="Amount to bridge (default: 10 USDC)",
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
    elif args.command == "alerts":
        from src.utils.db_manager import DatabaseManager
        db = DatabaseManager()
        unread = db.get_unread_alerts()
        if not unread:
            print("No unread alerts.")
        else:
            for a in unread:
                print(f"[{a['severity'].upper()}] {a['created_at']} \u2014 {a['message']}")
    elif args.command == "intel":
        from src.intelligence.ranker import EligibilityRanker
        from src.utils.db_manager import DatabaseManager
        db = DatabaseManager()
        signals_list = db.get_all_signals()
        ranker = EligibilityRanker()
        ranked = ranker.rank(signals_list)
        print(f"\n{'Protocol':<25} {'Score':>7} {'Action':>16}")
        print(f"{'─' * 50}")
        for r in ranked[:int(args.limit) if hasattr(args, 'limit') and args.limit else 15]:
            print(f"{r['name'][:24]:<25} {r['eligibility_score']:>7} {r['action_label']:<16}")
    elif args.command == "explain":
        from src.intelligence.ranker import EligibilityRanker
        from src.utils.db_manager import DatabaseManager
        db = DatabaseManager()
        signals_list = db.get_all_signals()
        ranker = EligibilityRanker()
        ranked = ranker.rank(signals_list)
        query = " ".join(remaining).strip().lower()
        if not query:
            print("Usage: python3 ecosystem.py explain <protocol_name>")
            sys.exit(1)
        for r in ranked:
            if r["name"].lower() == query:
                print(r["explain"])
                return
        print(f"Protocol '{query}' not found in current ranked list.")
    elif args.command == "api":
        import uvicorn
        uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)
    elif args.command == "chains":
        from src.intelligence.chain_registry import list_chains
        chains = list_chains()
        print(f"\n{'Chain':<15} {'ID':>8} {'Currency':>10} {'Explorer':<30} {'Tier':>5}")
        print(f"{'─' * 75}")
        for c in chains:
            tier_label = "P1" if c["tier"] == 1 else "P2"
            print(f"{c['name']:<15} {c['id']:>8} {c['currency']:>10} {c['explorer']:<30} {tier_label:>5}")
        print()
    elif args.command == "yield":
        cmd_yield(dry_run=args.dry_run)
    elif args.command == "nft":
        cmd_nft()
    elif args.command == "lz":
        cmd_lz()
    elif args.command == "bridge":
        from decimal import Decimal
        from src.bridge.layerzero_bridge import bridge_route, STARGATE_V1_DEPLOYED
        from_supported = STARGATE_V1_DEPLOYED.get(args.from_chain, False)
        to_supported = STARGATE_V1_DEPLOYED.get(args.to_chain, False)
        if not from_supported or not to_supported:
            print(f"\n\u26a0\ufe0f Stargate V1 not supported for {args.from_chain} \u2192 {args.to_chain}")
            print("   V1 is deployed on: " + ", ".join(k for k, v in STARGATE_V1_DEPLOYED.items() if v))
            print("   Use LiFi bridge for unsupported routes.")
            print()
            return
        result = bridge_route(
            from_chain=args.from_chain,
            to_chain=args.to_chain,
            amount=Decimal(str(args.amount)),
            dry_run=args.dry_run,
        )
        print(f"\n🌉 Bridge {args.from_chain} → {args.to_chain}")
        print(f"   Status: {result.status}")
        print(f"   Amount: {args.amount} USDC")
        if result.tx_hash:
            print(f"   Tx: {result.tx_hash}")
        if result.error:
            print(f"   Error: {result.error}")
        print()
    elif args.command == "state":
        cmd_state()


if __name__ == "__main__":
    main()
