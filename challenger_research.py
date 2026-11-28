"""Fixed, causal challenger tournament. Research only; never modifies decisions."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from config import ASSET_MATRICES, LOGIC_VERSION, is_directional
from evidence_windows import SCHEMA, bars, fresh_frame, grade_endpoint, utc, window
from state_schema import atomic_write_json
from system_clock import now_utc

METHOD = "T1_CHALLENGERS_V1"
HORIZONS = (4, 24, 72)
MAX_ROWS = 16000
LEDGER = "challenger_evidence.json"
REPORT = "challenger_report.json"
SYMBOLS = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SPX": "ES=F", "NQ": "NQ=F",
           "XAU": "GC=F", "XAG": "SI=F"}
PEERS = {"BTC": "ETH", "ETH": "BTC", "SPX": "NQ", "NQ": "SPX", "XAU": "XAG", "XAG": "XAU"}
# Frozen candidates; missing is null, no trade is 0. No ranking/selection by return.
RULES = {
    "mom4_z05": "4 elapsed hours, prior 48 hourly volatility, |z| >= .5",
    "mom4_z10": "4 elapsed hours, prior 48 hourly volatility, |z| >= 1",
    "mom24_z05": "24 elapsed hours, prior 48 hourly volatility, |z| >= .5",
    "fade4_z10": "opposite of mom4_z10",
    "trend_confirm": "4h and 24h momentum agree",
    "donchian20": "close outside prior 20 observed bars high/low",
    "donchian48": "close outside prior 48 observed bars high/low",
    "failed_break20": "high/low breaches prior 20 range but close returns inside",
    "bollinger20": "close beyond prior 20-bar mean +/- 2 std",
    "compression_break": "prior 20-bar volatility in bottom 25% of preceding 48; Donchian20",
    "volume_break": "Donchian20 with volume >= 1.5x prior 20 median (positive volume only)",
    "absorption_proxy": "volume >= 1.5x prior median, small body, close in outer quartile of range; not taker flow",
    "rsi_revert": "prior 14 observed bar gains/losses; RSI <= 30 / >= 70",
    "residual_trend": "4h sum of hourly peer residuals, beta estimated from preceding 48 exact paired changes, |z| >= .5",
    "residual_fade": "opposite of residual_trend",
    "macro_proxy": "3+ exact 4h pair votes, latest completed <=59min before asset bar time, >= 2/3 consensus; asset-specific signs",
    "macro_contrarian": "opposite of macro_proxy",
    "score_z035": "current aggregate score magnitude >= .35",
    "score_z065": "current aggregate score magnitude >= .65",
    "score_z100": "current aggregate score magnitude >= 1",
    "equal_cluster": "equal weight of >=2 observed directional clusters, mean signed raw >= .35",
    "flow_pressure": "BTC/ETH spot+linear fresh native sample imbalance agree at magnitude >= .08",
    "flow_divergence": "same flow pressure opposed to last completed hourly price body",
}
REGISTRY = hashlib.sha256(json.dumps({"method": METHOD, "rules": RULES, "horizons": HORIZONS,
                                      "label": SCHEMA}, sort_keys=True).encode()).hexdigest()
PRICE_RULES = tuple(list(RULES)[:17])
FLOW_RULES = ("flow_pressure", "flow_divergence")


def num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def side(x, threshold):
    v = num(x)
    return None if v is None else 1 if v >= threshold else -1 if v <= -threshold else 0


def hourly_close(frame):
    c = bars(frame, ["Close"])["Close"].dropna()
    # Yahoo hourly US equity-market bars can start at :30. Do not assign them
    # to :00 or fabricate a matched time; only exact timestamp comparisons.
    return c


def lag_exact(series, hours):
    x = series.copy()
    x.index = x.index + pd.Timedelta(hours=hours)
    return x.reindex(series.index)


def asof_vote(series, index):
    # Each value was measured at an actual joint timestamp. US ETF candles
    # can be offset by 30 minutes; allow only an earlier completed observation.
    return series.sort_index().reindex(index, method="ffill", tolerance=pd.Timedelta(minutes=59))


def log_change(c, h):
    return np.log(c / lag_exact(c, h))


def categorical(up, down, valid):
    # Ambiguous simultaneous breakout is neutral (not look-ahead resolution).
    return pd.Series(np.select([up & ~down, down & ~up], [1., -1.], default=0.),
                     index=valid.index).where(valid)


def threshold(z, threshold):
    return categorical(z >= threshold, z <= -threshold, z.notna() & np.isfinite(z))


def feature_table(asset, frames, grid):
    x = bars(frames.get(asset), ["Open", "High", "Low", "Close"])
    x = x.dropna()
    if x.empty:
        return pd.DataFrame(index=x.index, columns=PRICE_RULES, dtype=float)
    x = x[(x.High >= x[["Open", "Close"]].max(axis=1)) & (x.Low <= x[["Open", "Close"]].min(axis=1))]
    c = x.Close
    r = log_change(c, 1)
    sigma = r.shift(1).rolling(48, min_periods=30).std().replace(0, np.nan)
    z4, z24 = log_change(c, 4)/(sigma*2), log_change(c, 24)/(sigma*np.sqrt(24))
    f = pd.DataFrame(index=c.index)
    f["mom4_z05"], f["mom4_z10"], f["mom24_z05"] = threshold(z4,.5), threshold(z4,1), threshold(z24,.5)
    f["fade4_z10"] = -f.mom4_z10
    f["trend_confirm"] = categorical((z4>=.5)&(z24>=.5),(z4<=-.5)&(z24<=-.5),z4.notna()&z24.notna())
    for n in (20, 48):
        hi, lo = x.High.shift(1).rolling(n).max(), x.Low.shift(1).rolling(n).min()
        f[f"donchian{n}"] = categorical(c>hi,c<lo,hi.notna()&lo.notna())
        if n == 20:
            f["failed_break20"] = categorical((x.Low<lo)&(c>lo),(x.High>hi)&(c<hi),hi.notna()&lo.notna())
    mean, std = c.shift(1).rolling(20).mean(), c.shift(1).rolling(20).std()
    f["bollinger20"] = threshold((c-mean)/std.replace(0,np.nan),2)
    vol = r.rolling(20,min_periods=14).std().shift(1)
    q = vol.shift(1).rolling(48,min_periods=30).quantile(.25)
    f["compression_break"] = f.donchian20.where(vol<=q,0).where(vol.notna()&q.notna()&f.donchian20.notna())
    v = bars(frames.get(asset), ["Volume"]).Volume.reindex(c.index)
    rv = v/v.shift(1).rolling(20,min_periods=15).median().replace(0,np.nan)
    f["volume_break"] = f.donchian20.where(rv>=1.5,0).where(rv.notna()&f.donchian20.notna())
    width = (x.High-x.Low).replace(0,np.nan)
    loc, body = (c-x.Low)/width,(c-x.Open).abs()/width
    f["absorption_proxy"] = categorical((rv>=1.5)&(body<=.35)&(loc>=.75),(rv>=1.5)&(body<=.35)&(loc<=.25),rv.notna()&loc.notna())
    delta = c.diff()
    gain, loss = delta.clip(lower=0).rolling(14).sum(), (-delta.clip(upper=0)).rolling(14).sum()
    rsi = 100*gain/(gain+loss).replace(0,np.nan)
    f["rsi_revert"] = categorical(rsi<=30,rsi>=70,rsi.notna())
    peer = hourly_close(frames.get(PEERS[asset]))
    pr = log_change(peer,1).reindex(c.index)
    own = r.where(pr.notna())
    beta = own.shift(1).rolling(48,min_periods=30).cov(pr.shift(1))/pr.shift(1).rolling(48,min_periods=30).var().replace(0,np.nan)
    residual = own-beta*pr
    rz = residual.rolling(4,min_periods=4).sum()/(2*residual.shift(1).rolling(48,min_periods=30).std().replace(0,np.nan))
    # Four exact returns must be consecutive, even across session closures.
    rz = rz.where(log_change(c,4).notna())
    f["residual_trend"], f["residual_fade"] = threshold(rz,.5), -threshold(rz,.5)
    pairs = [("RSP","SPY",1),("HYG","LQD",1),("SMH","QQQ",1),("XLY","XLP",1)]
    if asset in ("XAU","XAG"):
        pairs = [("TLT","SHY",1),("RSP","SPY",-1),("XLY","XLP",-1),("HYG","LQD",-1)]
    votes = []
    for a,b,sgn in pairs:
        pair = pd.concat([hourly_close(grid.get(a)),hourly_close(grid.get(b))],axis=1,join="inner").dropna()
        ratio = pair.iloc[:,0]/pair.iloc[:,1]
        votes.append(sgn*asof_vote(np.sign(log_change(ratio,4)),c.index))
    votes.append(-asof_vote(np.sign(log_change(hourly_close(grid.get("DX-Y.NYB",grid.get("DXY"))),4)),c.index))
    vote = pd.concat(votes,axis=1)
    n, total = vote.notna().sum(axis=1),vote.sum(axis=1)
    f["macro_proxy"] = categorical(total>=n*2/3,total<=-n*2/3,n>=3)
    f["macro_contrarian"] = -f.macro_proxy
    return f.reindex(columns=PRICE_RULES)


def current_score_rules(asset, verdict):
    result = {f"score_z{k}": side(verdict.get("score"), t) for k,t in (("035",.35),("065",.65),("100",1))}
    factors = {i["name"]:i for i in ASSET_MATRICES[asset]["factors"] if is_directional(i)}
    clusters = {}
    for d in verdict.get("details") or []:
        p = factors.get(d.get("faktör"))
        raw = num(d.get("ham_deger"))
        if p and raw is not None:
            clusters.setdefault(p["cluster"], []).append(raw*p["base_sign"])
    result["equal_cluster"] = side(np.mean([np.mean(v) for v in clusters.values()]),.35) if len(clusters)>=2 else None
    return result


def flow_rules(asset, frame, now, path="research_30d/observations.csv"):
    out = dict.fromkeys(FLOW_RULES)
    if asset not in ("BTC","ETH") or not Path(path).exists():
        return out
    valid = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("asset")!=asset or row.get("status")!="OK_SAMPLE":
                continue
            ms = num(row.get("observed_at_ms"))
            if ms is None or not 0 <= now.timestamp()-ms/1000 <= 300:
                continue
            valid[row["market"]] = side(row.get("imbalance"),.08)
    if not {"spot","linear"}.issubset(valid) or None in valid.values():
        return out
    pressure = valid["spot"] if valid["spot"]==valid["linear"] else 0
    out["flow_pressure"] = pressure
    x = bars(frame,["Open","Close"])
    t = now.floor("h")-pd.Timedelta(hours=1)
    if t in x.index and x.loc[t].notna().all():
        out["flow_divergence"] = pressure if pressure*(x.loc[t,"Close"]-x.loc[t,"Open"])<=0 else 0
    return out


def make_row(asset, observed, status, signals):
    return {"asset":asset,"observed":utc(observed).isoformat(),"eligibility":status,
            "signals":[None if num(signals.get(k)) is None else int(signals[k]) for k in RULES],"labels":{}}


def reserve_slots(row, reservations):
    row["slots"] = []
    if row["eligibility"] != "FRESH":
        return
    last = reservations.setdefault(row["asset"], {})
    for h in HORIZONS:
        start,end = window(row["observed"],h)
        if str(h) not in last or start >= utc(last[str(h)]):
            row["slots"].append(h)
            last[str(h)] = end.isoformat()


def summary(rows, now, mode):
    result = {}
    for asset in SYMBOLS:
        ar = sorted((r for r in rows if r["asset"]==asset),key=lambda r:r["observed"])
        recent=[r for r in ar if r["eligibility"]=="FRESH"][-24:]
        data = {"coverage":dict(Counter(r["eligibility"] for r in ar)),"horizons":{},
                "recent_fresh_slots":len(recent),
                "recent_rule_availability":{k:sum(r["signals"][i] is not None for r in recent)
                                            for i,k in enumerate(RULES)}}
        for h in HORIZONS:
            sampled, last = [], None
            for r in ar:
                if r["eligibility"]!="FRESH": continue
                if "slots" in r:
                    if h in r["slots"]: sampled.append(r)
                    continue
                start,end = window(r["observed"],h)
                if last is not None and start<last: continue
                sampled.append(r)
                last=end
            known = [r for r in sampled if r["labels"].get(str(h),{}).get("status")=="EXACT"]
            metrics = {}
            for i,k in enumerate(RULES):
                active = [(r["signals"][i],r["labels"][str(h)]["log_return"],r["signals"][0])
                          for r in known if r["signals"][i] in (-1,1)]
                n=len(active)
                raw=np.array([s*ret*10000 for s,ret,_ in active])
                # Split by chronological order, report all three; no winning model selected.
                matched=[((s-base)*ret*10000) for s,ret,base in active if base is not None]
                valid_count=sum(r["signals"][i] is not None for r in known)
                metrics[k]={"n":n,"available":valid_count,"neutral":valid_count-n,"missing":len(known)-valid_count,
                            "hit":round(float((raw>0).mean()),4) if n else None,
                            "mean_bps":round(float(raw.mean()),3) if n else None,
                            "cost_sensitivity_bps":{str(c):round(float(raw.mean()-c),3) for c in (2,5,10)} if n else {},
                            "same_windows_long_bps":round(float(np.mean([r*10000 for _,r,_ in active])),3) if n else None,
                            "same_windows_short_bps":round(float(np.mean([-r*10000 for _,r,_ in active])),3) if n else None,
                            "vs_mom4_bps":round(float(np.mean(matched)),3) if matched else None,
                            "matched_n":len(matched),
                            "chronological_thirds_bps":[round(float(a.mean()),3) if len(a) else None for a in np.array_split(raw,3)],
                            "status":"DESCRIPTIVE_ONLY" if n>=100 else "INSUFFICIENT"}
            data["horizons"][str(h)]={"scheduled":len(sampled),"exact":len(known),
                                     "labels":dict(Counter(r["labels"].get(str(h),{}).get("status","PENDING") for r in sampled)),
                                     "rules":metrics}
        result[asset]=data
    return {"method":METHOD,"registry_sha256":REGISTRY,"logic_version":LOGIC_VERSION,"label_schema":SCHEMA,
            "status":"RESEARCH_ONLY","mode":mode,"as_of":utc(now).isoformat(),"rules":RULES,
            "no_live_promotion":True,"multiple_testing":"All rules reported; no inferential significance or winner selection.",
            "assets":result}


def settle(rows, frames, now):
    for r in rows:
        if r["eligibility"]!="FRESH": continue
        for h in r.get("slots", HORIZONS):
            if str(h) in r["labels"]: continue
            v=grade_endpoint(frames.get(r["asset"]),r["observed"],h,now,contiguous=h==4)
            if v["status"]!="PENDING": r["labels"][str(h)]=v


def run_cycle(verdicts, frames, contexts, grid, *, now=None, ledger=LEDGER, report=REPORT):
    now=utc(now or now_utc())
    path=Path(ledger)
    saved=json.loads(path.read_text()) if path.exists() else {"registry":REGISTRY,"logic_version":LOGIC_VERSION,"reservations":{},"rows":[]}
    if saved["registry"]!=REGISTRY or saved.get("logic_version")!=LOGIC_VERSION:
        raise ValueError("Registry changed; new ledger/method required")
    rows=saved["rows"]
    reservations=saved["reservations"]
    settle(rows,frames,now)
    current={}
    for asset in SYMBOLS:
        frame=frames.get(asset)
        closed=(contexts.get(asset,{}).get("session") or {}).get("phase")=="Kapalı"
        status="MARKET_CLOSED" if closed else "FRESH" if fresh_frame(frame,now) else "STALE_OR_MISSING"
        sig={}
        if status=="FRESH":
            tab=feature_table(asset,frames,grid)
            t=now.floor("h")-pd.Timedelta(hours=1)
            if t in tab.index: sig.update(tab.loc[t].to_dict())
            sig.update(current_score_rules(asset,verdicts.get(asset,{})))
            sig.update(flow_rules(asset,frame,now))
        rec=make_row(asset,now,status,sig)
        if not any(r["asset"]==asset and utc(r["observed"]).floor("h")==now.floor("h") for r in rows[-36:]):
            reserve_slots(rec,reservations)
            rows.append(rec)
        current[asset]={"eligibility":status,"available":sum(x is not None for x in rec["signals"]),"total":len(RULES) if asset in ("BTC","ETH") else len(RULES)-len(FLOW_RULES)}
    rows=rows[-MAX_ROWS:]
    result=summary(rows,now,"PROSPECTIVE")
    result["current"]=current
    missing_windows={}
    for asset in SYMBOLS:
        a=result["assets"][asset]["horizons"]["4"]["labels"]
        exact=a.get("EXACT",0); missing=a.get("MISSING_EXACT_WINDOW",0)
        if exact+missing>=12 and missing/(exact+missing)>.25:
            missing_windows[asset]={"exact":exact,"missing":missing}
    result["label_coverage_alerts"]=missing_windows
    atomic_write_json(str(path),{"registry":REGISTRY,"logic_version":LOGIC_VERSION,"reservations":reservations,"rows":rows},indent=None)
    atomic_write_json(str(report),result,indent=2)
    return {"status":"RESEARCH_ONLY","method":METHOD,"rules":len(RULES),
            "rows":len(rows),"current":current,"label_coverage_alerts":missing_windows,"report":str(report),"no_live_promotion":True}


def bootstrap(directory, now, *, report):
    """Exploratory archive only; never writes the forward ledger."""
    grid={}
    for p in Path(directory).glob("*.csv"):
        if p.stem.endswith("_1D"): continue
        key=p.stem.replace("_F","=F").replace("_X","=X")
        try:
            df=pd.read_csv(p,index_col="timestamp",parse_dates=True)
            df.index=pd.to_datetime(df.index,utc=True)
            grid[key]=df[df.index+pd.Timedelta(hours=1)<=utc(now)]
        except (ValueError,KeyError): continue
    frames={a:grid.get(s) for a,s in SYMBOLS.items()}
    rows=[]
    reservations={}
    for asset in SYMBOLS:
        tab=feature_table(asset,frames,grid)
        for t,r in tab.iterrows():
            if t.minute != 0 or t.second != 0: continue
            rec=make_row(asset,t+pd.Timedelta(hours=1),"FRESH",r.to_dict())
            reserve_slots(rec,reservations)
            rows.append(rec)
    settle(rows,frames,utc(now))
    result=summary(rows,now,"HISTORICAL_EXPLORATORY_NOT_FORWARD")
    atomic_write_json(str(report),result,indent=2)
    return result
