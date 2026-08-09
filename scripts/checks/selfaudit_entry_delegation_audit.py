# -*- coding: utf-8 -*-
"""走查入口腳本必須委派給共用實作 —— 防止「copy 式」入口再長回來（2026-08-09）。

## 為什麼需要這一支

引擎（`.shared-selfaudit/*.cjs`）早有 drift 稽核（`sync-vendored.sh --check`），
但**入口腳本沒有任何 gate**。實測結果：

  · lvrland 與 pile 的 `run_selfaudit.sh` **去註解後差異 0 行** —— 兩份完全相同
    的副本各自維護，pile 那份的檔頭還留著「CK_lvrland_Webmap」的複製殘留
  · DT 那份只因認證型別不同而差 33 行
  · **CK_Missive 那份最舊**：容器名與 adapter 路徑寫死、不讀 config，
    儘管它的 config 早就有 `auth.container`

症狀不會是「其中一份比較舊」，而是**改了一份、其他四份靜靜不同步**。
2026-08-08 新增 `LOCAL_STORAGE` 憑證時就必須同步改入口，漏一個就靜靜傳丟憑證
（那次查了五個錯方向才發現）。

## 判準

各消費 repo 的入口腳本必須呼叫 `.shared-selfaudit/run.sh`。
沒有委派 ＝ 自己重寫了一份核心流程 → RED。

**repo 清單不自己維護** —— 從 `shared-modules/sync-vendored.sh` 的 SCRIPT_SPECS
解析，那才是「誰在消費這個引擎」的權威來源。另建一份必然漂移
（`producer_output_watchdog` 就踩過：watchdog 自己維護第二份 MONITORED_JOBS）。

## 用法

    python scripts/checks/selfaudit_entry_delegation_audit.py
    python scripts/checks/selfaudit_entry_delegation_audit.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PORTFOLIO = Path("D:/CKProject")
SYNC_SCRIPT = PORTFOLIO / "shared-modules" / "sync-vendored.sh"

# 入口腳本的候選檔名。兩種命名是歷史造成的（Missive/CK_Website 較早、
# 其餘較晚），**不強制統一檔名** —— Windows 排程指向這些路徑，
# 為了整齊改名要同步改 5 支排程，風險大於收益。
ENTRY_NAMES = ("run_selfaudit.sh", "run_ui_smoke.sh")

DELEGATION_RE = re.compile(r"\.shared-selfaudit/run\.sh")

# 已知且有理由的例外。空的時候就該是空的 —— 有人往這裡加東西時，
# 理由必須寫在值裡，而不是只放一個名字。
ALLOWED: dict[str, str] = {}


def consumer_repos() -> list[str]:
    """從 sync-vendored.sh 取得引擎消費者清單（不自己維護第二份）。"""
    if not SYNC_SCRIPT.exists():
        print(f"✗ 找不到 {SYNC_SCRIPT} —— 無法判定消費者清單，不視為通過")
        raise SystemExit(2)
    txt = SYNC_SCRIPT.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'"selfaudit\|[^|]+\|([^"]+)"', txt)
    if not m:
        print("✗ sync-vendored.sh 內找不到 selfaudit 的 SCRIPT_SPECS 條目")
        raise SystemExit(2)
    repos = m.group(1).split()
    if not repos:
        print("✗ selfaudit 消費者清單為空 —— 解析失敗而非真的沒有消費者")
        raise SystemExit(2)
    return repos


def judge(findings: list[tuple[str, str]]) -> int:
    """抽出來才驗得了鑑別力。findings = [(repo, 狀態)]"""
    bad = [r for r, s in findings if s not in ("delegated", "allowed", "absent")]
    return 2 if bad else 0


def check_repo(repo: str) -> tuple[str, str]:
    base = PORTFOLIO / repo
    if not base.exists():
        return repo, "absent"  # repo 不在本機不算違規
    entries = [base / "scripts" / "checks" / n for n in ENTRY_NAMES]
    found = [p for p in entries if p.exists()]
    if not found:
        return repo, "no-entry"
    for p in found:
        txt = p.read_text(encoding="utf-8", errors="replace")
        if not DELEGATION_RE.search(txt):
            return repo, f"not-delegated:{p.name}"
    return repo, "delegated"


def self_test() -> int:
    """證明判準會動 —— 否則「全部通過」可能只是永遠不會紅。"""
    cases = [
        ("全部委派", [("a", "delegated"), ("b", "delegated")], 0),
        ("有一個沒委派", [("a", "delegated"), ("b", "not-delegated:run_x.sh")], 2),
        ("找不到入口", [("a", "no-entry")], 2),
        ("repo 不在本機不算違規", [("a", "absent")], 0),
        ("已登記例外", [("a", "allowed")], 0),
    ]
    bad = []
    for name, f, expect in cases:
        got = judge(f)
        ok = got == expect
        print(f"  {'✓' if ok else '✗'} {name:22s} 預期 exit={expect} 實際={got}")
        if not ok:
            bad.append(name)
    if bad:
        print(f"\n✗ 判準無鑑別力：{bad}")
        return 2
    print("\n✓ 判準有鑑別力（正向 3 例、負向 2 例）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    print("=== 走查入口委派稽核（防 copy 式入口復發）===")
    repos = consumer_repos()
    print(f"  消費者（取自 sync-vendored.sh）：{', '.join(repos)}\n")

    findings: list[tuple[str, str]] = []
    for repo in repos:
        r, status = check_repo(repo)
        if status == "not-delegated" or status.startswith("not-delegated"):
            if repo in ALLOWED:
                status = "allowed"
        findings.append((r, status))
        icon = {"delegated": "✓", "absent": "–", "allowed": "○"}.get(status, "✗")
        note = f"（例外：{ALLOWED[repo]}）" if status == "allowed" else ""
        print(f"  {icon} {repo:24s} {status}{note}")

    code = judge(findings)
    print()
    if code == 0:
        print("Status: [GREEN] 所有入口皆委派給共用實作")
        return 0
    print("Status: [RED] 有入口自行重寫核心流程")
    print("  處置：把該檔改為薄包裝 `exec bash \"$ROOT/scripts/checks/.shared-selfaudit/run.sh\" \"$@\"`；")
    print("  該 repo 特有的前後置步驟留在包裝裡（不要放進共用層）。")
    return code


if __name__ == "__main__":
    sys.exit(main())
