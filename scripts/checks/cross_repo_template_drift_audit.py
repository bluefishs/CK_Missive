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
#:
#: ⚠️ **豁免的理由必須是會被驗證的斷言，不是一句話。**
#:
#: 首版我寫「有 43 支自有檢核」—— 那句話**今天為真，一年後可能不為真**
#: （對方可能刪光了），而它不會有任何東西提醒我。
#: 對照 CK_AaaP 的指紋白名單：md5 一變就自動失效。我這個沒有等價機制。
#:
#: ⇒ 改為 `(最少幾支自有檢核, 說明)`。**每次執行都重數**，
#:   低於門檻就撤銷豁免、退回需要人看的狀態 ——
#:   同他們說的「把豁免當待驗斷言而不是開關」。
_ALTERNATIVE_MECHANISM = {
    # repo: (min_own_checks, why)
    "CK_lvrland_Webmap": (30, "2026-08-30 實測 43 支自有檢核（41 py + 2 sh）；"
                              "機制不同名不代表沒有"),
    "CK_PileMgmt": (8, "2026-08-30 實測 12 支自有檢核 —— 原本判 RED-zero（0/6），"
                       "而 0/6 只代表它沒有我這 6 個**特定檔名**"),
}

#: 已歸檔／已遷移的 repo —— 它們的分數沒有意義。
#: 這一份的斷言可查證的形式是「**遷移目的地存在**」。
_ARCHIVED = {
    # repo: (遷移目的地相對路徑, why)
    "CK_Showcase": ("../CK_AaaP/platform/services",
                    "ADR-0020 Phase 2 已遷入 CK_AaaP/platform/services/，目錄留著是歷史"),
}


def _own_check_count(repo_dir: Path) -> int:
    """數對方自己有幾支檢核腳本 —— 豁免斷言的可查證形式。"""
    d = repo_dir / "scripts" / "checks"
    if not d.is_dir():
        return 0
    return len(list(d.glob("*.py"))) + len(list(d.glob("*.sh")))


def _exemption_still_valid(name: str, repo_dir: Path) -> tuple[bool, str]:
    """豁免現在還成立嗎？回傳 (是否成立, 說明)。

    ⚠️ 這一支存在的理由：**沒有到期日的豁免會變成永久的盲點。**
    """
    if name in _ARCHIVED:
        dest, why = _ARCHIVED[name]
        ok = (repo_dir.parent / dest.replace("../", "")).exists() or Path(dest).exists()
        return ok, (why if ok else f"{why} —— ⚠️ **但遷移目的地 `{dest}` 不存在**，豁免不再成立")
    if name in _ALTERNATIVE_MECHANISM:
        floor, why = _ALTERNATIVE_MECHANISM[name]
        n = _own_check_count(repo_dir)
        ok = n >= floor
        return ok, (f"{why}（現在 {n} 支，門檻 {floor}）" if ok
                    else f"{why} —— ⚠️ **現在只剩 {n} 支（門檻 {floor}）**，豁免不再成立")
    return False, ""


def _repo_dir(name: str) -> Path:
    """repo 名 → 實際目錄。

    ⚠️ 2026-08-30：首版把 `TARGETS` 裡的 repo **名字**直接當路徑用
    （`Path(repo)/"scripts"/"checks"`）⇒ 相對於 cwd 而不是 monorepo
    ⇒ 數到 0 支 ⇒ **兩個豁免當場被判失效，而實際有 43 與 12 支**。
    正是本檔在修的那個病的鏡像：**判準對錯了對象**。
    """
    return ROOT.parent / name.strip("./\\").replace("../", "")


def classify(present: int, total: int, stale_count: int, repo: str = "") -> str:
    """把覆蓋率轉成判定。

    ⚠️ **RED 的語意是「該補而沒補」，不是「不一樣」。** 分不出來的一律 YELLOW。
    """
    name = repo.strip("./\\").replace("../", "")
    if name in _ARCHIVED or name in _ALTERNATIVE_MECHANISM:
        # ⚠️ **每次執行都重驗豁免的斷言** —— 不成立就撤銷豁免，
        # 退回一般判定（該紅就紅）。沒有到期日的豁免會變成永久盲點。
        still_ok, _ = _exemption_still_valid(name, _repo_dir(name))
        if still_ok:
            return "⚪ ARCHIVED" if name in _ARCHIVED else "🟡 ALT-MECH"
        # 落到下面的一般判定 —— 並由輸出段說明豁免為何失效
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
        print("以下不是缺口（豁免斷言**本次執行已重驗**，不需要 install-template）：")
        for t, v in noted:
            name = t.strip("./\\").replace("../", "")
            _, why = _exemption_still_valid(name, _repo_dir(name))
            print(f"    {v}  {name}：{why}")
        print()

    # 豁免登記著、但斷言已不成立的 —— 那比「沒有豁免」更該說出來
    revoked = [
        (t.strip("./\\").replace("../", ""), _exemption_still_valid(
            t.strip("./\\").replace("../", ""), _repo_dir(t))[1])
        for t, v, _, _ in summary_rows
        if v not in ("🟡 ALT-MECH", "⚪ ARCHIVED", "⚪ N/A")
        and t.strip("./\\").replace("../", "") in (_ALTERNATIVE_MECHANISM | _ARCHIVED)
    ]
    if revoked:
        print("⚠ **豁免已失效**（登記著，但斷言重驗不通過）：")
        for name, why in revoked:
            print(f"    {name}：{why}")
        print("    ⇒ 要嘛更新 `_ALTERNATIVE_MECHANISM` 的門檻與理由，"
              "要嘛承認它現在真的是缺口。")
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
