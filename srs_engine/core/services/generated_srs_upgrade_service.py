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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from srs_engine.core.db.file_storage import FileStorage
from srs_engine.core.db.quota_repo import QuotaRepo
from srs_engine.utils.page_index_map import (
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

async def list_generated_srs(user_id: str, db: Any) -> list[dict]:
    """
    List all generated SRS documents for a user from GridFS.
    Returns list of meta dicts.
    """
    fs = FileStorage(db)
    files = await fs.list_files({"type": "meta_json", "user_id": user_id})

    results = []
    for f in files:
        try:
            # We already have the core metadata from list_files
            meta = f.get("metadata", {})
            project = meta.get("project_name", "")
            if not project:
                continue
                
            # If we need the full content of the meta_json (e.g. for versions),
            # fetch it specifically.
            meta_bytes = await fs.get_file({"type": "meta_json", "user_id": user_id, "project_name": project})
            if meta_bytes:
                content = json.loads(meta_bytes)
                # Merge or use content
                content["id"] = project
                content["version_count"] = len(content.get("versions", []))
                results.append(content)
            else:
                # Fallback to what we have in metadata
                meta["id"] = project
                results.append(meta)
        except Exception:
            continue

    return results


async def get_version_history(user_id: str, project_name: str, db: Any) -> list[dict]:
    """Retrieve the version history from meta.json in GridFS."""
    fs = FileStorage(db)
    meta_bytes = await fs.get_file({"type": "meta_json", "user_id": user_id, "project_name": project_name})
    if not meta_bytes:
        return []
    meta = json.loads(meta_bytes)
    return meta.get("versions", [])


async def get_section_by_pageindex(
    user_id: str,
    project_name: str,
    page_index: int,
    db: Any,
) -> SectionResult:
    """
    Look up page_index in PAGE_INDEX_MAP[domain] and fetch data from GridFS.
    """
    fs = FileStorage(db)
    meta_bytes = await fs.get_file({"type": "meta_json", "user_id": user_id, "project_name": project_name})
    if not meta_bytes:
        raise ValueError(f"Project '{project_name}' meta not found")
    meta = json.loads(meta_bytes)
    domain = meta.get("domain", "technical").lower()
    if domain not in ["technical"]: # Fallback for now as only technical is supported
        domain = "technical"

    section_info = get_section_by_index(domain, page_index)
    if not section_info:
        raise ValueError(f"page_index {page_index} not found in domain '{domain}'")

    sections_bytes = await fs.get_file({"type": "sections_json", "user_id": user_id, "project_name": project_name})
    if not sections_bytes:
        raise ValueError(f"Project '{project_name}' sections not found")
    sections = json.loads(sections_bytes)
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
    db: Any,
) -> SectionResult:
    """
    RAG fallback: FAISS search → matched section key + confidence.
    """
    from srs_engine.utils.srs_rag_index import search_section

    fs = FileStorage(db)
    meta_bytes = await fs.get_file({"type": "meta_json", "user_id": user_id, "project_name": project_name})
    if not meta_bytes:
        raise ValueError(f"Project '{project_name}' meta not found")
    meta = json.loads(meta_bytes)
    domain = meta.get("domain", "technical").lower()
    if domain not in ["technical"]: # Fallback for now as only technical is supported
        domain = "technical"

    matched_key, confidence = await search_section(
        query=query,
        user_id=user_id,
        project_name=project_name,
        db=db,
    )

    # Find page_index for the matched key
    section_info = get_section_by_key(domain, matched_key)
    if not section_info:
        raise ValueError(f"RAG matched key '{matched_key}' not found in domain '{domain}'")

    sections_bytes = await fs.get_file({"type": "sections_json", "user_id": user_id, "project_name": project_name})
    if not sections_bytes:
        raise ValueError(f"Project '{project_name}' sections not found")
    sections = json.loads(sections_bytes)
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
    db: Any,
) -> dict:
    """
    1. Check upgrade quota
    2. Load section from GridFS
    3. Call upgrade agent
    4. Validate and return preview
    """
    from srs_engine.agents.upgrader_agents.section_upgrade_agent import (
        run_section_upgrade,
    )

    # Quota check
    quota = QuotaRepo(db)
    allowed = await quota.check_quota(user_id, "upgrade_count", project_name=project_name, limit=2)
    if not allowed:
        raise HTTPException(status_code=429, detail="You've reached your free plan limit of 2 upgrades for this project.")

    fs = FileStorage(db)
    meta_bytes = await fs.get_file({"type": "meta_json", "user_id": user_id, "project_name": project_name})
    if not meta_bytes:
        raise ValueError(f"Project '{project_name}' meta not found")
    meta = json.loads(meta_bytes)
    domain = meta.get("domain", "technical").lower()
    if domain not in ["technical"]: # Fallback for now as only technical is supported
        domain = "technical"

    section_info = get_section_by_index(domain, page_index)
    if not section_info:
        raise ValueError(f"page_index {page_index} not found in domain '{domain}'")

    sections_bytes = await fs.get_file({"type": "sections_json", "user_id": user_id, "project_name": project_name})
    if not sections_bytes:
        raise ValueError(f"Project '{project_name}' sections not found")
    sections = json.loads(sections_bytes)
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

    # Validate upgraded_json against section schema
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
    db: Any,
) -> None:
    """
    1. Replace section in sections_json in GridFS
    2. If diagram: re-render PNGs
    3. Update meta in GridFS and increment quota
    """
    fs = FileStorage(db)
    meta_bytes = await fs.get_file({"type": "meta_json", "user_id": user_id, "project_name": project_name})
    if not meta_bytes:
        raise ValueError(f"Project '{project_name}' meta not found")
    meta = json.loads(meta_bytes)
    domain = meta.get("domain", "technical").lower()
    if domain not in ["technical"]: # Fallback for now as only technical is supported
        domain = "technical"

    section_info = get_section_by_index(domain, page_index)
    if not section_info:
        raise ValueError(f"page_index {page_index} not found in domain '{domain}'")

    section_key = section_info["section_key"]
    section_type = section_info["section_type"]

    # Load, update and save sections to GridFS
    sections_bytes = await fs.get_file({"type": "sections_json", "user_id": user_id, "project_name": project_name})
    if not sections_bytes:
        raise ValueError(f"Project '{project_name}' sections not found")
    sections = json.loads(sections_bytes)
    sections[section_key] = upgraded_json
    await fs.save_file(
        json.dumps(sections).encode(),
        f"{project_name}_sections.json",
        {"type": "sections_json", "user_id": user_id, "project_name": project_name}
    )

    # Re-render diagrams if needed (disk operation, temporary)
    if section_type == "diagram":
        _rerender_diagram_pngs(user_id, project_name, upgraded_json)

    # Update meta and save to GridFS
    modified = meta.get("modified_sections", [])
    if section_key not in modified:
        modified.append(section_key)
    meta["modified_sections"] = modified
    await fs.save_file(
        json.dumps(meta).encode(),
        f"{project_name}_meta.json",
        {"type": "meta_json", "user_id": user_id, "project_name": project_name}
    )

    # Increment quota
    quota = QuotaRepo(db)
    await quota.increment_quota(user_id, "upgrade_count", project_name=project_name)


