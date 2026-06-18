# Airdrop Inbound AI

## Framework Overview

**Airdrop Inbound AI** is a qualitative airdrop farming framework focused on intelligent discovery and automated execution. It's designed to be more sustainable, educational, and technically interesting than traditional mass-sybil approaches.

## Core Philosophy

Instead of creating hundreds of fake wallets, this framework:
- **Discovers** high-quality opportunities using real data
- **Scores** them based on quantitative and qualitative metrics
- **Executes** only the most promising protocols
- **Persists** all activity for analysis and learning
- **Simulates** human behavior to avoid detection

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   DISCOVERY     │────▶│   SCORING/IA     │────▶│   EXECUÇÃO      │
│  (Oportunidades)│     │  (Priorização)   │     │  (On-chain)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                        │                        │
   - Twitter/X              - Métricas on-chain      - Wallet manager
   - Discord/Telegram       - Sentimento NLP         - Bridge/swap auto
   - Dados de funding       - Modelo preditivo       - Task scheduler
   - GitHub activity        - Risk scoring           - Gas optimizer
```

## Quick Start Guide

### Prerequisites
```bash
python3 >= 3.8
pip install -r requirements.txt
```

### Step 1: Run the Demo
```bash
python3 demo.py
```

### Step 2: View the Dashboard
```bash
streamlit run src/dashboard.py
```

### Step 3: Explore the Database
```bash
# Check logged transactions
sqlite3 airdrop_bot.db "SELECT * FROM transactions;"

# View discovered protocols  
sqlite3 airdrop_bot.db "SELECT * FROM signals;"
```

## Framework Components

### 1. Discovery (`src/discovery.py`)
Scans external sources for airdrop opportunities:
- **DeFiLlama API**: Protocol TVL and metrics
- **Chain Inference**: Automatically detects target chains

**Features**:
- Real-time data collection
- CEX filtering (focuses on DEXs)
- Chain preference (Arbitrum for farming)

### 2. Scoring (`src/scoring.py`)
Evaluates protocol potential using quantitative models:
- **TVL Scoring**: Logarithmic weight (up to 30 points)
- **Growth Metrics**: 7-day TVL growth (up to 40 points)
- **Funding Analysis**: Round size heuristics (up to 20 points)

**Algorithm**: 0-100 scores, only protocols with score ≥ 30 are executed

### 3. Execution (`src/execution.py`)
Handles on-chain operations with safety:
- **Secure Wallet Manager**: Keystore-encrypted wallets
- **Protocol Adapters**: 
  - Uniswap V3: Smart swaps with path optimization
  - Aave: Liquidity provision with risk management
- **Anti-Det. Simulation**: Human-like behavior patterns

### 4. Persistence (`src/utils/db_manager.py`)
Maintains activity history:
- **SQLite Database**: `airdrop_bot.db`
- **Tables**: `signals` (discovered opportunities), `transactions` (executed tasks)
- **Status Tracking**: pending/executed/ignored/error states

### 5. API Integration (`src/utils/api_client.py`)
Connects to external AI services:
- **z.ai Client**: Strategy generation and analysis
- **Fallback Engine**: Local decision making when API is unavailable

### 6. Dashboard (`src/dashboard.py`)
Real-time monitoring interface:
- **Metrics Panel**: Overview of discovered protocols and execution status
- **Protocol List**: Detailed view of all opportunities with scores
- **Transaction Log**: Complete history of executed trades
- **Visualizations**: Charts and graphs for trend analysis

## Configuration

### Environment Variables
```bash
# Optional: z.ai API key (for enhanced AI decisions)
export ZAI_API_KEY="your-api-key-here"
```

### RPC Endpoints (Free)
The framework uses free public RPC endpoints:
- **Ethereum**: https://eth.llamarpc.com
- **Arbitrum**: https://arb1.arbitrum.io/rpc
- **Base**: https://mainnet.base.org

## Security Considerations

### Best Practices
1. **Wallet Isolation**: Never mix farming with personal holdings
2. **Encrypted Storage**: All private keys use Keystore with AES-256
3. **Transaction Simulation**: Always simulate before signing
4. **Gas Optimization**: Use EIP-1559 where supported

### Risk Management
- **Slippage Control**: Limit max slippage percentage
- **Gas Optimization**: Dynamic gas price estimation
- **Amount Limits**: Set per-transaction caps
- **Monitor Balance**: Alert on low balance conditions

## Production Deployment

### Docker Setup
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/

CMD ["python3", "demo.py"]
```

### Docker Compose
```yaml
services:
  app:
    build: .
    volumes:
      - ./data:/app/data
    ports:
      - "8501:8501"
    environment:
      - PYTHONUNBUFFERED=1
```

## Customization

### Add New Protocols
1. **Discovery**: Extend `OpportunityScanner` with new data sources
2. **Adapters**: Implement `ProtocolAdapter` for new DeFi protocols
3. **Scoring**: Add new features to `AirdropPredictor`

### Adjust Strategy
- **Score Threshold**: Modify `if score >= 30:` in orchestrator
- **Execution Strategy**: Customize the strategy generation in `demo.py`
- **Gas Settings**: Adjust `gas` and `gasPrice` in adapters

## Monitoring & Maintenance

### Log Files
- **Execution Logs**: Console output during runs
- **Transaction History**: Full audit trail in SQLite
- **Dashboard**: Real-time web interface

### Health Checks
```bash
# Check if orchestrator is running
pgrep -f "orchestrator_final.py"

# Monitor database size
du -h airdrop_bot.db

# Check for errors in logs
grep "ERROR" orchestrator.log
```

## Technical Details

### Data Flow
1. **Discovery** → **Scoring** → **Persistence** → **Execution**
2. **Execution** → **Persistence** (transactions)
3. **Dashboard** ← **Persistence** (read-only)

### Async Design
- **Synchronous Adapters**: Prevent event loop hangs
- **Async Orchestrator**: Coordinate component execution
- **Thread Pool**: Handle blocking I/O operations

### Error Handling
- **Graceful Degradation**: Continue on component failures
- **Retry Logic**: Automatic retry for transient errors
- **Fallback Strategies**: Local decision making when APIs are unavailable

## Future Enhancements

### Phase 1 (Short Term)
- [x] Core framework working
- [ ] Add more DeFi protocols (Compound, Curve, Sushiswap)
- [ ] Implement advanced risk scoring
- [ ] Add notification system (Telegram/Discord)

### Phase 2 (Medium Term)
- [ ] Real-time execution with gas optimization
- [ ] Multi-wallet management
- [ ] Historical performance analysis
- [ ] Automated rebalancing strategies

### Phase 3 (Long Term)
- [ ] Decentralized orchestration
- [ ] Cross-chain arbitrage detection
- [ ] ML-powered opportunity prediction
- [ ] Adaptive risk management

## License

This framework is provided for educational and research purposes. Use at your own risk in compliance with applicable laws and regulations.

## Support

For issues, questions, or contributions:
- **GitHub Issues**: Report bugs and request features
- **Discussions**: Share experiences and best practices
- **Issues**: Technical support and troubleshooting

---

**Version**: 1.0
**Status**: ✅ DEMO READY
**Last Updated**: $(date)
