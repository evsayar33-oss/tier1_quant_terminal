"""Offline notifier tests: no Telegram calls or credentials required."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import research_autopilot_notify as notify


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = {
            "study_id": "tier1_v2_forward", "stage": "FINAL",
            "end_utc": "2026-11-24T00:00:00+00:00",
            "assessment": {"decision": "DATA_INSUFFICIENT", "reason": "limited observations"},
        }

    def make_pending(self):
        p = self.root / "tier1_v2_forward-final.json"
        p.write_text(json.dumps(self.record), encoding="utf-8")
        return p

    def test_empty_outbox_does_not_require_credentials(self):
        self.assertEqual(notify.send_pending(self.root), 0)

    def test_exactly_once_ack_on_confirmed_delivery(self):
        p = self.make_pending()
        sent = []
        def fake_send(token, chat, message):
            sent.append((token, chat, message))
        with patch.dict(os.environ, {"TELEGRAM_TOKEN": "TEST_TOKEN", "CHAT_ID": "999"}):
            self.assertEqual(notify.send_pending(self.root, sender=fake_send), 1)
            self.assertEqual(notify.send_pending(self.root, sender=fake_send), 0)
        self.assertEqual(len(sent), 1)
        self.assertIn("DATA_INSUFFICIENT", sent[0][2])
        self.assertTrue((self.root / "notification_acks" / (p.stem + ".txt")).exists())

    def test_failed_send_is_retryable(self):
        p = self.make_pending()
        def fail(*args):
            raise RuntimeError("network failure")
        with patch.dict(os.environ, {"TELEGRAM_TOKEN": "TEST_TOKEN", "CHAT_ID": "999"}):
            with self.assertRaisesRegex(RuntimeError, "network failure"):
                notify.send_pending(self.root, sender=fail)
        self.assertFalse((self.root / "notification_acks" / (p.stem + ".txt")).exists())


if __name__ == "__main__":
    unittest.main()
