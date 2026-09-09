import json
from pathlib import Path
import sys

import fitz
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from apply_manifest import ManifestExecutionError, apply_manifest
from knowledge_base import KnowledgeBase
from validate_manifest import validate_manifest


def _point(bbox: list[float]) -> dict:
    return {
        "id": "FIELD-01",
        "type": "FIELD",
        "pair_id": "PAIR-01",
        "base": {"file": "base.pdf", "page": 1, "bbox": bbox, "full_context": "Address: Old Value"},
        "target": {"file": "target.pdf", "page": 1, "bbox": bbox, "full_context": "Address: Old Value"},
        "semantic_reason": "投标函内的地址字段，以页面标签和完整值定位。",
        "confidence": 0.98,
        "auto_eligible": True,
        "operation": "replace-existing-field",
        "field_id": "contact-address",
        "anchor_label": "地址",
        "old_value": "Old Value",
        "new_value": "New Value",
        "value_span_complete": True,
    }


def _manifest(point: dict) -> dict:
    return {
        "schema_version": 1,
        "mode": "fast",
        "knowledge": {"effective_config_hash": "a" * 64},
        "documents": {"base": "base.pdf", "target": "target.pdf"},
        "points": [point],
    }


def test_validator_rejects_partial_field_value_and_overlapping_regions():
    knowledge = KnowledgeBase.load(ROOT / "knowledge" / "defaults")
    point = _point([10, 10, 80, 30])
    point["old_value"] = "Old"
    point["value_span_complete"] = False
    partial = validate_manifest(_manifest(point), knowledge)
    assert not partial.ok
    assert "完整" in " ".join(partial.errors)

    first = _point([10, 10, 80, 30])
    second = _point([40, 10, 100, 30])
    second["id"] = "FIELD-02"
    overlap = validate_manifest({**_manifest(first), "points": [first, second]}, knowledge)
    assert not overlap.ok
    assert "重叠" in " ".join(overlap.errors)


def test_executor_writes_valid_field_replacement(tmp_path: Path):
    target = tmp_path / "target.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 100), "Old Value", fontsize=12)
    document.save(target)
    document.close()
    document = fitz.open(target)
    bbox = list(document[0].search_for("Old Value")[0])
    document.close()
    point = _point(bbox)
    point["target"]["file"] = str(target)
    point["base"]["file"] = str(target)
    manifest = _manifest(point)
    manifest["documents"] = {"base": str(target), "target": str(target)}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "changed.pdf"

    receipt = apply_manifest(manifest_path, ROOT / "knowledge" / "defaults", output)

    changed = fitz.open(output)
    assert "New Value" in changed[0].get_text()
    assert receipt["points"][0]["status"] == "applied"
    assert output.with_suffix(".receipt.json").is_file()
    changed.close()


def test_executor_refuses_invalid_manifest_before_output(tmp_path: Path):
    manifest = tmp_path / "invalid.json"
    manifest.write_text(json.dumps({"schema_version": 1, "points": []}), encoding="utf-8")
    output = tmp_path / "changed.pdf"

    with pytest.raises(ManifestExecutionError):
        apply_manifest(manifest, ROOT / "knowledge" / "defaults", output)

    assert not output.exists()
