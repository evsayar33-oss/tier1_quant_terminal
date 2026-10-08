"""ATVS crypto daily MACD rules (EMA rule + X rule) — implementation for the karma bot.

Specification: STRATEJI_DEVIR.md (sections 2, 3, 5). Parameters are FIXED by the source system and must not be
tuned. Verified against test_vektorleri/ (signals bit-for-bit, trades to 1e-9 R) by tests/test_atvs.py.

Two layers:
  * pure functions (indicators, signals, single-trade simulation, batch backtest) — used for verification
  * AtvsBook — the stateful engine the bot runs once per closed daily candle: it opens/updates/closes positions
    exactly like the batch backtest, sizes them with the section-5 risk rules, and keeps a paper ledger (demo).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ fixed parameters (do NOT tune)
MACD_DIR = (675, 875, 475)       # user's 1h TradingView MACD, scaled to daily
BASE_MIN, TF_MIN = 60, 1440
ATR_LEN = 14
HORIZON = 48
SL_ATR, TRAIL_ATR = 1.0, 2.5
R_FLOOR, R_CAP = -3.0, 20.0
COOLDOWN = {"EMA": 6, "X": 3}
RISK = {"EMA": 0.005, "X": 0.02}  # fraction of equity risked per trade (1R)
PRIORITY = ("X", "EMA")           # when both fire on the same coin, X first
COINS = ("BTC", "ETH", "BNB", "XRP", "ADA", "SOL", "DOGE", "LTC", "LINK", "TRX", "DOT", "AVAX", "BCH", "ETC", "XLM")
COST_BPS = 13.0                   # round-trip cost used by the source backtest (fees + spread)
FUND_BPS_DAY = 3.0

# section 5 — risk manager
DD_BRAKES = ((0.30, 0.0), (0.20, 0.25), (0.10, 0.5))   # drawdown from peak -> risk multiplier (0 = no new trades)
DAILY_LOSS_LIMIT = 0.03
OPEN_RISK_CAP = 0.10
MAX_POSITIONS = 6


# ------------------------------------------------------------------ indicators and signals
def ema(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(span=n, adjust=False, min_periods=n).mean()


def rma(x: pd.Series, n: int) -> pd.Series:
    return x.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def atr(df: pd.DataFrame) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    a = rma(tr, ATR_LEN)
    return np.maximum(a, 0.5 * a.rolling(500, min_periods=50).median().bfill())


def direction(close: pd.Series) -> np.ndarray:
    s = BASE_MIN / TF_MIN
    nf, ns, nsig = (max(2, int(round(x * s))) for x in MACD_DIR)          # 28, 36, 20
    m = ema(close, nf) - ema(close, ns)
    return np.sign((m - ema(m, nsig)).to_numpy())


def _cooldown(e: np.ndarray, n: int) -> np.ndarray:
    prev = pd.Series(e.astype(np.int8)).shift(1).rolling(n, min_periods=1).max().fillna(0).to_numpy().astype(bool)
    return e & ~prev


def signals(df: pd.DataFrame) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """{"EMA": (long, short), "X": (long, short)} — signal at the close of bar i, entry at open of bar i+1."""
    c, h, l = (df[k].to_numpy(float) for k in ("close", "high", "low"))
    d = direction(df["close"])
    up, dn = d > 0, d < 0
    e20 = ema(df["close"], 20).to_numpy()
    fm = ema(df["close"], 12) - ema(df["close"], 26)
    x = (fm - ema(fm, 9)).to_numpy()
    xp = np.r_[np.nan, x[:-1]]
    with np.errstate(invalid="ignore"):
        le = up & (l <= e20) & (c > e20)
        se = dn & (h >= e20) & (c < e20)
        lx = up & (xp <= 0) & (x > 0)
    b = lambda a: np.nan_to_num(a.astype(float)).astype(bool)  # noqa: E731
    return {"EMA": (_cooldown(b(le), COOLDOWN["EMA"]), _cooldown(b(se), COOLDOWN["EMA"])),
            "X": (_cooldown(b(lx), COOLDOWN["X"]), np.zeros(len(c), bool))}


# ------------------------------------------------------------------ one trade (shared by batch and live engine)
@dataclass
class Trade:
    rule: str
    coin: str
    side: int
    signal_bar: str          # date of the signal candle
    atr: float               # ATR on the signal candle (fixed for the whole trade)
    entry: float = float("nan")
    stop: float = float("nan")
    ext: float = float("nan")
    k: int = 0               # bars evaluated since entry
    qty: float = 0.0         # paper/live size (units of the coin)
    risk_cash: float = 0.0   # qty * initial risk at entry
    entry_date: str = ""
    exit: float = float("nan")
    exit_date: str = ""
    R: float = float("nan")
    pnl_cash: float = 0.0
    status: str = "pending"  # pending -> open -> closed

    def open_at(self, price: float, date: str) -> None:
        self.entry, self.entry_date = price, date
        e = self.side * price
        self.stop, self.ext = e - SL_ATR * self.atr, e          # stored in "side space" (short: negated prices)
        self.status = "open"

    def stop_price(self) -> float:
        return self.side * self.stop

    def on_bar(self, o: float, h: float, l: float, c: float, date: str) -> bool:
        """Evaluate one closed candle; returns True when the trade closed on it. Stop first, then trail update."""
        self.k += 1
        hh = h if self.side == 1 else -l
        ll = l if self.side == 1 else -h
        e, risk = self.side * self.entry, SL_ATR * self.atr
        if ll <= self.stop:
            self._close((self.stop - e) / risk, self.side * self.stop, date)
            return True
        self.ext = max(self.ext, hh)
        self.stop = max(self.stop, self.ext - TRAIL_ATR * self.atr)
        if self.k >= HORIZON:
            self._close((self.side * c - e) / risk, c, date)
            return True
        return False

    def _close(self, r_raw: float, px: float, date: str) -> None:
        risk = SL_ATR * self.atr
        self.R = float(np.clip(r_raw, R_FLOOR, R_CAP)) - (COST_BPS / 1e4) * self.entry / risk \
            - (FUND_BPS_DAY / 1e4) * self.k * self.entry / risk
        self.exit, self.exit_date, self.status = px, date, "closed"
        self.pnl_cash = self.R * self.risk_cash

    def open_risk_cash(self) -> float:
        """Cash lost if the current stop is hit; 0 once the stop is at/after the entry (section 5.4)."""
        e = self.side * self.entry
        return max(0.0, (e - self.stop)) * self.qty


def backtest(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Single coin, single rule, no overlap — same contract as the reference backtest()."""
    a = atr(df).to_numpy()
    L, S = signals(df)[rule]
    ev = sorted([(int(i), 1) for i in np.flatnonzero(L)] + [(int(i), -1) for i in np.flatnonzero(S)])
    cnt = pd.Series([i for i, _ in ev]).value_counts().to_dict() if ev else {}
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n, rows, last = len(c), [], -1
    for i, side in ev:
        if cnt.get(i, 0) > 1 or i < last or i + HORIZON >= n or not np.isfinite(a[i]) or a[i] <= 0:
            continue
        t = Trade(rule, "", side, str(df.index[i]), float(a[i]))
        t.open_at(o[i + 1], str(df.index[i + 1]))
        j = i
        while t.status == "open":
            j += 1
            t.on_bar(o[j], h[j], l[j], c[j], str(df.index[j]))
        rows.append({"bar": i, "side": side, "k": t.k, "R": t.R, "entry_time": df.index[i + 1],
                     "exit_time": df.index[i + t.k] + pd.Timedelta(days=1)})
        last = i + t.k
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ section 5 risk manager
def risk_multiplier(equity: float, peak: float) -> float:
    dd = 1 - equity / peak if peak > 0 else 0.0
    for lim, mult in DD_BRAKES:
        if dd >= lim:
            return mult
    return 1.0


