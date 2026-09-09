"""Build a bounded Agent review queue from read-only evidence packages."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from knowledge_base import KnowledgeBase
from rank_candidates import rank_text_candidates


def _section_paragraphs(package: dict[str, Any], *, per_section: int = 12) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for page in package.get("pages", []):
        for paragraph in page.get("paragraphs", []):
            section_id = paragraph.get("section_id")
            text = str(paragraph.get("text", "")).strip()
            if section_id and 10 <= len(text) <= 320:
                grouped.setdefault(section_id, []).append(
                    {"title": section_id, "text": text, "page": page["page"], "bbox": paragraph["bbox"]}
                )
    return [item for group in grouped.values() for item in group[:per_section]]


def _length_tier(text: str) -> str:
    return "10-50" if len(text) <= 50 else "50-150" if len(text) <= 150 else "150-300"


def build_review_queue(base: dict[str, Any], target: dict[str, Any], knowledge: KnowledgeBase) -> dict[str, Any]:
    candidates = rank_text_candidates(_section_paragraphs(base), _section_paragraphs(target), knowledge)
    selected: list[dict[str, Any]] = []
    seen_targets: set[tuple[str, str]] = set()
    tier_counts: dict[tuple[str, str], int] = defaultdict(int)
    for candidate in candidates:
        if candidate["source_text"] == candidate["target_text"]:
            continue
        tier = _length_tier(candidate["source_text"])
        dedupe_key = (candidate["section_id"], candidate["target_text"])
        quota_key = (candidate["section_id"], tier)
        if dedupe_key in seen_targets or tier_counts[quota_key] >= 3:
            continue
        selected.append(candidate)
        seen_targets.add(dedupe_key)
        tier_counts[quota_key] += 1
    items = [
        {
            "candidate_id": f"TEXT-CAND-{index:03d}",
            "status": "needs_agent_review",
            "type": "TEXT",
            "section_id": candidate["section_id"],
            "length_tier": _length_tier(candidate["source_text"]),
            "confidence": candidate["confidence"],
            "reason": candidate["reason"],
            "proposed_base_text": candidate["source_text"],
            "proposed_target_text": candidate["target_text"],
            "source_page": candidate["source_page"],
            "target_page": candidate["target_page"],
        }
        for index, candidate in enumerate(selected, start=1)
    ]
    return {
        "schema_version": 1,
        "base": {"file": base.get("file"), "sha256": base.get("sha256")},
        "target": {"file": target.get("file"), "sha256": target.get("sha256")},
        "knowledge_hash": knowledge.effective_config_hash,
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="由证据包构建 Agent 待复核队列")
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--knowledge", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = json.loads(args.base.read_text(encoding="utf-8"))
    target = json.loads(args.target.read_text(encoding="utf-8"))
    queue = build_review_queue(base, target, KnowledgeBase.load(args.knowledge))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
