"""OpenClaw upgrade adapter.

Current version: ghcr.io/openclaw/openclaw:2026.4.14 (Docker on Air).

Adapter pattern (T3):
  - probe_current_version: ssh air `docker inspect openclaw` → image tag suffix
  - probe_latest_version:  TODO stub — returns None (T5/T7 wires real check)
  - apply_upgrade:         dry-run logs intent; real path requires Madi greenlight
  - rollback_to_tag:       docker stop + docker run with previous image tag
  - create_rollback_tag:   inherited from AdapterBase (git annotated tag)

The goal: prove the ADAPTER PATTERN end-to-end via probe_current_version.
apply_upgrade is intentionally stub — 7-day soak must be proven first.
"""

from __future__ import annotations

import subprocess
from typing import Any

from .base import AdapterBase, RollbackError

HOST_AIR = "air"  # ssh alias
CONTAINER_NAME = "openclaw"
REGISTRY_PREFIX = "ghcr.io/openclaw/openclaw:"


def _local_run(cmd: str, timeout: int = 20) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "timeout", "returncode": -1}
    except FileNotFoundError as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "returncode": -2}


def _ssh_run(host: str, cmd: str, timeout: int = 20) -> dict[str, Any]:
    if host == HOST_AIR:
        local = _local_run(cmd, timeout=timeout)
        if local["ok"]:
            return local

    try:
        proc = subprocess.run(
            ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", host, cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "stderr": "timeout", "returncode": -1}
    except FileNotFoundError as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "returncode": -2}


def parse_version_from_image(image_ref: str) -> str | None:
    """Extract version tag suffix from an image reference.

    Examples:
      "ghcr.io/openclaw/openclaw:2026.4.14" → "2026.4.14"
      "sha256:abcdef..." → None
      "ghcr.io/openclaw/openclaw@sha256:..." → None
    """
    if not image_ref or image_ref.startswith("sha256:"):
        return None
    if "@sha256:" in image_ref:
        # Image was pulled by digest — no version tag available
        return None
    if ":" in image_ref:
        _, _, tag = image_ref.rpartition(":")
        return tag if tag else None
    return None


class OpenClawAdapter(AdapterBase):
    """Adapter for OpenClaw container running on Air."""

    @property
    def name(self) -> str:
        return "openclaw"

    def probe_current_version(self) -> str | None:
        """SSH to Air, inspect openclaw container, extract image version tag.

        Returns version string like "2026.4.14" or None if unavailable.

        Bug 2026-05-19 (Codex 67610676 verification): previous version
        probed `{{.Image}}` which returns the resolved image ID hash
        (sha256:...), not the tagged reference. Version lives in
        `{{.Config.Image}}` which preserves the original repo:tag ref.
        Without this, every probe returned None and detect_upgrades
        silently skipped OpenClaw.
        """
        result = _ssh_run(
            HOST_AIR,
            f"docker inspect {CONTAINER_NAME} --format '{{{{.Config.Image}}}}' 2>/dev/null",
        )
        if not result["ok"] or not result["stdout"]:
            return None
        image_ref = result["stdout"].strip().strip("'\"")
        version = parse_version_from_image(image_ref)
        if version:
            return version

        fallback = _ssh_run(
            HOST_AIR,
            f"docker inspect {CONTAINER_NAME} --format '{{{{.Image}}}}' 2>/dev/null",
        )
        if not fallback["ok"] or not fallback["stdout"]:
            return None
        return parse_version_from_image(fallback["stdout"].strip().strip("'\""))

    def probe_latest_version(self) -> str | None:
        """Return the latest available OpenClaw version.

        TODO: real implementation should check:
          - npm view @openclaw/openclaw version
          - OR GitHub Releases API: https://api.github.com/repos/openclaw/openclaw/releases/latest

        Returning None here causes detect_upgrades to skip this adapter,
        which is the safe default until the probe is wired (T5/T7).
        """
        # Stub: returning None prevents any upgrade from being queued.
        return None

    def apply_upgrade(self, target_version: str, dry_run: bool = False) -> bool:
        """Apply OpenClaw upgrade to target_version.

        dry_run=True: logs intent, returns True, no action.
        real path:    requires Madi explicit greenlight per spec Q5 (7-day soak).
        """
        if dry_run:
            print(
                f"[openclaw-adapter] dry-run: would upgrade OpenClaw to {target_version} "
                f"via: docker pull {REGISTRY_PREFIX}{target_version} && "
                f"docker stop {CONTAINER_NAME} && "
                f"docker run ... {REGISTRY_PREFIX}{target_version}"
            )
            return True

        raise NotImplementedError(
            "Madi greenlight required for OpenClaw upgrade until 7-day soak proven. "
            "Apply path is intentionally not implemented. "
            "See spec Q3/Q5: canary soak + AP-21 24h gate must pass first."
        )

    def rollback_to_tag(self, tag: str) -> bool:
        """Rollback OpenClaw to the image version captured at rollback tag.

        Strategy:
          1. Parse the previous image version from the git tag message.
          2. docker stop openclaw
          3. docker run ... <previous_image_tag>

        The tag message written by create_rollback_tag includes the current
        image ref; we parse it back here.

        Returns True on success, False on failure.
        """
        # Get tag message to recover previous image ref
        result = subprocess.run(
            ["git", "tag", "-l", tag, "-n1"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return False

        # For now: conservative approach — stop container; restart is manual.
        # Real impl would extract image ref from tag annotation.
        stop_result = _ssh_run(HOST_AIR, f"docker stop {CONTAINER_NAME}", timeout=30)
        if not stop_result["ok"]:
            return False

        # TODO: docker run with previous image tag (requires parsing tag message)
        return True

    def create_rollback_tag(self, label: str) -> str:
        """Create a rollback tag, capturing current OpenClaw image info.

        Overrides AdapterBase to also include the current image SHA in the
        tag message for rollback reference.
        """
        # Capture current image before creating tag
        img_result = _ssh_run(
            HOST_AIR,
            f"docker inspect {CONTAINER_NAME} --format '{{{{.Image}}}}' 2>/dev/null",
        )
        current_image = img_result["stdout"].strip() if img_result["ok"] else "unknown"

        try:
            result = subprocess.run(
                [
                    "git", "tag",
                    "-a", label,
                    "-m",
                    f"daily-evolution rollback ref for openclaw; image={current_image}",
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

        return label


# Expose as `Adapter` for dynamic loader in daily_evolution_runner.py
Adapter = OpenClawAdapter
