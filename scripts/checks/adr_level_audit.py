# -*- coding: utf-8 -*-
"""ADR 接通完整度自評稽核（2026-08-09 補建）。

## 為什麼現在才有這支

`MODULARIZATION_STANDARDS_v1.md` §4.3 寫著：

    加 fitness step：`scripts/checks/adr_level_audit.py`（待建）

**「待建」寫了就沒有下文** —— 沒有任何機制在追這個待辦，而規範本身
（`.claude/rules/adr-anti-half-wired-sop.md`）明文要求所有新 ADR 必須達 L2。
於是「ADR 上線前要自評接通完整度」這條規定，**兩個月來沒有任何執行者**。

2026-08-09 由 `spec_executor_audit` 抓到：規範宣告了一個**檔案根本不存在**的機制。
這是 L01 斷鏈家族 —— 建議了一個沒有實作的東西，而建議本身看起來很完整。

## 判準（依 §4.3 原文）

  status=accepted 的 ADR，文末必須有「接通完整度自評」區塊 → 缺少即 RED
  proposed / archived / superseded 不要求（那正是還在討論或已退場的狀態）

**刻意不驗自評內容是否誠實**（例如打勾的 test 檔案是否真的存在）——
那需要逐一核實，且 §4.3 沒有要求。先讓「有沒有寫」這件事可機器判定。
真要驗實質，應該另立一支，而不是在這裡混進語意判斷。

## 用法

    python scripts/checks/adr_level_audit.py
    python scripts/checks/adr_level_audit.py --self-test
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
ADR_DIR = ROOT / "docs" / "adr"

# 自評區塊的標題（§4.3 原文）
SELF_ASSESS_RE = re.compile(r"##\s*接通完整度自評")
# status 行。**必須同時認中文與英文**：
#
# 2026-08-09 首版只寫英文 `status`，實跑得到「accepted 0 份、其他 23 份」→ GREEN。
# 那是假綠：本 repo 的 ADR 寫的是 `> **狀態**: accepted`（引言 + 中文 + 粗體）。
# 一個抓不到任何對象的檢核，看起來與「全部合規」一模一樣 ——
# 這正是本專案反覆記的「0 筆不等於健康」。
# 故下方 main() 另有守衛：accepted 為 0 時直接判未驗完，不給綠燈。
STATUS_RE = re.compile(
    r"^\s*>?\s*(?:\*\*)?(?:status|狀態)(?:\*\*)?\s*[:：]\s*\*{0,2}([A-Za-z\-]+)",
    re.MULTILINE | re.IGNORECASE,
)

# 非 ADR 的檔案（範本／索引），不納入判定
NON_ADR = {"README.md", "TEMPLATE.md", "REGISTRY.md", "index.md"}

# 規範生效日：`MODULARIZATION_STANDARDS_v1.md` §4.3 於此日建立。
#
# 2026-08-09 owner 決定：**只管規範之後的 ADR**。
# 理由與腳本強制表態閘門的 grandfathered 一致 ——
# 那 14 份 accepted 全部建立於 2026-04，規範是 05-25 才立的；
# 要求回溯補寫是拿新規範追溯既有產物，而且**一道一上線就全紅的閘門會被學會忽略**。
# 它們的實際接通狀況多數已由現行 fitness / producer 覆蓋。
#
# 存量仍會被列出（債要看得見），但不判紅 —— 同 grandfathered 的處理。
STANDARD_EFFECTIVE = "2026-05-25"


def judge(missing: list[str]) -> int:
    return 2 if missing else 0


def self_test() -> int:
    cases = [
        ("有 accepted 缺自評", ["0001"], 2),
        ("全部合規", [], 0),
    ]
    bad = []
    for name, m, expect in cases:
        got = judge(m)
        ok = got == expect
        print(f"  {'✓' if ok else '✗'} {name:20s} 預期 exit={expect} 實際={got}")
        if not ok:
            bad.append(name)

    # 正則鑑別力：確認標題比對抓得到、也不會亂抓
    ok1 = bool(SELF_ASSESS_RE.search("## 接通完整度自評\n- **級別**：L2"))
    ok2 = not SELF_ASSESS_RE.search("## 決策\n本 ADR 決定採用 X")
    print(f"  {'✓' if ok1 else '✗'} {'標題比對命中':20s}")
    print(f"  {'✓' if ok2 else '✗'} {'不誤抓其他章節':20s}")
    if not (ok1 and ok2):
        bad.append("regex")

    if bad:
        print(f"\n✗ 判準無鑑別力：{bad}")
        return 2
    print("\n✓ 判準有鑑別力（正向 2 例、負向 2 例）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    print("=== ADR 接通完整度自評稽核（MODULARIZATION_STANDARDS §4.3）===")
    if not ADR_DIR.is_dir():
        print(f"✗ 找不到 {ADR_DIR} —— 無法判定，不視為通過")
        return 2

    files = [p for p in sorted(ADR_DIR.glob("*.md")) if p.name not in NON_ADR]
    if not files:
        print("✗ 掃到 0 份 ADR —— 路徑設定可能錯（0 份不等於全部合規）")
        return 2

    accepted, missing, other, legacy = 0, [], 0, []
    for p in files:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        m = STATUS_RE.search(txt)
        status = (m.group(1).lower() if m else "")
        if status != "accepted":
            other += 1
            continue
        accepted += 1
        if SELF_ASSESS_RE.search(txt):
            continue
        # 建立日以 git 首次加入為準（檔案 mtime 會被任何編輯重置，不可靠）
        try:
            r = subprocess.run(
                ["git", "-C", str(ROOT), "log", "--diff-filter=A",
                 "--format=%ad", "--date=short", "--", str(p.relative_to(ROOT))],
                capture_output=True, text=True, timeout=30,
            )
            born = (r.stdout.strip().splitlines() or [""])[-1]
        except Exception:
            born = ""
        if born and born < STANDARD_EFFECTIVE:
            legacy.append(f"{p.name}（{born}）")
        else:
            missing.append(p.name)

    print(f"  ADR {len(files)} 份｜accepted {accepted}｜其他狀態 {other}｜"
          f"規範前存量 {len(legacy)}｜**規範後缺自評 {len(missing)}**")
    if legacy:
        # 存量要一直看得見，否則「暫時放過」會變成「永遠放過」
        print(f"  🟡 規範（{STANDARD_EFFECTIVE}）之前建立且未補自評：{len(legacy)} 份 —— 這是債，不是通過")
        for n in legacy[:6]:
            print(f"      · {n}")
        if len(legacy) > 6:
            print(f"      …另 {len(legacy) - 6} 份")

    # 掃到 0 份 accepted，幾乎必然是 status 解析壞了（本檔首版就是這樣）——
    # 而「沒有對象」與「全部合規」在輸出上長得一模一樣。不給綠燈。
    if accepted == 0:
        print("\n✗ 沒有任何 ADR 被判為 accepted —— 多半是 status 解析失效，")
        print("  而不是真的沒有 accepted ADR。不視為通過。")
        return 2
    if missing:
        print("\n🔴 status=accepted 但沒有「接通完整度自評」區塊：")
        for n in missing[:12]:
            print(f"    · {n}")
        if len(missing) > 12:
            print(f"    …另 {len(missing) - 12} 份")
        print("  → 補上 §4.3 的自評區塊（級別 + 驗證資產 + 邊角實測紀錄 + 7 天檢點）")

    code = judge(missing)
    print()
    print(f"Status: [{'RED' if code >= 2 else 'GREEN'}]")
    return code


if __name__ == "__main__":
    sys.exit(main())
