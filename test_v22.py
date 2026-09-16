"""Focused V2.2 architecture/regression tests."""
import numpy as np
import pandas as pd
from data_engine import ResilientDataEngine
from quant_processor import RobustQuantProcessor

def frame(n=40, volume=True):
    idx=pd.date_range("2026-09-01",periods=n,freq="h",tz="UTC")
    p=np.linspace(100,105,n)
    d=pd.DataFrame({"Open":p*0.999,"High":p*1.002,"Low":p*0.998,"Close":p,"Volume":np.full(n,100000.0) if volume else np.nan},index=idx)
    d.attrs.update({"source":"TEST-DIRECT","source_type":"DIRECT","is_real":True,"is_synthetic":False,"status":"LIVE","execution_eligible":True})
    return d

def test_method_signatures_and_real_gate():
    q=RobustQuantProcessor(); d=frame()
    direction=q.compute_realtime_price_action(d,vol_scale=1.0,asset_key="SPX")
    gate=q.evaluate_trade_entry_gate(d,asset_key="SPX")
    assert isinstance(direction,tuple) and len(direction)==4
    assert isinstance(gate,tuple) and len(gate)==4

def test_missing_volume_blocks_execution():
    q=RobustQuantProcessor(); ok,reason,atr,rvol=q.evaluate_trade_entry_gate(frame(volume=False),asset_key="SPX")
    assert ok is False and rvol==0.0

def test_stale_blocks_execution():
    q=RobustQuantProcessor(); d=frame(); d.attrs["status"]="STALE"; d.attrs["execution_eligible"]=False
    ok,_,_,_=q.evaluate_trade_entry_gate(d,asset_key="SPX"); assert ok is False

def test_engine_no_proxy_symbol_insertion():
    e=ResilientDataEngine(fred_api_key="")
    assert not hasattr(e,"candidate_symbols")

if __name__=="__main__":
    test_method_signatures_and_real_gate(); test_missing_volume_blocks_execution(); test_stale_blocks_execution(); test_engine_no_proxy_symbol_insertion(); print("V2.2 focused tests: PASS")
