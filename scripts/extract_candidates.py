"""Read PDF structure into evidence packages without changing source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import fitz

from knowledge_base import KnowledgeBase


HEADING = re.compile(r"^\s*(?:第?[一二三四五六七八九十\d]+[章节]|[一二三四五六七八九十]+、|\d+(?:\.\d+){0,3}[、.．])")


def _bbox(value: Any) -> list[float]:
    return [round(float(item), 1) for item in value[:4]]


def _line_text(line: dict[str, Any]) -> str:
    return "".join(span.get("text", "") for span in line.get("spans", [])).strip()


def _is_heading(line: dict[str, Any], text: str) -> bool:
    largest = max((float(span.get("size", 0)) for span in line.get("spans", [])), default=0)
    return bool(text and len(text) <= 80 and (HEADING.match(text) or largest >= 15))


def extract_pdf(pdf: Path, knowledge: KnowledgeBase) -> dict[str, Any]:
    pdf = Path(pdf)
    document = fitz.open(pdf)
    pages: list[dict[str, Any]] = []
    active_section_id: str | None = None
    try:
        for page_number, page in enumerate(document, start=1):
            headings: list[dict[str, Any]] = []
            paragraphs: list[dict[str, Any]] = []
            fields: list[dict[str, Any]] = []
            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                text = "\n".join(_line_text(line) for line in block.get("lines", []) if _line_text(line)).strip()
                if 20 <= len(text) <= 600:
                    paragraphs.append({"text": text, "bbox": _bbox(block["bbox"])})
                for line in block.get("lines", []):
                    line_text = _line_text(line)
                    if _is_heading(line, line_text):
                        classified = knowledge.classify_section(line_text)
                        headings.append({"title": line_text, "bbox": _bbox(line["bbox"]), "section_id": classified["id"] if classified else None})
                    compact = re.sub(r"\s+", "", line_text)
                    for field in knowledge.data.get("fields", []):
                        label = next((item for item in field.get("labels", []) if re.sub(r"\s+", "", item) in compact), None)
                        if label:
                            fields.append({"field_id": field["id"], "anchor_label": label, "line_text": line_text, "line_bbox": _bbox(line["bbox"]), "requires_value_bbox_confirmation": True})
                            break
            heading_positions = sorted((item["bbox"][1], item["section_id"]) for item in headings if item["section_id"])
            for paragraph in sorted(paragraphs, key=lambda item: item["bbox"][1]):
                previous = [section_id for y0, section_id in heading_positions if y0 <= paragraph["bbox"][1]]
                if previous:
                    active_section_id = previous[-1]
                paragraph["section_id"] = active_section_id
            images = []
            for image in page.get_image_info(xrefs=True):
                xref = image.get("xref")
                if xref:
                    raw = document.extract_image(xref).get("image", b"")
                    images.append({"bbox": _bbox(image["bbox"]), "sha256": hashlib.sha256(raw).hexdigest(), "xref": xref})
            pages.append({"page": page_number, "headings": headings, "paragraphs": paragraphs, "fields": fields, "images": images})
    finally:
        document.close()
    return {"schema_version": 1, "file": str(pdf), "sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(), "page_count": len(pages), "pages": pages}


def main() -> int:
    parser = argparse.ArgumentParser(description="提取 PDF 的只读结构化候选证据包")
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--knowledge", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = extract_pdf(args.pdf, KnowledgeBase.load(args.knowledge))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
