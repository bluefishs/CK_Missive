"""Fitness step 66 (v6.12, 2026-05-30): 跨 repo 已套用但未 commit staging 偵測

承接 step 65 (cross_repo_template_drift_audit) 揭發 → install-template 套用 → 但若子專案
owner 沒 commit，下次 git pull 會覆蓋或 conflict。

偵測 4 子專案是否有 install-template 後遺留 staging changes:
- 若 git status --porcelain 非空 → 待 commit
- 列出影響檔數量供 owner 知會子專案 owner

設計理念: 套用 ≠ 落實。GREEN audit 不代表已生效。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    "CK_lvrland_Webmap",
    "CK_PileMgmt",
    "CK_Showcase",
    "CK_KMapAdvisor",
]


def git_status_count(repo_path: Path) -> tuple[int, list[str]]:
    """回 (待 commit 檔數, 樣本檔名前 5)"""
    if not repo_path.is_dir() or not (repo_path / ".git").is_dir():
        return -1, []
    try:
        r = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            capture_output=True, text=True, timeout=8,
        )
        if r.returncode != 0:
            return -1, []
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        sample = [l[3:][:80] for l in lines[:5]]
        return len(lines), sample
    except Exception:
        return -1, []


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== 跨 repo uncommitted staging audit (step 66, v6.12) ===")
    print()
    print("套用 ≠ 落實: install-template 後若 owner 不 commit, 下次 pull 覆蓋風險")
    print()

    issues: list[tuple[str, int]] = []
    for tgt in TARGETS:
        tgt_path = ROOT.parent / tgt
        cnt, sample = git_status_count(tgt_path)
        if cnt < 0:
            print(f"⚪ {tgt}: 不存在 / 非 git repo")
            continue
        if cnt == 0:
            print(f"🟢 {tgt}: 0 staging — 全 committed ✓")
        else:
            print(f"🟡 {tgt}: {cnt} 未 commit (套用後遺留)")
            for s in sample:
                print(f"      {s}")
            issues.append((tgt, cnt))
        print()

    if not issues:
        print("✓ 所有 4 子專案無 uncommitted changes")
        return 0

    print(f"⚠ {len(issues)} repo 有待 commit changes:")
    for tgt, cnt in issues:
        print(f"    - {tgt}: {cnt} 檔")
    print()
    print("建議 owner action:")
    print("  for r in CK_lvrland_Webmap CK_PileMgmt CK_Showcase CK_KMapAdvisor; do")
    print('    cd ../$r')
    print('    git add scripts/checks/ .claude/rules/ wiki/memory/lessons/ docs/architecture/')
    print('    git commit -m "chore: install v6.12 governance template from CK_Missive"')
    print("    cd -")
    print("  done")
    if strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
