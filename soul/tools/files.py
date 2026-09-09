import os

# Cap for read_file output so a huge file doesn't blow up the LLM context
MAX_READ_CHARS = 20000


def _resolve(path: str) -> str:
    """Expand ~ and return the absolute path."""
    return os.path.abspath(os.path.expanduser(path.strip()))


def read_file(path: str, start_line: int = 1, end_line: int = 0) -> str:
    """
    Reads a text file from disk, optionally only a range of lines.

    Args:
        path (str): The path to the file to read.
        start_line (int): The first line to read (1-indexed). Defaults to 1.
        end_line (int): The last line to read (1-indexed, inclusive).
            0 means 'read to the end of the file'.
    """
    target = _resolve(path)

    if not os.path.exists(target):
        return f"Error: The file '{target}' does not exist."
    if not os.path.isfile(target):
        return f"Error: The path '{target}' is a directory, not a file."

    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except PermissionError:
        return f"Error: Permission denied reading '{target}'."
    except Exception as e:
        return f"Error: Failed to read '{target}': {str(e)}"

    total = len(lines)
    start = max(1, int(start_line or 1))
    end = int(end_line) if end_line else total
    end = min(total, max(end, start))

    chunk = lines[start - 1:end]
    text = "".join(chunk)

    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + f"\n... [truncated, file has {total} lines total]"

    header = f"Lines {start}-{end} of {total} in {target}:\n"
    return header + text


def write_file(path: str, content: str, append: bool = False) -> str:
    """
    Writes text to a file, creating parent directories if needed.

    Args:
        path (str): The path of the file to write.
        content (str): The text content to write.
        append (bool): If true, append to the file instead of overwriting it.
    """
    target = _resolve(path)

    try:
        parent = os.path.dirname(target)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        mode = "a" if append else "w"
        with open(target, mode, encoding="utf-8") as f:
            f.write(content)

        verb = "Appended to" if append else "Wrote"
        return f"{verb} {len(content)} characters to '{target}'."
    except PermissionError:
        return f"Error: Permission denied writing to '{target}'."
    except Exception as e:
        return f"Error: Failed to write '{target}': {str(e)}"


def move_file(source: str, destination: str) -> str:
    """
    Moves or renames a file or directory.

    Args:
        source (str): The path of the file or directory to move.
        destination (str): The new path (or new name, if only renaming in place).
    """
    src = _resolve(source)
    dst = _resolve(destination)

    if not os.path.exists(src):
        return f"Error: The source '{src}' does not exist."

    try:
        # Ensure the destination's parent directory exists
        dst_parent = os.path.dirname(dst)
        if dst_parent and not os.path.exists(dst_parent):
            os.makedirs(dst_parent, exist_ok=True)

        os.replace(src, dst)
        return f"Successfully moved '{src}' to '{dst}'."
    except PermissionError:
        return f"Error: Permission denied moving '{src}' to '{dst}'."
    except Exception as e:
        return f"Error: Failed to move '{src}' to '{dst}': {str(e)}"


# =====================================================================
# Tool Definition Metadata
# =====================================================================
files_tools_meta = [
    {
        'type': 'function',
        'function': {
            'name': 'read_file',
            'description': (
                "Reads a text file from the computer's disk. Use this to read "
                "notes, documents, code, or any text file. Can read a specific "
                "line range for large files."
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': "The path to the file to read (e.g., '/home/miko/notes.txt' or '~/notes.txt').",
                    },
                    'start_line': {
                        'type': 'integer',
                        'description': "The first line to read (1-indexed). Defaults to 1.",
                    },
                    'end_line': {
                        'type': 'integer',
                        'description': "The last line to read (1-indexed, inclusive). 0 means read to the end.",
                    },
                },
                'required': ['path'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'write_file',
            'description': (
                "Writes text to a file on the computer, creating it (and any "
                "missing parent folders) if needed. Use this to save notes, "
                "lists, or anything the user asks to be written down."
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': "The path of the file to write (e.g., '/home/miko/Desktop/todo.txt').",
                    },
                    'content': {
                        'type': 'string',
                        'description': "The text content to write to the file.",
                    },
                    'append': {
                        'type': 'boolean',
                        'description': "Set to true to append to the end of the file instead of overwriting it.",
                    },
                },
                'required': ['path', 'content'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'move_file',
            'description': (
                "Moves or renames a file or directory to a new path. Use this "
                "when the user asks to move, rename, or reorganize files."
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'source': {
                        'type': 'string',
                        'description': "The current path of the file or directory to move.",
                    },
                    'destination': {
                        'type': 'string',
                        'description': "The new path for the file or directory.",
                    },
                },
                'required': ['source', 'destination'],
            },
        },
    },
]
