#!/usr/bin/env python3
"""Rename 96 Cyrillic-named vault files to Latin transliteration.
Preserves original Russian title in YAML frontmatter `title:` field
so vec/lex search still surfaces by Russian content, AND literal slug
get works via the new Latin path.

Usage:
  python3 tools/cyrillic_rename_session82.py [--apply]

Default: dry-run. --apply does git mv + frontmatter rewrite.
"""
import sys, re, subprocess
from pathlib import Path

VAULT = Path("/Users/madia/Documents/Projects/Nous AGaaS/Nous")
APPLY = "--apply" in sys.argv

# GOST 7.79-2000 system B (BGN/PCGN-like) — common Cyrillic→Latin map
RU_MAP = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch',
    'ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
    'А':'a','Б':'b','В':'v','Г':'g','Д':'d','Е':'e','Ё':'yo','Ж':'zh','З':'z',
    'И':'i','Й':'y','К':'k','Л':'l','М':'m','Н':'n','О':'o','П':'p','Р':'r',
    'С':'s','Т':'t','У':'u','Ф':'f','Х':'kh','Ц':'ts','Ч':'ch','Ш':'sh','Щ':'shch',
    'Ъ':'','Ы':'y','Ь':'','Э':'e','Ю':'yu','Я':'ya',
}

def transliterate(s):
    return ''.join(RU_MAP.get(c, c) for c in s)

def main():
    files = list(VAULT.glob('pages/**/*.md'))
    cyr_files = [f for f in files if re.search(r'[а-яА-Я]', f.name)]
    print(f"Found {len(cyr_files)} Cyrillic-named files")

    renames = []
    for f in cyr_files:
        new_stem = transliterate(f.stem)
        # Clean up: lowercase, collapse non-alnum to hyphens
        new_stem = re.sub(r'[^a-z0-9._-]+', '-', new_stem.lower()).strip('-')
        new_stem = re.sub(r'-+', '-', new_stem)
        new_path = f.parent / f"{new_stem}.md"
        if new_path == f or new_path.exists():
            print(f"SKIP (collision or noop): {f.name} → {new_path.name}")
            continue
        renames.append((f, new_path, f.stem))

    print(f"\n{len(renames)} renames pending")
    if not APPLY:
        print("\n--- sample 5 ---")
        for old, new, orig in renames[:5]:
            print(f"  {old.relative_to(VAULT)}")
            print(f"    → {new.relative_to(VAULT)}")
        print(f"\nDRY-RUN. Re-run with --apply to git mv all {len(renames)} + inject Russian title into frontmatter.")
        return

    applied = 0
    skipped = 0
    for old, new, orig_stem in renames:
        try:
            # 1. Read content
            content = old.read_text(encoding='utf-8')
            # 2. Inject original Russian stem into title if frontmatter present + title missing
            if content.startswith('---'):
                end = content.find('\n---', 4)
                if end > 0:
                    fm = content[:end]
                    body = content[end:]
                    # If no title: line, add one with Russian stem
                    if not re.search(r'^\s*title\s*:', fm, re.MULTILINE):
                        # add title line after first --- or after type:
                        fm = fm + f'\ntitle: "{orig_stem}"'
                        # Also add original_filename for traceability
                        fm = fm + f'\noriginal_filename: "{orig_stem}"'
                    else:
                        # ensure original_filename for traceability
                        if not re.search(r'^\s*original_filename\s*:', fm, re.MULTILINE):
                            fm = fm + f'\noriginal_filename: "{orig_stem}"'
                    content = fm + body
            else:
                # No frontmatter — prepend minimal
                content = f'---\ntype: tenant-note\ntitle: "{orig_stem}"\noriginal_filename: "{orig_stem}"\n---\n\n' + content

            # 3. git mv (use git mv to preserve history)
            r = subprocess.run(
                ['git', 'mv', str(old.relative_to(VAULT)), str(new.relative_to(VAULT))],
                cwd=VAULT, capture_output=True, text=True
            )
            if r.returncode != 0:
                # git mv failed — fallback to plain rename
                old.rename(new)

            # 4. Write new content (with Russian title preserved)
            new.write_text(content, encoding='utf-8')
            applied += 1
        except Exception as e:
            print(f"FAIL: {old.name} → {e}")
            skipped += 1

    print(f"\n=== APPLIED: {applied} renames, {skipped} failures ===")

if __name__ == '__main__':
    main()
