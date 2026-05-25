"""File operations for agent code execution."""

import os
from config import CODEBASE_PATH


def _strip_frontend_prefix(rel_path: str) -> str:
    """Remove redundant 'satory-frontend/' prefix.

    CODEBASE_PATH already points to ./codebase/satory-frontend, but the Coder LLM
    is instructed to return paths like 'satory-frontend/src/...'. Joining them
    yields ./codebase/satory-frontend/satory-frontend/... — the phantom INNER
    directory from LESSON-048 and LESSON-052.
    """
    if rel_path.startswith("satory-frontend/"):
        return rel_path[len("satory-frontend/"):]
    return rel_path


def read_file(rel_path: str) -> str:
    """Read a file from the codebase."""
    rel_path = _strip_frontend_prefix(rel_path)
    full = os.path.join(CODEBASE_PATH, rel_path)
    if not os.path.isfile(full):
        return f"[ERROR] File not found: {rel_path}"
    with open(full, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def write_file(rel_path: str, content: str) -> str:
    """Write content to a file in the codebase."""
    rel_path = _strip_frontend_prefix(rel_path)
    full = os.path.join(CODEBASE_PATH, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written: {rel_path} ({len(content)} chars)"


def patch_file(rel_path: str, old_text: str, new_text: str) -> str:
    """Replace old_text with new_text in a file."""
    rel_path = _strip_frontend_prefix(rel_path)
    content = read_file(rel_path)
    if content.startswith("[ERROR]"):
        return content
    if old_text not in content:
        return f"[ERROR] Text not found in {rel_path}"
    updated = content.replace(old_text, new_text, 1)
    return write_file(rel_path, updated)


def list_files(rel_dir: str = "", extensions: tuple = (".py", ".ts", ".tsx")) -> list[str]:
    """List files in a directory matching extensions."""
    rel_dir = _strip_frontend_prefix(rel_dir)
    full = os.path.join(CODEBASE_PATH, rel_dir)
    if not os.path.isdir(full):
        return []
    result = []
    for root, dirs, files in os.walk(full):
        for f in files:
            if f.endswith(extensions):
                result.append(os.path.relpath(os.path.join(root, f), CODEBASE_PATH))
    return result
