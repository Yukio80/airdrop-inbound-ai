import streamlit as st
import pandas as pd
from src.utils.db_manager import DatabaseManager
import plotly.express as px

st.set_page_config(page_title="Airdrop Inbound AI Dashboard", layout="wide")

db = DatabaseManager()

st.title("🚀 Airdrop Inbound AI Dashboard")
st.markdown("Monitoring qualitative opportunities and on-chain execution.")

# Sidebar
st.sidebar.header("Controls")
if st.sidebar.button("Refresh Data"):
    st.rerun()

# Metrics Section
col1, col2, col3 = st.columns(3)

# Fetch data
with db._get_connection() as conn:
    conn.row_factory = pd.io.sql.DataFrame
    df_signals = pd.read_sql("SELECT * FROM signals", conn)
    df_txs = pd.read_sql("SELECT * FROM transactions", conn)

total_signals = len(df_signals)
executed_signals = len(df_signals[df_signals['status'] == 'executed'])
total_txs = len(df_txs)

col1.metric("Protocols Scanned", total_signals)
col2.metric("Successfully Farmed", executed_signals)
col3.metric("Total Transactions", total_txs)

# Main Content
tab1, tab2 = st.tabs(["🎯 Opportunities", "📜 Transaction Log"])

with tab1:
    st.subheader("Scanned Protocols & Scoring")
    if not df_signals.empty:
        # Sorting by score
        df_signals = df_signals.sort_values(by="score", ascending=False)
        
        # Color mapping for status
        def color_status(val):
            color = 'green' if val == 'executed' else 'orange' if val == 'pending' else 'grey'
            return f'color: {color}'
        
        st.dataframe(df_signals.style.applymap(color_status, subset=['status']), use_container_width=True)
        
        # Visualization
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

st.markdown("---")
st.caption("Airdrop Inbound AI - Qualitative Farming Framework")
