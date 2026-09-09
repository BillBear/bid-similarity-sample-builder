from pathlib import Path
import sys

import fitz


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_candidates import extract_pdf
from knowledge_base import KnowledgeBase


def test_extractor_classifies_paragraph_under_known_heading(tmp_path: Path):
    override = tmp_path / "sections.yml"
    override.write_text(
        "schema_version: 1\nsections:\n"
        "  - id: after-sales-service\n"
        "    aliases: [After Sales Plan]\n",
        encoding="utf-8",
    )
    pdf = tmp_path / "source.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "8. After Sales Plan", fontsize=16)
    page.insert_text((72, 110), "Provide scheduled inspection, on-site response, and user training services.", fontsize=12)
    document.save(pdf)
    document.close()

    result = extract_pdf(pdf, KnowledgeBase.load(ROOT / "knowledge" / "defaults", override_files=[override]))

    assert result["page_count"] == 1
    assert result["pages"][0]["headings"][0]["section_id"] == "after-sales-service"
    assert result["pages"][0]["paragraphs"][0]["section_id"] == "after-sales-service"
