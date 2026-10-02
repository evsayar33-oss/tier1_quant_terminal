"""v3.7 tests: state lives outside code history, files stay bounded."""
import io
import os
import tarfile

import state_sync as ss


def test_prune_caps_history_and_backups(tmp_path):
    p = tmp_path / "terminal_history_stateful.csv"
    p.write_text("h\n" + "".join(f"{i}\n" for i in range(ss.MAX_HISTORY_ROWS + 500)))
    (tmp_path / "state_backups").mkdir()
    for i in range(ss.MAX_BACKUPS + 7):
        f = tmp_path / "state_backups" / f"b{i}.bak"
        f.write_text("x")
        os.utime(f, (1000 + i, 1000 + i))
    ss.prune(str(tmp_path))
    lines = p.read_text().splitlines()
    assert lines[0] == "h" and len(lines) == ss.MAX_HISTORY_ROWS + 1 and lines[-1] == str(ss.MAX_HISTORY_ROWS + 499)
    assert len(os.listdir(tmp_path / "state_backups")) == ss.MAX_BACKUPS


def test_bundle_roundtrip(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    (src / "ohlcv_history").mkdir(parents=True)
    (src / "validation_reports").mkdir()
    (src / "terminal_state.json").write_text('{"a": 1}')
    (src / "ohlcv_history" / "X.csv").write_text("t,c\n")
    (src / "validation_reports" / "learned_model.json").write_text("{}")
    (src / "secret.txt").write_text("not bundled")
    out = ss.build_bundle(str(src))
    dst.mkdir()
    n = ss.unpack_bundle(open(out, "rb").read(), str(dst))
    assert n == 3 and (dst / "ohlcv_history" / "X.csv").exists() and not (dst / "secret.txt").exists()


def test_unpack_rejects_path_traversal(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"evil"
        ti = tarfile.TarInfo("../evil.py")
        ti.size = len(data)
        tar.addfile(ti, io.BytesIO(data))
    (tmp_path / "in").mkdir()
    ss.unpack_bundle(buf.getvalue(), str(tmp_path / "in"))
    assert not (tmp_path / "evil.py").exists()


def test_bundle_url_from_config():
    assert ss.bundle_url().endswith("/state/state_bundle.tar.gz")
