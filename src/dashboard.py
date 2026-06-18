import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from src.utils.db_manager import DatabaseManager
from src.backtesting import Backtester, BacktestConfig
import plotly.express as px

st.set_page_config(page_title="Airdrop Inbound AI Dashboard", layout="wide")

db = DatabaseManager()
bt = Backtester()

st.title("🚀 Airdrop Inbound AI Dashboard")
st.markdown("Monitoring qualitative opportunities and on-chain execution.")

# Sidebar
st.sidebar.header("Controls")
if st.sidebar.button("Refresh Data"):
    st.rerun()

# Fetch data
with db._get_connection() as conn:
    df_signals = pd.read_sql("SELECT * FROM signals", conn)
    df_txs = pd.read_sql("SELECT * FROM transactions", conn)

total_signals = len(df_signals)
executed_signals = len(df_signals[df_signals['status'] == 'executed']) if not df_signals.empty else 0
total_txs = len(df_txs)

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Protocols Scanned", total_signals)
col2.metric("Successfully Farmed", executed_signals)
col3.metric("Total Transactions", total_txs)

# Tabs
tab1, tab2, tab3 = st.tabs(["🎯 Opportunities", "📜 Transaction Log", "📊 Backtesting"])

with tab1:
    st.subheader("Scanned Protocols & Scoring")
    if not df_signals.empty:
        df_signals = df_signals.sort_values(by="score", ascending=False)

        def color_status(val):
            color = 'green' if val == 'executed' else 'orange' if val == 'pending' else 'grey'
            return f'color: {color}'

        st.dataframe(df_signals.style.map(color_status, subset=['status']), use_container_width=True)

        fig = px.bar(df_signals, x='protocol', y='score', color='status',
                     title="Opportunity Scores",
                     labels={'score': 'Quantitative Score', 'protocol': 'Protocol'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available. Run the orchestrator first!")

with tab2:
    st.subheader("Detailed Execution Log")
    if not df_txs.empty:
        st.table(df_txs.sort_values(by="timestamp", ascending=False))
    else:
        st.info("No transactions recorded yet.")

with tab3:
    st.subheader("Backtesting Engine")

    col_a, col_b, col_c = st.columns(3)
    threshold = col_a.slider("Score Threshold", 0, 100, 30)
    chain_opts = st.multiselect("Chains", ["arbitrum", "ethereum", "base"], default=["arbitrum", "ethereum"])
    action_opts = st.multiselect("Actions", ["swap", "supply", "stake"], default=["swap", "supply", "stake"])

    if st.button("Run Backtest"):
        config = BacktestConfig(
            name=f"threshold={threshold}",
            score_threshold=threshold,
            chains=chain_opts,
            actions=action_opts,
        )

        with st.spinner("Running backtest..."):
            result = bt.simulate(config)

        st.success(f"Backtest complete: {result.executed} protocols would execute")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Signals", result.total_signals)
        m2.metric("Would Execute", result.executed)
        m3.metric("Avg Score", f"{result.avg_score:.1f}")
        m4.metric("Est. Tx", result.total_transactions)

        if result.protocol_scores:
            df_proto = pd.DataFrame(result.protocol_scores)
            fig2 = px.bar(df_proto.head(10), x='protocol', y='score', color='chain',
                          title="Top Protocols by Score")
            st.plotly_chart(fig2, use_container_width=True)

        if result.action_distribution:
            df_act = pd.DataFrame(list(result.action_distribution.items()),
                                  columns=["action", "count"])
            fig3 = px.pie(df_act, values='count', names='action', title="Action Distribution")
            st.plotly_chart(fig3, use_container_width=True)

        st.text(bt.report(result))

    with st.expander("Compare Strategies"):
        configs = [
            BacktestConfig(name="conservative", score_threshold=50, chains=["arbitrum"]),
            BacktestConfig(name="moderate", score_threshold=30, chains=["arbitrum", "ethereum"]),
            BacktestConfig(name="aggressive", score_threshold=20, chains=["arbitrum", "ethereum", "base"]),
        ]
        if st.button("Compare All"):
            results = bt.compare(configs)
            df_comp = bt.to_dataframe(results)
            st.dataframe(df_comp, use_container_width=True)

            fig4 = px.bar(df_comp, x='config', y=['executed', 'skipped'],
                          title="Strategy Comparison",
                          labels={'value': 'Count', 'variable': 'Status'})
            st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")
st.caption("Airdrop Inbound AI - Qualitative Farming Framework")
