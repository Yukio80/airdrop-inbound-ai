# Airdrop Inbound AI

Capital-efficient airdrop farming framework: monitoramento de quests (Galxe) + automação de testnets + proof-of-activity em Solana + interações reais em EVM (Arbitrum).

## Comandos

```bash
python3 ecosystem.py dashboard   # Painel com saldos, quests e transações
python3 ecosystem.py scan        # Scan Galxe + DeFiLlama
python3 ecosystem.py farm        # Farm testnets + Solana
python3 ecosystem.py all         # Ciclo completo (scan + bridge + quest farm + farm)
python3 ecosystem.py audit       # Auditor de footprint on-chain (Arbiscan + Solana)
python3 ecosystem.py dryrun      # Stress test dry-run em todos os adapters
python3 ecosystem.py schedule    # Agenda cron diário (08:00)
```

## Status Atual

| Componente | Status |
|------------|--------|
| Discovery (DeFiLlama) | Real |
| Galxe Scanner | Real |
| Galxe Quest Executor | Real |
| Uniswap V3 | Real + dry-run |
| SushiSwap | Real + dry-run |
| Aave V3 | Real + dry-run |
| Compound V3 | Real + dry-run |
| Curve 3Pool | Real + dry-run |
| Lido (stake/wrap) | Real + dry-run |
| LiFi Bridge | Real |
| Solana Fragmetric | Real |
| Solana Jito | Real |
| Solana Jupiter | Real |
| Solana Kamino | Real |
| Solana Marinade | Real |
| Solana Meteora | Real |
| Solana Raydium | Real |
| Solana Sanctum | Real |
| Footprint Auditor | Real (Arbiscan + Solana RPC) |
| Testnet Farm (Sepolia/Hoodi/Amoy) | Real |
| Dashboard | Real |
| SQLite Proof Tracking | Real |

## Execution Flow

1. **Discovery**
   ├── DeFiLlama (Real-time protocol discovery)
   └── Galxe (Quest & Task scanning)

2. **Scoring**
   └── Opportunity ranking (TVL, Growth, Airdrop probability)

3. **Execution**
   ├── Uniswap V3 (Swaps)
   ├── SushiSwap (Swaps)
   ├── Aave V3 (Lending/Supply)
   ├── Compound V3 (Supply/Withdraw)
   ├── Curve 3Pool (Add/Remove liquidity)
   ├── Lido (Stake ETH → stETH, wrap → wstETH)
   └── Galxe (On-chain task fulfillment)

4. **Solana Activity**
   ├── Fragmetric (Stake SOL)
   ├── Jito (Stake SOL)
   ├── Jupiter (Swaps)
   ├── Kamino (Supply/Borrow)
   ├── Marinade (Stake SOL)
   ├── Meteora (DLMM pools)
   ├── Raydium (Swaps, LP)
   └── Sanctum (Stake SOL)

5. **Cross-Chain Funding**
   └── LiFi Bridge (Arbitrum ↔ BSC)

6. **Proof Tracking**
   └── SQLite (Transaction logs & status persistence)

7. **Footprint Audit**
   └── Arbiscan API + Solana RPC → SQLite reconciliation

8. **Dashboard**
   └── Terminal (Real-time monitoring & analytics)

## Dry-Run Mode

Todos os adapters suportam `dry_run=True`, que retorna resultados simulados sem enviar transações reais. Use para validar fluxos antes de executar com fundos reais:

```bash
python3 scripts/stress_test_dryrun.py   # Testa todos os adapters
python3 ecosystem.py all --dry-run      # Ciclo completo simulado
python3 ecosystem.py dryrun             # Alias para stress test
```

## Auditor de Footprint

O `FootprintAuditor` consulta o Arbiscan API e nós RPC Solana para reconciliar o histórico de transações no SQLite local:

```bash
python3 ecosystem.py audit              # Auditor completo
python3 ecosystem.py audit --evm-only   # Apenas EVM
python3 ecosystem.py audit --sol-only   # Apenas Solana
```

Requer `ARBISCAN_API_KEY` no `.env` (gratuita em arbiscan.io).

