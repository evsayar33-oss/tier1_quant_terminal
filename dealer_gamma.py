"""
Dealer Gamma Haritası (v15.0) — piyasa yapıcının hedge akışı
=============================================================
Neden var: sistemdeki her faktör bir DEĞİŞİMDİR (oran z-skoru, momentum,
vade eğrisi). Hiçbiri bir SEVİYE değildir. Oysa endeks vadelileri (NQ/ES)
gün içinde opsiyon piyasasının yarattığı seviyelere göre hareket eder:

* Opsiyonu satan taraf genellikle piyasa yapıcıdır (dealer). Dealer yönsüz
  kalmak için vadeli/ETF ile delta hedge yapar.
* Dealer net UZUN gama ise (+Γ): fiyat yükselince satar, düşünce alır.
  Hareket SIKIŞIR, büyük açık pozisyonlu strike'lar mıknatıs/duvar olur.
  "Seviye defalarca deneniyor ama kırılmıyor" görüntüsü budur.
* Dealer net KISA gama ise (−Γ): fiyat yükselince alır, düşünce satar.
  Hareket HIZLANIR. Duvar emildiğinde ya da fiyat "gamma flip" seviyesini
  geçtiğinde aynı dealer akışı yön değiştirir; kırılım dakikalar içinde olur.

Bu modül YÖN TAHMİNİ ÜRETMEZ. Gama, hareketin NASIL olacağını (sıkışma mı,
hızlanma mı) ve NEREDE durabileceğini (duvarlar, flip, pin) söyler. Yön
skoruna doğrudan eklenmez; giriş zamanlamasına not düşer ve kendi defterine
(DealerGammaLedger) yazılır. Defter, haritanın bu varlıkta gerçekten işe
yarayıp yaramadığını gerçekleşen fiyatla notlar. Kanıt (t ≥ 2, n ≥ 30)
oluşmadan harita giriş iznini KALDIRMAZ (politika: "advisory").

Varsayım (açıkça): müşteriler ağırlıklı olarak put alır ve call satar
(koruma + covered call). Bu yüzden dealer call'larda uzun, put'larda kısa
gama kabul edilir: GEX = Γ_call·OI − Γ_put·OI. Bu, sektörde yaygın "naive"
işaret kabulüdür; işlem yönü (alıcı/satıcı) verisi olmadan daha iyisi
bilinemez. Defter bu varsayımın bu varlıkta tutup tutmadığını da ölçer.

Veri: CBOE gecikmeli opsiyon zinciri (ücretsiz, ~15 dk gecikme), yoksa
yfinance opsiyon zinciri (QQQ/SPY). Ağ yoksa modül sessizce None döner;
sahte veri üretilmez.
"""
from __future__ import annotations

import math
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

try:  # Python ≥ 3.9
    from zoneinfo import ZoneInfo
    _NY = ZoneInfo("America/New_York")
except Exception:  # pragma: no cover - fallback without tz database
    _NY = None

from system_clock import now_utc

CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{symbol}.json"
HISTORY_FILE = "dealer_gamma_history.csv"

# Varlık → opsiyon kaynakları (önce endeks, sonra ETF). Hepsi aynı vadeli
# fiyat uzayına dönüştürülür ve dolar gaması toplanır.
GAMMA_SOURCES: Dict[str, Dict[str, Any]] = {
    "NQ": {"future": "NQ=F", "cboe": ["_NDX", "QQQ"], "yf": ["QQQ"]},
    "SPX": {"future": "ES=F", "cboe": ["_SPX", "SPY"], "yf": ["SPY"]},
    # v15.1: kripto opsiyonlarının ~%85'i Deribit'te. Dealer işaret varsayımı
    # kriptoda daha zayıftır (müşteri call satışı + put alışı daha karışık);
    # defter bunu da ölçer.
    "BTC": {"future": "BTC-USD", "deribit": "BTC"},
    "ETH": {"future": "ETH-USD", "deribit": "ETH"},
}
DERIBIT_URL = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={ccy}&kind=option"
_DERIBIT = re.compile(r"^([A-Z]+)-(\d{1,2}[A-Z]{3}\d{2})-(\d+(?:d\d+)?)-([CP])$")

def _policy_from_config() -> str:
    try:
        from config import DEALER_GAMMA_POLICY
        return str(DEALER_GAMMA_POLICY)
    except Exception:
        return "advisory"


GAMMA_CONFIG: Dict[str, Any] = {
    "max_expiry_days": 60,       # daha uzak vadelerin gün içi hedge etkisi küçük
    "profile_span": 0.10,        # flip araması: spot ± %10
    "profile_points": 161,
    "risk_free": 0.04,
    "min_t_years": 15.0 / (60 * 24 * 365),   # 0DTE kapanışa 15 dk kala taban
    "wall_near_em": 0.35,        # duvara uzaklık < 0.35 × günlük beklenen hareket → "duvara yakın"
    "touch_atr": 0.25,           # seviye testi: 1H tepesi seviyeye 0.25 ATR'den yakın
    # "advisory": sadece not düşer. "active": kanıt varsa pin riskinde girişi kapatır.
    "policy": _policy_from_config(),
    "evidence_min_n": 30,
    "evidence_min_t": 2.0,
}

_OCC = re.compile(r"^([A-Z]{1,6})(\d{6})([CP])(\d{8})$")


