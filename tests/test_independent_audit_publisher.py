"""Reproduce the dirty production-state checkout that broke audit publish.

Uses local Git only. This is a regression for preserving an unrelated
dirty checkout while committing evidence in a separate worktree.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True).stdout.strip()


class TestAuditWorktreePublisher(unittest.TestCase):
    def test_dirty_main_remains_untouched_when_evidence_committed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            git(root, "init", "-q", "-b", "main")
            git(root, "config", "user.email", "test@example.invalid")
            git(root, "config", "user.name", "test")
            (root / "production_state.json").write_text('{"cycle":1}\n')
            git(root, "add", ".")
            git(root, "commit", "-qm", "main")
            # Independent evidence branch with existing history.
            git(root, "checkout", "--orphan", "audit/30d-evidence")
            git(root, "rm", "-rf", ".")
            (root / "independent_audit").mkdir()
            (root / "independent_audit" / "ledger.json").write_text('{"old":1}\n')
            git(root, "add", ".")
            git(root, "commit", "-qm", "first evidence")
            evidence_ref = git(root, "rev-parse", "HEAD")
            git(root, "checkout", "main")
            (root / "production_state.json").write_text('{"cycle":2}\n')
            # This is the exact circumstance in the failed run:
            # a local checkout carries newer live state and untracked evidence.
            (root / "independent_audit").mkdir(exist_ok=True)
            (root / "independent_audit" / "ledger.json").write_text('{"new":2}\n')
            worktree = Path(tmp) / "clean-evidence"
            git(root, "worktree", "add", "--detach", str(worktree), evidence_ref)
            (worktree / "independent_audit" / "ledger.json").write_text('{"new":2}\n')
            git(worktree, "add", "independent_audit")
            git(worktree, "commit", "-qm", "new evidence")
            self.assertEqual((root / "production_state.json").read_text(), '{"cycle":2}\n')
            self.assertEqual((root / "independent_audit" / "ledger.json").read_text(), '{"new":2}\n')
            self.assertEqual((worktree / "independent_audit" / "ledger.json").read_text(), '{"new":2}\n')
            self.assertNotEqual(git(worktree, "rev-parse", "HEAD"), evidence_ref)


if __name__ == "__main__":
    unittest.main()
