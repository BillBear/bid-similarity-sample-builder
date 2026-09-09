"""Rank structurally comparable text candidates without editing source PDFs."""

from __future__ import annotations

from typing import Any

from knowledge_base import KnowledgeBase


def rank_text_candidates(
    source_sections: list[dict[str, Any]],
    target_sections: list[dict[str, Any]],
    knowledge: KnowledgeBase,
    *,
    threshold: float = 0.90,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for source in source_sections:
        source_section = knowledge.section(str(source.get("title", ""))) or knowledge.classify_section(str(source.get("title", "")))
        if not source_section or not knowledge.is_text_allowed(source_section["id"]):
            continue
        for target in target_sections:
            target_section = knowledge.section(str(target.get("title", ""))) or knowledge.classify_section(str(target.get("title", "")))
            if not target_section or target_section["id"] != source_section["id"]:
                continue
            if not knowledge.is_text_allowed(target_section["id"]):
                continue
            score = 0.96
            candidates.append(
                {
                    "type": "TEXT",
                    "section_id": source_section["id"],
                    "source_page": source.get("page"),
                    "target_page": target.get("page"),
                    "source_text": source.get("text", ""),
                    "target_text": target.get("text", ""),
                    "confidence": score,
                    "decision": "auto" if score >= threshold else "review",
                    "reason": "同一可配置章节族，且双方均为投标人自拟内容。",
                }
            )
    return candidates
