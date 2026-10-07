"""
State storage outside the code history (v3.7)
=============================================
Problem: the tracker committed ~1.6 MB of state (memory, terminal state,
OHLCV cache, thresholds...) to `main` on every run (~16x/day, 373 commits in
23 days). Git keeps every version forever, so the repository grows by
hundreds of MB per year, and Streamlit Cloud reloaded the app on every one of
those commits.

Design:
  * `main`    — CODE ONLY. Changes only when the user uploads files.
  * `state`   — the tracker's live state. Re-published every run as ONE
                orphan commit (force-push) -> the branch never grows.
  * `reports` — weekly walk-forward outputs, same single-commit scheme.
  * The app downloads one compressed bundle (state_bundle.tar.gz) from the
    `state` branch and unpacks it next to the code (read-only use).

CLI (used by the GitHub workflows):
  python state_sync.py prune            # cap every growing file
  python state_sync.py bundle           # build state_bundle.tar.gz
"""
from __future__ import annotations

import glob
import io
import os
import sys
import tarfile
import time
from typing import List, Optional

STATE_FILES = [
    "terminal_state.json",
    "stateful_adaptive_memory.json",
    "adaptive_regime_thresholds_state.json",
    "data_freshness_state.json",
    "timeframe_confluence_state.json",
    "performance_ledger.json",
    "performance_report.md",
    "terminal_history_stateful.csv",
    "signals.json",          # v3.8: bot contract
    "paper_ledger.json",     # v3.9: paper trading
    "paper_report.md",
    "lab_playbook.json",     # v4.0: strategy lab (weekly research -> live candidate)
    "lab_report.md",
    "lab_results.json",
    "bot_status.json",       # v3.8: engine heartbeat
]
STATE_DIRS = ["ohlcv_history"]
REPORT_FILES = [  # copied from the `reports` branch, needed by app + tracker
    "validation_reports/learned_model.json",
    "validation_reports/historical_replay_report.md",
    "validation_reports/historical_replay_summary.json",
]
BUNDLE = "state_bundle.tar.gz"

# growth caps
MAX_HISTORY_ROWS = 5000          # terminal_history*.csv
MAX_BACKUPS = 10                 # state_backups/*


def prune(root: str = ".") -> List[str]:
    """Keep every file that grows over time under a fixed cap."""
    done = []
    for name in ("terminal_history_stateful.csv", "terminal_history.csv"):
        p = os.path.join(root, name)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
            if len(lines) > MAX_HISTORY_ROWS + 1:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.writelines([lines[0]] + lines[-MAX_HISTORY_ROWS:])
                done.append(f"{name}: {len(lines) - 1} -> {MAX_HISTORY_ROWS} satır")
    backups = sorted(glob.glob(os.path.join(root, "state_backups", "*")), key=os.path.getmtime)
    for old in backups[:-MAX_BACKUPS] if len(backups) > MAX_BACKUPS else []:
        try:
            os.remove(old)
        except OSError:
            pass
    if len(backups) > MAX_BACKUPS:
        done.append(f"state_backups: {len(backups)} -> {MAX_BACKUPS}")
    return done


