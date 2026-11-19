"""Tier-1 read-only view of Quant Superlab's isolated H120 audit feedback.

Zero influence on production signals, model memory, state, reports,
audit ledgers, existing 30-day studies, H119, or Early Radar.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SUPERLAB = "evsayar33-oss/quant_superlab"
SOURCE = "evsayar33-oss/tier1_quant_terminal"
BRANCH = "research/h120-tier1-evidence"
SOURCE_AUDIT = "audit/30d-evidence"
SHA = re.compile(r"^[0-9a-f]{40}$")
ASSETS = ("SPX", "NQ", "XAU", "XAG", "BTC", "ETH")


def timestamp(x):
    t = datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("FEEDBACK_NAIVE_TIME")
    return t.astimezone(timezone.utc)


def text_url(url):
    headers = {"User-Agent": "tier1-readonly-superlab-feedback",
               "Accept": "application/vnd.github+json"}
    if url.startswith("https://api.github.com/"):
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
            headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def ref_sha(repo, branch, get=text_url):
    payload = json.loads(get(
        f"https://api.github.com/repos/{repo}/git/ref/heads/{branch}"))
    sha = payload["object"]["sha"]
    if not SHA.fullmatch(sha):
        raise ValueError("INVALID_SHA_REF")
    return sha


def compare_ancestry(old_sha, new_sha, get=text_url):
    if old_sha == new_sha:
        return "CURRENT"
    if not SHA.fullmatch(old_sha) or not SHA.fullmatch(new_sha):
        raise ValueError("FEEDBACK_INVALID_SOURCE_SHA")
    result = json.loads(get(
        f"https://api.github.com/repos/{SOURCE}/compare/{old_sha}...{new_sha}"))
    if result.get("status") == "ahead" and result.get("behind_by") == 0:
        return "UPSTREAM_AUDIT_HAS_NEWER_DATA"
    raise ValueError("FEEDBACK_SOURCE_AUDIT_HISTORY_DIVERGED")


def validate(report, report_sha, current_sha, now):
    if (report.get("schema") != "QS.h120.tier1_intelligence.v1"
            or report.get("source") != SOURCE
            or report.get("state_branch") != BRANCH
            or report.get("production_logic") != "UNCHANGED"
            or report.get("research_only") is not True
            or report.get("official_gate") != "NOT_RUN"):
        raise ValueError("UNTRUSTED_H120_FEEDBACK")
    upstream_sha = report.get("source_commits", {}).get(SOURCE_AUDIT)
    if not SHA.fullmatch(upstream_sha or ""):
        raise ValueError("FEEDBACK_HAS_NO_AUDIT_SHA")
    if not SHA.fullmatch(report_sha):
        raise ValueError("FEEDBACK_HAS_NO_PINNED_SUPERLAB_SHA")
    created = timestamp(report["asof_utc"])
    observed = timestamp(report["tier1_audit_utc"])
    if created > now or observed > created:
        raise ValueError("FEEDBACK_FUTURE_SOURCE_TIME")
    if report.get("entry_allowed") is None or not isinstance(report["entry_allowed"], int):
        raise ValueError("FEEDBACK_ENTRY_PERMISSION_NOT_PRESENT")
    if report["entry_allowed"] < 0:
        raise ValueError("FEEDBACK_NEGATIVE_ENTRY_COUNT")
    if report.get("replication_leads_not_accepts", 0) not in (0, 1, 2):
        raise ValueError("FEEDBACK_UNTRUSTED_CANDIDATE_COUNT")
    grades = report["grades"]
    if set(grades) != {"4", "24"}:
        raise ValueError("FEEDBACK_WRONG_HORIZON_SET")
    for key, g in grades.items():
        if (g.get("official_lab_gate") != "NOT_RUN"
                or g.get("grade") not in (
                    "NOT_ENOUGH_INDEPENDENT_EVIDENCE",
                    "REPLICATION_LEAD_REQUIRES_NATIVE_LAB_TEST")):
            raise ValueError("FEEDBACK_UNTRUSTED_MODEL_GRADE")
        for k in ("model_hit", "always_long_hit", "bonferroni_12_p"):
            value = g.get(k)
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("FEEDBACK_INVALID_RESEARCH_METRIC")
        if not isinstance(g.get("observations"), int) or g["observations"] < 0:
            raise ValueError("FEEDBACK_INVALID_OBSERVATION_COUNT")
    return {
        "schema": "tier1.superlab_readonly_feedback.v1",
        "source": SUPERLAB, "superlab_commit_sha": report_sha,
        "source_audit_sha": upstream_sha,
        "source_is_current": upstream_sha == current_sha,
        "superlab_assessment_utc": created.isoformat(),
        "tier1_last_audit_utc": observed.isoformat(),
        "superlab_report_age_hours": round((now-created).total_seconds()/3600, 2),
        "entry_allowed": report["entry_allowed"],
        "grades": grades,
        "research_candidates_not_accepts": report["replication_leads_not_accepts"],
        "terminal_production_changed": False,
        "side_effects": "NO_STATE_OR_MODEL_WRITES",
    }


def run(get=text_url, now=None):
    now = now or datetime.now(timezone.utc)
    superlab_commit = ref_sha(SUPERLAB, BRANCH, get)
    source_commit = ref_sha(SOURCE, SOURCE_AUDIT, get)
    path = (f"https://raw.githubusercontent.com/{SUPERLAB}/{superlab_commit}"
            "/tier1_h120/latest.json")
    raw = get(path)
    report = json.loads(raw)
    view = validate(report, superlab_commit, source_commit, now)
    # Ancestry verification; if the original audit advanced, treat the
    # current H120 assessment as pending refresh, not as an error or success.
    view["source_status"] = compare_ancestry(
        view["source_audit_sha"], source_commit, get)
    view["superlab_report_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return view


def markdown(view):
    rows = [
        "# Tier-1 <-> Quant Superlab H120 (research only)", "",
        "Assessment: " + view["superlab_assessment_utc"],
        "Original Tier-1 audit: " + view["tier1_last_audit_utc"],
        "Audit lineage: " + view["source_status"],
        "Allowed-entry observations: " + str(view["entry_allowed"]), "",
        "| Horizon | Independent n | Model hit | Always long | Corrected p | Status |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for horizon in ("4", "24"):
        g = view["grades"][horizon]
        rows.append(
            f"| {horizon}h | {g['observations']} | {g['model_hit']} | "
            f"{g['always_long_hit']} | {g['bonferroni_12_p']} | {g['grade']} |")
    rows += [
        "", "**Research-only.** Proxy prices are not fills or NAV.",
        "No Tier-1 direction/entry/stop or model weight has been changed.",
        "No Early Radar experiment is transferred.",
        "Quant Superlab ACCEPT remains NOT_RUN for all imported observations.",
    ]
    return "\n".join(rows) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="tier1-superlab-feedback")
    args = parser.parse_args()
    report = run()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "feedback.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)+"\n",
        encoding="utf-8")
    content = markdown(report)
    (out / "feedback.md").write_text(content, encoding="utf-8")
    print("TIER1_SUPERLAB_READONLY_OK", report["source_status"],
          "candidates_not_accept", report["research_candidates_not_accepts"])
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(content)


if __name__ == "__main__":
    main()
