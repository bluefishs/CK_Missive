# -*- coding: utf-8 -*-
"""shell script 不得帶 CRLF —— 那會讓它在 Linux 容器裡直接無法執行（2026-08-07）。

## 為什麼需要這一支

`fitness_daily` / `fitness_weekly` 是**容器內 APScheduler** 在跑。兩支 runner 帶著
CRLF 被 build 進容器後，bash 讀到 `\\r` 就 `command not found`，到函式定義直接
syntax error → **一行檢核都沒跑過**：daily 每日 rc=2、weekly 從 2026-W23 到 W31
連 9 週 RED。而在 host（Git Bash 容忍 CRLF）跑同一支永遠是「all passed」。

根因是 `.gitattributes` 有 `*.py`/`*.ts`/`*.tsx`/`*.js`/`*.jsx` 的 eol=lf，
**唯獨漏了 `*.sh`** —— 而 shell script 是唯一會因 CRLF 直接死掉的類型。
規則已補，但**規則存在不等於生效**（`core.autocrlf=true` 仍會作用在沒有屬性的
新副檔名上，而且沒有人會記得這件事）—— 所以要有東西持續在問。

與 `powershell_bom_audit.py`（.ps1 必須帶 UTF-8 BOM，L49.8）是同一家族：
**檔案編碼／行尾這種「看不見的位元組」壞掉時，症狀是整支腳本不執行而非報錯。**

## 判準

`scripts/**/*.sh` 與 `.claude/hooks/**/*.sh`（實際會被執行的）不得含任何 CRLF。
只看**會被執行**的腳本；文件裡的程式碼片段不在範圍。

## 用法

    python scripts/checks/shell_script_eol_audit.py
    python scripts/checks/shell_script_eol_audit.py --self-test

退出碼（三態，與印出的 Status 一致）：0=GREEN / 2=RED（有 CRLF）。
沒有 YELLOW —— 這件事不存在「可能有問題」的中間態。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
SCAN_DIRS = ("scripts", ".claude/hooks")
CRLF = bytes([13, 10])


def _shell_files() -> list[Path]:
    """只看**會被執行**的腳本。

    排除 `scripts/archive/` —— 那是本專案既有的「過時腳本存檔」慣例
    （見 .claude/rules/architecture.md），裡面的腳本已退役且未納版控，
    修它們不會持久、也不影響任何執行路徑。**這是依既有慣例劃定範圍，
    不是為了讓檢核變綠**；若哪天 archive 裡的東西又被叫起來執行，
    真正該做的是把它移出 archive。
    """
    out: list[Path] = []
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.sh")):
            if "archive" in p.relative_to(ROOT).parts:
                continue
            out.append(p)
    return out


def offenders(files: list[Path]) -> list[tuple[Path, int]]:
    bad = []
    for f in files:
        try:
            n = f.read_bytes().count(CRLF)
        except OSError:
            continue
        if n:
            bad.append((f, n))
    return bad


def self_test() -> int:
    """證明判準會動 —— 否則「0 個」可能只是掃不到檔案。"""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        good = Path(td) / "good.sh"
        bad = Path(td) / "bad.sh"
        good.write_bytes(b"#!/bin/bash\necho ok\n")
        bad.write_bytes(b"#!/bin/bash\r\necho bad\r\n")
        found = {p.name for p, _ in offenders([good, bad])}
    if found != {"bad.sh"}:
        print(f"✗ 判準無鑑別力：預期只抓到 bad.sh，實際 {found or '什麼都沒抓到'}")
        return 2
    print("✓ 判準有鑑別力（CRLF 檔被抓到、LF 檔未被誤報）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    print("=== shell script 行尾稽核（CRLF 會讓腳本在容器內完全無法執行）===")
    files = _shell_files()
    if not files:
        # 掃到 0 個不是「全部正確」，是掃錯地方 —— 這正是本專案反覆踩到的形狀。
        print("✗ 掃到 0 個 .sh —— SCAN_DIRS 或 ROOT 算錯，不是「全部正確」")
        return 2
    bad = offenders(files)
    print(f"  掃描 {len(files)} 支 shell script")
    if not bad:
        print("\nStatus: [GREEN] 全部為 LF")
        return 0
    print(f"\n🔴 {len(bad)} 支含 CRLF：")
    for f, n in bad:
        print(f"      {f.relative_to(ROOT)}（{n} 行）")
    print("\nStatus: [RED] 這些腳本在 Linux 容器內會 syntax error 而完全不執行")

    # 2026-09-02：**把答案印在紅燈下面，不要只給清單。**
    #
    # 08-30 與 08-31 這一步報了兩天 RED，沒有人收；09-01 起
    # run_fitness_daily.sh 自己變成 CRLF ⇒ 每日檢核一行都沒跑過，
    # 而它的死法（rc=2、紅燈清單為空）被 scheduler 記成「RED」、
    # 再被「連續相同紅燈」的去重靜音 ⇒ 連兩天沒有人知道。
    #
    # 當時的輸出已經寫了「會 syntax error」，但那是**一張清單**（哪些檔壞了），
    # 讀的人還要自己把「這幾支裡有 runner」跟「所以檢核會死」連起來。
    # ⇒ 判準與現場的距離不是行數，是**它有沒有以答案的形式出現**。
    #   （判準由 ck-website-37 於同日提出，本 repo 採用）
    # ⚠️ 已知限制：這是**檔名字串比對**。runner 若改名成不含 run_fitness 的
    #    名字就會漏（ck-website-37 的同型測試用 rc=134 擋住了「只認 255 這個
    #    字面值」的寫法；本條沒有等價的防護，因為判斷依據就是檔名本身）。
    # 雙側驗證（2026-09-02，兩側都做才有鑑別力）：
    #   正向 造 run_fitness_TEMPPROBE.sh(CRLF) ⇒ exit 2 且印出警示
    #   負向 造 zz_temp_probe_notrunner.sh(CRLF) ⇒ exit 2 但**不印**警示
    #   清理 兩者刪除後 ⇒ exit 0 GREEN，臨時檔確認移除
    # 少了負向那一側，把條件式改回無條件也能讓正向通過。
    _runners = [f for f, _n in bad if "run_fitness" in f.name]
    if _runners:
        print("")
        print("  🚨 名單裡有 fitness runner —— 那是**這支檢核自己的執行器**。")
        print("     它壞掉時的症狀是 rc=2 且紅燈清單為空（不是某一步紅）：")
        print("       · scheduler 會把非 0/1 的退出碼記成 RED（已於 09-02 改為 ERROR）")
        print("       · 「連續相同紅燈」的去重會把第二天判成「跟昨天一樣」而抑制")
        print("     ⇒ **檢核不會跑，而且不會有人收到通知。**")
        print("     2026-09-02 實例：08-30/08-31 報了兩天沒人收，09-01 起 runner 自己就跑不動了。")
        print("")

    print("  修法：確認 .gitattributes 有 `*.sh text eol=lf`，再把檔案轉為 LF")
    print("  ⚠️ git status 看不見這件事（比較時會正規化行尾），")
    print("     host 的 Git Bash 又容忍 CRLF ⇒ **手動跑永遠全綠**。")
    print("     要驗就在容器內跑：docker exec <容器> bash -n <腳本>")
    return 2


if __name__ == "__main__":
    sys.exit(main())
