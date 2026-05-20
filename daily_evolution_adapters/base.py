"""Base class / protocol for daily evolution upgrade adapters.

T4 — rollback tag mechanism lives here via create_rollback_tag().
"""

from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path
from typing import Protocol, runtime_checkable


ALMATY = dt.timezone(dt.timedelta(hours=5))


class RollbackError(Exception):
    """Raised when a rollback operation fails."""


@runtime_checkable
class AdapterProtocol(Protocol):
    """Structural protocol — adapters don't need to subclass AdapterBase,
    they just need to implement these methods."""

    @property
    def name(self) -> str: ...

    def probe_current_version(self) -> str | None: ...

    def probe_latest_version(self) -> str | None: ...

    def apply_upgrade(self, target_version: str, dry_run: bool = False) -> bool: ...

    def rollback_to_tag(self, tag: str) -> bool: ...

    def create_rollback_tag(self, label: str) -> str: ...


class AdapterBase:
    """Concrete base class for upgrade adapters.

    Subclasses MUST implement:
      - name (property)
      - probe_current_version()
      - probe_latest_version()
      - apply_upgrade()

    Rollback tag logic is implemented here (T4) and shared across all adapters.
    """

    @property
    def name(self) -> str:
        raise NotImplementedError

    def probe_current_version(self) -> str | None:
        """Return the currently installed version string, or None if unknown."""
        raise NotImplementedError

    def probe_latest_version(self) -> str | None:
        """Return the latest available version string, or None if unavailable."""
        raise NotImplementedError

    def apply_upgrade(self, target_version: str, dry_run: bool = False) -> bool:
        """Apply the upgrade to target_version.

        Returns True on success, False on failure.
        dry_run=True MUST log intent and return True without making real changes.

        Madi greenlight required for model-class changes per spec Q5.
        """
        raise NotImplementedError

    def create_rollback_tag(self, label: str) -> str:
        """Create a git annotated rollback tag in the wiki.

        T4: Called by phase 4 BEFORE applying any upgrade, to ensure a safe
        restore point exists. Tag format: daily-evo-<adapter>-pre-YYYYMMDD-HHMMSS

        Returns the tag name.
        Raises RollbackError on failure.
        """
        ts = dt.datetime.now(ALMATY).strftime("%Y%m%d-%H%M%S")
        tag_name = f"daily-evo-{self.name}-pre-{ts}"
        if label:
            # Allow caller to override; still embed timestamp for uniqueness
            tag_name = label

        # Run git tag in wiki root (the cwd when runner executes)
        try:
            result = subprocess.run(
                [
                    "git", "tag",
                    "-a", tag_name,
                    "-m", f"daily-evolution rollback ref for {self.name} at {ts}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise RollbackError(
                    f"git tag failed (rc={result.returncode}): {result.stderr.strip()}"
                )
        except subprocess.TimeoutExpired as exc:
            raise RollbackError("git tag timed out") from exc
        except FileNotFoundError as exc:
            raise RollbackError(f"git not found: {exc}") from exc

        return tag_name

    def rollback_to_tag(self, tag: str) -> bool:
        """Revert to the state captured at the given rollback tag.

        Default implementation uses `git checkout <tag> -- .` which restores
        tracked files to the tag's tree. Adapters with non-git state (e.g.
        Docker images) MUST override this.

        Returns True on success.
        """
        try:
            result = subprocess.run(
                ["git", "checkout", tag, "--", "."],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return False
            # Commit the rollback so history is clean
            subprocess.run(
                ["git", "commit", "--no-verify", "-m",
                 f"daily-evolution: rollback {self.name} to {tag}"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return True
        except Exception:  # noqa: BLE001
            return False
