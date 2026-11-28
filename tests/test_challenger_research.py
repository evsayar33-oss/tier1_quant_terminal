from datetime import timezone
import json
import math
import numpy as np
import pandas as pd
import challenger_research as c
from quant_processor import RobustQuantProcessor as Q
from stateful_memory_store import StatefulMemoryStore
from stateful_adaptive_model import AdaptiveScoreModel
from evidence_windows import window


def frame(n=160, seed=5):
    idx=pd.date_range("2026-09-01",periods=n,freq="h",tz="UTC")
    x=100*np.exp(np.random.default_rng(seed).normal(0,.005,n).cumsum())
    return pd.DataFrame({"Open":x,"High":x*1.002,"Low":x*.998,"Close":x,"Volume":np.arange(n)+100},index=idx)


def test_exact_utc_alignment_no_future():
    idx=pd.date_range("2026-09-01",periods=5,freq="h",tz="UTC")
    a=pd.Series([1,2,3,4,5],index=idx)
    b=pd.Series([10,11],index=idx[[1,3]].tz_convert("America/New_York"))
    x=Q._safe_align_series(a,b)
    assert list(x.index)==list(idx[[1,3]]) and list(x.s1)==[2,4]
    assert math.isnan(Q.compute_ratio_z(a.to_frame("Close"),b.to_frame("Close")))


def test_prior_mad_does_not_amplify_constant_history():
    assert Q.compute_robust_mad_zscore(pd.Series([1]*6))==0
    assert math.isnan(Q.compute_robust_mad_zscore(pd.Series([1]*6+[2])))


def test_missing_clock_momentum_is_not_neutral():
    a=frame()
    assert math.isfinite(Q.compute_intraday_direction_momentum(a))
    assert math.isnan(Q.compute_intraday_direction_momentum(a.drop(a.index[-5])))


def test_signed_short_and_unsupported_threshold(tmp_path):
    s=StatefulMemoryStore(tmp_path/"memory.json")
    for _ in range(80): s.record_score_outcome("BTC",5,-1.25,-.01)
    stats=s.score_calibration_snapshot("BTC",5,"short",1)
    assert stats["return_mean"]>0 and stats["hit_rate"]==1
    m=AdaptiveScoreModel(s)
    assert m._adaptive_candidate_threshold("BTC",5,"short",.8)[1]["adaptive"]>0
    for _ in range(120): s.record_score_outcome("ETH",5,1.25,-.01)
    assert m._adaptive_candidate_threshold("ETH",5,"long",.8)==(.8,{"adaptive":0.,"effective_n":0.,"wilson_lower":0.,"return_mean":0.})


def test_legacy_memory_preserved_not_reused(tmp_path):
    p=tmp_path/"memory.json"
    p.write_text(json.dumps({"version":"1.1.0","score_memory":{"original":123},"factor_memory":{"a":2},"pending_observations":[{"price":9}]}))
    s=StatefulMemoryStore(p)
    assert not s.memory["score_memory"] and s.memory["legacy_evidence"]["score_memory"]=={"original":123}
    assert not s.memory["pending_observations"] and s.memory["legacy_evidence"]["pending_observations"]==[{"price":9}]


def test_nonoverlap_and_exact_settlement(tmp_path):
    x=frame()
    s=StatefulMemoryStore(tmp_path/"memory.json")
    t=x.index[40]
    for j in range(5):
        s.add_pending_observation({"asset":"BTC","observed_at":(t+pd.Timedelta(hours=j)).isoformat(),
                                    "price":123,"model_score_adaptive":1,"direction":"LONG","factors":{}})
    now=t+pd.Timedelta(hours=12)
    outcome=s.settle_pending({"BTC":x},now=now.to_pydatetime())
    assert outcome["settled"]==2
    assert s.score_calibration_snapshot("BTC","REJIMSIZ_GECIS","long",.5)["n"]==2
    s2=StatefulMemoryStore(tmp_path/"m2.json")
    s2.add_pending_observation({"asset":"BTC","observed_at":t.isoformat(),"price":100,"model_score_adaptive":1})
    out=s2.settle_pending({"BTC":x.drop(t+pd.Timedelta(hours=5))},now=(t+pd.Timedelta(hours=110)).to_pydatetime())
    assert out["settled"]==0 and out["ignored"]==1


def test_features_prefix_invariant():
    x=frame(); y=frame(seed=6)
    full=c.feature_table("BTC",{"BTC":x,"ETH":y},{"DX-Y.NYB":y,"RSP":x,"SPY":y})
    prefix=c.feature_table("BTC",{"BTC":x.iloc[:100],"ETH":y.iloc[:100]},{"DX-Y.NYB":y.iloc[:100],"RSP":x.iloc[:100],"SPY":y.iloc[:100]})
    pd.testing.assert_frame_equal(full.iloc[:100],prefix)
    assert len(c.RULES)==23
    assert full.volume_break.notna().any()
    missing=c.feature_table("BTC",{"BTC":x.assign(Volume=0)}, {})
    assert missing.volume_break.isna().all() and missing.residual_trend.isna().all()


def test_challenger_no_backfill_or_duplicate(tmp_path):
    x=frame()
    now=x.index[-1]+pd.Timedelta(hours=1,minutes=2)
    paths={"ledger":str(tmp_path/"L.json"),"report":str(tmp_path/"R.json")}
    for i in range(2):
        r=c.run_cycle({"BTC":{"score":.8}},{"BTC":x},{"BTC":{}},{},now=now,**paths)
    assert r["rows"]==6 and r["no_live_promotion"]
    rows=json.loads((tmp_path/"L.json").read_text())["rows"]
    btc=next(r for r in rows if r["asset"]=="BTC")
    assert btc["signals"][list(c.RULES).index("score_z065")]==1 and not btc["labels"]
    assert len([r for r in rows if r["eligibility"]=="FRESH"])==1