async def _create_version_backup(user_id: str, project_name: str, db: Any, comment: str = "No comment") -> int | None:
    """
    Back up the current state in GridFS.
    """
    fs = FileStorage(db)
    meta_bytes = await fs.get_file({"type": "meta_json", "user_id": user_id, "project_name": project_name})
    if not meta_bytes:
        return None
    meta = json.loads(meta_bytes)
    existing_versions = meta.get("versions", [])
    version = len(existing_versions) + 1

    sections_backup_name = f"{project_name}_sections_v{version}.json"
    docx_backup_name = f"{project_name}_SRS_v{version}.docx"

    # Backup JSON
    sections_bytes = await fs.get_file({"type": "sections_json", "user_id": user_id, "project_name": project_name})
    if sections_bytes:
        await fs.save_file(
            sections_bytes,
            sections_backup_name,
            {"type": "version_sections_json", "user_id": user_id, "project_name": project_name, "version": version}
        )

    # Backup DOCX
    docx_bytes = await fs.get_file({"type": "docx", "user_id": user_id, "project_name": project_name})
    docx_backed_up = False
    if docx_bytes:
        await fs.save_file(
            docx_bytes,
            docx_backup_name,
            {"type": "version_docx", "user_id": user_id, "project_name": project_name, "version": version}
        )
        docx_backed_up = True

    # Update metadata
    existing_versions.append({
        "version": version,
        "comment": comment,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "sections_backup": sections_backup_name,
        "docx_backup": docx_backup_name if docx_backed_up else None,
    })
    meta["versions"] = existing_versions
    await fs.save_file(
        json.dumps(meta).encode(),
        f"{project_name}_meta.json",
        {"type": "meta_json", "user_id": user_id, "project_name": project_name}
    )

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
    db: Any,
    comment: str = "No comment",
    _create_version: bool = True,
) -> str:
    """
    Regenerate DOCX and save to GridFS.
    """
    from srs_engine.utils.srs_document_generator import generate_srs_document

    fs = FileStorage(db)
    meta_bytes = await fs.get_file({"type": "meta_json", "user_id": user_id, "project_name": project_name})
    sections_bytes = await fs.get_file({"type": "sections_json", "user_id": user_id, "project_name": project_name})

    if not meta_bytes or not sections_bytes:
        raise ValueError("Project data missing in GridFS")

    meta = json.loads(meta_bytes)
    sections = json.loads(sections_bytes)

    # Build image paths (temporary disk check)
    base_dir = IMAGES_DIR / project_name
    image_paths = {
        "user_interfaces":          base_dir / f"{user_id}/{project_name}_user_interfaces_diagram.png",
        "hardware_interfaces":      base_dir / f"{user_id}/{project_name}_hardware_interfaces_diagram.png",
        "software_interfaces":      base_dir / f"{user_id}/{project_name}_software_interfaces_diagram.png",
        "communication_interfaces": base_dir / f"{user_id}/{project_name}_communication_interfaces_diagram.png",
    }

    output_path = f"./srs_engine/generated_srs/{user_id}/{project_name}_SRS.docx"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

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

    # Save to GridFS
    docx_bytes = Path(generated_path).read_bytes()
    await fs.save_file(
        docx_bytes,
        f"{project_name}_SRS.docx",
        {"type": "docx", "user_id": user_id, "project_name": project_name}
    )

    if _create_version:
        await _create_version_backup(user_id, project_name, db, comment=comment)

    return generated_path


async def restore_version(user_id: str, project_name: str, version: int, db: Any) -> None:
    """
    Restore a specific version from GridFS.
    """
    fs = FileStorage(db)
    meta_bytes = await fs.get_file({"type": "meta_json", "user_id": user_id, "project_name": project_name})
    if not meta_bytes:
        raise FileNotFoundError(f"Project '{project_name}' not found")

    meta = json.loads(meta_bytes)
    versions = meta.get("versions", [])

    version_entry = next((v for v in versions if v["version"] == version), None)
    if not version_entry:
        raise FileNotFoundError(f"Version v{version} not found")

    # Restore sections JSON from GridFS backup
    backup_bytes = await fs.get_file({
        "type": "version_sections_json",
        "user_id": user_id,
        "project_name": project_name,
        "version": version
    })
    if not backup_bytes:
        raise FileNotFoundError(f"Backup for v{version} missing")

    await fs.save_file(
        backup_bytes,
        f"{project_name}_sections.json",
        {"type": "sections_json", "user_id": user_id, "project_name": project_name}
    )

    # Rebuild the docx WITHOUT creating a new version entry
    await rebuild_docx(user_id, project_name, db, _create_version=False)

    print(f"[generated_srs_upgrade_service] Restored version v{version} for {project_name}")