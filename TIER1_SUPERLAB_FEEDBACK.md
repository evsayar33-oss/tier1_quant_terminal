# Tier-1 Quant Terminal — Quant Superlab H120 Independent Feedback

This integration connects only Tier-1 Quant Terminal and Quant Superlab.
It does not incorporate any data, labels, hypotheses, thresholds, positions
or strategies from early_accumulation_radar or Quant Superlab H119.

## How it operates

Existing Tier-1 auditor independently records hourly first-seen 4h/24h
directional outcomes in audit/30d-evidence. Tier-1's research expiry workflow
will publish frozen FINAL study verdicts on audit/study-decisions after the
original study has ended and the labeling grace period passed.

Quant Superlab H120 reads these independent sources read-only and records
a Tier-1-specific analysis in research/h120-tier1-evidence, without
modifying either repository's existing strategy logic.

This repository's new superlab_feedback.py merely reads that *published,
pinned and source-verified* H120 verdict. It compares the original Tier-1
audit commit against the current audit to detect lag, and produces a
plain-language GitHub Actions summary + downloadable run artifact.

No live input to gatekeeper, adaptive threshold, stop, dealer gamma,
Streamlit dashboard, order flow model or existing 30-day experiment
is added or changed. The display remains unchanged.

## Workflow

Actions: Tier-1 ↔ Quant Superlab H120 (read-only feedback).
Runs twice per day at 08:17 and 20:17 UTC and can run manually.
GitHub scheduled workflow timings are best effort.

On merge, the modified-file push trigger runs a one-time bootstrap check.
The workflow has contents:read only; no state publishing and no Telegram
notifications (H120 sends real milestones centrally to prevent duplication).

View the GitHub Actions run summary or tier1-superlab-readonly-feedback
artifact. A green run means the research report was fetched and schema/
source-lineage verified, **not** that Tier-1 produces profit.

## Exclusions and safety

- Terminal live model LOGIC_VERSION 2026.10.23-v2 remains locked until
  the original 2026-11-23 endpoint. No retrospective label manipulation.
- Tier-1 30-day BTC/ETH sampled trade research (through 2026-12-14)
  and six-asset sentiment study (through 2026-12-15 + grace) are unchanged.
- H120 performs descriptive forecast-vs-always-long checks on first-seen
  delayed reference prices. These do not constitute actual order fills,
  realized returns or investable index prices.
- Zero permitted entries means winning directional forecasts cannot be
  called winning executable trades.
- Model adoption would require separate preregistered research, sufficient
  independent evidence, statistical/cost gates, and an explicit production
  release authorization. No automatic ACCEPT promotion.

CI verifies missing or invalid research status fails closed. Public GitHub
API reads are authenticated with the short-lived repo Actions token; no
cross-repository write token or paid data provider is necessary.

Offline test: python -m unittest discover -s tests -p 'test_superlab_feedback.py' -v
