"""v15.0 — dealer gamma map, its self-grading ledger, and the factor 'state' role."""
import math
import os
import tempfile

import numpy as np
import pandas as pd

import dealer_gamma as DG

NOW = pd.Timestamp("2026-10-14T15:00:00Z")          # Tuesday, NY 11:00
TODAY = pd.Timestamp("2026-10-14")


def _chain(spot, call_k, put_k, expiry=TODAY, oi=50_000, iv=0.20, root="NDX"):
    rows = []
    for k in np.arange(spot * 0.9, spot * 1.1, spot * 0.005):
        k = round(k, 2)
        rows.append({"root": root, "expiry": expiry, "type": "C", "strike": k, "iv": iv, "oi": 100.0, "volume": 0.0})
        rows.append({"root": root, "expiry": expiry, "type": "P", "strike": k, "iv": iv, "oi": 100.0, "volume": 0.0})
    rows.append({"root": root, "expiry": expiry, "type": "C", "strike": call_k, "iv": iv, "oi": oi, "volume": 0.0})
    rows.append({"root": root, "expiry": expiry, "type": "P", "strike": put_k, "iv": iv, "oi": oi, "volume": 0.0})
    return pd.DataFrame(rows)


def test_bs_gamma_matches_finite_difference_of_delta():
    from scipy.stats import norm
    S, K, T, v, r = 100.0, 105.0, 0.1, 0.25, 0.04

    def delta(s):
        d1 = (math.log(s / K) + (r + 0.5 * v * v) * T) / (v * math.sqrt(T))
        return norm.cdf(d1)
    fd = (delta(S + 0.01) - delta(S - 0.01)) / 0.02
    assert abs(float(DG.bs_gamma(S, K, T, v, r)) - fd) < 1e-6


def test_parse_cboe_payload_reads_occ_symbols_and_spot():
    payload = {"data": {"current_price": 21000.5, "options": [
        {"option": "NDX261014C21000000", "iv": 0.18, "open_interest": 120, "volume": 5},
        {"option": "NDXP261014P20500000", "iv": 0.22, "open_interest": 80, "volume": 1},
        {"option": "garbage", "iv": 0.2},
    ]}}
    ch, spot = DG.parse_cboe_payload(payload)
    assert spot == 21000.5 and len(ch) == 2
    assert set(ch["type"]) == {"C", "P"} and ch["strike"].tolist() == [21000.0, 20500.0]
    assert ch["root"].tolist() == ["NDX", "NDXP"] and ch["expiry"].iloc[0] == TODAY


MONTH = TODAY + pd.Timedelta(days=30)


def test_structural_walls_flip_and_regime_on_a_built_chain():
    spot = 20000.0
    ch = _chain(spot, call_k=20400.0, put_k=19500.0, expiry=MONTH)
    m = DG.build_gamma_map([(ch, spot)], future_price=spot, now=NOW)
    assert m["call_wall"] == 20400.0 and m["put_wall"] == 19500.0
    assert m["gamma_flip"] is not None and 19500.0 < m["gamma_flip"] < 20400.0
    assert m["share_0dte"] == 0.0 and m["call_wall_0dte"] is None
    # Price that has fallen onto the big put strike: dealers short gamma.
    m_dn = DG.build_gamma_map([(ch, 19500.0)], future_price=19500.0, now=NOW)
    assert m_dn["regime"] == "NEGATİF GAMA" and m_dn["gamma_flip"] > 19500.0
    m_up = DG.build_gamma_map([(ch, 20300.0)], future_price=20300.0, now=NOW)
    assert m_up["regime"] == "POZİTİF GAMA"
    assert m["expected_move_1d"] == round(spot * 0.20 / math.sqrt(252), 4)


def test_0dte_walls_are_separate_from_structural_walls():
    spot = 20000.0
    month = _chain(spot, 20400.0, 19500.0, expiry=MONTH)
    today = _chain(spot, 20100.0, 19900.0, expiry=TODAY, oi=20_000)
    m = DG.build_gamma_map([(pd.concat([month, today]), spot)], spot, now=NOW)
    assert (m["call_wall"], m["put_wall"]) == (20400.0, 19500.0)
    assert (m["call_wall_0dte"], m["put_wall_0dte"]) == (20100.0, 19900.0)
    assert 0 < m["share_0dte"] < 1


def test_index_and_etf_sources_map_to_the_same_futures_levels():
    F = 20100.0                                     # futures price (basis vs index 20000)
    idx = _chain(20000.0, 20400.0, 19500.0, expiry=MONTH)
    etf = _chain(500.0, 510.0, 487.5, expiry=MONTH, root="QQQ")   # same structure at 1/40 scale
    a = DG.build_gamma_map([(idx, 20000.0)], F, now=NOW)
    b = DG.build_gamma_map([(etf, 500.0)], F, now=NOW)
    assert a["call_wall"] == b["call_wall"] == round(20400 * F / 20000 / 25) * 25
    assert a["put_wall"] == b["put_wall"] and abs(a["gamma_flip"] - b["gamma_flip"]) < 30
    both = DG.build_gamma_map([(idx, 20000.0), (etf, 500.0)], F, now=NOW)
    assert abs(both["net_gex_usd_1pct"] - (a["net_gex_usd_1pct"] + b["net_gex_usd_1pct"])) < 1e-6 * abs(both["net_gex_usd_1pct"]) + 2