# ---------------------------------------------------------------------------
# Black–Scholes gama
# ---------------------------------------------------------------------------
def bs_gamma(spot: Any, strike: Any, t_years: Any, iv: Any, r: float = 0.04) -> np.ndarray:
    """Vektörel Black–Scholes gaması (call ve put için aynı)."""
    S = np.asarray(spot, dtype=float)
    K = np.asarray(strike, dtype=float)
    T = np.maximum(np.asarray(t_years, dtype=float), 1e-9)
    v = np.maximum(np.asarray(iv, dtype=float), 1e-6)
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(S / K) + (r + 0.5 * v * v) * T) / (v * np.sqrt(T))
        g = np.exp(-0.5 * d1 * d1) / (math.sqrt(2.0 * math.pi) * S * v * np.sqrt(T))
    return np.where(np.isfinite(g), g, 0.0)


def _d1d2(spot, strike, t_years, iv, r):
    S = np.asarray(spot, dtype=float)
    K = np.asarray(strike, dtype=float)
    T = np.maximum(np.asarray(t_years, dtype=float), 1e-9)
    v = np.maximum(np.asarray(iv, dtype=float), 1e-6)
    sq = v * np.sqrt(T)
    d1 = (np.log(S / K) + (r + 0.5 * v * v) * T) / sq
    return d1, d1 - sq, v, T, sq


def bs_vanna(spot, strike, t_years, iv, r: float = 0.04) -> np.ndarray:
    """∂Δ/∂σ (σ birim: 1.00 = %100). Call ve put için aynı."""
    d1, d2, v, T, sq = _d1d2(spot, strike, t_years, iv, r)
    out = -np.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) * d2 / v
    return np.where(np.isfinite(out), out, 0.0)


def bs_charm(spot, strike, t_years, iv, r: float = 0.04) -> np.ndarray:
    """∂Δ/∂t, zaman İLERLEDİKÇE (yıl başına). q=0'da call ve put için aynı."""
    d1, d2, v, T, sq = _d1d2(spot, strike, t_years, iv, r)
    out = -np.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) * (2 * r * T - d2 * sq) / (2 * T * sq)
    return np.where(np.isfinite(out), out, 0.0)


def _expiry_close_utc(expiry: pd.Timestamp) -> pd.Timestamp:
    """Opsiyon vade kapanışı: New York 16:00 (yaz/kış saati doğru)."""
    d = pd.Timestamp(expiry).date()
    if _NY is not None:
        local = datetime(d.year, d.month, d.day, 16, 0, tzinfo=_NY)
        return pd.Timestamp(local.astimezone(timezone.utc))
    return pd.Timestamp(datetime(d.year, d.month, d.day, 20, 0, tzinfo=timezone.utc))


def _today_ny(now: pd.Timestamp) -> Any:
    if _NY is not None:
        return now.tz_convert(_NY).date()
    return (now - pd.Timedelta(hours=4)).date()


# ---------------------------------------------------------------------------
# Zincir okuma
# ---------------------------------------------------------------------------
def parse_cboe_payload(payload: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], Optional[float]]:
    """CBOE gecikmeli JSON → (zincir, spot). Zincir sütunları:
    strike, type ('C'/'P'), expiry (Timestamp), iv, oi, volume, root."""
    data = (payload or {}).get("data") or {}
    spot = data.get("current_price") or data.get("close")
    try:
        spot = float(spot)
    except (TypeError, ValueError):
        spot = None
    rows = []
    for o in data.get("options") or []:
        m = _OCC.match(str(o.get("option", "")).strip())
        if not m:
            continue
        root, ymd, cp, k = m.groups()
        try:
            expiry = pd.Timestamp(datetime.strptime(ymd, "%y%m%d"))
            rows.append({
                "root": root, "expiry": expiry, "type": cp, "strike": int(k) / 1000.0,
                "iv": float(o.get("iv") or 0.0), "oi": float(o.get("open_interest") or 0.0),
                "volume": float(o.get("volume") or 0.0),
            })
        except (TypeError, ValueError):
            continue
    if not rows:
        return None, spot
    return pd.DataFrame(rows), spot


def fetch_cboe_chain(symbol: str, timeout: float = 20.0) -> Tuple[Optional[pd.DataFrame], Optional[float]]:
    try:
        import requests
        r = requests.get(CBOE_URL.format(symbol=symbol), timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0 tier1-quant-terminal"})
        if r.status_code != 200:
            return None, None
        return parse_cboe_payload(r.json())
    except Exception:
        return None, None


def parse_deribit_payload(payload: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], Optional[float]]:
    """Deribit özet listesi → zincir. Sözleşme = 1 coin (mult=1), vade 08:00 UTC."""
    rows, unders = [], []
    for o in (payload or {}).get("result") or []:
        m = _DERIBIT.match(str(o.get("instrument_name", "")))
        if not m:
            continue
        _, dstr, k, cp = m.groups()
        try:
            exp = pd.Timestamp(datetime.strptime(dstr.rjust(7, "0"), "%d%b%y"))
            rows.append({"root": "DERIBIT", "expiry": exp, "expiry_utc": exp.tz_localize("UTC") + pd.Timedelta(hours=8),
                         "type": cp, "strike": float(k.replace("d", ".")),
                         "iv": float(o.get("mark_iv") or 0.0) / 100.0, "oi": float(o.get("open_interest") or 0.0),
                         "volume": float(o.get("volume") or 0.0), "mult": 1.0})
            if o.get("underlying_price"):
                unders.append(float(o["underlying_price"]))
        except (TypeError, ValueError):
            continue
    if not rows:
        return None, None
    return pd.DataFrame(rows), (float(np.median(unders)) if unders else None)


