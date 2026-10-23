import numpy as np
import pandas as pd

import shock_monitor as SM


def _panel(shock_on=("ES", "NQ", "VIX"), signs=(-1, -1, 1), seed=0):
    idx = pd.date_range("2026-10-20", periods=12 * 24 * 3, freq="5min", tz="UTC")
    rng = np.random.default_rng(seed)
    out = {}
    for k in SM.PANEL:
        r = rng.normal(0, 0.001, len(idx))
        if k in shock_on:
            r[-6:-3] += signs[shock_on.index(k)] * 0.004      # ~3 bar içinde ~7σ
        out[k] = pd.DataFrame({"Close": 100 * np.exp(np.cumsum(r))}, index=idx)
    return out, idx[-1]


def test_broad_risk_off_detected_and_factor():
    panel, now = _panel()
    s = SM.detect(panel, now)
    assert s["active"] and s["broad"] and s["pattern"].startswith("risk-off")
    assert set(s["affected"]) == {"SPX", "NQ", "XAU", "XAG", "BTC", "ETH"}
    assert "⚡ Şok" in SM.note(s, "SPX")
    assert 1.0 <= SM.factor(s, "SPX") <= 2.0


def test_quiet_market_no_shock():
    panel, now = _panel(shock_on=())
    assert not SM.detect(panel, now)["active"]


def test_crypto_only_is_local():
    panel, now = _panel(shock_on=("BTC", "ETH"), signs=(1, 1))
    s = SM.detect(panel, now)
    assert s["active"] and not s["broad"] and s["pattern"] == "kriptoya özgü"
    assert s["affected"] == ["BTC", "ETH"] and SM.note(s, "SPX") == ""


def test_ledger_records_and_grades(tmp_path):
    panel, now = _panel()
    p = str(tmp_path / "s.csv")
    s = SM.detect(panel, now - pd.Timedelta(hours=5))
    shock_t = now - pd.Timedelta(minutes=20)
    s = SM.detect(panel, now)
    SM.ledger_cycle(s, panel, path=p, now=now)
    later = {k: pd.concat([df, pd.DataFrame({"Close": [df["Close"].iloc[-1]] * 60},
                                            index=pd.date_range(now + pd.Timedelta(minutes=5), periods=60, freq="5min"))])
             for k, df in panel.items()}
    out = SM.ledger_cycle(s, later, path=p, now=now + pd.Timedelta(hours=5))
    assert out["n"] >= 3 and 0.0 <= out["continuation"] <= 1.0


def test_session_open_gap_is_not_a_shock():
    idx1 = pd.date_range("2026-10-21 13:30", periods=78, freq="5min", tz="UTC")
    idx2 = pd.date_range("2026-10-22 13:30", periods=78, freq="5min", tz="UTC")
    rng = np.random.default_rng(5)
    r1, r2 = rng.normal(0, 0.0005, 78), rng.normal(0, 0.0005, 78)
    c1 = 20 * np.exp(np.cumsum(r1))
    c2 = c1[-1] * 1.08 * np.exp(np.cumsum(r2))              # gece %8 boşluk
    idx = idx1.append(pd.date_range("2026-10-20 13:30", periods=0, freq="5min", tz="UTC")).append(idx2)
    df = pd.DataFrame({"Close": np.r_[c1, c2]}, index=idx)
    s = SM.scan(df, idx2[3], lookback_h=4)
    assert abs(s["z15"]) < 5 and abs(s["z60"]) < 4
