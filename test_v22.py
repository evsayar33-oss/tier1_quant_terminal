"""Focused V2.2 architecture/regression tests."""
import numpy as np
import pandas as pd
from data_engine import ResilientDataEngine
from quant_processor import RobustQuantProcessor
from gatekeeper import PreTradeGatekeeper

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

def test_pair_direction_coherence():
    # Test-only correlated data; never used by production data_engine.
    a=frame(); b=frame();
    a["Close"] = np.linspace(100.0, 99.92, len(a))
    b["Close"] = np.linspace(200.0, 199.84, len(b))
    for d in (a,b):
        d["Open"]=d["Close"]*0.999; d["High"]=d["Close"]*1.001; d["Low"]=d["Close"]*0.998
    g=PreTradeGatekeeper(fred_api_key="")
    g.grid_1h={"ES=F":a,"SPX":a,"NQ=F":b,"NQ":b,"GC=F":a,"XAU":a,"SI=F":b,"XAG":b}
    g.crisis_active=False
    g.evaluate_asset_direction=lambda key, previous_signal="NÖTR (BEKLE)": {
        "verdict":"NÖTR (BEKLE)","forecast_direction":"NÖTR (BEKLE)",
        "current_direction":("🔴 AŞAĞI (%-0.10)" if key in ("NQ","XAG") else "⚪ YATAY (%-0.04)"),
        "current_icon":"🔴" if key in ("NQ","XAG") else "⚪", "current_color":"red" if key in ("NQ","XAG") else "gray",
        "current_roc":-0.1 if key in ("NQ","XAG") else -0.04, "score":-1.0 if key in ("NQ","XAG") else -0.1,
        "entry_allowed":False,"entry_reason":"test","rvol":1.0,"atr_ratio":1.0,"details":[]
    }
    out=g.evaluate_all_assets_harmonized({})
    assert out["XAU"]["current_icon"] == out["XAG"]["current_icon"]
    assert out["SPX"]["current_icon"] == out["NQ"]["current_icon"]

if __name__=="__main__":
    test_method_signatures_and_real_gate(); test_missing_volume_blocks_execution(); test_stale_blocks_execution(); test_engine_no_proxy_symbol_insertion(); test_pair_direction_coherence(); print("V2.2 focused tests: PASS")