# ------------------------------------------------------------------ stateful engine (one call per closed daily candle)
@dataclass
class AtvsBook:
    equity: float                                   # demo: paper equity of this sleeve; live: account equity
    peak: float = 0.0
    day_start_equity: float = 0.0
    trades: List[Trade] = field(default_factory=list)   # pending + open
    closed: List[dict] = field(default_factory=list)
    last_bar: Dict[str, str] = field(default_factory=dict)   # coin -> last processed candle date
    busy_until: Dict[str, str] = field(default_factory=dict)  # f"{rule}|{coin}" -> exit candle date (no-overlap rule)
    live: bool = False                              # True: equity is the real account (set by the caller every run)

    # -- persistence
    def to_dict(self) -> dict:
        d = asdict(self)
        d["trades"] = [asdict(t) for t in self.trades]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AtvsBook":
        b = cls(**{k: v for k, v in d.items() if k != "trades"})
        b.trades = [Trade(**t) for t in d.get("trades", [])]
        return b

    def open_positions(self) -> List[Trade]:
        return [t for t in self.trades if t.status == "open"]

    def open_risk(self) -> float:
        return sum(t.open_risk_cash() for t in self.open_positions())

    def step(self, candles: Dict[str, pd.DataFrame], other_positions: int = 0, other_coins: set = frozenset(),
             rules: Tuple[str, ...] = PRIORITY, entries_on: Optional[set] = None) -> List[str]:
        """Process every candle that closed since the last call.
        candles: coin -> daily OHLC (closed candles only, ascending, UTC 00:00 index), >= ~300 days of history.
        other_positions / other_coins: positions held by the rest of the system (section 2.6 / 5.5 — one position per
        coin system-wide, at most 6 positions in total).
        entries_on: if given, new entries are taken only from signals on these candle dates (live rule: act within
        2 hours of the 00:00 UTC close, never chase a signal seen later). None = every processed candle (backtest).
        Returns human-readable log lines."""
        log: List[str] = []
        dates = sorted({d for df in candles.values() for d in df.index})
        new_dates = [d for d in dates if all(str(d) > self.last_bar.get(c, "") for c in candles if d in candles[c].index)]
        if not self.peak:
            self.peak = self.equity
        for d in new_dates:
            if self.day_start_equity <= 0:
                self.day_start_equity = self.equity
            # 1) fill pending entries at today's open, then evaluate today's candle for every open trade
            for t in list(self.trades):
                df = candles.get(t.coin)
                if df is None or d not in df.index:
                    continue
                row = df.loc[d]
                if t.status == "pending":
                    t.open_at(float(row.open), str(d))
                    t.qty = t.risk_cash / (SL_ATR * t.atr)
                    log.append(f"ATVS AÇ {t.rule} {t.coin} {'LONG' if t.side > 0 else 'SHORT'} @ {t.entry:.6g} "
                               f"stop {t.stop_price():.6g} risk {t.risk_cash:,.2f} USDT")
                if t.on_bar(float(row.open), float(row.high), float(row.low), float(row.close), str(d)):
                    if not self.live:
                        self.equity += t.pnl_cash
                    self.busy_until[f"{t.rule}|{t.coin}"] = str(d)
                    self.closed.append(asdict(t))
                    self.trades.remove(t)
                    log.append(f"ATVS KAPA {t.rule} {t.coin} {t.R:+.2f}R ({t.pnl_cash:+,.2f} USDT) {t.k} gün")
            self.peak = max(self.peak, self.equity)
            # 2) new signals on today's close -> pending entries for tomorrow's open (risk rules decide)
            mult = risk_multiplier(self.equity, self.peak)
            day_loss = 1 - self.equity / self.day_start_equity if self.day_start_equity > 0 else 0.0
            blocked = mult == 0.0 or day_loss >= DAILY_LOSS_LIMIT
            held = {t.coin for t in self.trades} | set(other_coins)
            n_pos = len(self.trades) + other_positions
            for coin, df in sorted(candles.items()):
                if d not in df.index:
                    continue
                hist = df.loc[:d]
                if len(hist) < 60:
                    continue
                sig = signals(hist)
                a = float(atr(hist).iloc[-1])
                for rule in [r for r in PRIORITY if r in rules]:
                    L, S = sig[rule]
                    side = 1 if L[-1] else (-1 if S[-1] else 0)
                    if L[-1] and S[-1]:
                        side = 0
                    if side == 0:
                        continue
                    if entries_on is not None and str(d) not in entries_on:
                        log.append(f"ATVS sinyal atlandı {rule} {coin} (geç görüldü, fiyatın peşinden koşulmaz)")
                        continue
                    key = f"{rule}|{coin}"
                    if self.busy_until.get(key, "") > str(d) or any(t.rule == rule and t.coin == coin for t in self.trades):
                        continue
                    why = None
                    if blocked:
                        why = "risk freni" if mult == 0.0 else "günlük zarar limiti"
                    elif coin in held:
                        why = "coin'de zaten pozisyon var"
                    elif n_pos >= MAX_POSITIONS:
                        why = "6 pozisyon tavanı"
                    risk_cash = self.equity * RISK[rule] * mult
                    if why is None and self.open_risk() + sum(t.risk_cash for t in self.trades if t.status == "pending") \
                            + risk_cash > OPEN_RISK_CAP * self.equity:
                        why = "açık risk tavanı %10"
                    if why or not np.isfinite(a) or a <= 0:
                        log.append(f"ATVS sinyal atlandı {rule} {coin} ({why or 'ATR yok'})")
                        continue
                    self.trades.append(Trade(rule, coin, side, str(d), a, risk_cash=risk_cash))
                    held.add(coin)
                    n_pos += 1
                    log.append(f"ATVS SİNYAL {rule} {coin} {'LONG' if side > 0 else 'SHORT'} (giriş yarın açılışta)")
            for c in candles:
                if d in candles[c].index:
                    self.last_bar[c] = str(d)
            self.day_start_equity = self.equity
        return log


