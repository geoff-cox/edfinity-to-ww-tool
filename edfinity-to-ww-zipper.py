#!/usr/bin/env python3
"""
save_pg_tool.py — paste-friendly, Ctrl-C to finish, token-based PG splitter

Workflow:
1) Prompt for base filename; default "webwork-problems". Create unique "<base>/" (or "<base>-k/").
2) Prompt: "Paste ALL problems now. Press Ctrl-C when finished."
   - Reads input line-by-line via input(), so normal terminal pasting works.
   - Press Ctrl-C when done to stop capture (no auto-cleanup by design).
3) Splits the paste into problems by pairing DOCUMENT(); with the next ENDDOCUMENT();
   - Robust to comments after ENDDOCUMENT();, blank lines, and spacing variations.
4) Writes "<base>/<base>-n.pg" for n=1,2,... and zips the folder as "<base>.zip" (or "<base>-k>.zip").
"""

import os
import re
import sys
import shutil
from pathlib import Path
import string

# ---------- Filename safety ----------
ALLOWED_CHARS = set(string.ascii_letters + string.digits + " _.-")

def sanitize_basename(name: str) -> str:
    name = (name or "").strip()
    name = "".join(ch for ch in name if ch in ALLOWED_CHARS)
    name = " ".join(name.split())
    name = name.replace(" ", "-").strip(" .-")
    return name or "webwork-problems"

def unique_subfolder(root: Path, base: str) -> Path:
    p = root / base
    if not p.exists():
        return p
    k = 1
    while True:
        q = root / f"{base}-{k}"
        if not q.exists():
            return q
        k += 1

def unique_zip_path(root: Path, base: str) -> Path:
    z = root / f"{base}.zip"
    if not z.exists():
        return z
    k = 1
    while True:
        q = root / f"{base}-{k}.zip"
        if not q.exists():
            return q
        k += 1

def make_archive(folder: Path, zip_target: Path):
    base_no_ext = zip_target.with_suffix("")
    return shutil.make_archive(str(base_no_ext), "zip",
                               root_dir=str(folder.parent), base_dir=str(folder.name))

# ---------- Capture (line-based, paste-friendly) ----------
def capture_lines_until_ctrl_c() -> str:
    """
    Read lines using input() until Ctrl-C is pressed.
    Restores '\n' between lines so pasted text remains intact.
    """
    print("\nPaste ALL problems now. Press Ctrl-C when finished.\n")
    lines = []
    try:
        while True:
            line = input()               # no trailing newline
            lines.append(line + "\n")    # restore newline
    except KeyboardInterrupt:
        pass  # finish capture
    # Normalize newlines
    text = "".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    return text

# ---------- Token-based PG block extraction ----------
def extract_pg_blocks_tokenized(big_text: str):
    """
    Pair each DOCUMENT(); with the next ENDDOCUMENT(); and return a list of blocks.
    This ignores any comments/whitespace around markers and is robust to inline comments
    after ENDDOCUMENT();.
    """
    # Work on normalized text
    s = big_text

    # Find all marker positions in order
    tokens = [(m.start(), m.group()) for m in re.finditer(r'DOCUMENT\(\);|ENDDOCUMENT\(\);', s)]
    if not tokens:
        return []

    blocks = []
    level = 0
    current_start = None

    for pos, tok in tokens:
        if tok == 'DOCUMENT();':
            if level == 0:
                current_start = pos
            level += 1
        else:  # ENDDOCUMENT();
            if level > 0:
                level -= 1
                if level == 0 and current_start is not None:
                    # end position should include the ENDDOCUMENT(); token
                    end_pos = pos + len('ENDDOCUMENT();')
                    # Extend to the end of the line to include any trailing comment
                    # (up to, but not including, the next newline)
                    while end_pos < len(s) and s[end_pos] not in '\n':
                        end_pos += 1
                    block = s[current_start:end_pos]
                    # Ensure trailing newline for file neatness
                    if not block.endswith("\n"):
                        block += "\n"
                    blocks.append(block)
                    current_start = None
            else:
                # Unbalanced end; ignore and keep scanning
                pass

    return blocks

# ---------- Main ----------
def main():
    ROOT = Path.cwd()

    raw = input("Enter base filename (default: webwork-problems): ").strip()
    base = sanitize_basename(raw or "webwork-problems")

    pg_dir = "pg-folders/" + base
    pg_subfolder = unique_subfolder(ROOT, pg_dir)
    pg_subfolder.mkdir(parents=True, exist_ok=False)

    print(f'\n\nCreated folder: "{pg_dir}"\n')

    big_text = capture_lines_until_ctrl_c()

    print("\n\nCtrl-C Pressed. Processing zip-files...\n")

    if not big_text.strip():
        print("No input detected. Nothing to do.")
        return

    blocks = extract_pg_blocks_tokenized(big_text)
    if not blocks:
        print("No 'DOCUMENT(); ... ENDDOCUMENT();' blocks found. Aborting.")
        sys.exit(1)

    for i, block in enumerate(blocks, start=1):
        fname = f"{base}-{i}.pg"
        path = pg_subfolder / fname
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(block)
        print(f'Saved: "{path}"')
    
    zip_path = unique_zip_path(ROOT, base)
    make_archive(pg_subfolder, zip_path)
    print(f'\nCreated zip: "{zip_path}"')
    print("Done.")

if __name__ == "__main__":
    main()