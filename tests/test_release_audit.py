from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_release import audit_release


def test_audit_accepts_generic_source_tree(tmp_path: Path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "tool.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Sample Builder\n", encoding="utf-8")

    result = audit_release(tmp_path)

    assert result.ok
    assert result.issues == []


def test_audit_accepts_https_links(tmp_path: Path):
    (tmp_path / "README.md").write_text("Install from https://example.com/project\n", encoding="utf-8")

    result = audit_release(tmp_path)

    assert result.ok


def test_audit_reports_binary_material_and_private_paths(tmp_path: Path):
    (tmp_path / "fixture.pdf").write_bytes(b"%PDF-1.7")
    drive = "D" + ":"
    (tmp_path / "script.py").write_text(f"SOURCE = r'{drive}\\private\\input.pdf'\n", encoding="utf-8")

    result = audit_release(tmp_path)

    assert not result.ok
    assert any("fixture.pdf" in issue for issue in result.issues)
    assert any("script.py" in issue and "绝对路径" in issue for issue in result.issues)
