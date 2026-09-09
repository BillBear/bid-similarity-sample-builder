"""Fail-closed validation for Agent-authored sample Manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from knowledge_base import KnowledgeBase


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]


def _valid_bbox(value: Any) -> bool:
    return isinstance(value, list) and len(value) == 4 and all(isinstance(item, (int, float)) for item in value) and value[2] > value[0] and value[3] > value[1]


def _rects_overlap(left: list[float], right: list[float]) -> bool:
    return min(left[2], right[2]) > max(left[0], right[0]) and min(left[3], right[3]) > max(left[1], right[1])


def _editable_rects(point: dict[str, Any]) -> list[list[float]]:
    if point.get("type") == "ROW":
        return [cell["bbox"] for cell in point.get("cells", []) if _valid_bbox(cell.get("bbox"))]
    bbox = point.get("target", {}).get("bbox")
    return [bbox] if _valid_bbox(bbox) else []


def _validate_location(prefix: str, point: dict[str, Any], errors: list[str]) -> None:
    for side in ("base", "target"):
        location = point.get(side, {})
        if not location.get("file") or not isinstance(location.get("page"), int) or location["page"] < 1:
            errors.append(f"{prefix} 的 {side} 定位缺少文件或有效页码。")
        if not _valid_bbox(location.get("bbox")):
            errors.append(f"{prefix} 的 {side} 定位 bbox 必须是四个有效数字。")
        if not location.get("full_context"):
            errors.append(f"{prefix} 的 {side} 缺少完整上下文证据。")


def _validate_type(prefix: str, point: dict[str, Any], knowledge: KnowledgeBase, errors: list[str]) -> None:
    kind = point["type"]
    if kind == "FIELD":
        if point.get("operation") != "replace-existing-field":
            errors.append(f"{prefix} 的字段改造必须使用 replace-existing-field。")
        required = ("field_id", "anchor_label", "old_value", "new_value")
        if any(not point.get(key) for key in required):
            errors.append(f"{prefix} 的字段改造缺少字段锚点或新旧完整值。")
        elif not knowledge.field_has_label(point["field_id"], point["anchor_label"]):
            errors.append(f"{prefix} 的字段 id 与页面锚点标签不匹配。")
        if not point.get("value_span_complete"):
            errors.append(f"{prefix} 的字段改造未证明旧值范围完整。")
        if point.get("old_value") and point["old_value"] not in str(point.get("target", {}).get("full_context", "")):
            errors.append(f"{prefix} 的字段旧值未出现在目标完整上下文中。")
    elif kind == "TEXT":
        if point.get("operation") != "replace-existing-text":
            errors.append(f"{prefix} 的文本改造必须使用 replace-existing-text。")
        section_id = point.get("section_id")
        if not section_id or point.get("source_section_id") != section_id:
            errors.append(f"{prefix} 的文本改造必须标明双方同一章节族。")
        elif not knowledge.is_text_allowed(section_id):
            errors.append(f"{prefix} 的章节不适合文本重复改造。")
        if not point.get("old_text") or not point.get("new_text"):
            errors.append(f"{prefix} 的文本改造缺少替换前后文本。")
    elif kind == "ROW":
        if point.get("operation") != "replace-table-cells":
            errors.append(f"{prefix} 的表格改造必须使用 replace-table-cells。")
        for key in ("table_id", "header_mapping", "row_anchor", "editable_columns", "cells"):
            if not point.get(key):
                errors.append(f"{prefix} 的表格改造缺少 {key}。")
        for cell in point.get("cells", []):
            if not _valid_bbox(cell.get("bbox")) or not cell.get("old_value") or not cell.get("new_value"):
                errors.append(f"{prefix} 的表格单元格必须有完整 bbox 和新旧值。")
    elif kind == "IMG":
        if point.get("operation") != "replace-existing-image":
            errors.append(f"{prefix} 的图片改造必须使用 replace-existing-image。")
        for key in ("source_image_hash", "target_slot_description", "replacement_image"):
            if not point.get(key):
                errors.append(f"{prefix} 的图片改造缺少 {key}。")


def validate_manifest(manifest: dict[str, Any], knowledge: KnowledgeBase) -> ValidationResult:
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("Manifest 必须使用 schema_version: 1。")
    if manifest.get("mode") not in {"fast", "balanced", "deep"}:
        errors.append("Manifest 的 mode 必须是 fast、balanced 或 deep。")
    if not manifest.get("knowledge", {}).get("effective_config_hash"):
        errors.append("Manifest 缺少生效知识库版本哈希。")
    documents = manifest.get("documents", {})
    if not documents.get("base") or not documents.get("target"):
        errors.append("Manifest 必须声明基准与受控文件。")
    points = manifest.get("points")
    if not isinstance(points, list) or not points:
        return ValidationResult(False, [*errors, "Manifest 至少必须有一个改造点。"])

    identifiers: set[str] = set()
    target_rects: list[tuple[str, str, int, list[float]]] = []
    for index, point in enumerate(points, start=1):
        prefix = f"第 {index} 个改造点"
        identifier = point.get("id")
        if not identifier or identifier in identifiers:
            errors.append(f"{prefix} 的 id 缺失或重复。")
        identifiers.add(identifier)
        if point.get("type") not in {"FIELD", "TEXT", "ROW", "IMG"}:
            errors.append(f"{prefix} 的 type 非法。")
            continue
        if len(str(point.get("semantic_reason", ""))) < 12:
            errors.append(f"{prefix} 必须写明可复核的语义依据。")
        if manifest.get("mode") == "fast" and (point.get("confidence", 0) < 0.90 or not point.get("auto_eligible")):
            errors.append(f"{prefix} 在 Fast 模式下必须是高置信可自动执行候选。")
        _validate_location(prefix, point, errors)
        _validate_type(prefix, point, knowledge, errors)
        target = point.get("target", {})
        for rect in _editable_rects(point):
            target_rects.append((str(identifier), str(target.get("file")), target.get("page"), rect))

    for index, left in enumerate(target_rects):
        for right in target_rects[index + 1:]:
            if left[1] == right[1] and left[2] == right[2] and _rects_overlap(left[3], right[3]):
                errors.append(f"目标页 {left[2]} 的改造区域重叠：{left[0]} 与 {right[0]}。")
    return ValidationResult(not errors, errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 Manifest 的结构、证据和改造区域")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--knowledge", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = validate_manifest(manifest, KnowledgeBase.load(args.knowledge))
    if result.ok:
        print("Manifest 校验通过。")
        return 0
    for error in result.errors:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
