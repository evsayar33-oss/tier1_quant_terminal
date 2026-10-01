"""
Single-writer rule for persistent state (v3.5)
==============================================
Only the GitHub Actions background tracker may write the learning state
(stateful_adaptive_memory.json, adaptive_regime_thresholds_state.json,
data_freshness_state.json, timeframe_confluence_state.json,
terminal_state.json). The Streamlit app runs with TIER1_READ_ONLY_STATE=1:
it evaluates the live market against the PUBLISHED state and never mutates
it. Before v3.5 every "Canlı Verileri Yenile" click ran a full learning
cycle and rewrote these files inside the app container, while the
background job overwrote them again on its next commit -> two diverging
histories, different answers on every click.
"""
import os


def is_read_only() -> bool:
    return os.environ.get("TIER1_READ_ONLY_STATE", "") == "1"
