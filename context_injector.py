#!/usr/bin/env python3
"""context_injector.py — GOD_PROMPT v1.0 Task 28 cutover (2026-04-18).

Progressive-disclosure context injection is now the default.
This module is a thin re-export of tools/context_injector_v2.get_context_v2.
Archived v1: context_injector.py.v1-archived-2026-04-18 (50 KB injector).
"""

import sys
from pathlib import Path

_TOOLS = Path('/Users/madia/nous-agaas/tools')
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from context_injector_v2 import get_context_v2 as get_context  # noqa: F401

__all__ = ['get_context']
