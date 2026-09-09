from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_review_queue import build_review_queue
from knowledge_base import KnowledgeBase


def _package(texts: list[str], filename: str) -> dict:
    return {
        "file": filename,
        "sha256": "a" * 64,
        "pages": [{"page": 1, "paragraphs": [
            {"section_id": "after-sales-service", "text": text, "bbox": [1, 1, 200, 30]}
            for text in texts
        ]}],
    }


def test_queue_deduplicates_targets_and_marks_agent_review():
    knowledge = KnowledgeBase.load(ROOT / "knowledge" / "defaults")
    source = _package([f"第{i}项售后响应与巡检安排。" for i in range(8)], "base.pdf")
    target = _package([f"第{i}项受控文件原售后内容。" for i in range(8)], "target.pdf")

    queue = build_review_queue(source, target, knowledge)

    assert len(queue["items"]) == 3
    assert len({item["proposed_target_text"] for item in queue["items"]}) == 3
    assert {item["status"] for item in queue["items"]} == {"needs_agent_review"}
    assert {item["length_tier"] for item in queue["items"]} == {"10-50"}
