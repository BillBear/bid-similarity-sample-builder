"""Small, self-contained PDF editing primitives for validated Manifests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import fitz


class PdfWriterError(ValueError):
    """Raised when a validated PDF operation cannot be written safely."""


def _font_candidates() -> Iterable[Path]:
    environment = os.environ.get("BID_SAMPLE_FONT_PATH")
    if environment:
        yield Path(environment)
    windows_directory = os.environ.get("WINDIR")
    if windows_directory:
        yield from (
            Path(windows_directory) / "Fonts" / "simhei.ttf",
            Path(windows_directory) / "Fonts" / "msyh.ttc",
        )
    yield from (
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    )


def find_cjk_font(explicit_path: Path | None = None) -> Path:
    """Find a user-selected or system CJK font suitable for PDF insertion."""
    candidates = [Path(explicit_path)] if explicit_path is not None else list(_font_candidates())
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    if explicit_path is not None:
        raise PdfWriterError(f"找不到指定的中文字体：{explicit_path}")
    raise PdfWriterError("未找到中文字体；请通过 --font 或 BID_SAMPLE_FONT_PATH 指定可用字体文件。")


def _expanded(rect: fitz.Rect, padding: float = 2) -> fitz.Rect:
    return fitz.Rect(rect.x0 - padding, rect.y0 - padding, rect.x1 + padding, rect.y1 + padding)


def _has_complete_text_span(page: fitz.Page, rect: fitz.Rect, value: str) -> bool:
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                span_rect = fitz.Rect(span["bbox"])
                if span_rect.intersects(rect) and span.get("text", "").strip() == value.strip():
                    return True
    return False


def _insert_fitted_text(page: fitz.Page, rect: fitz.Rect, value: str, font_path: Path | None) -> None:
    font_name = "helv"
    kwargs: dict[str, object] = {"fontname": font_name}
    if font_path is not None:
        font_name = "bid_sample_cjk"
        kwargs = {"fontname": font_name, "fontfile": str(font_path)}
    for font_size in range(max(6, int(rect.height * 0.8)), 3, -1):
        remaining = page.insert_textbox(rect, value, fontsize=font_size, color=(0, 0, 0), **kwargs)
        if remaining >= 0:
            return
    raise PdfWriterError("替换文本无法放入原始区域；请在 Manifest 中提供更合适的完整区域。")


def replace_text(
    page: fitz.Page,
    bbox: fitz.Rect | list[float],
    old_value: str,
    new_value: str,
    *,
    font_path: Path | None = None,
) -> None:
    """Replace one complete text span inside a validated editable region."""
    rect = fitz.Rect(bbox)
    if not _has_complete_text_span(page, rect, old_value):
        raise PdfWriterError("原值未以完整文本范围出现在目标区域，拒绝执行部分替换。")
    write_rect = _expanded(rect)
    page.add_redact_annot(write_rect, fill=(1, 1, 1))
    page.apply_redactions()
    _insert_fitted_text(page, write_rect, new_value, font_path)


def replace_image(page: fitz.Page, bbox: fitz.Rect | list[float], image_path: Path) -> None:
    """Cover one validated image slot and place its replacement image."""
    rect = fitz.Rect(bbox)
    image_path = Path(image_path)
    if not image_path.is_file():
        raise PdfWriterError(f"替换图片不存在：{image_path}")
    page.draw_rect(rect, color=None, fill=(1, 1, 1), overlay=True)
    page.insert_image(rect, filename=str(image_path), keep_proportion=False, overlay=True)


def add_annotation(page: fitz.Page, bbox: fitz.Rect | list[float], title: str, content: str) -> None:
    """Attach one visible review annotation near the altered region."""
    rect = fitz.Rect(bbox)
    annotation = page.add_text_annot(rect.tl, content)
    annotation.set_info(title=title, content=content)
    annotation.update()
