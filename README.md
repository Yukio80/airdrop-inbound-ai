# Airdrop Inbound AI

Capital-efficient airdrop farming framework: monitoramento de quests (Galxe) + automação de testnets + proof-of-activity em Solana + interações reais multi-chain (Arbitrum, Base, Optimism, Polygon, BSC) + yield optimizer + NFT farming (Magic Eden) + LayerZero volume cadencing.

## Hardening

Módulo de resiliência integrado em todos os componentes críticos:

| Componente | Retry | Circuit Breaker | State Machine |
|---|---|---|---|
| LiFi Bridge | ✅ RPC + API | ✅ 3 CBs (RPC, API, bridge) | — |
| LZ Cadencer | — | ✅ LZ bridge CB | ✅ rotas + failures |
| Solana adapters | ✅ send_transaction | ✅ RPC CB | — |
| Testnet Farm | ✅ balance + send | — | — |
| Solana Daily Farm | ✅ proof-of-activity | — | ✅ protocol day |
| Ecosystem CLI | — | — | ✅ cycle steps |

```bash
python3 ecosystem.py state      # Estado persistido do bot
```

## Comandos

```bash
python3 ecosystem.py dashboard   # Painel com saldos, quests, transações, yield, LZ, gas
python3 ecosystem.py scan        # Scan Galxe + DeFiLlama
python3 ecosystem.py farm        # Farm testnets + Solana + yield optimizer
python3 ecosystem.py all         # Ciclo completo (bridge + scan + quest + farm + alerts)
python3 ecosystem.py all --dry-run  # Ciclo simulado
python3 ecosystem.py audit       # Auditor de footprint on-chain
python3 ecosystem.py dryrun      # Stress test dry-run em todos os adapters
python3 ecosystem.py schedule    # Agenda cron diário (08:00)
python3 ecosystem.py chains      # Lista chains suportadas
python3 ecosystem.py bridge      # Cross-chain bridge via LayerZero/Stargate
python3 ecosystem.py yield       # Yield optimizer (rebalance APY)
python3 ecosystem.py nft         # Magic Eden NFT portfolio/buy
python3 ecosystem.py lz          # LayerZero status/bridge
python3 ecosystem.py alerts      # Visualizar alertas
python3 ecosystem.py intel       # Ranking de protocolos
python3 ecosystem.py explain     # Score breakdown de um protocolo
python3 ecosystem.py api         # FastAPI REST (porta 8000)
python3 ecosystem.py state       # Bot state machine (persistência)
```

## Chains Suportadas

| Chain | ID | Explorer | LayerZero V1 | Stargate Pool |
|-------|----|----------|--------------|---------------|
| Arbitrum | 42161 | arbiscan.io | ✅ | USDC=1, USDT=2 |
| Optimism | 10 | optimistic.etherscan.io | ✅ | USDC=1, USDT=2 |
| BSC | 56 | bscscan.com | ✅ | USDC=1, USDT=2 |
| Polygon | 137 | polygonscan.com | ✅ | USDC=1, USDT=2 |
| Ethereum | 1 | etherscan.io | ✅ | USDC=1, USDT=2 |
| Base | 8453 | basescan.org | ❌ (pós-V1) | Use LiFi |

## Cross-Chain Bridge

### LayerZero V1 (Stargate)
USDC bridges entre Arbitrum, Optimism, BSC, Polygon, Ethereum:

```bash
python3 ecosystem.py bridge --from arbitrum --to optimism --amount 10
python3 ecosystem.py bridge --from arbitrum --to polygon --amount 50 --dry-run
```

### LZ Volume Cadencer
Bridge automática diária de $3 USDC em rotação entre chains para acúmulo de transações LZ:

```yaml
# config/scoring.yaml
layerzero_cadencer:
  enabled: true
  amount_usdc_per_bridge: 3.0
  max_daily_bridges: 2
  min_interval_hours: 6
  routes:
    - from: arbitrum → to: base
    - from: base → to: optimism
    - from: optimism → to: arbitrum
    - from: arbitrum → to: polygon
    - from: polygon → to: base
```

Tiers históricos ZRO: Tier 1 (1-4) → ~$40, Tier 2 (5-14) → ~$200, Tier 3 (15-29) → ~$500, Tier 4 (30+) → ~$2000+

```bash
python3 ecosystem.py lz --stats   # Total bridges, tier, volume
python3 ecosystem.py lz --bridge  # Executa uma bridge
```

### LiFi Bridge
Bridge BNB → ETH (Arbitrum) quando saldo ETH < 0.005:

```bash
python3 ecosystem.py all  # Auto-funding se necessário
```

## NFT Farming (Magic Eden)

Compra automatizada de NFTs na Solana via Magic Eden V2:

```yaml
# config/scoring.yaml
magic_eden:
  max_price_sol: 0.05
  target_nft_count: 3
  buy_frequency_days: 7
  enabled: true
```

```bash
python3 ecosystem.py nft              # Portfolio + saldos
python3 ecosystem.py nft --buy        # Comprar NFT
python3 ecosystem.py nft --buy --dry-run
```

## Yield Optimizer

Realoca fundos entre protocolos para maximizar APY. Consulta feeds DeFiLlama + Kamino + Marinade + Lido:

```bash
python3 ecosystem.py yield
```

Painel no dashboard: `💰 YIELD OPTIMIZER` com melhores taxas USDC/SOL/ETH.

## Telegram Notifications

Alertas críticos enviados automaticamente para o Telegram:

```env
TELEGRAM_BOT_TOKEN=seu_token
TELEGRAM_CHAT_ID=seu_chat_id
```

