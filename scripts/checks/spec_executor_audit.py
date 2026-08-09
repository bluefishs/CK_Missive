# -*- coding: utf-8 -*-
"""規範宣告 vs 執行者稽核（2026-08-09）。

## 為什麼需要這一支

owner：「因此要針對既有規範統整複查確認」。

起因是一個具體實例：`.claude/rules/adr-anti-half-wired-sop.md` §自查工具
明文寫著「月度執行」四支腳本 —— 而**沒有任何 runner 或排程在跑它們**。
規範裡的規定，沒有執行者。

實跑其中的 `sso_coverage_check.py` 當場揭露它印
「[FAIL] 2 個 admin 鎖死風險 — IdP outage 時無管理通道」**卻 exit 0**
（只有 `--ci` 才回 1，而 weekly runner 一律不傳旗標）。
那個風險因此從未被任何人看見 —— 兩層失效疊在一起：沒人跑，跑了也不會紅。

首次全面複查：**37 份規範文件宣告 33 支腳本，6 支有問題**，
其中 `adr_level_audit.py` **檔案根本不存在**（規範宣告了一個不存在的機制，L01 家族）。

## 判準

規範文件裡以 `scripts/checks/xxx.py` 形式出現的腳本，必須：

  · 檔案存在（不存在 → **RED**：規範指向空氣）
  · 且被某個執行者引用（`run_*.sh` / 後端排程 / Windows 排程）
    → 沒有執行者 → **YELLOW**（可能是刻意的人工工具，但必須看得見）

**刻意不判斷「規範內容是否還正確」**：那需要語意判斷，會產出無法採信的清單
（同 `doc_reference_integrity_audit` 立下的界線）。這裡只問可機器驗證的兩件事。

## 用法

    python scripts/checks/spec_executor_audit.py
    python scripts/checks/spec_executor_audit.py --self-test
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ROOT / "scripts" / "checks"

# 規範文件：行為準則（.claude/rules）+ 標準/SOP/契約類
SPEC_GLOBS = [
    (".claude/rules", "*.md"),
    ("docs/architecture", "*STANDARD*.md"),
    ("docs/architecture", "*SOP*.md"),
    ("docs/architecture", "*CONTRACT*.md"),
    ("docs/architecture", "*GOVERNANCE*.md"),
    ("docs/architecture", "*STRATEGY*.md"),
]

SCRIPT_RE = re.compile(r"scripts/checks/([A-Za-z0-9_\-]+\.(?:py|sh))")

# 已知的人工工具：規範提到它，但**刻意**不接排程。必須寫理由。
MANUAL_BY_DESIGN: dict[str, str] = {
    "v6_8_acceptance.sh": "v6.8 一次性驗收腳本，規範中作為歷史紀錄引用",
    "verify_architecture.py": "由 pre-commit hook 與 CI 呼叫，非 fitness runner（見 ci-cd.md）",
    "soul-fidelity-eval.py": "需人工判讀多 provider 輸出品質，且會消耗 LLM 配額 —— 刻意不掛 cron",
}


def _executors() -> str:
    """把所有可能的執行者串成一坨文字：runner + 後端 + Windows 排程。

    2026-08-09 教訓：初版只看 `run_*.sh`，於是把「由後端排程呼叫」與
    「由 Windows 排程呼叫」的腳本都誤報成孤兒。判定「有沒有人跑」
    必須涵蓋**所有**執行入口，漏一種就會產出不可採信的清單。
    """
    blob = []
    for p in CHECKS.glob("run_*.sh"):
        blob.append(p.read_text(encoding="utf-8", errors="ignore"))
    for p in (ROOT / "backend" / "app").rglob("*.py"):
        try:
            blob.append(p.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            pass
    # Windows 排程的 Actions（run_capability_snapshot.sh 就只在這裡被呼叫）
    try:
        ps = ("@(Get-ScheduledTask | Where-Object { $_.TaskName -match '^CK' } |"
              " ForEach-Object { $_.Actions } | ForEach-Object "
              "{ \"$($_.Execute) $($_.Arguments)\" }) -join \"`n\"")
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=120)
        if r.returncode == 0:
            blob.append(r.stdout)
    except Exception:
        # 查不到排程就講出來，不要靜靜當成「沒有」
        print("  ⚠ 無法查詢 Windows 排程 —— 由排程直接呼叫的腳本可能被誤報")
    return "\n".join(blob)


def judge(missing_file: list[str], no_exec: list[str]) -> int:
    if missing_file:
        return 2
    if no_exec:
        return 1
    return 0


def self_test() -> int:
    cases = [
        ("規範指向不存在的檔", ["a.py"], [], 2),
        ("有宣告但沒執行者", [], ["b.py"], 1),
        ("兩者皆有取最嚴重", ["a.py"], ["b.py"], 2),
        ("全部正常", [], [], 0),
    ]
    bad = []
    for name, mf, ne, expect in cases:
        got = judge(mf, ne)
        ok = got == expect
        print(f"  {'✓' if ok else '✗'} {name:20s} 預期 exit={expect} 實際={got}")
        if not ok:
            bad.append(name)
    if bad:
        print(f"\n✗ 判準無鑑別力：{bad}")
        return 2
    print("\n✓ 判準有鑑別力（正向 3 例、負向 1 例）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    print("=== 規範宣告 vs 執行者稽核 ===")
    print("  問的是：規範說要做的事，有沒有人在做\n")

    docs: list[Path] = []
    for d, pat in SPEC_GLOBS:
        base = ROOT / d
        if base.is_dir():
            docs += sorted(base.glob(pat))
    if not docs:
        print("✗ 掃到 0 份規範文件 —— 設定可能寫錯（0 份不等於全部合規）")
        return 2

    claimed: dict[str, set[str]] = {}
    for d in docs:
        try:
            txt = d.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name in SCRIPT_RE.findall(txt):
            claimed.setdefault(name, set()).add(d.name)
    if not claimed:
        print("✗ 規範中掃到 0 支腳本宣告 —— regex 可能失效")
        return 2

    execs = _executors()
    missing_file: list[str] = []
    no_exec: list[str] = []
    manual = 0
    for name, srcs in sorted(claimed.items()):
        if not (CHECKS / name).exists():
            missing_file.append(f"{name}（出處 {sorted(srcs)[0]}）")
            continue
        if name in execs:
            continue
        if MANUAL_BY_DESIGN.get(name, "").strip():
            manual += 1
            continue
        no_exec.append(f"{name}（出處 {sorted(srcs)[0]}）")

    print(f"  規範 {len(docs)} 份｜宣告 {len(claimed)} 支｜有執行者 "
          f"{len(claimed) - len(missing_file) - len(no_exec) - manual}"
          f"｜人工工具 {manual}｜**檔案不存在 {len(missing_file)}｜無執行者 {len(no_exec)}**")

    if missing_file:
        print("\n🔴 規範指向不存在的檔案（宣告了一個不存在的機制）：")
        for m in missing_file:
            print(f"    · {m}")
    if no_exec:
        print("\n🟡 有宣告但沒有任何執行者：")
        for m in no_exec:
            print(f"    · {m}")
        print("  → 接進 runner／排程，或加進 MANUAL_BY_DESIGN 並**寫明理由**")

    code = judge(missing_file, no_exec)
    print()
    print(f"Status: [{'RED' if code >= 2 else 'YELLOW' if code == 1 else 'GREEN'}]")
    return code


if __name__ == "__main__":
    sys.exit(main())
