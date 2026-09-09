from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from knowledge_base import KnowledgeBase, KnowledgeBaseError


def test_default_knowledge_classifies_configured_section():
    knowledge = KnowledgeBase.load(ROOT / "knowledge" / "defaults")

    section = knowledge.classify_section("第八章 售后服务方案")

    assert section is not None
    assert section["id"] == "after-sales-service"
    assert knowledge.is_text_allowed(section["id"])


def test_project_override_extends_existing_section_alias(tmp_path: Path):
    override = tmp_path / "sections.yml"
    override.write_text(
        "schema_version: 1\nsections:\n"
        "  - id: after-sales-service\n"
        "    aliases: [项目售后安排]\n",
        encoding="utf-8",
    )

    knowledge = KnowledgeBase.load(ROOT / "knowledge" / "defaults", override_files=[override])

    assert knowledge.classify_section("项目售后安排")["id"] == "after-sales-service"


def test_conflicting_alias_is_rejected(tmp_path: Path):
    override = tmp_path / "sections.yml"
    override.write_text(
        "schema_version: 1\nsections:\n"
        "  - id: unrelated\n"
        "    title: 其他安排\n"
        "    role: bidder-authored-solution\n"
        "    aliases: [售后服务方案]\n",
        encoding="utf-8",
    )

    with pytest.raises(KnowledgeBaseError, match="别名冲突"):
        KnowledgeBase.load(ROOT / "knowledge" / "defaults", override_files=[override])
