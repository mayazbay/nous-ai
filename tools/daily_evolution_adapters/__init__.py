"""daily_evolution_adapters — upgrade adapter interface + concrete implementations.

Each adapter module MUST expose an `Adapter` class (or any class with
`probe_current_version` method) that implements the AdapterBase protocol.

Adapter naming convention:
  - `name` property returns a short, stable snake_case identifier.
  - One module per upgrade target: openclaw.py, codex.py, gbrain.py, etc.
"""

from __future__ import annotations

from .base import AdapterBase, RollbackError

__all__ = ["AdapterBase", "RollbackError"]
