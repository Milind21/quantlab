import json
from quantlab.config import load_config
from quantlab.manifest import write_manifest


def test_manifest_contents(tmp_path):
    cfg = load_config("configs/base.yaml")
    run_dir = write_manifest(tmp_path, cfg, ts="2026-06-30T00:00:00+00:00")
    m = json.loads((run_dir / "manifest.json").read_text())
    assert m["git_sha"]
    assert m["config_hash"] == m["run_id"]
    assert "pandas" in m["package_versions"]
    assert m["config"]["risk"]["position_pct_cap"] == 0.05
    # reproducible: same config+sha -> same run_id dir name
    run_dir2 = write_manifest(tmp_path, cfg, ts="2026-06-30T01:00:00+00:00")
    assert run_dir.name == run_dir2.name
