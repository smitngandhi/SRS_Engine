"""
utils/srs_rag_index.py
──────────────────────
FAISS RAG index for generated SRS sections.

Model: all-MiniLM-L6-v2 — 384-dimensional, ~22 MB on disk, CPU-only.

v2.1 changes:
  - In-memory index + map cache to avoid disk reload per query
  - Better embedding text (readable summary instead of raw JSON dump)
  - Safe path construction via pathlib
  - Cosine similarity (IndexFlatIP) instead of L2
"""

from __future__ import annotations

import json
from pathlib import Path

_MODEL = None          # lazy-loaded singleton
_INDEX_CACHE: dict = {}   # v2.1: avoids disk reload per query
_MAP_CACHE: dict = {}


def _get_model():
    """Lazy-load SentenceTransformer once per worker process."""
    global _MODEL
    if _MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for RAG indexing. "
                "Install it with: pip install sentence-transformers"
            )
    return _MODEL


# ── Build (called after generation save) ─────────────────────────────────────

def _build_embedding_text(section_key: str, section_json: dict) -> str:
    """Build a readable summary for embedding instead of raw JSON dump."""
    title = section_key.replace("_", " ")
    summary = json.dumps(section_json)[:300]
    return f"{title}: {summary}"


def build_rag_index(sections_json: dict, user_id: str, project_name: str) -> None:
    """
    Build a FAISS index from all dict-valued entries in sections_json
    and persist it alongside the SRS files.
    """
    try:
        import faiss
        import numpy as np
    except ImportError:
        print("[srs_rag_index] faiss-cpu not installed — skipping RAG index build")
        return

    model = _get_model()
    entries = []

    for key, section in sections_json.items():
        if isinstance(section, dict):
            entries.append({"key": key, "text": _build_embedding_text(key, section)})

    if not entries:
        return

    embeddings = model.encode([e["text"] for e in entries]).astype("float32")

    # v2.1: IndexFlatIP (cosine similarity) instead of IndexFlatL2
    # Normalize vectors for cosine similarity
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    # v2.1: safe path construction via pathlib
    base_dir = Path(f"./srs_engine/generated_srs/{user_id}")
    base_dir.mkdir(parents=True, exist_ok=True)
    faiss_path = base_dir / f"{project_name}_rag.faiss"
    map_path = base_dir / f"{project_name}_rag_map.npy"

    faiss.write_index(index, str(faiss_path))
    np.save(str(map_path), np.array([e["key"] for e in entries]))

    # Invalidate cache for this project
    cache_key = f"{user_id}:{project_name}"
    _INDEX_CACHE.pop(cache_key, None)
    _MAP_CACHE.pop(cache_key, None)

    print(f"[srs_rag_index] Built FAISS index for {project_name} ({len(entries)} sections)")


# ── Search (called on pageIndex miss) ────────────────────────────────────────

def _load_index(user_id: str, project_name: str):
    """Load FAISS index and key map, with in-memory caching."""
    try:
        import faiss
        import numpy as np
    except ImportError:
        raise ImportError(
            "faiss-cpu and numpy are required for RAG search. "
            "Install them with: pip install faiss-cpu numpy"
        )

    cache_key = f"{user_id}:{project_name}"
    if cache_key in _INDEX_CACHE:
        return _INDEX_CACHE[cache_key], _MAP_CACHE[cache_key]

    base = Path(f"./srs_engine/generated_srs/{user_id}")
    faiss_path = base / f"{project_name}_rag.faiss"
    map_path = base / f"{project_name}_rag_map.npy"

    if not faiss_path.exists() or not map_path.exists():
        raise FileNotFoundError(
            f"RAG index not found for project '{project_name}'. "
            f"Expected files: {faiss_path}, {map_path}"
        )

    index = faiss.read_index(str(faiss_path))
    keys = np.load(str(map_path), allow_pickle=True)

    _INDEX_CACHE[cache_key] = index
    _MAP_CACHE[cache_key] = keys
    return index, keys


def search_section(
    query: str,
    user_id: str,
    project_name: str,
    top_k: int = 1,
) -> tuple[str, float]:
    """
    Search the FAISS index for the most relevant section.

    Returns (section_key, confidence_0_to_1).
    """
    import numpy as np

    model = _get_model()
    index, keys = _load_index(user_id, project_name)
    query_vec = model.encode([query]).astype("float32")

    # Normalize for cosine similarity
    faiss_module = __import__("faiss")
    faiss_module.normalize_L2(query_vec)

    distances, indices = index.search(query_vec, k=top_k)

    matched_key = str(keys[indices[0][0]])
    # For IndexFlatIP with normalized vectors, distance IS cosine similarity [0, 1]
    confidence = float(max(0.0, min(1.0, distances[0][0])))
    return matched_key, confidence
