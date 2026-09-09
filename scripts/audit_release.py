"""Audit a source tree before publishing it as a reusable Skill."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


BLOCKED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".docx",
    ".xlsx",
    ".pptx",
    ".zip",
}
TEXT_EXTENSIONS = {".md", ".py", ".json", ".yml", ".yaml", ".txt", ".toml"}
ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|file://|/(?:Users|home)/)")
EXTERNAL_BUILDER = "build_" + "samples_n1"


@dataclass(frozen=True)
class AuditResult:
    issues: list[str]

    @property
    def ok(self) -> bool:
        return not self.issues


def audit_release(root: Path) -> AuditResult:
    """Return all publishing issues found below *root*."""
    root = root.resolve()
    issues: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts or ".pytest_cache" in relative.parts:
            continue
        if path.is_dir():
            if path.name == "__pycache__":
                continue
            continue
        if path.suffix.lower() in BLOCKED_EXTENSIONS:
            issues.append(f"二进制样本材料：{relative}")
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if relative.parts and relative.parts[0] == "tests":
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        if relative == Path("scripts/audit_release.py"):
            continue
        if ABSOLUTE_PATH.search(content):
            issues.append(f"绝对路径：{relative}")
        if EXTERNAL_BUILDER in content:
            issues.append(f"外部构建器引用：{relative}")
    return AuditResult(issues)


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 Skill 发布目录是否适合公开发布")
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    args = parser.parse_args()
    result = audit_release(args.root)
    if result.ok:
        print("发布审计通过。")
        return 0
    print("发布审计发现问题：")
    for issue in result.issues:
        print(f"- {issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
