"""
Walk-Forward Signal Optimizer — the system learns its own factor weights
========================================================================
Why this exists
---------------
The 700-day point-in-time replay (historical_replay.py) showed that the
hand-weighted factor model was no better than a lagged trend follower:
model hit-rate ~= "trend takibi" at every horizon (4h 48.3 vs 49.0,
24h 46.6 vs 47.2, 72h 46.5 vs 46.2) and below "Hep AL" everywhere.
The live online learner could not fix that: its weight multiplier was
boxed into [0.65, 1.35] (a factor with a proven NEGATIVE IC kept voting
with the wrong sign at ~70% weight), it had no intercept (so it could
never learn the positive drift), it learned from 4h outcomes while the
signal horizon is 24h-1w, and its effective sample was ~34.

What it does
------------
For every asset, from the replay's point-in-time factor panel:

1. Target      y = forward log return over H hours / trailing volatility
               (vol-normalised, so calm and wild periods weigh equally).
2. Features    every factor's SIGNED reading (ham_deger x base_sign),
               clipped to +-1.8, standardised with TRAIN-ONLY statistics.
               A missing reading becomes 0 after standardisation.
3. Model       hierarchical ridge regression with an unpenalised drift
               term:   y = b0 + b_r + X (w + d_r)
               w   = weights shared across macro regimes,
               d_r = regime deviations, penalised kappa x harder, so a
                     regime only gets its own weights when its data
                     really insists (empirical-Bayes style shrinkage).
               Weights may be negative: a factor that works in reverse is
               flipped, one that carries nothing is shrunk to ~0.
4. Validation  expanding-window walk-forward: train on everything up to
               a fold start minus an EMBARGO of H hours (no label
               overlap / leakage), predict the next FOLD_DAYS, roll.
               The ridge strength is chosen inside each training window
               by a purged time split -- never with test data.
5. Evidence    on the concatenated out-of-sample predictions: rank IC,
               t = IC x sqrt(independent samples), directional hit-rate,
               mean signed return, and the SAME statistics for three
               baselines on the SAME timestamps: always-long, the legacy
               model and trend-following.
6. Deployment  the final model (same procedure, all data) is DEPLOYED for
               an asset only if its out-of-sample evidence is real:
               t(IC) >= 2, hit-rate >= always-long and positive mean
               signed return. Otherwise the asset is marked "not proven"
               and the live system abstains instead of publishing a
               signal with negative expected value.

The weekly GitHub Actions replay re-runs this on fresh data, so the
weights, the regime deviations and the deploy decision all update
themselves as evidence accumulates.
"""

from __future__ import annotations

import json
import math
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

PRIMARY_HORIZON_H = 24
HORIZONS_H = (24, 72)
MIN_TRAIN_DAYS = 90
FOLD_DAYS = 30
VOL_LOOKBACK_BARS = 240
LAMBDA_GRID = (1.0, 3.0, 10.0, 30.0, 100.0, 300.0)
REGIME_KAPPA = 4.0            # regime deviations penalised 4x harder
MIN_REGIME_ROWS = 150         # a regime needs this many training rows for its own deviation
SIGNAL_Z_MIN = 0.25           # |z| below this = no directional call when measuring hit-rate
DEPLOY_T_MIN = 2.0
CLIP_X = 1.8
CLIP_Y = 4.0
MODEL_VERSION = "wfo-1.1"


