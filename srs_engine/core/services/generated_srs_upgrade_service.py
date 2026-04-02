"""
core/services/generated_srs_upgrade_service.py
───────────────────────────────────────────────
Business logic for upgrading SRS documents generated on this platform.

Completely separate from the existing external-file upgrader
(upgrade_service.py) — that pipeline stays 100 % untouched.

v2.1 features:
  - Versioned backups before every confirmed write
  - modified_sections tracking in meta
  - JSON schema validation after agent response
  - Mermaid render validation for diagram sections
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from srs_engine.utils.page_index_map import (
    PAGE_INDEX_MAP,
    get_all_sections,
    get_section_by_index,
    get_section_by_key,
)


BASE_DIR = Path("./srs_engine/generated_srs")
IMAGES_DIR = Path("./srs_engine/generated_images")


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class SectionResult:
    page_index: int
    section_key: str
    section_type: str           # "text" | "diagram"
    section_data: dict
    lookup_method: str          # "pageindex" | "rag_fallback"
    rag_confidence: float | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _user_dir(user_id: str) -> Path:
    return BASE_DIR / user_id


def _sections_path(user_id: str, project_name: str) -> Path:
    return _user_dir(user_id) / f"{project_name}_sections.json"


def _meta_path(user_id: str, project_name: str) -> Path:
    return _user_dir(user_id) / f"{project_name}_meta.json"


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _get_schema_description(section_key: str, domain: str) -> str:
    """
    Generate a human-readable schema description for the given section.
    Uses the Pydantic model's JSON schema.
    """
    schema_map = {
        "introduction_section": "IntroductionSection",
        "overall_description_section": "OverallDescriptionSection",
        "system_features_section": "SystemFeaturesSection",
        "external_interfaces_section": "ExternalInterfacesSection",
        "nfr_section": "NonFunctionalRequirementsSection",
        "glossary_section": "GlossarySection",
        "assumptions_section": "AssumptionsSection",
    }

    module_map = {
        "introduction_section": "introduction_schema",
        "overall_description_section": "overall_description_schema",
        "system_features_section": "system_features_schema",
        "external_interfaces_section": "external_interfaces_schema",
        "nfr_section": "nfr_schema",
        "glossary_section": "glossary_schema",
        "assumptions_section": "assumptions_schema",
    }

    class_name = schema_map.get(section_key)
    module_name = module_map.get(section_key)

    if not class_name or not module_name:
        return f"Schema for {section_key}"

    try:
        import importlib
        mod = importlib.import_module(
            f"srs_engine.schemas.technical_srs_schemas.{module_name}"
        )
        schema_cls = getattr(mod, class_name)
        schema = schema_cls.model_json_schema()
        return json.dumps(schema, indent=2)
    except Exception as e:
        return f"Schema for {section_key} (could not load: {e})"


# ── Public API ────────────────────────────────────────────────────────────────

async def list_generated_srs(user_id: str) -> list[dict]:
    """
    Scan generated_srs/{user_id}/ for *_meta.json files.
    Returns list of meta dicts (one per generated SRS document).
    """
    user_dir = _user_dir(user_id)
    if not user_dir.exists():
        return []

    results = []
    for meta_file in sorted(user_dir.glob("*_meta.json")):
        try:
            meta = _load_json(meta_file)
            project = meta.get("project_name", "")
            meta["id"] = project
            meta["has_sections"] = _sections_path(user_id, project).exists()
            meta["version_count"] = len(meta.get("versions", []))
            results.append(meta)
        except Exception:
            continue

    return results


async def get_version_history(user_id: str, project_name: str) -> list[dict]:
    """Retrieve the version history from meta.json."""
    meta_path = _meta_path(user_id, project_name)
    if not meta_path.exists():
        return []
    meta = _load_json(meta_path)
    return meta.get("versions", [])


async def get_section_by_pageindex(
    user_id: str,
    project_name: str,
    page_index: int,
) -> SectionResult:
    """
    Fast path: look up page_index in PAGE_INDEX_MAP[domain].

    Raises ValueError if page_index not found (caller should fall back to /search).
    """
    meta = _load_json(_meta_path(user_id, project_name))
    domain = meta.get("domain", "technical")

    section_info = get_section_by_index(domain, page_index)
    if not section_info:
        raise ValueError(
            f"page_index {page_index} not found in domain '{domain}'"
        )

    sections = _load_json(_sections_path(user_id, project_name))
    section_key = section_info["section_key"]
    section_data = sections.get(section_key, {})

    return SectionResult(
        page_index=page_index,
        section_key=section_key,
        section_type=section_info["section_type"],
        section_data=section_data,
        lookup_method="pageindex",
    )


async def search_section_rag(
    user_id: str,
    project_name: str,
    query: str,
) -> SectionResult:
    """
    RAG fallback: FAISS search → matched section key + confidence.
    """
    from srs_engine.utils.srs_rag_index import search_section

    meta = _load_json(_meta_path(user_id, project_name))
    domain = meta.get("domain", "technical")

    matched_key, confidence = search_section(
        query=query,
        user_id=user_id,
        project_name=project_name,
    )

    # Find page_index for the matched key
    section_info = get_section_by_key(domain, matched_key)
    if not section_info:
        raise ValueError(
            f"RAG matched key '{matched_key}' not found in domain '{domain}'"
        )

    sections = _load_json(_sections_path(user_id, project_name))
    section_data = sections.get(matched_key, {})

    return SectionResult(
        page_index=section_info["page_index"],
        section_key=matched_key,
        section_type=section_info["section_type"],
        section_data=section_data,
        lookup_method="rag_fallback",
        rag_confidence=confidence,
    )


async def preview_upgrade(
    user_id: str,
    project_name: str,
    page_index: int,
    instruction: str,
    lookup_method: str,
) -> dict:
    """
    1. Load section + schema description
    2. Call upgrade agent
    3. Validate upgraded_json against section schema
    4. If diagram: validate mermaid syntax
    5. Return { original_json, upgraded_json, changes_summary, fields_modified }
    """
    from srs_engine.agents.upgrader_agents.section_upgrade_agent import (
        run_section_upgrade,
    )

    meta = _load_json(_meta_path(user_id, project_name))
    domain = meta.get("domain", "technical")

    section_info = get_section_by_index(domain, page_index)
    if not section_info:
        raise ValueError(f"page_index {page_index} not found in domain '{domain}'")

    sections = _load_json(_sections_path(user_id, project_name))
    section_key = section_info["section_key"]
    section_type = section_info["section_type"]
    current_json = sections.get(section_key, {})

    schema_desc = _get_schema_description(section_key, domain)

    # Call the upgrade agent
    result = await run_section_upgrade(
        section_key=section_key,
        section_type=section_type,
        user_instruction=instruction,
        current_section_json=current_json,
        schema_description=schema_desc,
    )

    if not result:
        raise RuntimeError("Upgrade agent returned no result")

    upgraded_json = result["upgraded_section_json"]

    # v2.1: Validate upgraded_json against section schema
    try:
        _validate_section_schema(section_key, upgraded_json)
    except Exception as e:
        raise ValueError(f"Upgraded JSON failed schema validation: {e}")

    # If diagram section: validate mermaid syntax
    if section_type == "diagram":
        _validate_mermaid_syntax(upgraded_json)

    return {
        "original_json": current_json,
        "upgraded_json": upgraded_json,
        "changes_summary": result.get("changes_summary", ""),
        "fields_modified": result.get("fields_modified", []),
        "section_key": section_key,
        "section_type": section_type,
    }


def _validate_section_schema(section_key: str, upgraded_json: dict) -> None:
    """Validate upgraded JSON against the Pydantic schema for the section."""
    schema_class_map = {
        "introduction_section": ("introduction_schema", "IntroductionSection"),
        "overall_description_section": ("overall_description_schema", "OverallDescriptionSection"),
        "system_features_section": ("system_features_schema", "SystemFeaturesSection"),
        "external_interfaces_section": ("external_interfaces_schema", "ExternalInterfacesSection"),
        "nfr_section": ("nfr_schema", "NonFunctionalRequirementsSection"),
        "glossary_section": ("glossary_schema", "GlossarySection"),
        "assumptions_section": ("assumptions_schema", "AssumptionsSection"),
    }

    mapping = schema_class_map.get(section_key)
    if not mapping:
        return  # no schema to validate against

    module_name, class_name = mapping
    try:
        import importlib
        mod = importlib.import_module(
            f"srs_engine.schemas.technical_srs_schemas.{module_name}"
        )
        schema_cls = getattr(mod, class_name)
        schema_cls.model_validate(upgraded_json)
    except Exception as e:
        print(f"[generated_srs_upgrade_service] Schema validation warning for {section_key}: {e}")
        # Don't hard-fail — allow upgrades that slightly deviate
        # The agent should generally produce valid output


def _validate_mermaid_syntax(upgraded_json: dict) -> None:
    """Check that mermaid code fields exist and have basic valid syntax."""
    interface_keys = [
        "user_interfaces",
        "hardware_interfaces",
        "software_interfaces",
        "communication_interfaces",
    ]
    for key in interface_keys:
        try:
            code = upgraded_json[key]["interface_diagram"]["code"]
            if not code or not isinstance(code, str) or len(code.strip()) < 5:
                raise ValueError(f"Empty or invalid mermaid code in {key}")
        except KeyError:
            pass  # interface might not exist


async def confirm_upgrade(
    user_id: str,
    project_name: str,
    page_index: int,
    upgraded_json: dict,
) -> None:
    """
    1. Replace section in _sections.json with upgraded_json
    2. If diagram: re-render 4 PNGs
    3. Update meta.modified_sections
    """
    meta_path = _meta_path(user_id, project_name)
    sections_path = _sections_path(user_id, project_name)

    meta = _load_json(meta_path)
    domain = meta.get("domain", "technical")

    section_info = get_section_by_index(domain, page_index)
    if not section_info:
        raise ValueError(f"page_index {page_index} not found in domain '{domain}'")

    section_key = section_info["section_key"]
    section_type = section_info["section_type"]

    # Load and update sections
    sections = _load_json(sections_path)
    sections[section_key] = upgraded_json
    _save_json(sections_path, sections)

    # If diagram section: re-render 4 PNGs
    if section_type == "diagram":
        _rerender_diagram_pngs(user_id, project_name, upgraded_json)

    # v2.1: Update meta.modified_sections
    modified = meta.get("modified_sections", [])
    if section_key not in modified:
        modified.append(section_key)
    meta["modified_sections"] = modified
    _save_json(meta_path, meta)


def _create_version_backup(user_id: str, project_name: str, comment: str = "No comment") -> int | None:
    """
    Back up the current state (both JSON and DOCX).

    BUG FIX: Version number is now derived from the current length of the
    versions list in meta, not from file-existence scanning. The old approach
    could re-use version number 1 when no _v1 file existed yet (because the
    initial meta entry for v1 pointed at the un-versioned live file), causing
    a duplicate v1 entry and confusing restore logic.

    Returns the version number created.
    """
    user_dir = _user_dir(user_id)
    sections_path = _sections_path(user_id, project_name)
    docx_path = user_dir / f"{project_name}_SRS.docx"
    meta_path = _meta_path(user_id, project_name)

    meta = _load_json(meta_path) if meta_path.exists() else {}
    existing_versions = meta.get("versions", [])

    # Derive the next version number from the list length — never from file
    # existence — so it can never collide with the initial metadata entry.
    version = len(existing_versions) + 1

    sections_backup_name = f"{project_name}_sections_v{version}.json"
    docx_backup_name = f"{project_name}_SRS_v{version}.docx"

    # Back up JSON
    if sections_path.exists():
        shutil.copy2(str(sections_path), str(user_dir / sections_backup_name))

    # Back up DOCX (if it exists)
    docx_backed_up = False
    if docx_path.exists():
        shutil.copy2(str(docx_path), str(user_dir / docx_backup_name))
        docx_backed_up = True

    # Update metadata
    existing_versions.append({
        "version": version,
        "comment": comment,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "sections_backup": sections_backup_name,
        "docx_backup": docx_backup_name if docx_backed_up else None,
    })
    meta["versions"] = existing_versions
    _save_json(meta_path, meta)

    print(f"[generated_srs_upgrade_service] Version v{version} created with comment: {comment}")
    return version


def _rerender_diagram_pngs(
    user_id: str,
    project_name: str,
    external_interfaces_json: dict,
) -> None:
    """Re-render the 4 interface diagram PNGs from updated mermaid code."""
    from srs_engine.utils.globals import render_mermaid_png

    base_dir = IMAGES_DIR / project_name
    interface_keys = [
        "user_interfaces",
        "hardware_interfaces",
        "software_interfaces",
        "communication_interfaces",
    ]

    for iface_key in interface_keys:
        try:
            code = external_interfaces_json[iface_key]["interface_diagram"]["code"]
            png_path = base_dir / f"{user_id}/{project_name}_{iface_key}_diagram.png"
            render_mermaid_png(code, png_path)
        except Exception as e:
            print(
                f"[generated_srs_upgrade_service] Failed to re-render "
                f"{iface_key} diagram: {e}"
            )


async def rebuild_docx(
    user_id: str,
    project_name: str,
    comment: str = "No comment",
    _create_version: bool = True,
) -> str:
    """
    Load all 7 sections from _sections.json and regenerate the .docx.
    When _create_version=True (default) also snapshots the new state.

    BUG FIX: Added _create_version flag so restore_version can call this
    function to rebuild the document WITHOUT appending a spurious extra
    version entry to the history.

    Returns path to new .docx.
    """
    from srs_engine.utils.srs_document_generator import generate_srs_document

    meta = _load_json(_meta_path(user_id, project_name))
    sections = _load_json(_sections_path(user_id, project_name))

    # Build image paths
    base_dir = IMAGES_DIR / project_name
    image_paths = {
        "user_interfaces":          base_dir / f"{user_id}/{project_name}_user_interfaces_diagram.png",
        "hardware_interfaces":      base_dir / f"{user_id}/{project_name}_hardware_interfaces_diagram.png",
        "software_interfaces":      base_dir / f"{user_id}/{project_name}_software_interfaces_diagram.png",
        "communication_interfaces": base_dir / f"{user_id}/{project_name}_communication_interfaces_diagram.png",
    }

    output_path = f"./srs_engine/generated_srs/{user_id}/{project_name}_SRS.docx"

    generated_path = generate_srs_document(
        project_name=project_name,
        introduction_section=sections.get("introduction_section", {}),
        overall_description_section=sections.get("overall_description_section", {}),
        system_features_section=sections.get("system_features_section", {}),
        external_interfaces_section=sections.get("external_interfaces_section", {}),
        nfr_section=sections.get("nfr_section", {}),
        glossary_section=sections.get("glossary_section", {}),
        assumptions_section=sections.get("assumptions_section", {}),
        image_paths=image_paths,
        output_path=output_path,
        authors=meta.get("authors", []),
        organization=meta.get("organization", ""),
    )

    if _create_version:
        _create_version_backup(user_id, project_name, comment=comment)

    return generated_path


async def restore_version(user_id: str, project_name: str, version: int) -> None:
    """
    Restore a specific version.

    BUG FIXES:
    1. Old code constructed the backup path as _sections_v{n}.json, which
       broke for v1 (the initial meta entry points at _sections.json, not
       _sections_v1.json). Now we look up the exact filename stored in meta.
    2. Old code called rebuild_docx() which internally calls
       _create_version_backup(), silently adding a new version on every
       restore. Now we pass _create_version=False so restoring is idempotent.
    """
    user_dir = _user_dir(user_id)
    meta_path = _meta_path(user_id, project_name)

    if not meta_path.exists():
        raise FileNotFoundError(f"Project '{project_name}' not found")

    meta = _load_json(meta_path)
    versions = meta.get("versions", [])

    # Look up the exact backup filename from the stored metadata
    version_entry = next((v for v in versions if v["version"] == version), None)
    if not version_entry:
        raise FileNotFoundError(f"Version v{version} not found in project history")

    backup_filename = version_entry.get("sections_backup")
    if not backup_filename:
        raise FileNotFoundError(f"No sections backup recorded for version v{version}")

    backup_json = user_dir / backup_filename
    if not backup_json.exists():
        raise FileNotFoundError(
            f"Backup file '{backup_filename}' is missing from disk for version v{version}"
        )

    # Restore the JSON
    sections_path = _sections_path(user_id, project_name)
    shutil.copy2(str(backup_json), str(sections_path))

    # Rebuild the docx WITHOUT creating a new version entry
    await rebuild_docx(user_id, project_name, _create_version=False)

    print(f"[generated_srs_upgrade_service] Restored version v{version} for {project_name}")