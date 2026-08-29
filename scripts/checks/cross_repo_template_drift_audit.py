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
# 2026-08-15：weekly 跑在 host（cp950），而 ✅🔴⚠ 這些符號 cp950 編不出來。
# 崩潰是**路徑相依**的 —— 平常走 GREEN 分支沒事，偏偏在要報問題的那一刻崩掉，
# 而那時看到的是 UnicodeEncodeError 不是它本來要講的事。同 L49.8（.ps1 的 BOM）家族。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


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


#: 這些 repo 已被查證為「換成了別的機制」，不是「還沒跟進」。
#:
#: ⚠️ 2026-08-30：本稽核原本把「沒有我這 6 個檔」直接判 RED 並建議
#: 「install-template 補完」。而實查 `CK_lvrland_Webmap`：
#: **它有 43 支自己的檢核腳本**（41 py + 2 sh），只是不叫這 6 個名字。
#:
#: 形狀由 CK_AaaP 2026-08-30 提出（他們的 L73）：
#:   **工具能取得的事實是二元（有／沒有），而它輸出的是三元判斷
#:     （跟上了／落後了／不存在）。「落後了」是從「沒有」推論出來的，
#:     而那個推論沒有根據。**
#: 「沒有」至少四種成因：還沒跟進／**已經在我們之上加了東西**／
#: **換成了別的機制**／我們自己退步了。**只有第一種適用「補完」**。
#:
#: ⇒ 建議「補完」之前要先分類。未分類者一律 YELLOW（需要人看），不判 RED。
_ALTERNATIVE_MECHANISM = {
    "CK_lvrland_Webmap": "有 43 支自有檢核（41 py + 2 sh），機制不同名不代表沒有",
    "CK_PileMgmt": "有 12 支自有檢核 —— 原本判 RED-zero（0/6），"
                   "而 0/6 只代表它沒有我這 6 個**特定檔名**，不代表它沒有檢核",
}

#: 已歸檔／已遷移的 repo —— 它們的分數沒有意義
_ARCHIVED = {
    "CK_Showcase": "ADR-0020 Phase 2 已遷入 CK_AaaP/platform/services/，目錄留著是歷史",
}


def classify(present: int, total: int, stale_count: int, repo: str = "") -> str:
    """把覆蓋率轉成判定。

    ⚠️ **RED 的語意是「該補而沒補」，不是「不一樣」。** 分不出來的一律 YELLOW。
    """
    name = repo.strip("./\\").replace("../", "")
    if name in _ARCHIVED:
        return "⚪ ARCHIVED"
    if name in _ALTERNATIVE_MECHANISM:
        # 有自己的機制 —— 不是缺口，但仍值得每年看一次兩邊是否還等價
        return "🟡 ALT-MECH"
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
        verdict = classify(present, total, stale, tgt) if r["exists"] else "⚪ N/A"
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

    # 先把「換了別的機制／已歸檔」講清楚 —— 它們不是缺口
    noted = [(t, v) for t, v, _, _ in summary_rows if v in ("🟡 ALT-MECH", "⚪ ARCHIVED")]
    if noted:
        print("以下不是缺口（已查證，不需要 install-template）：")
        for t, v in noted:
            name = t.strip("./\\").replace("../", "")
            why = _ALTERNATIVE_MECHANISM.get(name) or _ARCHIVED.get(name, "")
            print(f"    {v}  {name}：{why}")
        print()

    if overall_issues:
        print(f"⚠ {len(overall_issues)} repo 覆蓋率偏低 —— **先分類，不要直接補完**：")
        for i in overall_issues:
            print(f"    - {i}")
        print()
        # ⚠️ 2026-08-30：原本這裡直接印「需要 install-template 補完」＋指令。
        # 而「沒有這 6 個檔」至少四種成因，**只有一種適用補完**：
        #   ① 還沒跟進  ② 已在我們之上加了東西  ③ 換成別的機制  ④ 我們自己退步了
        # 對 ②③ 執行 install-template 會**覆蓋掉它們正在運作的東西**，
        # 而終端會印「安裝完成」。（CK_AaaP 2026-08-30 在他們的 hook 安裝器上
        # 差一點做了這件事：兩個 repo 的 pre-push 分別是**擴充版**與**委派版**。）
        print("  先問：它是「還沒跟進」，還是「已經有等價或更好的東西」？")
        print("    · 看看對方的 scripts/checks/ 有幾支自己的檢核")
        print("    · 確認是①之後，再跑：")
        print("        bash scripts/install-template-to.sh ../<repo_name> \\")
        print("          --include=cross-file-ssot,fitness-tier,governance-dashboard,l4x-lessons")
        print("    · 若是②③，請寫進本檔的 `_ALTERNATIVE_MECHANISM` 並附理由")
        if strict:
            return 1
    else:
        print("✓ 沒有需要分類的覆蓋率缺口")
    return 0


if __name__ == "__main__":
    sys.exit(main())