# ----------------------------------------------------------------------
# Panel construction
# ----------------------------------------------------------------------
def build_panel(
    factor_rows: Iterable[Tuple],
    meta_rows: Iterable[Tuple],
    closes: Dict[str, pd.Series],
    horizons: Tuple[int, ...] = HORIZONS_H,
) -> pd.DataFrame:
    """factor_rows: (asset, t, fid, name, cluster, signed_x)
    meta_rows:   (asset, t, regime_id, legacy_score)
    closes:      asset -> hourly close series (UTC index)
    Returns one row per (asset, t) with factor columns 'f::<fid>', regime,
    legacy score, trailing vol, past 24h return and forward returns."""
    fr = pd.DataFrame(list(factor_rows), columns=["asset", "t", "fid", "name", "cluster", "x"])
    mr = pd.DataFrame(list(meta_rows), columns=["asset", "t", "regime", "legacy_score"])
    if fr.empty or mr.empty:
        return pd.DataFrame()
    fr["t"] = pd.to_datetime(fr["t"], utc=True)
    mr["t"] = pd.to_datetime(mr["t"], utc=True)
    wide = fr.pivot_table(index=["asset", "t"], columns="fid", values="x", aggfunc="last")
    wide.columns = [f"f::{c}" for c in wide.columns]
    panel = mr.set_index(["asset", "t"]).join(wide, how="left").reset_index()

    out = []
    for asset, grp in panel.groupby("asset"):
        s = closes.get(asset)
        g = grp.sort_values("t").copy()
        if s is None or len(s) < 50:
            continue
        s = s.sort_index()
        s = s[~s.index.duplicated(keep="last")]
        s.index = pd.to_datetime(s.index, utc=True)
        logp = np.log(s.astype(float))
        ix = s.index.as_unit("ns").asi8                     # int ns, tz-safe
        tt = pd.to_datetime(g["t"], utc=True)
        tn = pd.DatetimeIndex(tt).as_unit("ns").asi8
        H1 = 3600 * 10**9
        n_s = len(s)
        pos0 = np.searchsorted(ix, tn, side="right") - 1    # last bar <= t
        valid = pos0 >= 0
        p0 = np.where(valid, logp.values[np.clip(pos0, 0, n_s - 1)], np.nan)
        r1 = logp.diff()
        vol = r1.rolling(VOL_LOOKBACK_BARS, min_periods=48).std()
        g["vol_1h"] = np.where(valid, vol.values[np.clip(pos0, 0, n_s - 1)], np.nan)
        pos24 = np.searchsorted(ix, tn - 24 * H1, side="right") - 1
        g["past_24h"] = np.where(valid & (pos24 >= 0), p0 - logp.values[np.clip(pos24, 0, n_s - 1)], np.nan)
        for h in horizons:
            tg = tn + h * H1
            pos1 = np.searchsorted(ix, tg, side="right") - 1
            ok = valid & (pos1 > pos0) & (tg <= ix[-1])
            g[f"r{h}"] = np.where(ok, logp.values[np.clip(pos1, 0, n_s - 1)] - p0, np.nan)
        out.append(g)
    if not out:
        return pd.DataFrame()
    return pd.concat(out, ignore_index=True)


# ----------------------------------------------------------------------
# Hierarchical ridge
# ----------------------------------------------------------------------
def _design(X: np.ndarray, regimes: np.ndarray, regime_list: List[Any]) -> Tuple[np.ndarray, np.ndarray]:
    """[1 | X | 1_r ... | X*1_r ...] and a penalty multiplier per column
    (0 for the global intercept, 1 for shared weights, kappa for regime terms)."""
    n, k = X.shape
    cols = [np.ones((n, 1)), X]
    pen = [0.0] + [1.0] * k
    for r in regime_list:
        m = (regimes == r).astype(float)[:, None]
        cols.append(m)
        pen.append(REGIME_KAPPA)
        cols.append(X * m)
        pen.extend([REGIME_KAPPA] * k)
    return np.hstack(cols), np.asarray(pen, dtype=float)


def _ridge(A: np.ndarray, y: np.ndarray, pen: np.ndarray, lam: float) -> np.ndarray:
    P = np.diag(pen * lam)
    return np.linalg.solve(A.T @ A + P + 1e-9 * np.eye(A.shape[1]), A.T @ y)


FAMILIES = ("ridge_regime", "ridge", "nonneg", "equal")
FAMILY_TR = {
    "ridge_regime": "ridge + rejim sapmaları",
    "ridge": "ridge (rejimsiz)",
    "nonneg": "ekonomik işaret korumalı",
    "equal": "eşit ağırlık (öğrenmesiz)",
}