## Opportunity Scoring

Protocols are ranked using a quantitative algorithm based on:

- **TVL (Total Value Locked)**: Baseline for protocol significance.
- **Growth Rate**: Velocity of capital inflow.
- **Airdrop Probability**: Heuristics based on funding and tokenomics.
- **Historical Reward Signal**: Analysis of similar protocol rewards.

Higher scores are prioritized by the farm engine to optimize capital efficiency.

## Security

All secrets are loaded from environment variables. **Never commit private keys or wallet files to the repository.**

Required environment variables:
```env
ARBITRUM_RPC_URL=
ETH_RPC_URL=
BSC_RPC_URL=
SOLANA_RPC_URL=
ARBISCAN_API_KEY=
PRIVATE_KEY=
SOLANA_PRIVATE_KEY=
GALXE_API_KEY=
```

## Estrutura

```
src/
├── adapters/
│   ├── __init__.py              # Mapa de endereços de tokens
│   ├── uniswap.py               # Uniswap V3 (real + dry-run)
│   ├── sushi.py                 # SushiSwap (real + dry-run)
│   ├── aave.py                  # Aave V3 (real + dry-run)
│   ├── compound.py              # Compound V3 (real + dry-run)
│   ├── curve.py                 # Curve 3Pool (real + dry-run)
│   ├── lido.py                  # Lido stake/wrap (real + dry-run)
│   └── solana/
│       ├── real_base.py         # Solana RPC base
│       ├── solana_real.py       # Solana helpers
│       ├── fragmetric_real.py   # Fragmetric staking
│       ├── jito_real.py         # Jito staking
│       ├── jupiter_real.py      # Jupiter swaps
│       ├── kamino_real.py       # Kamino lending
│       ├── marinade_real.py     # Marinade staking
│       ├── meteora_real.py      # Meteora DLMM
│       ├── raydium_real.py      # Raydium swaps/LP
│       └── sanctum_real.py      # Sanctum staking
├── audit/
│   └── footprint.py             # FootprintAuditor (Arbiscan + Solana)
├── bridge/
│   └── lifi_bridge.py           # Cross-chain bridge via LI.FI
├── quests/
│   ├── galxe.py                 # Cliente GraphQL Galxe + scan persistente
│   ├── testnet_farm.py          # Farm automatizado (Sepolia, Hoodi, Amoy)
│   ├── faucet.py                # Guia de faucets
│   └── pow_miner.py             # Minerador PoW
├── utils/
│   └── db_manager.py            # Persistência SQLite
├── arbitrum_real.py             # Transações reais na Arbitrum
├── dashboard.py                 # Painel de controle terminal
├── discovery.py                 # Scanner DeFiLlama
├── scoring.py                   # Pontuação de protocolos
├── execution.py                 # Gerenciamento de execução
└── models.py                    # Modelos compartilhados (SwapResult, etc.)

ecosystem.py                     # CLI principal
quest_farm.py                    # Orquestrador de quests on-chain
solana_daily_farm.py             # Farm Solana diário
solana_weekly_farm.py            # Farm Solana semanal
scripts/
├── stress_test_dryrun.py        # Stress test all adapters
└── run_audit.py                 # Script de auditoria standalone
reports/                         # Relatórios de teste
logs/                            # Logs de execução
```

## Requisitos

```bash
pip install -r requirements.txt
```

## Support the Project

If this project saves you time, helps you farm airdrops, or inspires your own work, consider supporting its continued development.

**Channels:**
- USDC (Arbitrum): `0x50C905a210E5585B0F0124a0B53195f7Eb3d994C`
- ETH (Arbitrum): `0x50C905a210E5585B0F0124a0B53195f7Eb3d994C`
- SOL (Solana): `<solana_address>`

Every contribution helps fund:
- RPC infrastructure
- Testnet experimentation
- New protocol integrations
- Development time

Thank you for your support.

## Disclaimer

This software interacts with public blockchains and may spend real assets.

Users are solely responsible for:
- private key management
- gas costs
- protocol risks
- compliance with local regulations

**Use at your own risk.**
