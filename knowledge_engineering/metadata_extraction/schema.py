"""Pydantic models cho metadata contract — Task 1.8, Sprint 1.

Validate knowledge_object + semantic tag + review ABSA theo ontology/metadata_schema.yaml.
Ràng buộc QUAN TRỌNG: mọi concept_id trong tag/aspect/semantic phải TỒN TẠI trong ontology
(ontology/core/*.yaml) — bắt sớm tag trỏ concept không có thật.

Chạy self-test: .venv/Scripts/python.exe -X utf8 -m knowledge_engineering.metadata_extraction.schema
"""

from __future__ import annotations

import glob
from enum import Enum
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator

# --- nạp tập concept_id hợp lệ từ ontology (1 lần) ---------------------------
CORE_GLOB = "ontology/core/*.yaml"


def load_concept_ids(core_glob: str = CORE_GLOB) -> set[str]:
    ids: set[str] = set()
    for f in sorted(glob.glob(core_glob)):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        ids.update((d.get("concepts") or {}).keys())
    return ids


CONCEPT_IDS = load_concept_ids()


class Sentiment(str, Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"
    mixed = "mixed"


class Tag(BaseModel):
    """Semantic tag PRESENCE (HARD) KE gắn cho object. concept TRUNG TÍNH + confidence + provenance.

    QUAN TRỌNG (semantics): `confidence` = ĐỘ CHẮC TAG ĐÚNG (presence từ structured/rule), KHÔNG
    phải điểm trải nghiệm review. Tín hiệu review (yên tĩnh tới mức nào) thuộc `semantic_profile`
    với trường `score` — KHÔNG đổ vào đây. Vì vậy `review_profile` KHÔNG phải source hợp lệ của tag.
    """

    concept: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[str] = Field(min_length=1)

    @field_validator("concept")
    @classmethod
    def concept_must_exist(cls, v: str) -> str:
        if v not in CONCEPT_IDS:
            raise ValueError(f"concept '{v}' không có trong ontology/core/*.yaml")
        return v

    @field_validator("sources")
    @classmethod
    def sources_are_presence(cls, v: list[str]) -> list[str]:
        # tag = presence; tín hiệu review đi vào semantic_profile, KHÔNG vào tags.
        if "review_profile" in v:
            raise ValueError(
                "source 'review_profile' không hợp lệ cho tag (presence). "
                "Điểm review thuộc semantic_profile.score, không phải tags.confidence."
            )
        return v


class AspectSentiment(BaseModel):
    """1 cặp khía cạnh–cảm xúc từ ABSA (Sprint 2)."""

    aspect: str
    sentiment: Sentiment
    confidence: float = Field(ge=0.0, le=1.0)
    span: Optional[str] = None

    @field_validator("aspect")
    @classmethod
    def aspect_must_be_aspect_concept(cls, v: str) -> str:
        if v not in CONCEPT_IDS:
            raise ValueError(f"aspect '{v}' không có trong ontology")
        if not v.startswith("ASPECT_"):
            raise ValueError(f"aspect '{v}' phải là concept facet=aspect (ASPECT_*)")
        return v


class ReviewExtra(BaseModel):
    overall_sentiment: Sentiment
    aspects: list[AspectSentiment] = Field(default_factory=list)


class ProfileEntry(BaseModel):
    """1 mục semantic_profile — điểm SOFT/trải nghiệm review (Bước 5). KHÔNG lọc cứng.

    `score` = mức MẠNH/YẾU của trải nghiệm (Wilson), KHÁC `confidence` của Tag (độ chắc tag đúng).
    """

    score: float = Field(ge=0.0, le=1.0)
    evidence_count: int = Field(ge=0)
    source: str


class NegativeStyleEntry(BaseModel):
    """Negative evidence riêng cho STYLE_* (vd STYLE_QUIET bị chê ồn).

    Không tạo concept đối nghịch kiểu STYLE_NOT_QUIET; vẫn giữ concept trung tính và sentiment riêng.
    """

    negative_score: float = Field(ge=0.0, le=1.0)
    neg: int = Field(ge=0)
    pos: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    top_spans: list[str] = Field(default_factory=list)
    source: str


class KnowledgeObject(BaseModel):
    """Đơn vị tài liệu cuối (rút gọn cho contract Sprint 1; mở rộng metadata ở Sprint 3)."""

    id: str
    type: str
    title: str
    source: str
    content: Optional[str] = None
    tags: list[Tag] = Field(default_factory=list)
    semantic_metadata: dict[str, Any] = Field(default_factory=dict)
    semantic_profile: dict[str, ProfileEntry] = Field(default_factory=dict)
    negative_style_profile: dict[str, NegativeStyleEntry] = Field(default_factory=dict)
    review_extra: Optional[ReviewExtra] = None

    @field_validator("semantic_metadata")
    @classmethod
    def semantic_metadata_concepts_exist(cls, v: dict[str, Any]) -> dict[str, Any]:
        def check_concept(value: Any, path: str) -> None:
            if value is None:
                return
            if isinstance(value, str):
                if value not in CONCEPT_IDS:
                    raise ValueError(f"semantic_metadata.{path} concept '{value}' khÃ´ng cÃ³ trong ontology")
                return
            if isinstance(value, list):
                for i, item in enumerate(value):
                    check_concept(item, f"{path}[{i}]")

        for facet, value in v.items():
            check_concept(value, facet)
        loc = v.get("location")
        if loc is not None and (not isinstance(loc, str) or not loc.startswith("LOC_")):
            raise ValueError("semantic_metadata.location pháº£i lÃ  LOC_* concept_id")
        return v

    @field_validator("semantic_profile")
    @classmethod
    def profile_concepts_exist(cls, v: dict[str, ProfileEntry]) -> dict[str, ProfileEntry]:
        for cid in v:
            if cid not in CONCEPT_IDS:
                raise ValueError(f"semantic_profile concept '{cid}' không có trong ontology")
        return v

    @field_validator("negative_style_profile")
    @classmethod
    def negative_style_concepts_exist(cls, v: dict[str, NegativeStyleEntry]) -> dict[str, NegativeStyleEntry]:
        for cid in v:
            if cid not in CONCEPT_IDS:
                raise ValueError(f"negative_style_profile concept '{cid}' không có trong ontology")
            if not cid.startswith("STYLE_"):
                raise ValueError(f"negative_style_profile concept '{cid}' phải là STYLE_*")
        return v


# --- self-test với object mẫu dựng từ data thật ------------------------------
def _sample() -> dict:
    return {
        "id": "acc_805030",
        "type": "resort",
        "title": "Vinpearl Resort & Spa Nha Trang Bay",
        "source": "agoda",
        "content": "Resort 5 sao tại Hòn Tre, Nha Trang...",
        "tags": [
            {"concept": "AMEN_BEACHFRONT", "confidence": 0.98, "sources": ["source_tag", "rule"]},
            {"concept": "OBJ_RESORT", "confidence": 1.0, "sources": ["source_tag"]},
        ],
        "semantic_metadata": {
            "object_type": "OBJ_RESORT",
            "location": "LOC_HON_TRE",
            "amenity": ["AMEN_BEACHFRONT"],
            "setting": ["SETTING_ISLAND"],
            "purpose": ["PURPOSE_ROMANTIC"],
            "price_tier": "PRICE_LUXURY",
            "style": [],
        },
        # điểm review (yên tĩnh tới mức nào) -> semantic_profile.score, KHÔNG phải tags.confidence
        "semantic_profile": {
            "ASPECT_CLEANLINESS": {"score": 0.90, "evidence_count": 8123, "source": "agoda_grades"},
            "STYLE_QUIET": {"score": 0.40, "evidence_count": 12, "source": "absa"},
        },
        "negative_style_profile": {
            "STYLE_QUIET": {
                "negative_score": 0.55,
                "neg": 8,
                "pos": 2,
                "evidence_count": 10,
                "top_spans": ["hơi ồn"],
                "source": "absa",
            }
        },
        "review_extra": {
            "overall_sentiment": "mixed",
            "aspects": [
                {"aspect": "ASPECT_CLEANLINESS", "sentiment": "positive", "confidence": 0.9, "span": "Phòng sạch"},
                {"aspect": "ASPECT_LOCATION", "sentiment": "negative", "confidence": 0.7, "span": "hơi ồn"},
            ],
        },
    }


if __name__ == "__main__":
    print(f"Loaded {len(CONCEPT_IDS)} concept_id từ ontology.")
    obj = KnowledgeObject.model_validate(_sample())
    print("[OK] object mẫu HỢP LỆ:", obj.id, "-", len(obj.tags), "tags")

    # negative test: concept không tồn tại -> phải raise
    bad = _sample()
    bad["tags"][0]["concept"] = "AMEN_NOT_A_REAL_CONCEPT"
    try:
        KnowledgeObject.model_validate(bad)
        print("[FAIL] đáng lẽ phải báo lỗi concept không tồn tại")
    except Exception as e:
        print("[OK] bắt đúng concept sai:", str(e).splitlines()[-1][:70])

    # negative test: aspect không phải ASPECT_*
    bad2 = _sample()
    bad2["review_extra"]["aspects"][0]["aspect"] = "AMEN_POOL"
    try:
        KnowledgeObject.model_validate(bad2)
        print("[FAIL] đáng lẽ phải báo lỗi aspect sai facet")
    except Exception as e:
        print("[OK] bắt đúng aspect sai facet:", str(e).splitlines()[-1][:70])

    # negative test: review_profile làm source của tag (trộn score vào confidence) -> phải raise
    bad3 = _sample()
    bad3["tags"].append({"concept": "STYLE_QUIET", "confidence": 0.40, "sources": ["review_profile"]})
    try:
        KnowledgeObject.model_validate(bad3)
        print("[FAIL] đáng lẽ phải từ chối source review_profile trong tag")
    except Exception as e:
        print("[OK] bắt đúng review_profile trong tag:", str(e).splitlines()[-1][:70])