class _Fitted:
    def __init__(self, feats, mu, sd, regime_list, beta, lam, family="ridge_regime"):
        self.feats, self.mu, self.sd = feats, mu, sd
        self.regime_list, self.beta, self.lam, self.family = regime_list, beta, lam, family

    def std_x(self, Xraw: np.ndarray) -> np.ndarray:
        Z = (np.clip(Xraw, -CLIP_X, CLIP_X) - self.mu) / self.sd
        return np.nan_to_num(Z, nan=0.0)

    def predict(self, Xraw: np.ndarray, regimes: np.ndarray) -> np.ndarray:
        A, _ = _design(self.std_x(Xraw), regimes, self.regime_list)
        return A @ self.beta


def _fit(Xraw: np.ndarray, y: np.ndarray, regimes: np.ndarray, feats: List[str], lam: float,
         family: str = "ridge_regime") -> _Fitted:
    """Model families (v3.4.1):
      ridge_regime : shared weights + drift + regime deviations (hierarchical)
      ridge        : shared weights + drift, no regime terms
      nonneg       : like 'ridge' but a factor may never act against its
                     economic sign (negative weights dropped and refit) and no
                     drift term -- the conservative 'prior-respecting' model
      equal        : no learning at all: equal weights on the signed factors
    """
    Xc = np.clip(Xraw, -CLIP_X, CLIP_X)
    with warnings.catch_warnings():          # a factor can be all-NaN inside one window
        warnings.simplefilter("ignore", category=RuntimeWarning)
        mu = np.nan_to_num(np.nanmean(Xc, axis=0), nan=0.0)
        sd = np.nanstd(Xc, axis=0)
    sd = np.where(~np.isfinite(sd) | (sd < 1e-6), 1.0, sd)
    Z = np.nan_to_num((Xc - mu) / sd, nan=0.0)
    k = Z.shape[1]
    if family == "equal":
        beta = np.r_[0.0, np.full(k, 1.0 / max(k, 1))]
        return _Fitted(feats, mu, sd, [], beta, 0.0, family)
    regime_list: List[Any] = []
    if family == "ridge_regime":
        vc = pd.Series(regimes).value_counts()
        regime_list = [r for r, c in vc.items() if c >= MIN_REGIME_ROWS]
    A, pen = _design(Z, regimes, regime_list)
    L = lam * len(y) / 1000.0
    beta = _ridge(A, y, pen, L)
    if family == "nonneg":
        keep = np.r_[False, beta[1:1 + k] > 0]
        beta = np.zeros(1 + k)
        if keep.any():
            b2 = _ridge(A[:, keep], y, pen[keep], L)
            beta[keep] = b2
    return _Fitted(feats, mu, sd, regime_list, beta, lam, family)


def _select_lambda(Xraw, y, regimes, t, feats, horizon_h, family="ridge_regime") -> float:
    """Purged time split inside the TRAINING window only."""
    if family == "equal" or len(y) < 200:
        return 30.0
    cut_t = t.iloc[int(len(t) * 0.75)]
    tr = (t <= cut_t - pd.Timedelta(hours=horizon_h)).values
    va = (t > cut_t).values
    if tr.sum() < 100 or va.sum() < 50:
        return 30.0
    best, best_lam = -np.inf, 30.0
    for lam in LAMBDA_GRID:
        m = _fit(Xraw[tr], y[tr], regimes[tr], feats, lam, family)
        p = m.predict(Xraw[va], regimes[va])
        ic = pd.Series(p).rank().corr(pd.Series(y[va]).rank())
        ic = -np.inf if not np.isfinite(ic) else ic
        if ic > best + 1e-9:
            best, best_lam = ic, lam
    return best_lam


# ----------------------------------------------------------------------
# Walk-forward
# ----------------------------------------------------------------------
def _xy(g: pd.DataFrame, feats: List[str], h: int):
    vol_h = g["vol_1h"].values * math.sqrt(h)
    y = g[f"r{h}"].values / np.where(vol_h > 0, vol_h, np.nan)
    y = np.clip(y, -CLIP_Y, CLIP_Y)
    X = g[feats].values.astype(float) if feats else np.zeros((len(g), 0))
    return X, y


