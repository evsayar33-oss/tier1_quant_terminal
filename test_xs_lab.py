"""Tests for xs_lab (v9.0): point-in-time universe/weights, P&L accounting, noise vs planted cross-sectional edge."""
import math

import numpy as np
import pandas as pd

import xs_lab as X


def _panel(S=70, T=2300, seed=0, edge=0.0, carry_edge=0.0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-01", periods=T, freq="D", tz="UTC")
    rows = []
    # persistent coin-specific drift that changes every ~60 days -> momentum works when edge > 0
    for s in range(S):
        start = int(rng.integers(0, 600))
        end = T if rng.random() > 0.15 else int(rng.integers(start + 300, T))      # some coins are delisted
        drift = np.repeat(rng.normal(0, 1, T // 60 + 1), 60)[:T] * edge
        fund = rng.normal(0, 0.0003, T)
        r = drift + rng.normal(0, 0.04, T) - carry_edge * np.r_[0.0, fund[:-1]] * 30
        c = 10 * np.exp(np.cumsum(r))
        qv = np.exp(rng.normal(15 + (S - s) * 0.02, 0.3, T))
        for t in range(start, end):
            rows.append((dates[t], f"C{s:03d}USDT", c[t], c[t], c[t], c[t], qv[t], fund[t]))
    df = pd.DataFrame(rows, columns=["date", "symbol", "open", "high", "low", "close", "quote_volume", "funding"])
    btc = df[df.symbol == "C000USDT"].copy()
    btc["symbol"] = "BTCUSDT"
    return pd.concat([df, btc], ignore_index=True)


def test_weights_are_point_in_time():
    P = _panel(S=40, T=900, seed=1)
    W = X.wide(P)
    F = X.features(W)
    U = X.universe(W, 20)
    vol = np.log(W["close"] / W["close"].shift(1)).rolling(28, min_periods=20).std()
    w = X.weights(F["mom:28"], U, 0.2, "LS", "iv", vol, 7)
    cut = W["close"].index[600]
    P2 = P[P["date"] <= cut]
    W2 = X.wide(P2)
    F2 = X.features(W2)
    U2 = X.universe(W2, 20)
    vol2 = np.log(W2["close"] / W2["close"].shift(1)).rolling(28, min_periods=20).std()
    w2 = X.weights(F2["mom:28"], U2, 0.2, "LS", "iv", vol2, 7)
    cols = list(W2["close"].columns)
    idx = [list(W["close"].columns).index(c) for c in cols]
    assert np.allclose(w[:601][:, idx], w2)
    # market-neutral book: +0.5 long, -0.5 short when active
    act = np.abs(w).sum(1) > 0
    assert np.allclose(w[act].sum(1), 0.0) and np.allclose(np.abs(w[act]).sum(1), 1.0)


def test_pnl_accounting_funding_costs_and_delisting():
    R = np.array([[np.nan, np.nan], [0.10, -0.05], [0.02, np.nan], [0.01, 0.0]])
    Fd = np.array([[0, 0], [0.001, 0.002], [0.0, 0.0], [0, 0]], float)
    w = np.array([[0.5, -0.5], [0.5, -0.5], [0.5, 0.0], [0, 0]], float)
    out = X.pnl(w, R, Fd, 0.001)
    # day1: 0.5*0.10 + (-0.5)*(-0.05) - (0.5*0.001 - 0.5*0.002) - cost*1.0
    assert math.isclose(out[1], 0.05 + 0.025 - (0.0005 - 0.001) - 0.001)
    # day2: second coin stopped trading -> exited at its last close (no return, exit cost)
    assert math.isclose(out[2], 0.5 * 0.02 - 0.001 * 0.5)
    assert math.isclose(out[3], 0.5 * 0.01 - 0.001 * 0.0)


def test_noise_is_not_proven():
    res = X.research(_panel(S=60, T=2300, seed=2), ns=(20,), qs=(0.2,), rebals=(7,))
    assert not res["proven"], res["chosen"]


def test_planted_cross_sectional_momentum_is_proven():
    res = X.research(_panel(S=70, T=2300, seed=3, edge=0.004), ns=(20, 50), qs=(0.2,), rebals=(1, 7))
    assert res["chosen"]["label"].startswith(("Momentum", "Riske göre")), res["chosen"]
    assert res["proven"], (res["chosen"], res["wf"], res["ok"])
    fam = {f["family"]: f for f in res["families"]}
    assert fam["Momentum (28g) · long/short"]["exam_mean"] > 1.0
    assert "mühürlü" in X.report_md(res)


def test_archive_download_offline(monkeypatch, tmp_path):
    import io
    import zipfile
    import xs_data

    def z(text):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as f:
            f.writestr("x.csv", text)
        return b.getvalue()

    months = ["2024-01", "2024-02"]

    def fake(url, params=None, timeout=60):
        if url == xs_data.S3:
            pre = params["prefix"]
            if pre == "data/futures/um/monthly/klines/":
                return ("<ListBucketResult><Prefix>" + pre + "</Prefix><CommonPrefixes><Prefix>" + pre + "AAAUSDT/</Prefix></CommonPrefixes>"
                        "<CommonPrefixes><Prefix>" + pre + "USDCUSDT/</Prefix></CommonPrefixes></ListBucketResult>").encode()
            if "AAAUSDT" in pre:
                kind = "klines/AAAUSDT/1d" if "klines" in pre else "fundingRate/AAAUSDT"
                return ("<ListBucketResult><Prefix>x</Prefix>" + "".join(
                    f"<Key>data/futures/um/monthly/{kind}/AAAUSDT-{'1d' if 'klines' in pre else 'fundingRate'}-{m}.zip</Key>" for m in months)
                        + "</ListBucketResult>").encode()
            return b"<ListBucketResult></ListBucketResult>"
        for m in months:
            if url.endswith(f"AAAUSDT-1d-{m}.zip"):
                days = pd.date_range(m + "-01", periods=3, freq="D", tz="UTC")
                head = "open_time,open,high,low,close,volume,close_time,quote_volume,count,tbv,tbqv,ignore\n" if m == "2024-02" else ""
                return z(head + "".join(f"{d.value // 10**6},1,2,0.5,1.5,10,0,100,1,1,1,0\n" for d in days))
            if url.endswith(f"AAAUSDT-fundingRate-{m}.zip"):
                t0 = pd.Timestamp(m + "-01", tz="UTC").value // 10**6
                return z("calc_time,funding_interval_hours,last_funding_rate\n" +
                         "".join(f"{t0 + h * 3600_000},8,0.0001\n" for h in (0, 8, 16)))
        return None

    monkeypatch.setattr(xs_data, "_get", fake)
    out = str(tmp_path / "p.csv.gz")
    P = xs_data.build(out, start="2024-01", workers=2)
    assert set(P["symbol"]) == {"AAAUSDT"}                               # stablecoin pair excluded
    assert len(P) == 6 and np.allclose(P["close"], 1.5) and np.allclose(P["quote_volume"], 100)
    first_days = P[P["date"].dt.day == 1]
    assert np.allclose(first_days["funding"], 0.0003)                  # three 8-hour payments summed per day