def start_book(equity: float, candles: Dict[str, pd.DataFrame]) -> AtvsBook:
    """A fresh book starts at the latest closed candle: history is used for indicators only, never traded."""
    b = AtvsBook(equity=equity, peak=equity, day_start_equity=equity)
    for c, df in candles.items():
        if len(df) >= 2:
            b.last_bar[c] = str(df.index[-2])
    return b


def summary(book: AtvsBook) -> List[str]:
    out = []
    cl = pd.DataFrame(book.closed)
    for rule, exp in (("EMA", 0.222), ("X", 0.633)):
        x = cl[cl.rule == rule] if len(cl) else cl
        if len(x):
            out.append(f"ATVS {rule}: {len(x)} işlem · ort {x.R.mean():+.3f}R (beklenti {exp:+.3f}R) · kazanma %{(x.R > 0).mean() * 100:.0f}")
        else:
            out.append(f"ATVS {rule}: henüz kapanmış işlem yok (beklenti {exp:+.3f}R)")
    for t in book.open_positions():
        out.append(f"  açık {t.rule} {t.coin} {'LONG' if t.side > 0 else 'SHORT'} giriş {t.entry:.6g} stop {t.stop_price():.6g} gün {t.k}")
    out.append(f"ATVS demo kasa {book.equity:,.2f} USDT · zirveden düşüş %{(1 - book.equity / book.peak) * 100 if book.peak else 0:.1f}"
               f" · risk çarpanı x{risk_multiplier(book.equity, book.peak):g}")
    return out
