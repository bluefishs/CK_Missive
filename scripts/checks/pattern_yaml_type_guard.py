#!/usr/bin/env python3
"""
Pattern YAML Type Guard — 掃 memory/patterns/failures/proposals 等 YAML frontmatter

背景：2026-04-24 事故
  wiki/memory/patterns/pattern-8692128536.md 的 `template_hash: 8692128536`
  被 _parse_frontmatter 誤推為 int，混入 str hash 造成 sorted() TypeError
  → `/api/ai/memory/nebula/graph` 500 Internal Server Error（高頻）。

規則：
  id-like 欄位（template_hash / pattern_id / session_id 等）若為純數字，
  必須加雙引號 `"..."` 防止 YAML type coercion。

被掃目錄：
  wiki/memory/patterns/
  wiki/memory/failures/
  wiki/memory/proposals/
  wiki/memory/evolutions/ (只掃 non-*-W*.md 如有)

--fix 會自動加雙引號。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIKI_DIR = ROOT / "wiki" / "memory"

# ID-like 欄位清單（純數字時必須加引號）
ID_LIKE_FIELDS = {
    "template_hash",
    "pattern_id",
    "failure_id",
    "proposal_id",
    "crystal_id",
    "session_id",
    "request_id",
    "user_id",  # 雖然 DB 是 int，memory layer 存 str 為安全
    "trace_id",
}

# 掃哪些目錄
SCAN_DIRS = [
    WIKI_DIR / "patterns",
    WIKI_DIR / "failures",
    WIKI_DIR / "proposals",
    WIKI_DIR / "evolutions",
]


FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
LINE_PATTERN = re.compile(r"^([a-zA-Z_][\w]*?):\s*(.+?)\s*$")


def check_file(path: Path, fix: bool = False) -> list[tuple[int, str]]:
    """回傳 (line_no, message) 清單；fix=True 會即時修改檔案"""
    issues: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return [(0, f"讀檔失敗: {e}")]

    fm_match = FM_PATTERN.match(text)
    if not fm_match:
        return issues  # 沒 frontmatter，跳過

    fm = fm_match.group(1)
    modified = False
    new_fm_lines: list[str] = []

    for i, line in enumerate(fm.splitlines(), start=2):  # +2 因為 --- 佔第 1 行
        m = LINE_PATTERN.match(line)
        if not m:
            new_fm_lines.append(line)
            continue

        key, val = m.group(1), m.group(2).strip()
        if key in ID_LIKE_FIELDS and val.isdigit():
            issues.append((
                i,
                f"{key}: {val}（純數字未加引號，會被 YAML parse 為 int 造成型別混合）",
            ))
            if fix:
                new_fm_lines.append(f'{key}: "{val}"')
                modified = True
                continue
        new_fm_lines.append(line)

    if fix and modified:
        new_fm = "\n".join(new_fm_lines)
        new_text = FM_PATTERN.sub(f"---\n{new_fm}\n---", text, count=1)
        path.write_text(new_text, encoding="utf-8")

    return issues


def main() -> int:
    fix = "--fix" in sys.argv

    if not WIKI_DIR.exists():
        print(f"wiki/memory dir not found: {WIKI_DIR}")
        return 0

    total_issues = 0
    fixed_files = 0

    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for md in d.rglob("*.md"):
            if md.name.startswith("."):
                continue
            issues = check_file(md, fix=fix)
            if issues:
                rel = md.relative_to(ROOT)
                for lineno, msg in issues:
                    print(f"{rel}:{lineno}: {msg}")
                total_issues += len(issues)
                if fix:
                    fixed_files += 1

    if total_issues:
        if fix:
            print(f"\n[FIX] 已修正 {fixed_files} 檔 / {total_issues} 處")
            return 0
        print(f"\n[FAIL] 發現 {total_issues} 處 id-like 純數字未加引號；")
        print("      執行 `python scripts/checks/pattern_yaml_type_guard.py --fix` 自動修正")
        return 1

    print("[OK] pattern YAML id-like 欄位型別安全")
    return 0


if __name__ == "__main__":
    sys.exit(main())