def publish(branch: str, paths: List[str], root: str = ".", message: str = "") -> bool:
    """Force-push `paths` as ONE orphan commit to `branch` (no history growth).
    Needs GH_TOKEN + GITHUB_REPOSITORY (set by GitHub Actions)."""
    import shutil
    import subprocess
    import tempfile
    token, repo = os.environ.get("GH_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    remote = os.environ.get("TIER1_PUBLISH_REMOTE") or (
        f"https://x-access-token:{token}@github.com/{repo}.git" if token and repo else None)
    if not remote:
        print("[publish] GH_TOKEN/GITHUB_REPOSITORY yok; atlandı")
        return False
    tmp = tempfile.mkdtemp(prefix="pub_")
    try:
        for f in paths:
            src = os.path.join(root, f)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(tmp, f))
            elif os.path.exists(src):
                os.makedirs(os.path.dirname(os.path.join(tmp, f)) or tmp, exist_ok=True)
                shutil.copy2(src, os.path.join(tmp, f))
        run = lambda *a: subprocess.run(a, cwd=tmp, check=True, capture_output=True)
        run("git", "init", "-q")
        run("git", "checkout", "-q", "-b", branch)
        run("git", "config", "user.email", "quantbot@github.com")
        run("git", "config", "user.name", "QuantBot Tier-1")
        run("git", "add", "-A")
        run("git", "commit", "-q", "-m", message or f"{branch} {time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())}")
        for _ in range(3):
            r = subprocess.run(["git", "push", "-q", "-f", remote, branch], cwd=tmp, capture_output=True)
            if r.returncode == 0:
                return True
            time.sleep(5)
        print("[publish] push başarısız:", r.stderr.decode(errors="ignore")[-300:].replace(token or "", "***"))
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


STATE_PUBLISH_PATHS = STATE_FILES + STATE_DIRS + ["state_backups", BUNDLE]


def build_bundle(root: str = ".", out: Optional[str] = None) -> str:
    out = out or os.path.join(root, BUNDLE)
    with tarfile.open(out, "w:gz", compresslevel=9) as tar:
        for f in STATE_FILES + REPORT_FILES:
            p = os.path.join(root, f)
            if os.path.exists(p):
                tar.add(p, arcname=f)
        for d in STATE_DIRS:
            p = os.path.join(root, d)
            if os.path.isdir(p):
                tar.add(p, arcname=d)
    return out


def _safe_members(tar: tarfile.TarFile):
    for m in tar.getmembers():
        name = os.path.normpath(m.name)
        if name.startswith("..") or os.path.isabs(name) or not (m.isfile() or m.isdir()):
            continue
        yield m


def unpack_bundle(data: bytes, root: str = ".") -> int:
    n = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        members = list(_safe_members(tar))
        tar.extractall(root, members=members)
        n = sum(1 for m in members if m.isfile())
    return n


def bundle_url(repo: Optional[str] = None, branch: str = "state") -> Optional[str]:
    repo = repo or os.environ.get("TIER1_STATE_REPO")
    if not repo:
        try:
            from config import STATE_REPO
            repo = STATE_REPO
        except Exception:
            repo = None
    if not repo:
        return None
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{BUNDLE}"


_LAST = {"t": 0.0, "ok": False, "msg": ""}


def ensure_local_state(root: str = ".", max_age_s: float = 120.0, force: bool = False) -> dict:
    """App side: fetch the latest published state bundle (at most every
    `max_age_s` seconds unless forced). If the `state` branch does not exist
    yet (first deployment) the files already in the code checkout are used."""
    now = time.time()
    if not force and now - _LAST["t"] < max_age_s:
        return dict(_LAST)
    _LAST["t"] = now
    url = bundle_url()
    if not url:
        _LAST.update(ok=False, msg="STATE_REPO tanımlı değil; kod içindeki durum dosyaları kullanılıyor.")
        return dict(_LAST)
    try:
        import requests
        r = requests.get(url, params={"t": int(now)}, timeout=15)
        if r.status_code != 200 or not r.content:
            _LAST.update(ok=False, msg=f"state dalı henüz yok ({r.status_code}); kod içindeki dosyalar kullanılıyor.")
            return dict(_LAST)
        n = unpack_bundle(r.content, root)
        _LAST.update(ok=True, msg=f"state dalından {n} dosya yüklendi ({len(r.content) // 1024} KB).")
    except Exception as exc:
        _LAST.update(ok=False, msg=f"state indirilemedi ({type(exc).__name__}); önceki dosyalar kullanılıyor.")
    return dict(_LAST)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "prune":
        for line in prune():
            print("[prune]", line)
    elif cmd == "bundle":
        p = build_bundle()
        print("[bundle]", p, os.path.getsize(p) // 1024, "KB")
    else:
        print(__doc__)