def test_expired_and_far_expiries_are_excluded():
    spot = 20000.0
    old = _chain(spot, 20400.0, 19500.0, expiry=TODAY - pd.Timedelta(days=1))
    far = _chain(spot, 20400.0, 19500.0, expiry=TODAY + pd.Timedelta(days=200))
    assert DG.build_gamma_map([(old, spot), (far, spot)], spot, now=NOW) is None


def _bars(levels_high, base=100.0):
    idx = pd.date_range("2026-10-13", periods=len(levels_high), freq="h", tz="UTC")
    h = np.asarray(levels_high, float)
    lows = np.linspace(base - 3, base - 0.8, len(h))      # rising lows
    c = np.minimum(h - 0.3, base - 0.2)
    return pd.DataFrame({"Open": c, "High": h, "Low": lows, "Close": c}, index=idx)


def test_level_pressure_counts_failed_tests_with_rising_lows():
    highs = [98.5, 99, 99.95, 99.2, 99.0, 100.0, 99.3, 99.1, 99.98, 99.4] * 4
    p = DG.level_pressure(_bars(highs), level=100.0, side="above", lookback=30)
    assert p["touches"] >= 4 and p["compression"] > 0 and not p["broken_recently"]


def _price_frame(start, hours, step_range):
    idx = pd.date_range(start, periods=hours, freq="h", tz="UTC")
    rng = np.random.default_rng(1)
    c = 20000 + np.cumsum(rng.normal(0, 1, hours))
    hi = c + np.asarray(step_range)
    lo = c - np.asarray(step_range)
    return pd.DataFrame({"Open": c, "High": hi, "Low": lo, "Close": c}, index=idx)


def test_ledger_dedupes_grades_and_finds_compression_evidence():
    with tempfile.TemporaryDirectory() as d:
        led = DG.DealerGammaLedger(os.path.join(d, "g.csv"))
        days = 50
        start = pd.Timestamp("2026-06-01T14:00:00Z")
        ranges = []
        for i in range(days):
            ts = start + pd.Timedelta(days=i)
            pos = i % 2 == 0
            snap = {"as_of": ts.isoformat(), "future_price": 20000.0, "regime": "POZİTİF GAMA" if pos else "NEGATİF GAMA",
                    "net_gex_usd_1pct": 1e9 if pos else -1e9, "gex_0dte_usd_1pct": 0, "share_0dte": 0.4,
                    "gamma_flip": 19800.0, "call_wall": 20100.0, "put_wall": 19700.0, "pin_0dte": 20000.0,
                    "expected_move_1d": 200.0}
            assert led.record({"NQ": snap}) == 1
            assert led.record({"NQ": snap}) == 0            # same hour -> no double count
            ranges += [20.0 if pos else 60.0] * 24          # +Γ days move ~3x less
        frame = _price_frame(start, days * 24 + 30, ranges + [20.0] * 30)
        assert led.grade({"NQ": frame}, now=start + pd.Timedelta(days=days + 2)) == days
        ev = led.evidence("NQ")
        assert ev["range_over_em_pos"] < ev["range_over_em_neg"]
        assert ev["proven_compression"] and ev["verdict"] == "KANITLANDI"
        led.save()
        assert len(DG.DealerGammaLedger(os.path.join(d, "g.csv")).df) == days


def test_ledger_without_effect_stays_unproven():
    with tempfile.TemporaryDirectory() as d:
        led = DG.DealerGammaLedger(os.path.join(d, "g.csv"))
        start = pd.Timestamp("2026-06-01T14:00:00Z")
        rng = np.random.default_rng(7)
        ranges = []
        for i in range(50):
            ts = start + pd.Timedelta(days=i)
            led.record({"NQ": {"as_of": ts.isoformat(), "future_price": 20000.0,
                               "regime": "POZİTİF GAMA" if i % 2 == 0 else "NEGATİF GAMA",
                               "expected_move_1d": 200.0, "call_wall": 20100.0}})
            ranges += [float(rng.uniform(20, 60))] * 24      # no regime effect
        led.grade({"NQ": _price_frame(start, 50 * 24 + 30, ranges + [30.0] * 30)},
                  now=start + pd.Timedelta(days=52))
        assert not led.evidence("NQ")["proven_compression"]


def _snap(regime="POZİTİF GAMA"):
    return {"NQ": {"regime": regime, "future_price": 20000.0, "call_wall": 20050.0, "put_wall": 19700.0,
                   "gamma_flip": 19800.0, "pin_0dte": 20000.0, "expected_move_1d": 200.0, "share_0dte": 0.4,
                   "net_gex_usd_1pct": 1e9}}