def fetch_deribit_chain(ccy: str, timeout: float = 20.0) -> Tuple[Optional[pd.DataFrame], Optional[float]]:
    try:
        import requests
        r = requests.get(DERIBIT_URL.format(ccy=ccy), timeout=timeout)
        if r.status_code != 200:
            return None, None
        return parse_deribit_payload(r.json())
    except Exception:
        return None, None


def fetch_yf_chain(symbol: str, max_expiries: int = 10) -> Tuple[Optional[pd.DataFrame], Optional[float]]:
    try:
        import yfinance as yf
        tk = yf.Ticker(symbol)
        spot = None
        try:
            spot = float(tk.fast_info["last_price"])
        except Exception:
            h = tk.history(period="1d", interval="1m")
            spot = float(h["Close"].iloc[-1]) if not h.empty else None
        rows = []
        for exp in list(tk.options or [])[:max_expiries]:
            ch = tk.option_chain(exp)
            for cp, frame in (("C", ch.calls), ("P", ch.puts)):
                if frame is None or frame.empty:
                    continue
                f = pd.DataFrame({
                    "root": symbol, "expiry": pd.Timestamp(exp), "type": cp,
                    "strike": pd.to_numeric(frame["strike"], errors="coerce"),
                    "iv": pd.to_numeric(frame.get("impliedVolatility"), errors="coerce"),
                    "oi": pd.to_numeric(frame.get("openInterest"), errors="coerce"),
                    "volume": pd.to_numeric(frame.get("volume"), errors="coerce"),
                })
                rows.append(f)
        if not rows:
            return None, spot
        return pd.concat(rows, ignore_index=True).fillna({"oi": 0.0, "volume": 0.0}), spot
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Gama haritası
# ---------------------------------------------------------------------------
def _prepare(chain: pd.DataFrame, now: pd.Timestamp, cfg: Dict[str, Any]) -> pd.DataFrame:
    c = chain.copy()
    c = c[(c["iv"] > 0.01) & (c["iv"] < 5.0) & (c["oi"] > 0) & (c["strike"] > 0)]
    if c.empty:
        return c
    exp = pd.to_datetime(c["expiry"])
    if "expiry_utc" in c.columns:
        t_years = (pd.to_datetime(c["expiry_utc"], utc=True) - now).dt.total_seconds() / (365.0 * 86400.0)
        c = c.assign(t=t_years.to_numpy(float), expiry=exp)
    else:
        uniq = exp.drop_duplicates()
        t_of = {e: (_expiry_close_utc(e) - now).total_seconds() / (365.0 * 86400.0) for e in uniq}
        c = c.assign(t=exp.map(t_of).to_numpy(float), expiry=exp)
    if "mult" not in c.columns:
        c["mult"] = 100.0
    c["mult"] = pd.to_numeric(c["mult"], errors="coerce").fillna(100.0)
    c = c[(c["t"] > -1e-6) & (c["t"] <= cfg["max_expiry_days"] / 365.0)].copy()
    c["t"] = np.maximum(c["t"], cfg["min_t_years"])
    today = _today_ny(now)
    if "expiry_utc" in c.columns:      # 7/24 piyasa (Deribit): önümüzdeki 24 saatte biten seriler
        c["is_0dte"] = c["t"] <= 1.0 / 365.0
    else:
        c["is_0dte"] = c["expiry"].dt.date == today
    c["sgn"] = np.where(c["type"] == "C", 1.0, -1.0)
    return c


def _dollar_gex(c: pd.DataFrame, spot_src: Any, r: float) -> np.ndarray:
    """$ dealer gaması / fiyatta %1 hareket, satır bazında (dealer işareti dahil)."""
    g = bs_gamma(spot_src, c["strike"].to_numpy(), c["t"].to_numpy(), c["iv"].to_numpy(), r)
    s = np.asarray(spot_src, dtype=float)
    return c["sgn"].to_numpy() * g * c["oi"].to_numpy() * c["mult"].to_numpy() * s * s * 0.01


