# -*- coding: utf-8 -*-
"""文件宣稱數字納管 —— 標記制（2026-08-04）

## 為何需要這支

本專案的文件裡散落大量「宣稱的數字」：fitness 幾步、producer 幾個、UI 檢核幾條。
這些數字**寫下來的那一刻就開始漂移**，而既有的 `doc_reference_integrity_audit`
只驗「引用的路徑還在不在」，不驗「宣稱的數字還對不對」。

08-04 實際踩到：頂層 `CLAUDE.md` 宣稱「182 ADRs / 7 repo」，實際 185/8。
它是被跨 repo 的 pre-push 閘門**偶然**擋下才發現的 —— 而那道閘門一擋住，
整個 portfolio 的 push 就停了數週（見當日覆盤）。沒有人在主動問這件事。

## 作法（借自 CK_FacilityDev `tools/check_docs.py` S-29）

標記制：**行首**有 `<!--baseline:<key>-->` 的行才納管，其宣稱的數字必須等於
該 key 的實際值。沒標的行（歷史紀錄、覆盤段落、CHANGELOG 舊節）一律不碰 ——
逼人改歷史只會讓大家不敢寫數字。

CK_FacilityDev 已經踩過並記下兩個取捨，這裡直接沿用，不重踩：
  1. 用 HTML 註解當標記，**不要用中文字**（如「現況基線」）——
     行文只要提到那四個字就會誤觸。
  2. **只認行首**，否則「說明本機制的那份文件」會被自己抓到。

## 新增一個 key 的作法

在 `RESOLVERS` 加一筆：key → 回傳整數的函式。解析器必須讀**實際來源**
（registry / config / 目錄），不得再讀另一份文件 —— 那只是把漂移換個地方放。

用法：
    python scripts/checks/doc_baseline_claim_audit.py

退出碼（三態，**必須與印出的 Status 一致**）：
    0 = GREEN  所有納管宣稱與實際相符（或目前沒有任何行標記納管）
    1 = YELLOW 有標記但無法判定（未驗完，不等於通過）
    2 = RED    有數字漂移，或掃到 0 份文件（SCAN_GLOBS/ROOT 錯，不是「全部正確」）

⚠️ 2026-08-07 之前這裡寫的是「1 有漂移（--ci）」，而漂移在原生模式下實際回 0 ——
`run_fitness_weekly.sh` **一律不傳旗標**、依原生三態判斷，於是這一支印著 [RED]
卻被 runner 收成 GREEN：**管理文件數字的檢核，自己是假綠**。已改為退出碼與印出
狀態一致；`--ci` 因此不再影響任何行為，已移除（留著會讓人以為它有作用＝L01）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # L49.8：host 為 cp950
except Exception:
    pass

# parents[2] 才是 repo 根（本檔在 scripts/checks/）——初版寫 parents[1] 落在 scripts/，
# 於是掃到 0 份文件卻印 INFO。0 份不是「都對」，是根本沒掃到（標準 §3 假綠家族）。
ROOT = Path(__file__).resolve().parents[2]
MARK_RE = re.compile(r"^<!--baseline:([a-z0-9_]+)-->")
NUM_RE = re.compile(r"\d+")

# 掃描範圍：治理文件與專案說明。刻意不掃 wiki/（那是產出，不是宣稱）。
SCAN_GLOBS = ["CLAUDE.md", "README.md", "docs/architecture/*.md", "docs/runbooks/*.md"]


def _producer_count() -> int:
    d = json.loads((ROOT / "backend" / "config" / "producer_outcome_registry.json")
                   .read_text(encoding="utf-8"))
    return len(d["producers"])


def _ui_flow_count() -> int:
    d = json.loads((ROOT / "selfaudit.config.json").read_text(encoding="utf-8"))
    return len(d["flows"])


def _fitness_step_count() -> int:
    """主 fitness runner 的步數 —— 讀腳本裡的 [N/總數] 標頭宣告。"""
    txt = (ROOT / "scripts" / "checks" / "run_fitness.sh").read_text(encoding="utf-8", errors="ignore")
    m = re.findall(r"/(\d+)\]", txt)
    if not m:
        raise ValueError("run_fitness.sh 找不到 [N/總數] 標頭")
    return max(int(x) for x in m)


def _count_run_steps(script: str) -> int:
    """數 run_step 呼叫數。

    ⚠️ 必須容許**縮排** —— 初版用 `^run_step`，漏掉包在條件式裡的三步，
    daily 因此被算成 6（實際 9）。而那個 6 又被寫進文件、被本稽核判為一致 ——
    **錯的數字被檢查背書**，比沒有檢查更糟。
    """
    txt = (ROOT / "scripts" / "checks" / script).read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r'^[ 	]*run_step\s+"', txt, re.MULTILINE))


def _weekly_step_count() -> int:
    """weekly runner 的步數 —— 數 run_step 呼叫數，不用最大編號。

    編號是**不連續**的（23 之後直接跳 26）—— 用 max 會把「編號」當成「數量」，
    正是這支稽核要抓的那種宣稱與實際不符。
    """
    return _count_run_steps("run_fitness_weekly.sh")


def _daily_step_count() -> int:
    return _count_run_steps("run_fitness_daily.sh")


def _selfaudit_repo_count() -> int:
    """已導入瀏覽器自我走查的 repo 數（含本 repo）。

    這個數字一直用人工在文件裡寫「3/6」，而它會隨每次導入而變 ——
    典型的「寫完就開始漂」的宣稱。

    須以 `project` 去重：走查支援「集中執行、目標專案零足跡」模式
    （設定檔放在目標 repo 外、用 repo_root 指回去），所以磁碟上會有兩份設定
    指向同一個專案。直接數檔案會得到 4，實際只有 3 個專案 ——
    這支稽核自己產出假數字就沒有立場管別人。
    """
    projects = set()
    for cfg in ROOT.parent.glob("*/selfaudit.config.json"):
        try:
            projects.add(json.loads(cfg.read_text(encoding="utf-8")).get("project")
                         or cfg.parent.name)
        except Exception:
            projects.add(cfg.parent.name)
    return len(projects)


def _producer_signal_count() -> int:
    sys.path.insert(0, str(ROOT / "scripts" / "checks"))
    from producer_registry import KNOWN_SIGNALS  # noqa: PLC0415
    return len(KNOWN_SIGNALS)


def _tracked_job_count() -> int:
    txt = (ROOT / "backend" / "app" / "core" / "scheduler.py").read_text(
        encoding="utf-8", errors="ignore")
    return len(re.findall(r'@tracked_job\(', txt))


RESOLVERS = {
    "producers": _producer_count,
    "ui_flows": _ui_flow_count,
    "fitness_steps": _fitness_step_count,
    # 2026-08-05 擴大納管。判準不變：**只收可機器驗證的數字**。
    # 刻意不納「這份文件的結論是否還成立」—— 那需要語意判斷，
    # 會產出無法採信的清單（同 08-03 已立的判準）。
    "weekly_steps": _weekly_step_count,
    "daily_steps": _daily_step_count,
    "selfaudit_repos": _selfaudit_repo_count,
    "producer_signals": _producer_signal_count,
    "tracked_jobs": _tracked_job_count,
}


def main() -> int:
    # 不接受任何旗標：唯一呼叫端（run_fitness_weekly.sh step 26）不傳，
    # 而原本的 --ci 在退出碼改為三態後已不影響任何行為 —— 留著會讓人以為它有作用。
    argparse.ArgumentParser().parse_args()

    print("=" * 66)
    print("文件宣稱數字納管（標記制 `<!--baseline:key-->`）")
    print("=" * 66)

    files: list[Path] = []
    for g in SCAN_GLOBS:
        files.extend(sorted(ROOT.glob(g)))

    claims, drift, unresolved = 0, [], []
    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            m = MARK_RE.match(line)
            if not m:
                continue
            claims += 1
            key = m.group(1)
            resolver = RESOLVERS.get(key)
            rel = f.relative_to(ROOT)
            if not resolver:
                unresolved.append(f"{rel}:{i} 未知的 key「{key}」（可用：{', '.join(RESOLVERS)}）")
                continue
            nums = NUM_RE.findall(line[m.end():])
            if not nums:
                unresolved.append(f"{rel}:{i} 標記了但整行沒有數字")
                continue
            try:
                actual = resolver()
            except Exception as e:  # noqa: BLE001
                unresolved.append(f"{rel}:{i} key「{key}」解析失敗：{e}")
                continue
            if not any(int(n) == actual for n in nums):
                drift.append(f"{rel}:{i} 宣稱 {'/'.join(nums)}，實際 {key}={actual}")

    if not files:
        print("✗ 掃到 0 份文件 —— SCAN_GLOBS 設定錯或 ROOT 算錯，不是「全部正確」。")
        return 2
    print(f"  掃描 {len(files)} 份文件｜納管宣稱 {claims} 處")
    if unresolved:
        print(f"\n⚠ 無法判定 {len(unresolved)} 處：")
        for u in unresolved:
            print(f"      {u}")
    if drift:
        print(f"\n🔴 數字漂移 {len(drift)} 處：")
        for d in drift:
            print(f"      {d}")
        print("\nStatus: [RED] 文件宣稱與實際不符")
        # 2026-08-07：原本是 `return 1 if args.ci else 0`（--ci 已移除），而 run_fitness_weekly
        # **一律不傳旗標**（依原生三態判斷）→ 這一支印著 RED 卻回 0，於是
        # **管理文件數字的檢核，自己在 weekly 裡是假綠**。同 v6.33 的 `|| true` 家族。
        # 三態語意：0=GREEN / 1=YELLOW / 2+=RED，退出碼必須與印出的狀態一致。
        return 2
    if unresolved:
        print("\nStatus: [YELLOW] 有標記無法判定（未驗完，不等於通過）")
        # 原本回 2（＝RED），比真正的漂移還嚴重 —— 兩者的嚴重度與退出碼是對調的。
        return 1
    if claims == 0:
        # 0 處納管不是「全部正確」，是還沒有人標 —— 明講，不印綠燈。
        print("\nStatus: [INFO] 目前沒有任何行標記納管；要納管請在行首加 `<!--baseline:key-->`")
        return 0
    print("\nStatus: [GREEN] 所有納管宣稱與實際一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