Eventos notificados:
- 🔴 `low_gas` — Saldo ETH abaixo de 0.005 (crítico)
- ℹ️ `low_frequency` — Menos de 2d/semana de atividade
- ℹ️ `yield_opportunity` — Melhor APY disponível

## Gas Health Monitor

Alerta automático quando saldo ETH na Arbitrum cai abaixo de 0.005 ETH:

```
💧 GAS HEALTH
  Arbitrum ETH:       0.000101   ⚠️  2% do mínimo (0.005 ETH)
  Threshold mínimo:   0.005 ETH para automação
```

## Testnets

| Testnet | Chain ID | Native | Faucet |
|---------|----------|--------|--------|
| Sepolia | 11155111 | ETH | PoW, QuickNode, GetBlock |
| Hoodi | 560048 | ETH | PoW, QuickNode, Google Cloud |
| Amoy | 80002 | POL | QuickNode, GetBlock |
| Base Sepolia | 84532 | ETH | QuickNode, Coinbase, Alchemy |
| Optimism Sepolia | 11155420 | ETH | QuickNode, Alchemy, Coinbase |

```bash
python3 ecosystem.py farm        # Farm todas as testnets
python3 ecosystem.py farm --chains sepolia,base_sepolia
```

## Execution Integrity

Relatório de integridade disponível no dashboard:

```
🛡️ EXECUTION INTEGRITY
  Real txs (7d):          95   ✅
  Simulated calls (7d):    0   ⚠️
  Failed txs (7d):         0   ✅
  Adapters no real tx:     compound, curve   ⚠️
```

## API REST

```bash
python3 ecosystem.py api     # uvicorn na porta 8000
```

Endpoints:
```
GET  /api/health                  Status do bot
GET  /api/wallet/balance/{addr}   Saldos EVM + Solana
GET  /api/wallet/audit/{addr}     Multi-chain audit
GET  /api/opportunities           Oportunidades ranqueadas
GET  /api/intel/campaigns         Campanhas Galxe
GET  /api/nft/portfolio/{wallet}  NFT portfolio
GET  /api/lz/stats                LayerZero stats
GET  /api/yield/rates             APY feed
GET  /api/yield/optimize          Melhor realocação
GET  /api/state                   Bot state machine
POST /api/state/reset             Resetar estado
```

## Security

All secrets are loaded from environment variables. **Never commit private keys or wallet files to the repository.**

Required environment variables:
```env
ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc
BSC_RPC_URL=https://bsc-dataseed.binance.org
ETH_RPC_URL=https://eth.llamarpc.com
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
ARBISCAN_API_KEY=your_key_here
PRIVATE_KEY=your_evm_private_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Estrutura

```
src/
├── adapters/
│   ├── aave.py / compound.py / curve.py / lido.py / sushi.py / uniswap.py
│   ├── magic_eden_real.py         # Magic Eden NFT buy
│   └── solana/
│       ├── real_base.py           # Base com circuit breaker + retry
│       ├── fragmetric_real.py
│       ├── jito_real.py / jupiter_real.py
│       ├── kamino_real.py / marinade_real.py
│       ├── meteora_real.py / raydium_real.py / sanctum_real.py
├── api/
│   └── routes/
│       ├── intelligence.py / opportunities.py / wallet.py / state.py
├── audit/
│   └── footprint.py
├── bridge/
│   ├── lifi_bridge.py             # LiFi (BNB → ETH)
│   ├── layerzero_bridge.py        # Stargate V1 (USDC)
│   └── lz_cadencer.py             # LZ volume builder
├── hardening/                     # ⚡ Resiliência
│   ├── retry.py                   # @retry / @retry_async
│   ├── circuit_breaker.py         # CircuitBreaker (CLOSED/OPEN/HALF_OPEN)
│   └── state_machine.py           # StateMachine (JSON persistence)
├── intelligence/
│   ├── alert_engine.py            # Gas health + activity alerts
│   ├── chain_registry.py          # Chain configs
│   └── ranker.py                  # EligibilityRanker
├── quests/
│   ├── galxe.py / testnet_farm.py / faucet.py / pow_miner.py
├── yield_optimizer/
│   ├── apy_feed.py / balance_reader.py / optimizer.py
├── utils/
│   └── db_manager.py
├── dashboard.py                   # Painel terminal
├── notifications.py               # Telegram + Discord
├── config_loader.py               # YAML → Config dataclass
├── solana_wallet.py               # Keystore manager
└── models.py
ecosystem.py                       # CLI principal
solana_daily_farm.py               # Farm Solana diário
config/
└── scoring.yaml                   # Pesos + alerts + bridges config
state/
└── bot_state.json                 # Estado persistido (auto-gerado)
```

## Requisitos

```bash
pip install -r requirements.txt
```

## Dry-Run Mode

Todos os adapters suportam `dry_run=True`. Use para validar fluxos antes de usar fundos reais:

```bash
python3 ecosystem.py all --dry-run      # Ciclo completo simulado
python3 ecosystem.py yield --dry-run    # Yield optimizer simulado
python3 ecosystem.py nft --buy --dry-run
python3 ecosystem.py bridge --from arbitrum --to base --amount 10 --dry-run
```

## Support the Project

If this project saves you time, helps you farm airdrops, or inspires your own work, consider supporting its continued development.

**Channels:**
- USDC (Arbitrum): `0x50C905a210E5585B0F0124a0B53195f7Eb3d994C`
- ETH (Arbitrum): `0x50C905a210E5585B0F0124a0B53195f7Eb3d994C`

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