def build_gamma_map(
    chains: Iterable[Tuple[pd.DataFrame, float]],
    future_price: float,
    now: Optional[pd.Timestamp] = None,
    cfg: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Bir veya daha çok (zincir, kaynak_spot) çiftinden, VADELİ fiyat uzayında
    tek bir dealer gama haritası üretir. Her kaynak, k = vadeli/kaynak_spot ile
    vadeli uzaya taşınır (baz farkı dahil). Dolar gaması birimden bağımsızdır,
    bu yüzden kaynaklar toplanabilir."""
    cfg = {**GAMMA_CONFIG, **(cfg or {})}
    now = pd.Timestamp(now or now_utc())
    if now.tzinfo is None:
        now = now.tz_localize("UTC")
    if not future_price or not np.isfinite(future_price) or future_price <= 0:
        return None
    prepared = []
    for chain, src_spot in chains:
        if chain is None or chain.empty or not src_spot or src_spot <= 0:
            continue
        c = _prepare(chain, now, cfg)
        if c.empty:
            continue
        k = float(future_price) / float(src_spot)
        c = c.assign(strike_f=c["strike"] * k, k=k)
        prepared.append((c, float(src_spot), k))
    if not prepared:
        return None
    r = float(cfg["risk_free"])
    F = float(future_price)

    per_strike = []
    net = gex0 = abs_total = 0.0
    vanna_flow = charm_flow = charm_flow_0dte = 0.0
    for c, s_src, k in prepared:
        # Dealer hedge akışı ($, + = dealer ALIR): hedge = −(dealer opsiyon deltası değişimi).
        pos = c["sgn"].to_numpy() * c["oi"].to_numpy() * c["mult"].to_numpy()
        va = bs_vanna(s_src, c["strike"].to_numpy(), c["t"].to_numpy(), c["iv"].to_numpy(), r)
        vanna_flow += float((pos * va * 0.01 * s_src).sum())          # IV 1 puan DÜŞERSE
        ch = bs_charm(s_src, c["strike"].to_numpy(), c["t"].to_numpy(), c["iv"].to_numpy(), r)
        cf = -pos * ch / 365.0 * s_src                                 # 1 gün GEÇERSE
        charm_flow += float(cf.sum())
        charm_flow_0dte += float(cf[c["is_0dte"].to_numpy()].sum())
        g = _dollar_gex(c, s_src, r)
        c = c.assign(gex=g)
        net += float(g.sum())
        gex0 += float(g[c["is_0dte"].to_numpy()].sum())
        abs_total += float(np.abs(g).sum())
        # Duvar gücü = fiyat strike'a GELDİĞİNDE oradaki dealer gaması (Γ @ S=K).
        # Spot'taki gama kullanılırsa 0DTE ATM her şeyi ezer ve duvar spot'a çöker.
        g_at_k = c["sgn"].to_numpy() * bs_gamma(c["strike"], c["strike"], c["t"], c["iv"], r) \
            * c["oi"].to_numpy() * c["mult"].to_numpy() * c["strike"].to_numpy() ** 2 * 0.01
        c = c.assign(gex_at_k=g_at_k)
        per_strike.append(c[["strike_f", "type", "gex", "gex_at_k", "oi", "is_0dte", "iv", "t"]])
    ps = pd.concat(per_strike, ignore_index=True)
    # Kaynakların strike ızgaraları farklıdır; vadeli uzayda 1 tick'e yuvarla.
    tick = _level_tick(F)
    ps["lvl"] = (ps["strike_f"] / tick).round() * tick
    ps = ps[(ps["lvl"] > F * (1 - 2 * cfg["profile_span"])) & (ps["lvl"] < F * (1 + 2 * cfg["profile_span"]))]

    def _walls(rows: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
        if rows.empty:
            return None, None
        w = rows.groupby(["lvl", "type"])["gex_at_k"].sum().unstack(fill_value=0.0)
        cw = float(w["C"].idxmax()) if "C" in w and (w["C"] > 0).any() else None
        pw = float(w["P"].idxmin()) if "P" in w and (w["P"] < 0).any() else None
        return cw, pw

    # Yapısal duvarlar: ≥1 gün vadeli seriler (gün içinde kaybolmazlar). Sadece
    # bir haftalık beklenen hareketin 3 katı içindeki strike'lar: çok uzaktaki
    # çeyreklik koruma put'ları (SPX'te −%16 gibi) gün içi seviye değildir.
    em_w, _ = _expected_move(prepared, F, now, float(cfg.get("periods_per_year", 252.0)))
    reach = 3.0 * em_w * math.sqrt(5.0) if em_w else F * cfg["profile_span"]
    near = ps[(ps["lvl"] - F).abs() <= reach]
    call_wall, put_wall = _walls(near[~near["is_0dte"]])
    # Gün içi duvarlar: sadece bugün vadeli (0DTE) seriler; 20:00 UTC'de biter.
    zero = ps[ps["is_0dte"]]
    call_wall_0dte, put_wall_0dte = _walls(zero)
    total_lvl = ps.groupby("lvl")["gex"].sum()
    pin = float(total_lvl.abs().idxmax()) if not total_lvl.empty else None
    pin_0dte = None
    if not zero.empty:
        z = zero.groupby("lvl")["gex"].sum()
        z = z[(z.index > F * 0.95) & (z.index < F * 1.05)]
        if not z.empty:
            pin_0dte = float(z.abs().idxmax())

    # Gama profili: fiyat S' olsaydı dealer net gaması ne olurdu? (flip arama)
    grid = np.linspace(F * (1 - cfg["profile_span"]), F * (1 + cfg["profile_span"]), int(cfg["profile_points"]))
    prof = np.zeros_like(grid)
    for c, s_src, k in prepared:
        for i, Sf in enumerate(grid):
            prof[i] += float(_dollar_gex(c, Sf / k, r).sum())
    flip = _nearest_zero_crossing(grid, prof, F)

    em_1d, atm_iv = _expected_move(prepared, F, now, float(cfg.get("periods_per_year", 252.0)))
    # Rejim = dealer net gamasının SPOT'taki işareti. Flip sadece bu işaretin
    # değiştiği en yakın seviyedir (oraya varılınca hedge akışı tersine döner).
    regime = "POZİTİF GAMA" if net > 0 else "NEGATİF GAMA"
    out = {
        "as_of": now.isoformat(),
        "future_price": round(F, 4),
        "net_gex_usd_1pct": round(net, 0),
        "gex_0dte_usd_1pct": round(gex0, 0),
        "share_0dte": round(abs(gex0) / abs_total, 4) if abs_total > 0 else 0.0,
        "gamma_flip": _r(flip, tick),
        "call_wall": _r(call_wall, tick),
        "put_wall": _r(put_wall, tick),
        "call_wall_0dte": _r(call_wall_0dte, tick),
        "put_wall_0dte": _r(put_wall_0dte, tick),
        "pin_strike": _r(pin, tick),
        "pin_0dte": _r(pin_0dte, tick),
        "vanna_flow_iv_down_1pt_usd": round(vanna_flow, 0),
        "charm_flow_1d_usd": round(charm_flow, 0),
        "charm_flow_0dte_usd": round(charm_flow_0dte, 0),
        "atm_iv": round(atm_iv, 4) if atm_iv else None,
        "expected_move_1d": round(em_1d, 4) if em_1d else None,
        "regime": regime,
        "sources": [{"spot": round(s, 4), "basis_k": round(k, 6), "rows": int(len(c))} for c, s, k in prepared],
        "profile": {"grid": [round(x, 2) for x in grid[::8]], "gex": [round(x, 0) for x in prof[::8]]},
    }
    out["interpretation"] = interpret(out)
    return out


def _level_tick(price: float) -> float:
    if price > 10000:
        return 25.0
    if price > 2000:
        return 5.0
    if price > 200:
        return 1.0
    return 0.5


def _r(x: Optional[float], tick: float) -> Optional[float]:
    return None if x is None or not np.isfinite(x) else round(round(x / tick) * tick, 4)


def _nearest_zero_crossing(grid: np.ndarray, prof: np.ndarray, spot: float) -> Optional[float]:
    s = np.sign(prof)
    idx = np.where(s[:-1] * s[1:] < 0)[0]
    if len(idx) == 0:
        return None
    xs = []
    for i in idx:
        x0, x1, y0, y1 = grid[i], grid[i + 1], prof[i], prof[i + 1]
        xs.append(x0 - y0 * (x1 - x0) / (y1 - y0))
    xs = np.asarray(xs)
    return float(xs[np.argmin(np.abs(xs - spot))])


def _expected_move(prepared, F: float, now: pd.Timestamp, periods: float = 252.0) -> Tuple[Optional[float], Optional[float]]:
    """Piyasa yapıcının fiyatladığı 1 günlük hareket: ATM IV / √252 (≥1 gün vadeli en yakın seri)."""
    best = None
    for c, s_src, k in prepared:
        c1 = c[c["t"] >= 0.9 / 365.0]
        if c1.empty:
            continue
        t_min = c1["t"].min()
        near = c1[c1["t"] == t_min]
        atm = near.iloc[(near["strike_f"] - F).abs().argsort()[:4]]
        iv = float(atm["iv"].median())
        if best is None or t_min < best[0]:
            best = (t_min, iv)
    if best is None:
        return None, None
    iv = best[1]
    return F * iv / math.sqrt(periods), iv


def interpret(m: Dict[str, Any]) -> Dict[str, str]:
    F = m.get("future_price")
    flip = m.get("gamma_flip")
    pos = m.get("regime") == "POZİTİF GAMA"
    hedge = ("Dealer yükselişte satar, düşüşte alır → hareket sıkışır, seviyeler tutunur."
             if pos else
             "Dealer yükselişte alır, düşüşte satar → hareket hızlanır, kırılımlar uzar.")
    where = "—"
    if flip and F:
        where = (f"En yakın gamma flip {flip:.0f} (fiyat {F:.0f}, fark %{100 * (flip / F - 1):+.2f}). "
                 f"Fiyat bu seviyeyi geçerse dealer hedge akışı yön değiştirir.")
    walls = []
    if m.get("call_wall"):
        walls.append(f"Call duvarı {m['call_wall']:.0f} (yükselişte direnç/mıknatıs)")
    if m.get("put_wall"):
        walls.append(f"Put duvarı {m['put_wall']:.0f} (düşüşte destek; kırılırsa hızlanma)")
    if m.get("call_wall_0dte") or m.get("put_wall_0dte"):
        walls.append("0DTE gün içi duvarlar "
                     f"{m.get('put_wall_0dte') or '—'} / {m.get('call_wall_0dte') or '—'}")
    if m.get("pin_0dte"):
        walls.append(f"0DTE pin {m['pin_0dte']:.0f} (gün sonuna doğru çekim; vade kapanışında etkisi biter)")
    def _usd(x):
        return f"{x / 1e9:+.2f} mlr $" if abs(x) >= 1e8 else f"{x / 1e6:+.0f} mn $"
    flows = []
    if m.get("vanna_flow_iv_down_1pt_usd") is not None:
        v = float(m["vanna_flow_iv_down_1pt_usd"])
        flows.append(f"Vanna: IV 1 puan düşerse dealer {'ALIR' if v > 0 else 'SATAR'} ({_usd(v)}).")
    if m.get("charm_flow_1d_usd") is not None:
        c = float(m["charm_flow_1d_usd"])
        flows.append(f"Charm: zaman geçtikçe (1 gün) dealer {'ALIR' if c > 0 else 'SATAR'} ({_usd(c)}).")
    return {"hedge_flow": hedge, "flip": where, "levels": " · ".join(walls) or "—",
            "vanna_charm": " ".join(flows) or "—",
            "share_0dte": f"0DTE gama payı %{100 * float(m.get('share_0dte') or 0):.0f}"}


def snapshot_asset(asset: str, future_price: float, now: Optional[pd.Timestamp] = None,
                   fetch_cboe=fetch_cboe_chain, fetch_yf=fetch_yf_chain,
                   fetch_deribit=fetch_deribit_chain) -> Optional[Dict[str, Any]]:
    src = GAMMA_SOURCES.get(asset)
    if not src or not future_price:
        return None
    chains = []
    origin = "—"
    if src.get("deribit"):
        ch, spot = fetch_deribit(src["deribit"])
        if ch is not None and spot:
            chains.append((ch, spot))
            origin = "Deribit"
    for sym in src.get("cboe", []):
        ch, spot = fetch_cboe(sym)
        if ch is not None and spot:
            chains.append((ch, spot))
            origin = "CBOE (15 dk gecikmeli)"
    if not chains:
        for sym in src.get("yf", []):
            ch, spot = fetch_yf(sym)
            if ch is not None and spot:
                chains.append((ch, spot))
                origin = "yfinance"
    if not chains:
        return None
    m = build_gamma_map(chains, float(future_price), now=now,
                        cfg={"periods_per_year": 365.0 if src.get("deribit") else 252.0})
    if m is not None:
        m["source"] = origin
        m["asset"] = asset
    return m


def _last_close(df: Any) -> Optional[float]:
    try:
        s = pd.to_numeric(df["Close"], errors="coerce").dropna()
        return float(s.iloc[-1]) if not s.empty else None
    except Exception:
        return None


def build_snapshots(grid_1h: Dict[str, Any], now: Optional[pd.Timestamp] = None, **kw) -> Dict[str, Any]:
    out = {}
    for asset, src in GAMMA_SOURCES.items():
        sym = src["future"]
        df = grid_1h.get(sym.replace("=F", ""), grid_1h.get(sym))
        F = _last_close(df) if df is not None else None
        try:
            snap = snapshot_asset(asset, F, now=now, **kw) if F else None
        except Exception as exc:  # gama haritası asla döngüyü düşürmez
            print(f"[gamma] {asset} atlandı: {exc}", flush=True)
            snap = None
        if snap is not None:
            out[asset] = snap
    return out


# ---------------------------------------------------------------------------
# Seviye testi: "bir seviyeyi defalarca deniyor ama kıramıyor"
# ---------------------------------------------------------------------------
def level_pressure(df_1h: pd.DataFrame, level: Optional[float], side: str = "above",
                   lookback: int = 24, touch_atr: float = 0.25) -> Optional[Dict[str, Any]]:
    """Son `lookback` saatlik barda bir seviyenin kaç kez test edildiğini ve
    testlerin arasında diplerin yükselip yükselmediğini ölçer.

    Mantık: Duvarda dealer satışı (veya limit emir yığını) her testi emer.
    Testler arasında dipler yükseliyorsa (üçgen sıkışması) emilen likidite
    tükeniyor demektir; kırılım olasılığı ve hızı artar. Bu bir yön tahmini
    değil, seviyenin "ne kadar yorulduğunun" ölçüsüdür.
    side='above': direnç (call duvarı), side='below': destek (put duvarı)."""
    if level is None or df_1h is None or len(df_1h) < 20:
        return None
    d = df_1h.tail(lookback + 14)
    h, l, c = (pd.to_numeric(d[x], errors="coerce") for x in ("High", "Low", "Close"))
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = float(tr.rolling(14, min_periods=5).mean().iloc[-1])
    if not np.isfinite(atr) or atr <= 0:
        return None
    h, l, c = h.tail(lookback), l.tail(lookback), c.tail(lookback)
    tol = touch_atr * atr
    if side == "above":
        touched = (h >= level - tol) & (c < level)
        broke = bool((c >= level).iloc[-3:].any())
        extremes = l[touched]
        trend = np.polyfit(np.arange(len(extremes)), extremes.to_numpy(float), 1)[0] / atr if len(extremes) >= 3 else 0.0
    else:
        touched = (l <= level + tol) & (c > level)
        broke = bool((c <= level).iloc[-3:].any())
        extremes = h[touched]
        trend = -np.polyfit(np.arange(len(extremes)), extremes.to_numpy(float), 1)[0] / atr if len(extremes) >= 3 else 0.0
    n = int(touched.sum())
    return {"level": level, "side": side, "touches": n, "broken_recently": broke,
            "compression": round(float(trend), 3),
            "distance_atr": round((level - float(c.iloc[-1])) / atr, 2),
            "note": (f"{n} test; dipler {'yükseliyor' if trend > 0.05 else 'yatay'}"
                     if side == "above" else f"{n} test; tepeler {'alçalıyor' if trend > 0.05 else 'yatay'}")}


# ---------------------------------------------------------------------------
# Kendi kendini notlayan defter (self-improving evidence)
# ---------------------------------------------------------------------------
class DealerGammaLedger:
    """Her döngüde haritayı kaydeder, 24 saat sonra gerçekleşen fiyatla notlar.

    Test edilen iki önerme (önceden tanımlı, sonradan seçilmez):
      1) SIKIŞMA: +Γ anlarında sonraki 24s gerçekleşen aralık / beklenen
         hareket, −Γ anlarından KÜÇÜK müdür?
      2) DUVAR: fiyat call duvarına yakınken (< wall_near_em × EM) sonraki
         24s içinde duvar kapanışla aşılmadan kalıyor mu? (taban: %50)
    Kanıt eşiği (n ≥ 30 bağımsız gün, t ≥ 2) aşılmadan politika 'active'e
    geçmez. Model bu defterden YÖN öğrenmez."""

    COLS = ["ts", "asset", "future_price", "regime", "net_gex", "gex_0dte", "share_0dte",
            "gamma_flip", "call_wall", "put_wall", "call_wall_0dte", "put_wall_0dte", "pin_0dte", "em_1d",
            "range_24h", "ret_24h", "wall_held"]

    def __init__(self, path: str = HISTORY_FILE):
        self.path = path
        try:
            self.df = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame(columns=self.COLS)
        except Exception:
            self.df = pd.DataFrame(columns=self.COLS)
        for c in self.COLS:
            if c not in self.df.columns:
                self.df[c] = np.nan

    def record(self, snapshots: Dict[str, Any]) -> int:
        added = 0
        for asset, m in (snapshots or {}).items():
            ts = pd.Timestamp(m["as_of"]).floor("h").isoformat()
            if ((self.df["ts"] == ts) & (self.df["asset"] == asset)).any():
                continue
            self.df.loc[len(self.df)] = {
                "ts": ts, "asset": asset, "future_price": m.get("future_price"), "regime": m.get("regime"),
                "net_gex": m.get("net_gex_usd_1pct"), "gex_0dte": m.get("gex_0dte_usd_1pct"),
                "share_0dte": m.get("share_0dte"), "gamma_flip": m.get("gamma_flip"),
                "call_wall": m.get("call_wall"), "put_wall": m.get("put_wall"),
                "call_wall_0dte": m.get("call_wall_0dte"), "put_wall_0dte": m.get("put_wall_0dte"),
                "pin_0dte": m.get("pin_0dte"), "em_1d": m.get("expected_move_1d"),
                "range_24h": np.nan, "ret_24h": np.nan, "wall_held": np.nan,
            }
            added += 1
        return added

    def grade(self, price_frames: Dict[str, pd.DataFrame], now: Optional[pd.Timestamp] = None) -> int:
        """24 saati dolmuş kayıtları gerçekleşen 1H barlarla notlar."""
        now = pd.Timestamp(now or now_utc())
        graded = 0
        for i, row in self.df[self.df["range_24h"].isna()].iterrows():
            df = price_frames.get(row["asset"])
            if df is None or df.empty:
                continue
            t0 = pd.Timestamp(row["ts"])
            if t0.tzinfo is None:
                t0 = t0.tz_localize("UTC")
            if now < t0 + pd.Timedelta(hours=24):
                continue
            idx = pd.to_datetime(df.index, utc=True)
            w = df[(idx > t0) & (idx <= t0 + pd.Timedelta(hours=24))]
            if len(w) < 6:
                continue
            F = float(row["future_price"])
            hi, lo = float(pd.to_numeric(w["High"]).max()), float(pd.to_numeric(w["Low"]).min())
            self.df.at[i, "range_24h"] = (hi - lo) / F
            self.df.at[i, "ret_24h"] = float(pd.to_numeric(w["Close"]).iloc[-1]) / F - 1.0
            cw = row["call_wall"]
            if pd.notna(cw) and cw > F:
                self.df.at[i, "wall_held"] = float(float(pd.to_numeric(w["Close"]).max()) < cw)
            graded += 1
        return graded

    def evidence(self, asset: str) -> Dict[str, Any]:
        cfg = GAMMA_CONFIG
        d = self.df[(self.df["asset"] == asset) & self.df["range_24h"].notna()].copy()
        out: Dict[str, Any] = {"asset": asset, "n": int(len(d))}
        if d.empty:
            out["verdict"] = "VERİ YOK"
            return out
        # Bağımsızlık: günde bir gözlem (çakışan 24s pencereleri şişirmesin).
        d["day"] = pd.to_datetime(d["ts"], utc=True).dt.floor("D")
        d["rel"] = d["range_24h"] * d["future_price"] / d["em_1d"].replace(0, np.nan)
        daily = d.groupby(["day", "regime"])["rel"].mean().reset_index()
        pos = daily[daily["regime"] == "POZİTİF GAMA"]["rel"].dropna()
        neg = daily[daily["regime"] == "NEGATİF GAMA"]["rel"].dropna()
        out.update({"n_pos_days": int(len(pos)), "n_neg_days": int(len(neg)),
                    "range_over_em_pos": round(float(pos.mean()), 3) if len(pos) else None,
                    "range_over_em_neg": round(float(neg.mean()), 3) if len(neg) else None})
        t = None
        if len(pos) >= 3 and len(neg) >= 3:
            se = math.sqrt(pos.var(ddof=1) / len(pos) + neg.var(ddof=1) / len(neg))
            t = (neg.mean() - pos.mean()) / se if se > 0 else None
        out["t_compression"] = round(float(t), 2) if t is not None else None
        wh = d.dropna(subset=["wall_held"])
        wh = wh[(wh["call_wall"] - wh["future_price"]).abs() < cfg["wall_near_em"] * wh["em_1d"]]
        whd = wh.groupby("day")["wall_held"].mean()
        out["n_wall_days"] = int(len(whd))
        if len(whd) >= 3:
            p = float(whd.mean())
            se = math.sqrt(max(p * (1 - p), 1e-6) / len(whd))
            out["wall_hold_rate"] = round(p, 3)
            out["t_wall"] = round((p - 0.5) / se, 2)
        n_ok = min(len(pos), len(neg)) >= cfg["evidence_min_n"] // 2 and len(pos) + len(neg) >= cfg["evidence_min_n"]
        proven_comp = bool(n_ok and t is not None and t >= cfg["evidence_min_t"])
        proven_wall = bool(out.get("n_wall_days", 0) >= cfg["evidence_min_n"]
                           and (out.get("t_wall") or 0) >= cfg["evidence_min_t"])
        out["proven_compression"] = proven_comp
        out["proven_wall"] = proven_wall
        out["verdict"] = ("KANITLANDI" if (proven_comp or proven_wall)
                          else "KANIT TOPLANIYOR" if len(d) else "VERİ YOK")
        return out

    def save(self, max_rows: int = 20000) -> None:
        self.df.tail(max_rows).to_csv(self.path, index=False)


# ---------------------------------------------------------------------------
# Karar katmanına bağlantı (sadece zamanlama notu; yön değişmez)
# ---------------------------------------------------------------------------
def _side_of(verdict: Dict[str, Any]) -> int:
    v = str(verdict.get("verdict", ""))
    if "SAT" in v:
        return -1
    if "AL" in v.replace("SAT", ""):
        return 1
    return 0


def annotate_verdicts(verdicts: Dict[str, Dict[str, Any]], snapshots: Dict[str, Any],
                      evidence: Optional[Dict[str, Dict[str, Any]]] = None,
                      price_frames: Optional[Dict[str, pd.DataFrame]] = None,
                      policy: Optional[str] = None,
                      intraday_frames: Optional[Dict[str, pd.DataFrame]] = None) -> Dict[str, Dict[str, Any]]:
    """Her SPX/NQ kararına gama bağlamı ekler. Giriş iznini sadece KALDIRABİLİR,
    asla vermez; ve bunu sadece politika 'active' VE defterde kanıt varsa yapar."""
    policy = policy or GAMMA_CONFIG["policy"]
    evidence = evidence or {}
    price_frames = price_frames or {}
    for asset, m in (snapshots or {}).items():
        v = verdicts.get(asset)
        if not isinstance(v, dict):
            continue
        F, em = m.get("future_price"), m.get("expected_move_1d")
        side = _side_of(v)
        notes: List[str] = []
        pin_risk = False
        above = [x for x in (m.get("call_wall"), m.get("call_wall_0dte")) if x and F and x >= F]
        below = [x for x in (m.get("put_wall"), m.get("put_wall_0dte")) if x and F and x <= F]
        wall_up = min(above) if above else None
        wall_dn = max(below) if below else None
        if m["regime"] == "POZİTİF GAMA":
            if side > 0 and wall_up and em and wall_up - F < GAMMA_CONFIG["wall_near_em"] * em:
                pin_risk = True
                notes.append(f"⚠️ +Γ: alış call duvarına ({wall_up:.0f}) çok yakın; dealer satışı testi emebilir.")
            if side < 0 and wall_dn and em and F - wall_dn < GAMMA_CONFIG["wall_near_em"] * em:
                pin_risk = True
                notes.append(f"⚠️ +Γ: satış put duvarına ({wall_dn:.0f}) çok yakın; dealer alışı testi emebilir.")
        else:
            notes.append("⚡ −Γ: dealer hedge'i hareketi büyütür; stop mesafesi beklenen hareketle uyumlu olmalı.")
        df5 = (intraday_frames or {}).get(asset)
        df = df5 if isinstance(df5, pd.DataFrame) and len(df5) >= 40 else price_frames.get(asset)
        pressure = None
        if df is not None and side != 0:
            lvl = wall_up if side > 0 else wall_dn
            # 5 dk barda son 6 saat (72 bar), 1H barda son 24 saat.
            lb = 72 if df is df5 else 24
            pressure = level_pressure(df, lvl, "above" if side > 0 else "below", lookback=lb,
                                      touch_atr=GAMMA_CONFIG["touch_atr"])
            if pressure:
                pressure["timeframe"] = "5dk" if df is df5 else "1s"
            if pressure and pressure["touches"] >= 3 and pressure["compression"] > 0.05:
                notes.append(f"🔁 Seviye yoruluyor: {pressure['note']} (emilim azalıyor, kırılım hızlı olabilir).")
        ev = evidence.get(asset) or {}
        gate_on = policy == "active" and bool(ev.get("proven_wall"))
        v["dealer_gamma"] = {
            "regime": m["regime"], "gamma_flip": m.get("gamma_flip"), "call_wall": m.get("call_wall"),
            "put_wall": m.get("put_wall"), "pin_0dte": m.get("pin_0dte"),
            "call_wall_0dte": m.get("call_wall_0dte"), "put_wall_0dte": m.get("put_wall_0dte"),
            "expected_move_1d": em, "share_0dte": m.get("share_0dte"),
            "net_gex_usd_1pct": m.get("net_gex_usd_1pct"), "pin_risk": pin_risk,
            "level_pressure": pressure, "notes": notes, "policy": policy,
            "evidence_verdict": ev.get("verdict", "VERİ YOK"), "gate_applied": False,
        }
        if pin_risk and gate_on and v.get("entry_allowed"):
            v["entry_allowed"] = False
            v["entry_status"] = "🔴 İŞLEME GİRİŞ ÖNERİLMEZ"
            v["entry_reason"] = (notes[0] + " (kanıtlı gama kapısı) | " + str(v.get("entry_reason", ""))).strip()
            v["dealer_gamma"]["gate_applied"] = True
    return verdicts


def run_cycle(grid_1h: Dict[str, Any], verdicts: Dict[str, Dict[str, Any]],
              price_frames: Dict[str, pd.DataFrame], path: str = HISTORY_FILE,
              now: Optional[pd.Timestamp] = None, intraday_frames: Optional[Dict[str, pd.DataFrame]] = None,
              **fetch_kw) -> Dict[str, Any]:
    """Arka plan döngüsü için tek giriş noktası: harita → defter → not → kanıt."""
    snapshots = build_snapshots(grid_1h, now=now, **fetch_kw)
    led = DealerGammaLedger(path)
    led.record(snapshots)
    led.grade(price_frames, now=now)
    evidence = {a: led.evidence(a) for a in GAMMA_SOURCES}
    led.save()
    annotate_verdicts(verdicts, snapshots, evidence, price_frames, intraday_frames=intraday_frames)
    return {"snapshots": snapshots, "evidence": evidence,
            "policy": GAMMA_CONFIG["policy"], "history_rows": int(len(led.df))}
