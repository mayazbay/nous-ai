import subprocess
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "tools" / "check_design_contract.py"
DESIGN = REPO_ROOT / "DESIGN.md"


def test_design_contract_passes_for_repo_design_md():
    result = subprocess.run(
        ["python3", str(CHECKER), str(DESIGN)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "OK: DESIGN.md contract valid" in result.stdout


def test_design_contract_rejects_negative_letter_spacing(tmp_path):
    bad_design = tmp_path / "DESIGN.md"
    bad_design.write_text(
        textwrap.dedent(
            """\
            ---
            version: alpha
            name: Satory / Nous Operator System
            colors:
              primary: "#183A37"
              secondary: "#2F5E8E"
              tertiary: "#C97718"
              neutral: "#F6F8F7"
              surface: "#FFFFFF"
              surface-muted: "#EDF2F0"
              on-surface: "#16201F"
              on-muted: "#52615E"
              border: "#CBD7D3"
              success: "#147A55"
              warning: "#B66A00"
              danger: "#B42318"
              info: "#2563EB"
            typography:
              headline-lg:
                letterSpacing: -0.02em
              headline-md:
                letterSpacing: 0em
              body-md:
                letterSpacing: 0em
              body-sm:
                letterSpacing: 0em
              label-sm:
                letterSpacing: 0em
            rounded:
              sm: 4px
              md: 8px
              lg: 8px
            ---

            # Satory / Nous DESIGN.md

            ## Overview
            Operator-facing Satory copy defaults to Russian.
            satory-nextjs-g2grt4mi8-mayazbay-4383s-projects.vercel.app
            index-BSiWURaO.js
            python3 tools/check_design_contract.py
            @google/design.md lint DESIGN.md

            ## Colors
            Text.
            ## Typography
            Text.
            ## Layout
            Text.
            ## Elevation & Depth
            Text.
            ## Shapes
            Text.
            ## Components
            Text.
            ## Do's and Don'ts
            Text.
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["python3", str(CHECKER), str(bad_design)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "negative letterSpacing is banned" in result.stderr
