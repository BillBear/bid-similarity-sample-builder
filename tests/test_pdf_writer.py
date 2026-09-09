from pathlib import Path
import sys

import fitz
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pdf_writer import PdfWriterError, add_annotation, find_cjk_font, replace_image, replace_text


def _text_pdf(path: Path) -> tuple[Path, fitz.Rect]:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 100), "Old Value", fontsize=12)
    document.save(path)
    document.close()
    document = fitz.open(path)
    bbox = document[0].search_for("Old Value")[0]
    document.close()
    return path, bbox


def test_replace_text_requires_full_old_value_and_writes_new_value(tmp_path: Path):
    path, bbox = _text_pdf(tmp_path / "source.pdf")
    document = fitz.open(path)

    replace_text(document[0], bbox, "Old Value", "New Value")
    document.save(tmp_path / "changed.pdf")
    document.close()

    changed = fitz.open(tmp_path / "changed.pdf")
    assert "New Value" in changed[0].get_text()
    changed.close()


def test_replace_text_rejects_partial_old_value(tmp_path: Path):
    path, bbox = _text_pdf(tmp_path / "source.pdf")
    document = fitz.open(path)

    with pytest.raises(PdfWriterError, match="完整"):
        replace_text(document[0], bbox, "Old", "New Value")

    document.close()


def test_writer_adds_annotation_and_replaces_image_slot(tmp_path: Path):
    image = fitz.Pixmap(fitz.csRGB, 2, 2, bytes([0, 0, 255] * 4), False)
    image_path = tmp_path / "replacement.png"
    image.save(image_path)
    document = fitz.open()
    page = document.new_page()
    slot = fitz.Rect(72, 72, 144, 144)

    replace_image(page, slot, image_path)
    add_annotation(page, slot, "IMG-01", "图片槽位替换")
    document.save(tmp_path / "annotated.pdf")
    document.close()

    changed = fitz.open(tmp_path / "annotated.pdf")
    assert changed[0].get_images()
    assert changed[0].first_annot is not None
    changed.close()


def test_missing_explicit_font_has_clear_error(tmp_path: Path):
    with pytest.raises(PdfWriterError, match="中文字体"):
        find_cjk_font(tmp_path / "missing.ttf")
