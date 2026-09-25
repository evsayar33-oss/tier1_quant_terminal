"""
Stateful Factor Quality / Missing-Data Guard v1.0
=================================================
Normalizes factor observations before adaptive scoring.

Goals:
* Never treat missing data as numeric zero.
* Preserve genuine zero observations when source data exists.
* Recompute selected relative-value factors with correct denominator columns.
* Attach explicit data-status metadata for the UI and learning ledger.
* Avoid a second network call; only uses the already refreshed gatekeeper grid.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from config import ASSET_MATRICES
from quant_processor import RobustQuantProcessor
from dynamic_pair_model import DynamicPairModel, XAG_XAU_MODEL, ETH_BTC_MODEL


_ALIAS = {
    "SPX": ("ES=F", "ES", "SPX"),
    "NQ": ("NQ=F", "NQ", "NQ"),
    "XAU": ("GC=F", "GC", "XAU"),
    "XAG": ("SI=F", "SI", "XAG"),
    "BTC": ("BTC-USD", "BTC"),
    "ETH": ("ETH-USD", "ETH"),
}


def _frame(grid: Dict[str, Any], *keys: str) -> pd.DataFrame:
    for key in keys:
        df = grid.get(key)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
    return pd.DataFrame()


def _close(df: pd.DataFrame) -> Optional[pd.Series]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return None
    if "Close" not in df.columns:
        return None
    s = pd.to_numeric(df["Close"], errors="coerce")
    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    return s if not s.empty else None


def _aligned_close(a: pd.DataFrame, b: pd.DataFrame) -> Optional[pd.DataFrame]:
    sa = _close(a)
    sb = _close(b)
    if sa is None or sb is None:
        return None
    out = pd.concat([sa.rename("a"), sb.rename("b")], axis=1, join="inner").dropna()
    return out if len(out) >= 5 else None


def _robust_mad_z(values: pd.Series, window: int = 48) -> Optional[float]:
    s = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(s) < 5:
        return None
    w = min(int(window), len(s))
    x = s.tail(w)
    med = float(x.median())
    mad = float(np.median(np.abs(x.to_numpy(float) - med)))
    scale = 1.4826 * mad
    if scale <= 1e-12:
        std = float(x.std(ddof=1)) if len(x) > 1 else 0.0
        scale = max(std, 1e-8)
    return float(np.clip((float(x.iloc[-1]) - med) / scale, -2.0, 2.0))


def _safe_ratio_z(num: pd.DataFrame, den: pd.DataFrame, window: int = 48) -> Optional[float]:
    aligned = _aligned_close(num, den)
    if aligned is None:
        return None
    ratio = aligned["a"] / aligned["b"].replace(0.0, np.nan)
    return _robust_mad_z(ratio, window=window)


def _factor_id_map(asset_key: str) -> Dict[str, str]:
    return {
        str(f.get("name")): str(f.get("id"))
        for f in ASSET_MATRICES.get(asset_key, {}).get("factors", [])
    }


def _source_requirements(asset_key: str, factor_id: str, grid: Dict[str, Any], gatekeeper: Any = None) -> Tuple[bool, str]:
    if factor_id == "asset_direction":
        ok = not _frame(grid, *_ALIAS.get(asset_key, ())).empty
        return ok, f"{asset_key} fiyat serisi"
    if factor_id == "gold_sympathy":
        ok = not _frame(grid, "XAU", "GC=F", "GC").empty
        return ok, "XAU/GC fiyat serisi"
    if factor_id == "btc_sympathy":
        ok = not _frame(grid, "BTC", "BTC-USD").empty
        return ok, "BTC fiyat serisi"
    if factor_id == "semi_lead":
        ok = not _frame(grid, "SMH").empty
        return ok, "SMH fiyat serisi"
    if factor_id == "market_breadth":
        ok = not _frame(grid, "RSP").empty and not _frame(grid, "SPX", "ES=F").empty
        return ok, "RSP + SPX serileri"
    if factor_id in {"gold_oil_ratio", "stagflation_shock"}:
        ok = not _frame(grid, "XAU", "GC=F").empty and not _frame(grid, "OIL", "CL=F").empty
        return ok, "XAU + petrol serileri"
    if factor_id in {"copper_gold"}:
        ok = not _frame(grid, "COPPER", "HG=F", "HG").empty and not _frame(grid, "XAU", "GC=F").empty
        return ok, "HG + XAU serileri"
    if factor_id in {"silver_monetary_catchup", "gold_sympathy", "gsr_velocity"}:
        ok = not _frame(grid, "XAG", "SI=F", "XAU", "GC=F").empty and not _frame(grid, "XAU", "GC=F").empty
        return ok, "XAG + XAU serileri"
    if factor_id == "silver_copper":
        ok = not _frame(grid, "XAG", "SI=F").empty and not _frame(grid, "COPPER", "HG=F", "HG").empty
        return ok, "XAG + HG serileri"
    if factor_id == "eth_btc_beta":
        ok = not _frame(grid, "ETH", "ETH-USD").empty and not _frame(grid, "BTC", "BTC-USD").empty
        return ok, "ETH + BTC serileri"
    if factor_id == "credit_spread":
        ok = not _frame(grid, "HYG").empty and not _frame(grid, "LQD").empty
        return ok, "HYG + LQD serileri"
    if factor_id in {"vix_strain", "safe_haven", "vix_term"}:
        ok = not _frame(grid, "VIX", "^VIX").empty
        return ok, "VIX serisi"
    if factor_id == "usd_strength":
        ok = not _frame(grid, "DXY", "UUP").empty
        return ok, "DXY/UUP serisi"
    if factor_id == "real_yield":
        ok = not _frame(grid, "DFII10", "TIPS", "TIP").empty
        return ok, "DFII10/TIPS serisi"
    if factor_id == "breakeven_infl":
        ok = not _frame(grid, "T10YIE").empty or (
            not _frame(grid, "IEF").empty and not _frame(grid, "TIPS", "TIP").empty
        )
        return ok, "T10YIE veya IEF/TIPS serileri"
    if factor_id == "duration_risk":
        ok = not _frame(grid, "TLT").empty and not _frame(grid, "SHY").empty
        return ok, "TLT + SHY serileri"
    if factor_id == "net_dollar_liquidity":
        value = getattr(gatekeeper, "ndl_z", None)
        ok = value is not None
        try:
            ok = ok and np.isfinite(float(value))
        except (TypeError, ValueError):
            ok = False
        return ok, "Gatekeeper NDL metriği"
    if factor_id == "usd_jpy_carry":
        ok = not _frame(grid, "USDJPY", "JPY=X").empty
        return ok, "USDJPY serisi"
    return True, "faktörün mevcut kaynakları"


def _recompute_factor_value(asset_key: str, factor_id: str, gatekeeper: Any) -> Optional[float]:
    grid = getattr(gatekeeper, "grid_1h", {}) or {}
    proc = getattr(gatekeeper, "processor", None) or RobustQuantProcessor()

    if factor_id == "asset_direction":
        df = _frame(grid, *_ALIAS.get(asset_key, ()))
        if df.empty:
            return None
        val = proc.compute_intraday_direction_momentum(df, vol_scale=ASSET_MATRICES.get(asset_key, {}).get("vol_scale", 1.0))
        return float(val) if np.isfinite(float(val)) else None

    if factor_id == "gold_sympathy":
        df = _frame(grid, "XAU", "GC=F", "GC")
        if df.empty:
            return None
        val = proc.compute_intraday_direction_momentum(df, vol_scale=1.0)
        return float(val) if np.isfinite(float(val)) else None

    if factor_id == "btc_sympathy":
        df = _frame(grid, "BTC", "BTC-USD")
        if df.empty:
            return None
        val = proc.compute_intraday_direction_momentum(df, vol_scale=1.8)
        return float(val) if np.isfinite(float(val)) else None

    # Correct relative-value calculations: denominator must use denominator.Close.
    if factor_id == "silver_monetary_catchup":
        return _safe_ratio_z(_frame(grid, "XAG", "SI=F", "XAG"), _frame(grid, "XAU", "GC=F", "GC"), window=24)
    if factor_id == "silver_copper":
        return _safe_ratio_z(_frame(grid, "XAG", "SI=F", "XAG"), _frame(grid, "COPPER", "HG=F", "HG"), window=24)
    if factor_id == "copper_gold":
        return _safe_ratio_z(_frame(grid, "COPPER", "HG=F", "HG"), _frame(grid, "XAU", "GC=F", "GC"), window=48)
    if factor_id == "eth_btc_beta":
        return _safe_ratio_z(_frame(grid, "ETH", "ETH-USD"), _frame(grid, "BTC", "BTC-USD"), window=48)
    if factor_id == "gsr_velocity":
        return _safe_ratio_z(_frame(grid, "XAU", "GC=F", "GC"), _frame(grid, "XAG", "SI=F", "XAG"), window=24)
    if factor_id == "gold_oil_ratio":
        return _safe_ratio_z(_frame(grid, "XAU", "GC=F", "GC"), _frame(grid, "OIL", "CL=F"), window=48)
    if factor_id == "market_breadth":
        return _safe_ratio_z(_frame(grid, "RSP"), _frame(grid, "SPX", "ES=F"), window=24)

    # Scalar macro factors are accepted only from an explicitly refreshed
    # gatekeeper value with a live supporting source. This avoids legacy
    # fallback constants such as 0.25 / 0.45 / 0.65 being interpreted as data.
    if factor_id == "usd_strength":
        value = getattr(gatekeeper, "dxy_velocity", None)
        try:
            return float(np.clip(float(value), -1.8, 1.8)) if value is not None and np.isfinite(float(value)) else None
        except (TypeError, ValueError):
            return None
    if factor_id == "real_yield":
        value = getattr(gatekeeper, "real_yield_z", None)
        try:
            return float(np.clip(float(value), -1.8, 1.8)) if value is not None and np.isfinite(float(value)) else None
        except (TypeError, ValueError):
            return None
    if factor_id == "breakeven_infl":
        value = getattr(gatekeeper, "breakeven_z", None)
        try:
            return float(np.clip(float(value), -1.8, 1.8)) if value is not None and np.isfinite(float(value)) else None
        except (TypeError, ValueError):
            return None
    if factor_id == "credit_spread":
        value = getattr(gatekeeper, "credit_velocity", None)
        try:
            return float(np.clip(float(value), -1.8, 1.8)) if value is not None and np.isfinite(float(value)) else None
        except (TypeError, ValueError):
            return None
    if factor_id == "stagflation_shock":
        value = getattr(gatekeeper, "stagflation_z", None)
        try:
            return float(np.clip(float(value), -1.8, 1.8)) if value is not None and np.isfinite(float(value)) else None
        except (TypeError, ValueError):
            return None
    if factor_id == "usd_jpy_carry":
        value = getattr(gatekeeper, "yen_carry_z", None)
        try:
            return float(np.clip(float(value), -1.8, 1.8)) if value is not None and np.isfinite(float(value)) else None
        except (TypeError, ValueError):
            return None
    if factor_id == "net_dollar_liquidity":
        value = getattr(gatekeeper, "ndl_z", None)
        try:
            return float(np.clip(float(value), -1.8, 1.8)) if value is not None and np.isfinite(float(value)) else None
        except (TypeError, ValueError):
            return None
    if factor_id == "credit_spread":
        return _safe_ratio_z(_frame(grid, "HYG"), _frame(grid, "LQD"), window=24)
    return None


def sanitize_factor_rows(asset_key: str, detail_rows: Iterable[Dict[str, Any]], gatekeeper: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    grid = getattr(gatekeeper, "grid_1h", {}) or {}
    id_by_name = _factor_id_map(asset_key)
    out: List[Dict[str, Any]] = []
    valid_weight = 0.0
    configured_weight = 0.0
    missing_ids: List[str] = []
    zero_ids: List[str] = []

    for factor in ASSET_MATRICES.get(asset_key, {}).get("factors", []):
        configured_weight += float(factor.get("base_weight", 0.0))

    rows_by_name = {
        str(row.get("faktör")): row
        for row in detail_rows
        if isinstance(row, dict)
    }

    for factor in ASSET_MATRICES.get(asset_key, {}).get("factors", []):
        fname = str(factor.get("name"))
        fid = str(factor.get("id"))
        row = dict(rows_by_name.get(fname, {"faktör": fname, "küme": factor.get("cluster", "UNKNOWN")}))
        source_ok, source_desc = _source_requirements(asset_key, fid, grid, gatekeeper)
        raw = row.get("ham_deger")
        numeric: Optional[float]
        try:
            numeric = float(raw)
            if not np.isfinite(numeric):
                numeric = None
        except (TypeError, ValueError):
            numeric = None

        # Recompute selected factors from authoritative grid values so buggy
        # legacy ratio helpers cannot contaminate the adaptive score.
        corrected = _recompute_factor_value(asset_key, fid, gatekeeper)
        if corrected is not None:
            numeric = float(np.clip(corrected, -1.8, 1.8))

        if not source_ok and fid not in {"net_dollar_liquidity"}:
            numeric = None

        if numeric is None:
            missing_ids.append(fid)
            row["ham_deger"] = None
            row["puan"] = None
            row["veri_durumu"] = "VERİ YETERSİZ"
            row["veri_kaynagi"] = source_desc
        else:
            numeric = float(np.clip(numeric, -1.8, 1.8))
            row["ham_deger"] = round(numeric, 6)
            if abs(numeric) < 1e-12:
                zero_ids.append(fid)
                row["veri_durumu"] = "MEVCUT / NÖTR"
            else:
                row["veri_durumu"] = "MEVCUT"
            row["veri_kaynagi"] = source_desc
            valid_weight += float(factor.get("base_weight", 0.0))
            # Display score is reconstructed later by AdaptiveScoreModel.
            row["puan"] = row.get("puan") if row.get("puan") is not None else None

        row["faktor_id"] = fid
        out.append(row)

    coverage = valid_weight / max(configured_weight, 1e-12)
    status = "OK" if coverage >= 0.55 else "DÜŞÜK VERİ KAPSAMI" if coverage >= 0.45 else "YETERSİZ VERİ"
    return out, {
        "coverage": round(float(coverage), 4),
        "configured_weight": round(float(configured_weight), 4),
        "valid_weight": round(float(valid_weight), 4),
        "valid_factor_count": sum(1 for r in out if r.get("veri_durumu") != "VERİ YETERSİZ"),
        "missing_factor_count": len(missing_ids),
        "missing_factor_ids": missing_ids,
        "zero_value_factor_ids": zero_ids,
        "status": status,
    }
