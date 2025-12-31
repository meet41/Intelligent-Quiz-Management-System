#!/usr/bin/env python
"""
Repository comment cleanup utility.
- Targets: .py, .css, .js, .html, .htm
- Removes: commented-out code and large/obsolete comment blocks
- Preserves: Python docstrings, short helpful comments, license/copyright headers
- Modes: dry-run (default) prints summary; apply with --apply writes changes

Heuristics:
- Python: keep triple-quoted docstrings at module/class/def level; remove blocks of 3+ consecutive comment-only lines, and lone comment lines that look like commented-out code (contain tokens like 'def ', 'class ', 'import ', 'return', '=', ':{'). Keep TODO/FIXME.
- CSS/JS/HTML: remove /* ... */ and //... (JS) and <!-- ... --> if block length > 2 lines. Keep blocks containing 'license' or 'copyright'.

Usage:
  python tools/strip_comments.py [--apply]
"""
from __future__ import annotations
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PY_CODE_TOKENS = re.compile(r"\\b(def |class |import |from |return|if |for |while |try:|except |with |=|:\\s*$)")
KEEP_WORDS = re.compile(r"(license|copyright|@license|mit|apache|gpl|todo|fixme)", re.IGNORECASE)

EXTS = {".py", ".css", ".js", ".html", ".htm"}


def iter_files(root: Path):
    for p in root.rglob("*"):
        if p.is_dir():
            # skip virtualenvs and node_modules and migrations
            name = p.name.lower()
            if name in {"venv", ".venv", "node_modules", "dist", "build", "__pycache__"}: 
                continue
        else:
            if p.suffix.lower() in EXTS:
                yield p


def clean_python(text: str) -> str:
    lines = text.splitlines()
    out = []
    i = 0
    n = len(lines)
    # Track simple module docstring preservation
    in_triple = False
    triple_quote = None
    def is_comment_only(line: str) -> bool:
        s = line.lstrip()
        return s.startswith('#')

    while i < n:
        line = lines[i]
        s = line.lstrip()
        # preserve triple-quoted blocks verbatim
        if not in_triple and (s.startswith("\"\"\"") or s.startswith("'''")):
            in_triple = True
            triple_quote = s[:3]
            out.append(line)
            i += 1
            continue
        if in_triple:
            out.append(line)
            if s.endswith(triple_quote):
                in_triple = False
                triple_quote = None
            i += 1
            continue

        if is_comment_only(line):
            # gather consecutive comment block
            j = i
            block = []
            while j < n and is_comment_only(lines[j]):
                block.append(lines[j])
                j += 1
            block_text = "\n".join(block)
            if KEEP_WORDS.search(block_text):
                out.extend(block)
            else:
                # remove long blocks (3+ lines) or code-like single comments
                if len(block) >= 3:
                    pass  # drop block
                else:
                    # single comment line: drop if looks like commented-out code
                    if PY_CODE_TOKENS.search(block[0]):
                        pass
                    else:
                        out.extend(block)
            i = j
            continue
        else:
            out.append(line)
            i += 1
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def strip_block_comments(text: str, kind: str) -> str:
    original = text
    # CSS/JS block comments /* ... */
    if kind in {"css", "js"}:
        def repl(m):
            content = m.group(1)
            if KEEP_WORDS.search(content):
                return m.group(0)
            # remove only if multi-line or long
            if "\n" in content or len(content) > 80:
                return ""
            return m.group(0)
        text = re.sub(r"/\*(.*?)\*/", repl, text, flags=re.S)
        if kind == "js":
            # Remove // lines that are long or code-like
            def repl_line(m):
                content = m.group(1).strip()
                if KEEP_WORDS.search(content):
                    return m.group(0)
                if len(content) > 40 or re.search(r"[{}();=]", content):
                    return ""
                return m.group(0)
            text = re.sub(r"(^|\n)\s*//(.*)$", lambda m: ("\n" if m.group(1) else "") + repl_line(m), text, flags=re.M)
        return text
    # HTML comments <!-- ... -->
    if kind == "html":
        def repl(m):
            content = m.group(1)
            if KEEP_WORDS.search(content):
                return m.group(0)
            if content.count("\n") >= 2 or len(content) > 120:
                return ""
            return m.group(0)
        return re.sub(r"<!--(.*?)-->", repl, text, flags=re.S)
    return text


def clean_file(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    ext = path.suffix.lower()
    new = text
    if ext == ".py":
        new = clean_python(text)
    elif ext == ".css":
        new = strip_block_comments(text, "css")
    elif ext == ".js":
        new = strip_block_comments(text, "js")
    elif ext in {".html", ".htm"}:
        new = strip_block_comments(text, "html")
    return (new != text), new


def main(apply: bool = False):
    changed = []
    removed_lines = 0
    for f in iter_files(ROOT):
        try:
            did_change, new = clean_file(f)
        except Exception as e:
            print(f"Skip {f}: {e}")
            continue
        if did_change:
            if apply:
                f.write_text(new, encoding="utf-8")
            # estimate removed lines by diffing lengths
            try:
                old_lines = len(f.read_text(encoding="utf-8", errors="ignore").splitlines())
            except Exception:
                old_lines = 0
            new_lines = len(new.splitlines())
            delta = max(0, old_lines - new_lines)
            removed_lines += delta
            changed.append((f, delta))
    print(f"Changed files: {len(changed)} | Estimated comment lines removed: {removed_lines}")
    for f, delta in sorted(changed)[:50]:
        print(f" - {f.relative_to(ROOT)} (-{delta} lines)")
    if len(changed) > 50:
        print(f" ... and {len(changed)-50} more files")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    main(apply)
