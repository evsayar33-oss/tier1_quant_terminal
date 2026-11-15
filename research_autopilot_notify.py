"""Telegram outbox: only acknowledge a research decision after confirmed delivery.

Workflow runs this on main AFTER committing immutable decision records to the
audit branch. On missing credentials or HTTP errors it exits nonzero; no ack is
written. It does not send trade instructions or authorize orders.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def render(item):
    a = item["assessment"]
    head = ("Tier-1 | Otomatik arastirma karari\n"
            + item["study_id"] + " | " + item["stage"] + "\n"
            + "Sonuc: " + str(a["decision"]) + "\n"
            + "Pencere bitisi (UTC): " + str(item.get("end_utc")) + "\n")
    if a.get("reason"):
        head += str(a["reason"])[:500] + "\n"
    if a.get("followup_assets"):
        head += "Yeniden dogrulama adaylari: " + ", ".join(a["followup_assets"]) + "\n"
    if a.get("per_asset"):
        for symbol, stat in sorted(a["per_asset"].items()):
            n = stat.get("independent_4h_n", stat.get("nonoverlap_n", "?"))
            status = stat.get("suggested_status", stat.get("status", "?"))
            head += f"{symbol}: n={n}, {status}\n"
    head += "Otomatik uygulanan: ARAŞTIRMA DURUMU. Canli islem/strateji terfisi: YOK."
    return head[:3900]


def post(token, chat_id, message):
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": message,
                                   "disable_web_page_preview": "true"}).encode()
    request = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/sendMessage",
        data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("ok") is not True:
        raise RuntimeError("Telegram did not confirm delivery")


def send_pending(directory, sender=post):
    root = Path(directory)
    files = sorted(root.glob("*.json"))
    pending = [p for p in files if not (root / "notification_acks" / (p.stem + ".txt")).exists()]
    if not pending:
        return 0
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Telegram credentials missing; pending decisions remain unacknowledged")
    ackdir = root / "notification_acks"
    ackdir.mkdir(parents=True, exist_ok=True)
    for path in pending:
        record = json.loads(path.read_text(encoding="utf-8"))
        sender(token, chat_id, render(record))
        stamp = datetime.now(timezone.utc).isoformat()
        ack = ackdir / (path.stem + ".txt")
        ack.write_text("DELIVERED_UTC=" + stamp + "\n", encoding="utf-8")
        print("Telegram delivery confirmed:", path.stem)
    return len(pending)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="research_decisions")
    args = parser.parse_args()
    print("New delivered notifications:", send_pending(args.out))


if __name__ == "__main__":
    main()