def test_annotation_is_advisory_by_default_and_never_grants_entry():
    v = {"NQ": {"verdict": "AL", "entry_allowed": True}, "SPX": {"verdict": "AL", "entry_allowed": False}}
    DG.annotate_verdicts(v, _snap(), evidence={"NQ": {"proven_wall": True}}, policy="advisory")
    assert v["NQ"]["entry_allowed"] is True and v["NQ"]["dealer_gamma"]["pin_risk"]
    assert not v["NQ"]["dealer_gamma"]["gate_applied"]
    v2 = {"NQ": {"verdict": "AL", "entry_allowed": True}}
    DG.annotate_verdicts(v2, _snap(), evidence={"NQ": {"proven_wall": False}}, policy="active")
    assert v2["NQ"]["entry_allowed"] is True                         # no evidence -> no gate
    DG.annotate_verdicts(v2, _snap(), evidence={"NQ": {"proven_wall": True}}, policy="active")
    assert v2["NQ"]["entry_allowed"] is False and v2["NQ"]["dealer_gamma"]["gate_applied"]
    v3 = {"NQ": {"verdict": "AL", "entry_allowed": False}}
    DG.annotate_verdicts(v3, _snap("NEGATİF GAMA"), evidence={"NQ": {"proven_wall": True}}, policy="active")
    assert v3["NQ"]["entry_allowed"] is False and "−Γ" in v3["NQ"]["dealer_gamma"]["notes"][0]


def test_snapshot_falls_back_to_yfinance_and_returns_none_without_data():
    ch = _chain(500.0, 510.0, 487.5, root="QQQ")
    none = lambda s: (None, None)
    m = DG.snapshot_asset("NQ", 20000.0, now=NOW, fetch_cboe=none, fetch_yf=lambda s: (ch, 500.0))
    assert m["source"] == "yfinance" and m["asset"] == "NQ"
    assert DG.snapshot_asset("NQ", 20000.0, now=NOW, fetch_cboe=none, fetch_yf=none) is None
    out = DG.run_cycle({"NQ": pd.DataFrame({"Close": [20000.0]})}, {}, {},
                       path=os.path.join(tempfile.mkdtemp(), "g.csv"), now=NOW,
                       fetch_cboe=none, fetch_yf=none)
    assert out["snapshots"] == {} and out["evidence"]["NQ"]["verdict"] == "VERİ YOK"


# ---------------------------------------------------------------------------
# Factor role "state": computed + logged, but no vote in the direction score
# ---------------------------------------------------------------------------
def test_state_factors_do_not_move_the_direction_score():
    from config import ASSET_MATRICES, is_directional
    from stateful_adaptive_model import AdaptiveScoreModel

    factors = ASSET_MATRICES["NQ"]["factors"]
    states = {f["id"] for f in factors if not is_directional(f)}
    assert states == {"asset_direction", "vix_strain", "vix_term", "vix_term_lead",
                      "cta_trend_position", "liquidity_sweep", "vol_control_flow"}

    def rows(state_value):
        return [{"faktör": f["name"], "faktor_id": f["id"],
                 "ham_deger": state_value if f["id"] in states else 0.5, "veri_durumu": "MEVCUT"}
                for f in factors]
    with tempfile.TemporaryDirectory() as d:
        from stateful_memory_store import StatefulMemoryStore
        model = AdaptiveScoreModel(StatefulMemoryStore(os.path.join(d, "m.json")))
        a = model.recompute_score("NQ", rows(+1.8))
        b = model.recompute_score("NQ", rows(-1.8))
    assert a["score"] == b["score"]
    assert a["factor_runtime"]["vix_term"]["status"] == "STATE"
    assert a["data_coverage"] == 1.0


def test_replay_stability_verdict():
    from historical_replay import stability_verdict
    assert stability_verdict([-0.07, -0.21, -0.09]).startswith("⛔")
    assert stability_verdict([0.05, 0.03, 0.04]).startswith("✅")
    assert stability_verdict([0.05, -0.03, 0.04]).startswith("〰️")
    assert stability_verdict([None, -0.1, -0.1]) == "—"


def test_walls_respect_side_of_price():
    import pandas as pd
    payload = {"result": [
        {"instrument_name": "BTC-16OCT26-110000-P", "open_interest": 5000, "mark_iv": 50.0, "underlying_price": 101000},
        {"instrument_name": "BTC-16OCT26-95000-P", "open_interest": 300, "mark_iv": 50.0, "underlying_price": 101000},
        {"instrument_name": "BTC-16OCT26-92000-C", "open_interest": 5000, "mark_iv": 50.0, "underlying_price": 101000},
        {"instrument_name": "BTC-16OCT26-108000-C", "open_interest": 300, "mark_iv": 50.0, "underlying_price": 101000},
    ]}
    ch, spot = DG.parse_deribit_payload(payload)
    m = DG.snapshot_asset("BTC", 101000.0, now=pd.Timestamp("2026-10-14T15:00:00Z"),
                          fetch_deribit=lambda c: (ch, spot), fetch_cboe=lambda s: (None, None),
                          fetch_yf=lambda s: (None, None))
    assert m["put_wall"] == 95000.0 and m["call_wall"] == 108000.0     # ITM yığınlar duvar sayılmaz
