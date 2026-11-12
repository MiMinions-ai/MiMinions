"""Duplicate / near-duplicate filtering for the in-memory agent context.

Persistent tiers (MEMORY.md, HISTORY.md, vector store) are never deduplicated;
these helpers only shrink what is shown to the model.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
SEMANTIC_THRESHOLD = 0.8


def _exact_keep(texts: list[str]) -> list[int]:
    seen: set[str] = set()
    kept: list[int] = []
    for i, text in enumerate(texts):
        key = text.casefold()
        if key not in seen:
            seen.add(key)
            kept.append(i)
    return kept


def _semantic_keep(texts: list[str], threshold: float) -> list[int]:
    """Indices to keep: drop texts whose cosine similarity to a kept text >= threshold."""
    assert 0.0 < threshold <= 1.0
    everything = list(range(len(texts)))
    if len(texts) < 2:
        return everything
    try:
        import numpy as np
        from fastembed import TextEmbedding

        model = TextEmbedding(_EMBED_MODEL)
        vectors = np.array(list(model.embed(texts)), dtype=float)
    except Exception as exc:  # fastembed missing or model unavailable
        logger.warning("Semantic dedupe unavailable, using exact match only: %s", exc)
        return everything

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / np.maximum(norms, 1e-12)
    kept: list[int] = []
    for i in everything:
        if kept and float(np.max(vectors[kept] @ vectors[i])) >= threshold:
            continue
        kept.append(i)
    return kept


def unique_indices(texts: list[str], threshold: float = SEMANTIC_THRESHOLD) -> list[int]:
    """Indices of texts left after exact (case-insensitive) then semantic dedupe, first wins."""
    exact = _exact_keep(texts)
    semantic = _semantic_keep([texts[i] for i in exact], threshold)
    return [exact[i] for i in semantic]


def dedupe_facts(
    facts: list[tuple[str, str]], threshold: float = SEMANTIC_THRESHOLD
) -> tuple[list[tuple[str, str]], int]:
    """Return (unique facts, dropped count); the first occurrence is kept."""
    kept = unique_indices([text for _, text in facts], threshold)
    return [facts[i] for i in kept], len(facts) - len(kept)


def dedupe_memory_text(text: str, threshold: float = SEMANTIC_THRESHOLD) -> str:
    """Drop duplicate top-level bullets from markdown text; all other lines are kept."""
    lines = text.splitlines()
    bullet_idx = [i for i, line in enumerate(lines) if line.startswith("- ")]
    keep = unique_indices([lines[i][2:].strip() for i in bullet_idx], threshold)
    drop = {bullet_idx[j] for j in range(len(bullet_idx))} - {bullet_idx[j] for j in keep}
    if not drop:
        return text
    return "\n".join(line for i, line in enumerate(lines) if i not in drop)