def _stats(sig: np.ndarray, ret: np.ndarray, span_h: float, h: int) -> Dict[str, float]:
    m = np.isfinite(sig) & np.isfinite(ret) & (sig != 0)
    n = int(m.sum())
    if n == 0:
        return {"n": 0}
    hit = float((np.sign(sig[m]) == np.sign(ret[m])).mean())
    n_ind = max(1.0, span_h / h * (n / max(len(sig), 1)))
    se = math.sqrt(max(hit * (1 - hit), 1e-9) / n_ind)
    return {"n": n, "hit": round(hit, 4), "hit_lb95": round(hit - 1.96 * se, 4),
            "mean_bps": round(float(np.mean(np.sign(sig[m]) * ret[m])) * 1e4, 2),
            "n_indep": round(n_ind, 1)}


def _norm_regime(series: pd.Series) -> np.ndarray:
    # v3.4.1: CSV round-trips produced both "3" and 3 / "3.0" -> one key per regime
    return series.astype(str).str.replace(r"\.0$", "", regex=True).values


def required_t(n_tests: int) -> float:
    """Bonferroni-adjusted two-sided 95% critical value for picking the best
    of n_tests candidate models (selection must pay for its own luck)."""
    from statistics import NormalDist
    return float(NormalDist().inv_cdf(1.0 - 0.025 / max(int(n_tests), 1)))


def walk_forward_asset(g: pd.DataFrame, horizon_h: int = PRIMARY_HORIZON_H,
                       family: str = "ridge_regime") -> Dict[str, Any]:
    g = g.sort_values("t").reset_index(drop=True)
    feats = [c for c in g.columns if c.startswith("f::") and g[c].notna().mean() >= 0.30]
    if f"r{horizon_h}" not in g.columns:
        return {"status": "NO_HORIZON", "rows": 0}
    X, y = _xy(g, feats, horizon_h)
    t = g["t"]
    ok = np.isfinite(y)
    if ok.sum() < 300 or not feats:
        return {"status": "INSUFFICIENT_DATA", "rows": int(ok.sum())}
    regimes = _norm_regime(g["regime"])
    start = t.iloc[0] + pd.Timedelta(days=MIN_TRAIN_DAYS)
    fold_starts = pd.date_range(start, t.iloc[-1], freq=f"{FOLD_DAYS}D")
    oos = np.full(len(g), np.nan)
    fold_w = []
    for fs in fold_starts:
        fe = fs + pd.Timedelta(days=FOLD_DAYS)
        tr = (ok & (t <= fs - pd.Timedelta(hours=horizon_h))).values
        te = ((t > fs) & (t <= fe)).values
        if tr.sum() < 200 or te.sum() == 0:
            continue
        lam = _select_lambda(X[tr], y[tr], regimes[tr], t[tr].reset_index(drop=True), feats, horizon_h, family)
        m = _fit(X[tr], y[tr], regimes[tr], feats, lam, family)
        oos[te] = m.predict(X[te], regimes[te])
        fold_w.append(m.beta[1:1 + len(feats)])
    sel = np.isfinite(oos) & ok
    if sel.sum() < 100:
        return {"status": "INSUFFICIENT_OOS", "rows": int(sel.sum())}

    ret = g[f"r{horizon_h}"].values
    span_h = (t[sel].iloc[-1] - t[sel].iloc[0]).total_seconds() / 3600.0
    ic = float(pd.Series(oos[sel]).rank().corr(pd.Series(y[sel]).rank()))
    ic = 0.0 if not np.isfinite(ic) else ic
    n_ind = max(1.0, span_h / horizon_h)
    t_ic = ic * math.sqrt(n_ind)
    z_scale = float(np.nanstd(oos[sel])) or 1.0
    z = oos / z_scale
    learned_sig = np.where(np.abs(z) >= SIGNAL_Z_MIN, np.sign(z), 0.0)
    legacy = g["legacy_score"].values.astype(float)
    legacy_sig = np.where(np.abs(legacy) >= 0.5, np.sign(legacy), 0.0)
    trend_sig = np.sign(g["past_24h"].values.astype(float))
    ones = np.ones(len(g))
    r_sel = np.where(sel, ret, np.nan)
    ev = {
        "learned": _stats(np.where(sel, learned_sig, np.nan), r_sel, span_h, horizon_h),
        "always_long": _stats(np.where(sel, ones, np.nan), r_sel, span_h, horizon_h),
        "legacy_model": _stats(np.where(sel, legacy_sig, np.nan), r_sel, span_h, horizon_h),
        "trend_follow": _stats(np.where(sel, trend_sig, np.nan), r_sel, span_h, horizon_h),
    }
    W = np.vstack(fold_w) if fold_w else np.zeros((1, len(feats)))
    stability = (np.sign(W) == np.sign(np.median(W, axis=0))).mean(axis=0)

    last_ok = t[ok].iloc[-1]
    tr_all = (ok & (t <= last_ok)).values
    lam = _select_lambda(X[tr_all], y[tr_all], regimes[tr_all], t[tr_all].reset_index(drop=True), feats, horizon_h, family)
    final = _fit(X[tr_all], y[tr_all], regimes[tr_all], feats, lam, family)
    k = len(feats)
    regime_terms = {}
    off = 1 + k
    for r in final.regime_list:
        regime_terms[str(r)] = {"intercept": float(final.beta[off]),
                                "weights": [float(v) for v in final.beta[off + 1: off + 1 + k]]}
        off += 1 + k
    return {
        "status": "OK",
        "family": family,
        "horizon_h": horizon_h,
        "features": [f[3:] for f in feats],
        "mu": [float(v) for v in final.mu],
        "sd": [float(v) for v in final.sd],
        "intercept": float(final.beta[0]),
        "weights": [float(v) for v in final.beta[1:1 + k]],
        "regime_terms": regime_terms,
        "lambda": lam,
        "z_scale": z_scale,
        "weight_sign_stability": {f[3:]: round(float(s_), 3) for f, s_ in zip(feats, stability)},
        "oos": {"ic": round(ic, 4), "t_ic": round(t_ic, 2), "rows": int(sel.sum()),
                "from": str(t[sel].iloc[0]), "to": str(t[sel].iloc[-1]), **{k2: v for k2, v in ev.items()}},
        "trained_until": str(last_ok),
        "train_rows": int(tr_all.sum()),
    }


