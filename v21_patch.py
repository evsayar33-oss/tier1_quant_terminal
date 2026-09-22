"""Compatibility shim for the legacy v2.1 regression test.

The production entry implementation now lives in RobustQuantProcessor and
uses the current dynamic ATR/RVOL gate. This module preserves the old private
helper names used by test_v21_patch.py without introducing a second engine.
"""
from quant_processor import RobustQuantProcessor


def _attach_quality(df, source="TEST", fetched_at=None):
    frame = df.copy()
    frame.attrs.update({
        "source": source,
        "source_type": "DIRECT",
        "is_real": True,
        "is_synthetic": False,
        "status": "LIVE",
        "execution_eligible": True,
        "fetched_at": fetched_at,
    })
    return frame


def _v21_evaluate_trade_entry_gate(df, asset_key="SPX"):
    return RobustQuantProcessor.evaluate_trade_entry_gate(df, asset_key=asset_key)
