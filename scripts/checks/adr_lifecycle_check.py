#!/usr/bin/env python3
"""
ADR Lifecycle Check — 列出所有 ADR 並統計 active_count

規則（ADR-0029）：
  - active = proposed + accepted
  - archived / superseded / removed / rejected / deprecated = 非活躍
  - active_count 健康區間：≤ 15
  - 警戒線：> 20 觸發瘦身 sprint
  - 紅燈：> 25 必須開 session review

執行：
  python scripts/checks/adr_lifecycle_check.py
  python scripts/checks/adr_lifecycle_check.py --verbose
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADR_DIR = ROOT / "docs" / "adr"

STATUS_PATTERN = re.compile(
    r"^(?:\s*[-*>])?\s*\*\*(?:狀態|Status|status)\*\*\s*[:：]\s*"
    r"\*{0,2}`?([A-Za-z_]+)`?\*{0,2}",
    re.MULTILINE,
)

ACTIVE_STATES = {"proposed", "accepted"}
INACTIVE_STATES = {"archived", "superseded", "removed", "rejected", "deprecated"}


def extract_status(text: str) -> str:
    """抽取 ADR 頂部的狀態標籤"""
    # 讀前 30 行
    head = "\n".join(text.splitlines()[:30])
    match = STATUS_PATTERN.search(head)
    if not match:
        return "unknown"
    raw = match.group(1).strip().lower()
    # 取第一個單字（去 "superseded by ADR-..." 這種字尾）
    first = raw.split()[0] if raw else "unknown"
    return first


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    if not ADR_DIR.is_dir():
        print(f"[SKIP] ADR 目錄不存在: {ADR_DIR}")
        return 0

    counts: dict[str, int] = {}
    entries: list[tuple[str, str, Path]] = []  # (number, status, path)

    # 掃主目錄與 archived/ 子目錄
    for p in sorted(ADR_DIR.rglob("*.md")):
        name = p.name
        if name in ("README.md", "TEMPLATE.md"):
            continue
        match = re.match(r"^(\d{4})-", name)
        if not match:
            continue
        number = match.group(1)
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        # 若落在 archived/ 目錄，強制視為 archived
        if "archived" in p.parts:
            status = "archived"
        else:
            status = extract_status(text)

        counts[status] = counts.get(status, 0) + 1
        entries.append((number, status, p))

    active = sum(counts.get(s, 0) for s in ACTIVE_STATES)
    inactive = sum(counts.get(s, 0) for s in INACTIVE_STATES)
    unknown = counts.get("unknown", 0)
    total = sum(counts.values())

    print(f"ADR Lifecycle Report")
    print(f"====================")
    print(f"Active (proposed + accepted): {active}")
    print(f"Inactive (archived/superseded/removed/rejected/deprecated): {inactive}")
    if unknown:
        print(f"Unknown status: {unknown}")
    print(f"Total ADR files: {total}")
    print()

    # 狀態分佈
    for status in sorted(counts.keys()):
        print(f"  {status:15s}  {counts[status]}")
    print()

    # 健康度評估
    if active > 25:
        print("[RED] active_count > 25 — 必須開 session review")
        rc = 1
    elif active > 20:
        print("[YELLOW] active_count > 20 — 建議觸發瘦身 sprint")
        rc = 0
    elif active > 15:
        print("[GREEN-] active_count 略超 15（目標）— 持續觀察")
        rc = 0
    else:
        print("[GREEN] active_count 在健康區間（≤ 15）")
        rc = 0

    if verbose:
        print()
        print("Details:")
        for number, status, path in entries:
            rel = path.relative_to(ROOT).as_posix()
            marker = "*" if status in ACTIVE_STATES else " "
            print(f" {marker} ADR-{number}  [{status:12s}]  {rel}")

    return rc


if __name__ == "__main__":
    sys.exit(main())
