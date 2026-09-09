"""Apply a validated Manifest using only package-local PDF writer functions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import fitz

from knowledge_base import KnowledgeBase
from pdf_writer import PdfWriterError, add_annotation, find_cjk_font, replace_image, replace_text
from validate_manifest import validate_manifest


class ManifestExecutionError(RuntimeError):
    """Raised when a Manifest cannot be validated or applied safely."""


def _requires_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value))


def _annotation_text(point: dict[str, Any]) -> str:
    return f"{point['type']}：{point.get('semantic_reason', '')}"


def apply_manifest(
    manifest_path: Path,
    knowledge_dir: Path,
    output_path: Path,
    *,
    font_path: Path | None = None,
    annotate: bool = False,
) -> dict[str, Any]:
    manifest_path, knowledge_dir, output_path = map(Path, (manifest_path, knowledge_dir, output_path))
    if output_path.exists():
        raise ManifestExecutionError(f"输出文件已存在：{output_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestExecutionError(f"无法读取 Manifest：{exc}") from exc
    knowledge = KnowledgeBase.load(knowledge_dir)
    validation = validate_manifest(manifest, knowledge)
    if not validation.ok:
        raise ManifestExecutionError("Manifest 校验失败：" + "；".join(validation.errors))
    target_path = Path(manifest["documents"]["target"])
    if not target_path.is_file():
        raise ManifestExecutionError(f"受控文件不存在：{target_path}")
    needs_font = any(
        _requires_cjk(str(point.get("new_value", point.get("new_text", ""))))
        for point in manifest["points"]
        if point["type"] in {"FIELD", "TEXT", "ROW"}
    )
    selected_font = find_cjk_font(font_path) if needs_font else None
    document = fitz.open(target_path)
    receipt_points: list[dict[str, Any]] = []
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        for point in manifest["points"]:
            page = document[point["target"]["page"] - 1]
            bbox = point["target"]["bbox"]
            if point["type"] == "FIELD":
                replace_text(page, bbox, point["old_value"], point["new_value"], font_path=selected_font)
            elif point["type"] == "TEXT":
                replace_text(page, bbox, point["old_text"], point["new_text"], font_path=selected_font)
            elif point["type"] == "ROW":
                for cell in point["cells"]:
                    replace_text(page, cell["bbox"], cell["old_value"], cell["new_value"], font_path=selected_font)
            else:
                replace_image(page, bbox, Path(point["replacement_image"]))
            if annotate:
                add_annotation(page, bbox, point["id"], _annotation_text(point))
            receipt_points.append({"id": point["id"], "type": point["type"], "status": "applied", "page": point["target"]["page"], "bbox": bbox})
        output_path.parent.mkdir(parents=True, exist_ok=True)
        document.save(temporary)
        temporary.replace(output_path)
    except (PdfWriterError, IndexError, OSError) as exc:
        if temporary.exists():
            temporary.unlink()
        raise ManifestExecutionError(f"PDF 写入失败：{exc}") from exc
    finally:
        document.close()
    receipt_path = output_path.with_suffix(".receipt.json")
    receipt = {
        "schema_version": 1,
        "manifest": str(manifest_path),
        "output": str(output_path),
        "receipt": str(receipt_path),
        "points": receipt_points,
    }
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="按经校验的 Manifest 构造 PDF 受控样本")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--knowledge", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--annotate", action="store_true")
    args = parser.parse_args()
    receipt = apply_manifest(args.manifest, args.knowledge, args.out, font_path=args.font, annotate=args.annotate)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