def _deployable(m: Dict[str, Any], t_req: float) -> bool:
    if m.get("status") != "OK":
        return False
    o = m["oos"]
    lw, al = o.get("learned") or {}, o.get("always_long") or {}
    return bool(o.get("t_ic", 0) >= t_req and lw.get("n", 0) > 0
                and lw.get("hit", 0) >= al.get("hit", 1) and lw.get("mean_bps", -1) > 0)


def optimize(panel: pd.DataFrame, horizons: Tuple[int, ...] = HORIZONS_H,
             families: Tuple[str, ...] = FAMILIES) -> Dict[str, Any]:
    """Self-optimising model selection (v3.4.1): every asset tries every
    (family x horizon) candidate out-of-sample and keeps the best by t(IC).
    Because picking the best of N candidates inflates luck, deployment needs
    the Bonferroni-adjusted t, not 2.0."""
    n_tests = len(horizons) * len(families)
    t_req = required_t(n_tests)
    res = {"version": MODEL_VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
           "horizons_h": list(horizons), "families": list(families), "n_tests": n_tests,
           "t_required": round(t_req, 2), "assets": {}}
    if panel is None or panel.empty:
        return res
    for asset, g in panel.groupby("asset"):
        cands: List[Dict[str, Any]] = []
        for h in horizons:
            for fam in families:
                try:
                    m = walk_forward_asset(g, h, fam)
                except Exception as exc:          # never break the replay report
                    m = {"status": f"ERROR: {exc}"}
                m.setdefault("family", fam)
                m.setdefault("horizon_h", h)
                cands.append(m)
        ok = [m for m in cands if m.get("status") == "OK"]
        if not ok:
            res["assets"][str(asset)] = {"status": cands[0].get("status", "NO_MODEL"), "rows": cands[0].get("rows", 0)}
            continue
        best = max(ok, key=lambda m: m["oos"]["t_ic"])
        best = dict(best)
        best["deploy"] = _deployable(best, t_req)
        best["t_required"] = round(t_req, 2)
        best["candidates"] = [
            {"family": m.get("family"), "horizon_h": m.get("horizon_h"), "status": m.get("status"),
             "ic": (m.get("oos") or {}).get("ic"), "t_ic": (m.get("oos") or {}).get("t_ic"),
             "hit": ((m.get("oos") or {}).get("learned") or {}).get("hit"),
             "mean_bps": ((m.get("oos") or {}).get("learned") or {}).get("mean_bps")}
            for m in cands
        ]
        res["assets"][str(asset)] = best
    return res


