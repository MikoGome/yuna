"""
RAG (Retrieval-Augmented Generation) engine for Yuna's long-term memory.

Memories live in ``soul/memory.json``. This module embeds each memory with a
local Ollama embedding model (``nomic-embed-text``) and retrieves the most
relevant ones for a query using cosine similarity. Embeddings are cached in
``soul/memory_embeddings.json`` so each memory is only embedded once.

If the embedding server is unreachable, retrieval falls back to simple
keyword scoring so recall never hard-fails.
"""

import os
import re
import json
import math
import hashlib

from utils import file_dir
from ollama import Client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://10.0.0.22:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

SOUL_DIR = file_dir(__file__)
MEMORY_FILE = os.path.join(SOUL_DIR, "memory.json")
CACHE_FILE = os.path.join(SOUL_DIR, "memory_embeddings.json")

# Minimum cosine similarity for a memory to count as relevant.
SIMILARITY_THRESHOLD = 0.35
DEFAULT_TOP_K = 5

_client = None


def _get_client() -> Client:
    """Lazily create (and reuse) the Ollama client for embeddings."""
    global _client
    if _client is None:
        _client = Client(host=OLLAMA_HOST)
    return _client


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------
def _load_memories() -> list:
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _load_cache() -> dict:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f)


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _round_vector(vec: list) -> list:
    return [round(x, 6) for x in vec]


# ---------------------------------------------------------------------------
# Embedding + similarity
# ---------------------------------------------------------------------------
def _embed(texts: list) -> list:
    """Embed a list of texts, returning a list of vectors (lists of floats)."""
    if not texts:
        return []
    response = _get_client().embed(model=EMBED_MODEL, input=texts)
    return response.embeddings


def _cosine(a: list, b: list) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _ensure_embeddings(memories: list) -> dict:
    """
    Return a mapping of memory id -> embedding vector, computing and caching
    any missing embeddings. Stale cache entries (deleted memories) are pruned.
    """
    cache = _load_cache()
    vectors = {}
    to_embed = []  # list of (id, text)

    for m in memories:
        mid = m.get("id")
        text = m.get("text", "")
        key = _text_hash(text)
        entry = cache.get(str(mid))
        if entry and entry.get("hash") == key:
            vectors[mid] = entry["vector"]
        else:
            to_embed.append((mid, text))

    dirty = False

    if to_embed:
        try:
            new_vectors = _embed([t for _, t in to_embed])
        except Exception as e:
            print(f"[RAG] embedding failed: {e}")
            new_vectors = []
        for (mid, _text), vec in zip(to_embed, new_vectors):
            vectors[mid] = vec
            cache[str(mid)] = {
                "hash": _text_hash(_text),
                "vector": _round_vector(vec),
            }
            dirty = True

    # Prune cache entries for memories that no longer exist.
    current_ids = {str(m.get("id")) for m in memories}
    for k in [k for k in cache if k not in current_ids]:
        del cache[k]
        dirty = True

    if dirty:
        _save_cache(cache)

    return vectors


# ---------------------------------------------------------------------------
# Keyword fallback (used when the embedding server is unavailable)
# ---------------------------------------------------------------------------
def _keyword_retrieve(memories: list, query: str, top_k: int) -> list:
    query_words = [w for w in re.split(r"\W+", query.lower()) if len(w) > 2]
    if not query_words:
        return []
    scored = []
    for m in memories:
        haystack = f"{m.get('text', '')} {m.get('category', '')}".lower()
        score = sum(1 for w in query_words if w in haystack)
        if score > 0:
            entry = dict(m)
            entry["score"] = score
            scored.append((score, entry))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [entry for _, entry in scored[:top_k]]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Retrieve the memories most relevant to ``query``.

    Returns a list of memory dicts (each augmented with a ``score``), ordered
    by relevance. Empty list if nothing is relevant.
    """
    memories = _load_memories()
    if not memories:
        return []

    query = (query or "").strip()
    if not query:
        return []

    vectors = _ensure_embeddings(memories)

    try:
        q_vec = _embed([query])[0]
    except Exception as e:
        print(f"[RAG] query embedding failed, falling back to keywords: {e}")
        return _keyword_retrieve(memories, query, top_k)

    scored = []
    for m in memories:
        vec = vectors.get(m.get("id"))
        if not vec:
            continue
        score = _cosine(q_vec, vec)
        if score >= SIMILARITY_THRESHOLD:
            scored.append((score, m))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    results = []
    for score, m in scored[:top_k]:
        entry = dict(m)
        entry["score"] = round(score, 4)
        results.append(entry)
    return results


def format_memories(memories: list) -> str:
    """Format retrieved memories as a compact block for prompt injection."""
    if not memories:
        return ""
    lines = [
        f"#{m.get('id')} [{m.get('category', 'general')}] {m.get('text', '')}"
        for m in memories
    ]
    return "Relevant memories from long-term memory:\n" + "\n".join(lines)
