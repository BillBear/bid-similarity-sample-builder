from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_documented_commands_expose_help():
    commands = {
        "extract_candidates.py": "只读结构化候选证据包",
        "build_review_queue.py": "待复核队列",
        "validate_manifest.py": "校验 Manifest",
        "apply_manifest.py": "构造 PDF 受控样本",
    }

    for script, expected in commands.items():
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert expected in result.stdout