# ----------------------------------------------------------------------
# Live scoring
# ----------------------------------------------------------------------
def score_live(model: Dict[str, Any], signed_values: Dict[str, float], regime_id: Any) -> Optional[Dict[str, Any]]:
    """Returns {'z', 'expected_vol_units', 'contributions': {fid: c}} or None."""
    if not model or model.get("status") != "OK":
        return None
    feats = model["features"]
    x = np.array([signed_values.get(f, np.nan) for f in feats], dtype=float)
    mu, sd = np.array(model["mu"]), np.array(model["sd"])
    zx = np.nan_to_num((np.clip(x, -CLIP_X, CLIP_X) - mu) / sd, nan=0.0)
    w = np.array(model["weights"], dtype=float)
    b = float(model["intercept"])
    rt = (model.get("regime_terms") or {}).get(str(regime_id))
    if rt:
        w = w + np.array(rt["weights"], dtype=float)
        b += float(rt["intercept"])
    contrib = zx * w
    pred = b + float(contrib.sum())
    zs = float(model.get("z_scale") or 1.0)
    return {
        "z": float(np.clip(pred / zs, -3.5, 3.5)),
        "expected_vol_units": pred,
        "drift_component": b / zs,
        "contributions": {f: float(c / zs) for f, c in zip(feats, contrib)},
        "missing": [f for f, v in zip(feats, x) if not np.isfinite(v)],
    }


def report_lines(res: Dict[str, Any]) -> List[str]:
    tr = res.get("t_required", DEPLOY_T_MIN)
    L = ["## 🤖 Kendini optimize eden model (walk-forward, örneklem dışı)",
         f"Her varlık için {res.get('n_tests', 1)} aday model ({', '.join(FAMILY_TR.get(f, f) for f in res.get('families', []))}"
         f" × ufuk {res.get('horizons_h')}) yalnız o güne kadarki veriyle eğitilip hiç görülmemiş veride sınandı; "
         "eğitim ile test arasında ufuk kadar ambargo var.",
         f"**Canlıya alma kuralı:** en iyi adayın t(IC) ≥ {tr} (en iyiyi seçmenin şans payı düzeltilmiş eşik), "
         "isabet ≥ Hep AL ve ortalama getiri > 0. Sağlamayan varlıkta sinyal **bilgi amaçlı (KANITSIZ)** gösterilir, "
         "işleme giriş izni verilmez.", "",
         "| Varlık | Durum | En iyi aday | IC | t | Öğrenilmiş | Eski model | Hep AL | Trend |",
         "|---|---|---|---|---|---|---|---|---|"]
    f = lambda d: "—" if not d or not d.get("n") else f"%{d['hit']*100:.1f} / {d['mean_bps']:+.0f}bps"
    for a, m in sorted(res.get("assets", {}).items()):
        if m.get("status") != "OK":
            L.append(f"| {a} | {m.get('status')} | — | — | — | — | — | — | — |")
            continue
        o = m["oos"]
        st = "✅ CANLI" if m.get("deploy") else "⛔ kanıt yok"
        L.append(f"| {a} | {st} | {FAMILY_TR.get(m.get('family'), m.get('family'))}, {m.get('horizon_h')}s | "
                 f"{o['ic']:+.3f} | {o['t_ic']:+.1f} | {f(o['learned'])} | {f(o['legacy_model'])} | "
                 f"{f(o['always_long'])} | {f(o['trend_follow'])} |")
    L.append("")
    L.append("**Tüm adaylar (t değeri):**")
    for a, m in sorted(res.get("assets", {}).items()):
        if m.get("status") != "OK":
            continue
        c = ", ".join(f"{FAMILY_TR.get(x['family'], x['family'])}/{x['horizon_h']}s "
                      f"{'—' if x.get('t_ic') is None else format(x['t_ic'], '+.1f')}" for x in m.get("candidates", []))
        L.append(f"- **{a}**: {c}")
    L.append("")
    return L


def save(res: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
