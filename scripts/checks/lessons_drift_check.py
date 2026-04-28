#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lessons Drift Check — 防 LESSONS_REGISTRY 成為 dead doc

L20 prevention 落實：
- parse docs/architecture/LESSONS_REGISTRY.md 抓所有 L## entries
- git log 過去 N 天 commit messages
- 找出含「fix/修/踩雷/淬鍊/regression」等修補字眼但未 `Refs: L##` 的
- 報「候選未登記」清單，提醒 owner 補 L## 或 commit refs

讓 LESSONS_REGISTRY 不重演 L01 dead doc 反模式（自身就是 L20 規劃的 SSOT）。

Usage:
    python scripts/checks/lessons_drift_check.py            # 掃過去 30 天
    python scripts/checks/lessons_drift_check.py --days 60  # 自訂時長
    python scripts/checks/lessons_drift_check.py --ci       # 有未登記 exit 1

Exit codes:
    0 — 所有 lesson-worthy commit 都已 ref L##
    1 — 有候選未登記（warning 模式仍 exit 0；--ci 才 exit 1）

Version: 1.0.0 (2026-04-28)
Refs: L20
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REGISTRY_PATH = Path("docs/architecture/LESSONS_REGISTRY.md")

# 觸發字眼 — commit 含這些就視為 lesson-worthy
LESSON_TRIGGERS = [
    "fix:",        # conventional commits fix
    "踩雷",
    "淬鍊",
    "regression",
    "根因",
    "斷鏈",
    "反模式",
    "anti-pattern",
    "incident",
]

# 已知白名單：明確不需 ref 的 commit pattern（如 typo 修正 / docs 修正本身）
WHITELIST_PATTERNS = [
    r"^docs:.*lessons.*registry",   # registry 自身的維護
    r"^docs:.*playbook",             # playbook 維護（已含 SOP refs）
    r"^docs:.*changelog",            # changelog 純記錄
    r"^chore:",                       # 雜務
    r"^style:",                       # 格式調整
    r"^test:",                        # 純測試新增
]


def parse_registry_lessons() -> set[str]:
    """parse LESSONS_REGISTRY.md 抓出所有 L## entries（如 L01, L02, ..., L21）"""
    if not REGISTRY_PATH.exists():
        print(f"❌ {REGISTRY_PATH} not found", file=sys.stderr)
        sys.exit(2)
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^## (L\d+)\b", text, re.MULTILINE))


def get_registry_creation_commit() -> str | None:
    """回 LESSONS_REGISTRY.md 第一次被 commit 的 SHA（用於 --since-registry 模式）"""
    try:
        out = subprocess.check_output(
            ["git", "log", "--diff-filter=A", "--format=%H", "--", str(REGISTRY_PATH)],
            text=True, encoding="utf-8",
        ).strip()
        # `--diff-filter=A` 找新增 commit，最後一行是最早（git log 倒序）
        lines = [ln for ln in out.split("\n") if ln.strip()]
        return lines[-1] if lines else None
    except subprocess.CalledProcessError:
        return None


def get_recent_commits(days: int, since_registry: bool = False) -> list[tuple[str, str]]:
    """git log 過去 N 天 commit (hash, message)，或 registry 建立後"""
    args = ["git", "log", "--pretty=format:%h%x09%s%x09%b%x1e"]
    if since_registry:
        creation_sha = get_registry_creation_commit()
        if creation_sha:
            args.append(f"{creation_sha}..HEAD")
        else:
            args.append(f"--since={days} days ago")
    else:
        args.append(f"--since={days} days ago")
    try:
        out = subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        print(f"❌ git log failed: {e}", file=sys.stderr)
        sys.exit(2)
    commits = []
    for entry in out.split("\x1e"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("\t", 2)
        if len(parts) >= 2:
            sha = parts[0]
            subject = parts[1]
            body = parts[2] if len(parts) > 2 else ""
            commits.append((sha, f"{subject}\n{body}"))
    return commits


def is_lesson_worthy(message: str) -> tuple[bool, list[str]]:
    """判斷 commit 是否屬 lesson-worthy（含修補字眼）"""
    matched = [t for t in LESSON_TRIGGERS if t.lower() in message.lower()]
    return bool(matched), matched


def is_whitelisted(subject: str) -> bool:
    """白名單判斷"""
    for pat in WHITELIST_PATTERNS:
        if re.match(pat, subject, re.IGNORECASE):
            return True
    return False


def has_lesson_ref(message: str) -> list[str]:
    """從 commit message 抓所有 Refs: L## refs"""
    return re.findall(r"Refs?:\s*((?:L\d+(?:\s*,\s*L\d+)*)+)", message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--days", type=int, default=30, help="掃過去 N 天 commit（預設 30）")
    parser.add_argument("--since-registry", action="store_true",
                        help="只掃 LESSONS_REGISTRY 建立後的 commit（避開歷史包袱，預設模式）")
    parser.add_argument("--all-history", action="store_true",
                        help="強制掃 --days 全範圍（含 registry 建立前的歷史）")
    parser.add_argument("--ci", action="store_true", help="有未登記即 exit 1")
    args = parser.parse_args()

    # 預設行為：since-registry（避免回填式 registry 將整個 git history 列為候選）
    use_since_registry = not args.all_history

    mode = "since registry creation" if use_since_registry else f"last {args.days} days"
    print(f"=== Lessons Drift Check ({mode}) ===\n")

    lessons = parse_registry_lessons()
    print(f"📚 Registry: {len(lessons)} lessons ({', '.join(sorted(lessons))})")

    commits = get_recent_commits(args.days, since_registry=use_since_registry)
    print(f"📜 Commits in last {args.days}d: {len(commits)}\n")

    candidates = []  # commit lesson-worthy 但無 Refs
    referenced = []  # commit 已正確 ref
    bad_refs = []    # commit Refs L## 但 L## 不存在

    for sha, message in commits:
        subject = message.split("\n", 1)[0]
        worthy, triggers = is_lesson_worthy(message)
        if not worthy:
            continue
        if is_whitelisted(subject):
            continue

        refs_groups = has_lesson_ref(message)
        if refs_groups:
            # 抓出所有 L##
            all_refs = []
            for grp in refs_groups:
                all_refs.extend(re.findall(r"L\d+", grp))
            valid = [r for r in all_refs if r in lessons]
            invalid = [r for r in all_refs if r not in lessons]
            referenced.append((sha, subject, valid))
            if invalid:
                bad_refs.append((sha, subject, invalid))
        else:
            candidates.append((sha, subject, triggers))

    # === Output ===
    print(f"✅ Lesson-worthy + has Refs: {len(referenced)}")
    print(f"⚠️  Lesson-worthy but NO Refs (candidate): {len(candidates)}")
    print(f"❌ Refs L## but not in registry (broken): {len(bad_refs)}")
    print()

    if candidates:
        print("候選未登記清單（建議補 LESSON 或 commit Refs）:")
        for sha, subject, triggers in candidates[:20]:
            print(f"  {sha} {subject[:70]}")
            print(f"        triggers: {triggers[:3]}")
        if len(candidates) > 20:
            print(f"  ... 另 {len(candidates) - 20} 筆")
        print()

    if bad_refs:
        print("Broken refs（commit 提到 L## 但 registry 無此 entry）:")
        for sha, subject, invalid in bad_refs:
            print(f"  {sha} {subject[:70]}  → broken: {invalid}")
        print()

    if not candidates and not bad_refs:
        print("🎉 所有 lesson-worthy commit 都已正確 ref L##，registry 健康")
        return 0

    if args.ci and (candidates or bad_refs):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
