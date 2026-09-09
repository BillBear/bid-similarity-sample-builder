from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from knowledge_base import KnowledgeBase
from rank_candidates import rank_text_candidates


def test_same_bidder_authored_section_is_ranked_for_review():
    knowledge = KnowledgeBase.load(ROOT / "knowledge" / "defaults")
    source = [{"title": "售后服务方案", "text": "提供现场响应、巡检和培训服务。", "page": 10}]
    target = [{"title": "售后服务承诺", "text": "提供验收后的持续技术支持。", "page": 12}]

    candidates = rank_text_candidates(source, target, knowledge)

    assert len(candidates) == 1
    assert candidates[0]["section_id"] == "after-sales-service"
    assert candidates[0]["decision"] == "auto"


def test_evidence_section_is_excluded_from_text_candidates():
    knowledge = KnowledgeBase.load(ROOT / "knowledge" / "defaults")
    source = [{"title": "营业执照", "text": "示例证明材料文本。", "page": 3}]
    target = [{"title": "营业执照", "text": "另一份示例证明材料文本。", "page": 4}]

    assert rank_text_candidates(source, target, knowledge) == []
