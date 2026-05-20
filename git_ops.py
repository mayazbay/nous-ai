"""Git operations for agent code execution."""

import subprocess
import os
from config import CODEBASE_PATH


def run_git(args: list[str], cwd: str = None) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    cwd = cwd or os.path.abspath(CODEBASE_PATH)
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def init_repo() -> str:
    """Initialize git repo in codebase if not exists."""
    cwd = os.path.abspath(CODEBASE_PATH)
    if not os.path.isdir(os.path.join(cwd, ".git")):
        run_git(["init"], cwd)
        run_git(["add", "-A"], cwd)
        run_git(["commit", "-m", "Initial codebase import"], cwd)
    return "Git repo ready"


def create_branch(task_id: int, name: str) -> str:
    """Create a new branch for a task."""
    branch = f"task/{task_id}-{name}"
    code, out, err = run_git(["checkout", "-b", branch])
    if code != 0:
        run_git(["checkout", branch])
    return branch


def get_current_branch() -> str:
    """Get current branch name."""
    _, out, _ = run_git(["branch", "--show-current"])
    return out


def commit_changes(message: str) -> str:
    """Stage all changes and commit."""
    run_git(["add", "-A"])
    code, out, err = run_git(["commit", "-m", message])
    if code != 0 and "nothing to commit" in (err + out):
        return "nothing to commit"
    return out or err


def get_diff(base: str = "main") -> str:
    """Get diff between current branch and base."""
    current = get_current_branch()
    if not current or current == base:
        return "On main branch, no diff"
    _, out, _ = run_git(["diff", f"{base}..{current}", "--stat"])
    _, full, _ = run_git(["diff", f"{base}..{current}"])
    if len(full) > 3000:
        full = full[:3000] + "\n... (truncated)"
    return f"Stats:\n{out}\n\nDiff:\n{full}"


def merge_to_main(branch: str) -> str:
    """Merge branch to main."""
    run_git(["checkout", "main"])
    code, out, err = run_git(["merge", branch])
    if code != 0:
        return f"Merge failed: {err}"
    run_git(["branch", "-d", branch])
    return f"Merged {branch} to main"


def revert_branch_changes() -> str:
    """Revert all uncommitted changes on current branch and switch to main."""
    current = get_current_branch()
    if current and current != "main" and current != "master":
        run_git(["checkout", "--", "."])  # Discard all changes
        run_git(["clean", "-fd"])  # Remove untracked files
        run_git(["checkout", "main"])
        run_git(["branch", "-D", current])  # Delete the failed branch
        return f"Reverted and deleted branch {current}"
    return "Already on main, nothing to revert"


def rollback_last_merge() -> str:
    """Revert the last merge commit on main. Use if post-merge tests fail."""
    current = get_current_branch()
    if current != "main":
        return "Not on main, cannot rollback"

    # Check if last commit was a merge
    _, log, _ = run_git(["log", "--oneline", "-1"])

    # Revert the last commit (creates a new revert commit, doesn't destroy history)
    code, out, err = run_git(["revert", "--no-edit", "HEAD"])
    if code != 0:
        return f"Rollback failed: {err}"
    return f"Rolled back: {log}. New revert commit created."


def checkout_main() -> str:
    """Switch back to main branch."""
    code, out, err = run_git(["checkout", "main"])
    if code != 0:
        # If main doesn't exist yet, create it
        code2, _, _ = run_git(["branch", "-M", "main"])
    return "On main"
