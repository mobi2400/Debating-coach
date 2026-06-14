from __future__ import annotations

from urllib.parse import urlparse

from core.topic_utils import TOPIC_KEYWORDS


DOC_SOURCE_CLASS = {
    "topic_pdf": "domain_reference",
    "news": "article",
    "wikipedia": "encyclopedic_background",
    "your_speech": "personal_style",
    "debate_format": "debate_style",
    "personal_notes": "personal_style",
    "debate_theory": "debate_theory",
    "rhetoric": "debate_theory",
    "argument_theory": "debate_theory",
    "english_vocab": "vocabulary",
    "youtube_debate": "debate_transcript",
    "youtube_ted": "speech_transcript",
}

DOC_TIME_SCOPE = {
    "news": "recent",
    "wikipedia": "durable",
    "topic_pdf": "durable",
    "debate_theory": "durable",
    "rhetoric": "durable",
    "argument_theory": "durable",
    "debate_format": "durable",
    "your_speech": "durable",
    "personal_notes": "durable",
    "english_vocab": "durable",
    "youtube_debate": "durable",
    "youtube_ted": "durable",
}

DOC_DEBATE_UTILITY = {
    "topic_pdf": ["definition", "mechanism", "example"],
    "news": ["example", "case_evidence", "mechanism"],
    "wikipedia": ["definition", "history", "preknowledge"],
    "your_speech": ["style", "framing", "weighing"],
    "debate_format": ["style", "framing", "rebuttal"],
    "personal_notes": ["style", "framing", "mechanism"],
    "debate_theory": ["mechanism", "clash", "rebuttal"],
    "rhetoric": ["style", "framing", "weighing"],
    "argument_theory": ["mechanism", "clash", "rebuttal"],
    "english_vocab": ["vocabulary"],
    "youtube_debate": ["example", "rebuttal", "framing"],
    "youtube_ted": ["example", "style", "framing"],
}


def infer_topic_family(text: str) -> str | None:
    haystack = str(text or "").lower()
    if not haystack:
        return None

    for family, keywords in TOPIC_KEYWORDS.items():
        family_terms = [family] + list(keywords)
        if any(term.lower() in haystack for term in family_terms):
            return family
    return None


def _source_quality(doc_type: str, source_ref: str) -> str:
    doc_type = str(doc_type or "").strip().lower()
    ref = str(source_ref or "").lower()

    if doc_type in {"debate_theory", "argument_theory", "rhetoric", "topic_pdf"}:
        return "high"
    if doc_type in {"wikipedia", "debate_format", "your_speech", "personal_notes", "youtube_debate"}:
        return "medium"
    if doc_type == "news":
        if any(domain in ref for domain in ("aeon.co", "theatlantic.com", "epw.in")):
            return "high"
        return "medium"
    return "medium"


def build_metadata(doc_type: str, source_ref: str, extra: dict | None = None) -> dict:
    extra = dict(extra or {})
    source_ref = str(source_ref or "")
    doc_type = str(doc_type or "").strip()
    topic_seed = " ".join(
        str(value)
        for value in [
            extra.get("topic"),
            extra.get("title"),
            extra.get("source_path"),
            extra.get("url"),
            extra.get("channel_name"),
        ]
        if value
    )

    metadata = {
        "doc_type": doc_type,
        "source_class": DOC_SOURCE_CLASS.get(doc_type, "reference"),
        "time_scope": DOC_TIME_SCOPE.get(doc_type, "durable"),
        "debate_utility": DOC_DEBATE_UTILITY.get(doc_type, ["reference"]),
        "source_quality": _source_quality(doc_type, source_ref),
        "topic_family": infer_topic_family(topic_seed),
    }

    if source_ref.startswith("http"):
        parsed = urlparse(source_ref)
        metadata["source_domain"] = parsed.netloc.lower()

    metadata.update(extra)
    return metadata
