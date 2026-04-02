"""
utils/page_index_map.py
───────────────────────
Domain-aware registry mapping page indices to section keys.
Every entry carries ``section_type`` to drive post-processing.

v2.1: indices spaced by 10 to prevent collisions when new sections
      are inserted between existing ones.
"""

from __future__ import annotations


PAGE_INDEX_MAP: dict[str, list[dict]] = {
    "technical": [
        {"page_index": 10, "section_key": "introduction_section",        "section_type": "text",    "schema_module": "introduction_schema"},
        {"page_index": 20, "section_key": "overall_description_section",  "section_type": "text",    "schema_module": "overall_description_schema"},
        {"page_index": 30, "section_key": "system_features_section",      "section_type": "text",    "schema_module": "system_features_schema"},
        {"page_index": 40, "section_key": "external_interfaces_section",  "section_type": "diagram", "schema_module": "external_interfaces_schema"},
        {"page_index": 50, "section_key": "nfr_section",                  "section_type": "text",    "schema_module": "nfr_schema"},
        {"page_index": 60, "section_key": "glossary_section",             "section_type": "text",    "schema_module": "glossary_schema"},
        {"page_index": 70, "section_key": "assumptions_section",          "section_type": "text",    "schema_module": "assumptions_schema"},
    ],
    # Add "aerospace", "automotive", "healthcare" etc. here — everything adapts automatically
}


def get_section_by_index(domain: str, page_index: int) -> dict | None:
    """Look up a section entry by its page_index within the given domain."""
    return next(
        (s for s in PAGE_INDEX_MAP.get(domain, []) if s["page_index"] == page_index),
        None,
    )


def get_section_by_key(domain: str, section_key: str) -> dict | None:
    """Look up a section entry by its section_key within the given domain."""
    return next(
        (s for s in PAGE_INDEX_MAP.get(domain, []) if s["section_key"] == section_key),
        None,
    )


def get_all_sections(domain: str) -> list[dict]:
    """Return all section entries for the given domain, ordered by page_index."""
    return sorted(
        PAGE_INDEX_MAP.get(domain, []),
        key=lambda s: s["page_index"],
    )
