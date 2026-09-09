import os
import json
import re
import datetime

from utils import file_dir

# Store memories next to the personality files (soul/memory.json)
MEMORY_FILE = os.path.join(file_dir(__file__), "..", "memory.json")


def _load_memories() -> list:
    """Load the list of memory entries from disk (empty list if none yet)."""
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_memories(memories: list) -> None:
    """Persist the list of memory entries to disk."""
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=2, ensure_ascii=False)


def _next_id(memories: list) -> int:
    """Return the next available integer id."""
    return max((m.get("id", 0) for m in memories), default=0) + 1


def _score(memory: dict, query_words: list) -> int:
    """Score a memory by how many query words appear in it (case-insensitive)."""
    haystack = f"{memory.get('text', '')} {memory.get('category', '')}".lower()
    return sum(1 for word in query_words if word in haystack)


def manage_memory(
    action: str = "recall",
    text: str = "",
    category: str = "",
    query: str = "",
    memory_id: int | None = None,
) -> str:
    """
    Manages Yuna's long-term memory so she can remember facts across sessions.

    Args:
        action (str): The memory operation. Must be one of: 'save', 'recall', 'list', or 'delete'.
        text (str): The fact or detail to remember. Required for 'save'.
        category (str): Optional label to group memories (e.g. 'preferences', 'people', 'schedule').
        query (str): Search terms to find relevant memories. Used for 'recall'.
        memory_id (int): The id of a specific memory to delete. Required for 'delete'.
    """
    action = action.lower().strip()
    valid_actions = {"save", "recall", "list", "delete"}

    if action not in valid_actions:
        return f"Error: Invalid action '{action}'. Must be one of: {', '.join(sorted(valid_actions))}."

    memories = _load_memories()

    # ------------------------------------------------------------------
    # SAVE: store a new fact
    # ------------------------------------------------------------------
    if action == "save":
        if not text.strip():
            return "Error: 'text' is required to save a memory."

        entry = {
            "id": _next_id(memories),
            "text": text.strip(),
            "category": category.strip().lower() or "general",
            "created": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        memories.append(entry)
        _save_memories(memories)
        return f"Saved memory #{entry['id']} ({entry['category']}): {entry['text']}"

    # ------------------------------------------------------------------
    # RECALL: find memories matching the query
    # ------------------------------------------------------------------
    if action == "recall":
        if not memories:
            return "No memories stored yet."

        query_words = [w for w in re.split(r"\W+", query.lower()) if len(w) > 2]

        if not query_words:
            # No usable query: return the most recent few memories
            matches = memories[-5:]
        else:
            scored = [
                (score, m) for m in memories
                if (score := _score(m, query_words)) > 0
            ]
            scored.sort(key=lambda pair: pair[0], reverse=True)
            matches = [m for _, m in scored[:5]]

        if not matches:
            return f"No memories found matching '{query}'."

        lines = [
            f"#{m['id']} [{m.get('category', 'general')}] {m['text']}"
            for m in matches
        ]
        return "Relevant memories:\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # LIST: show all memories, optionally filtered by category
    # ------------------------------------------------------------------
    if action == "list":
        if not memories:
            return "No memories stored yet."

        if category.strip():
            cat = category.strip().lower()
            memories = [m for m in memories if m.get("category", "general") == cat]
            if not memories:
                return f"No memories in category '{cat}'."

        lines = [
            f"#{m['id']} [{m.get('category', 'general')}] {m['text']}"
            for m in memories
        ]
        return f"{len(memories)} memories:\n" + "\n".join(lines)

    # ------------------------------------------------------------------
    # DELETE: remove a specific memory by id
    # ------------------------------------------------------------------
    if action == "delete":
        if memory_id is None:
            return "Error: 'memory_id' is required to delete a memory."

        for i, m in enumerate(memories):
            if m.get("id") == memory_id:
                removed = memories.pop(i)
                _save_memories(memories)
                return f"Deleted memory #{memory_id}: {removed['text']}"

        return f"No memory found with id {memory_id}."

    # Should be unreachable since action is validated above
    return f"Error: Invalid action '{action}'."


# =====================================================================
# Ollama Tool Definition Metadata
# =====================================================================
memory_tools_meta = [
    {
        'type': 'function',
        'function': {
            'name': 'manage_memory',
            'description': (
                "Manages Yuna's long-term memory so she can remember facts, "
                "preferences, and context across conversations. Use 'save' to "
                "remember something, 'recall' to find relevant memories, 'list' "
                "to see everything stored, and 'delete' to forget a specific one."
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'action': {
                        'type': 'string',
                        'enum': ['save', 'recall', 'list', 'delete'],
                        'description': (
                            "The memory operation. 'save' to remember a fact, "
                            "'recall' to search for relevant memories, 'list' to "
                            "show all memories, 'delete' to remove one by id."
                        ),
                    },
                    'text': {
                        'type': 'string',
                        'description': "The fact or detail to remember. Required for 'save'.",
                    },
                    'category': {
                        'type': 'string',
                        'description': (
                            "Optional label to group memories (e.g. 'preferences', "
                            "'people', 'schedule'). Defaults to 'general'."
                        ),
                    },
                    'query': {
                        'type': 'string',
                        'description': "Search terms to find relevant memories. Used for 'recall'.",
                    },
                    'memory_id': {
                        'type': 'integer',
                        'description': "The id of a specific memory to delete. Required for 'delete'.",
                    },
                },
                'required': ['action'],
            },
        },
    }
]
