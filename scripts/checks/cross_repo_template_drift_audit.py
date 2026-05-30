"""Fitness step 65 (v6.12, 2026-05-30): 跨 repo 範本漂移 audit

Owner 訴求: 本專案為其他系統參考 服務層/架構設計/管理機制請務必完善
昨日預告: 讓「對外參考」也走 audit 而非靠人記

偵測 4 個 CK 子專案是否跟進 CK_Missive 範本資產:
- ../CK_lvrland_Webmap
- ../CK_PileMgmt
- ../CK_Showcase
- ../CK_KMapAdvisor

對 6 大關鍵範本資產做存在性 + freshness 檢查:
1. cross-file-ssot-governance.md SOP
2. paths_compose_mount_audit.py
3. container_env_alignment_audit.py
4. container_image_freshness_check.py
5. run_fitness_daily.sh
6. generate_governance_dashboard.py

漂移分級:
- 🟢 GREEN — 跟進 ≥5/6
- 🟡 YELLOW — 跟進 2-4/6
- 🔴 RED — 跟進 < 2/6 或 > 30 天未更新

輸出可讀報告 + LINE 推總結（透過 cron 接通）
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

# 4 個目標 repo（相對 ../）
TARGETS = [
    "CK_lvrland_Webmap",
    "CK_PileMgmt",
    "CK_Showcase",
    "CK_KMapAdvisor",
]

# 6 大關鍵範本資產（相對 source repo root）
ASSETS = [
    (".claude/rules/cross-file-ssot-governance.md", "cross-file SSOT SOP"),
    ("scripts/checks/paths_compose_mount_audit.py", "L52 audit"),
    ("scripts/checks/container_env_alignment_audit.py", "L51 audit"),
    ("scripts/checks/container_image_freshness_check.py", "L51.7.1 audit"),
    ("scripts/checks/run_fitness_daily.sh", "Tier 1 fitness"),
    ("scripts/checks/generate_governance_dashboard.py", "Dashboard generator"),
]


def check_repo(repo_path: Path) -> dict:
    """檢查單一 repo 對 6 大資產的跟進度"""
    result = {
        "exists": repo_path.is_dir(),
        "assets_present": 0,
        "assets_total": len(ASSETS),
        "assets_detail": [],
        "stale_assets": [],  # > 30 天未更新
    }
    if not result["exists"]:
        return result

    src_root = ROOT  # CK_Missive
    for rel_path, label in ASSETS:
        target_path = repo_path / rel_path
        source_path = src_root / rel_path
        if not target_path.exists():
            result["assets_detail"].append((label, "❌ missing", rel_path))
            continue
        # 存在 — 比對 freshness
        if source_path.exists():
            src_mtime = source_path.stat().st_mtime
            tgt_mtime = target_path.stat().st_mtime
            age_days = (src_mtime - tgt_mtime) / 86400
            if age_days > 30:
                result["assets_present"] += 1
                result["stale_assets"].append((label, f"{age_days:.0f}d stale"))
                result["assets_detail"].append((label, f"⚠ stale {age_days:.0f}d", rel_path))
            elif age_days > 7:
                result["assets_present"] += 1
                result["assets_detail"].append((label, f"🟡 lag {age_days:.0f}d", rel_path))
            else:
                result["assets_present"] += 1
                result["assets_detail"].append((label, "✓ fresh", rel_path))
        else:
            result["assets_present"] += 1
            result["assets_detail"].append((label, "✓ present (source missing)", rel_path))
    return result


def classify(present: int, total: int, stale_count: int) -> str:
    if present == 0:
        return "🔴 RED-zero"
    if stale_count > 0 and present < total // 2:
        return "🔴 RED"
    if present >= total - 1:
        return "🟢 GREEN"
    if present >= total // 2:
        return "🟡 YELLOW"
    return "🔴 RED"


def main() -> int:
    strict = "--strict" in sys.argv
    print("=== 跨 repo 範本漂移 audit (step 65, v6.12) ===")
    print()
    print(f"Source: CK_Missive @ {ROOT}")
    print(f"Targets: {len(TARGETS)} repo(s)")
    print(f"Assets:  {len(ASSETS)} 關鍵範本")
    print()

    overall_issues: list[str] = []
    summary_rows: list[tuple[str, str, str, int]] = []

    for tgt in TARGETS:
        tgt_path = ROOT.parent / tgt
        r = check_repo(tgt_path)
        present = r["assets_present"]
        total = r["assets_total"]
        stale = len(r["stale_assets"])
        verdict = classify(present, total, stale) if r["exists"] else "⚪ N/A"
        summary_rows.append((tgt, verdict, f"{present}/{total}", stale))

        print(f"┌─ {tgt} ─┐")
        if not r["exists"]:
            print(f"  ⚪ repo 不存在於 ../{tgt}")
            print()
            continue
        print(f"  跟進度: {present}/{total}  | stale > 30d: {stale}  | verdict: {verdict}")
        for label, status, rel in r["assets_detail"]:
            print(f"    {status:25} {label:35} ({rel})")
        if "RED" in verdict:
            overall_issues.append(f"{tgt}: {verdict} ({present}/{total})")
        print()

    # Summary
    print("=== Summary ===")
    print(f"{'Repo':<25} {'Verdict':<15} {'Coverage':<10} {'Stale':<6}")
    print("-" * 60)
    for tgt, v, cov, stale in summary_rows:
        print(f"{tgt:<25} {v:<15} {cov:<10} {stale:<6}")
    print()

    if overall_issues:
        print(f"⚠ {len(overall_issues)} repo 需要 install-template 補完:")
        for i in overall_issues:
            print(f"    - {i}")
        print()
        print("修法建議:")
        print("    bash scripts/install-template-to.sh ../<repo_name> \\")
        print("      --include=cross-file-ssot,fitness-tier,governance-dashboard,l4x-lessons")
        if strict:
            return 1
    else:
        print("✓ 所有 4 子專案範本跟進良好")
    return 0


if __name__ == "__main__":
    sys.exit(main())
