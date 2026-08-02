"""文件引用完整性稽核（2026-08-02）

## 為什麼要有這支

`docs/architecture/` 已累積 **102 份**文件，但沒有任何檢核在問「它們寫的還算數嗎」。
既有治理全部朝向程式碼與資料（fitness 78 步 / producer watchdog / 頁面掃描），
文件只有 `check-doc-drift.sh` 看修改時間——**時間新不代表內容還成立**。

本檢查取一個**客觀可驗**的切面：文件裡引用的檔案路徑是否還存在。
路徑失效是「文件與現實脫節」最不需要解讀的證據（同 L01 斷鏈家族）。

## 刻意不做的事

不判斷文字內容是否過時——那需要語意判斷，會產出大量無法採信的噪音
（同 pg_trgm 對中文、719 個 0.905 前端嵌入相似度的教訓）。

## 判定

失效率 = 失效引用 / 全部引用。
- < 10%   GREEN（少量陳舊，屬正常代謝）
- 10~20%  YELLOW（該排一次清理）
- >= 20%  RED（文件已大幅脫離現實）

首次基線（2026-08-02）：361 引用 / 34 失效 = 9.4% GREEN。
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
DOC_DIRS = ["docs/architecture"]

# 只認「看起來像本 repo 相對路徑」的引用，且必須被反引號/括號包住
# （避免把散文裡的字詞誤當路徑）
PATH_RE = re.compile(
    r"[`\(\[]\s*((?:backend|frontend|scripts|docs|wiki|configs|\.claude)/[A-Za-z0-9_./-]+\.[a-z]{2,4})"
)

# 佔位符：文件用來示意格式的路徑，不是真實檔案（實測會誤判，必須排除）
PLACEHOLDER_RE = re.compile(r"YYYY|MM-DD|XXXX|\{|\}|<|>|NNNN|\*")

WARN_PCT = 10.0
FAIL_PCT = 20.0


def scan() -> tuple[int, Counter, Counter]:
    total = 0
    missing: Counter = Counter()
    per_doc: Counter = Counter()
    for d in DOC_DIRS:
        for md in sorted((ROOT / d).glob("*.md")):
            try:
                text = md.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in PATH_RE.finditer(text):
                rel = m.group(1)
                if PLACEHOLDER_RE.search(rel):
                    continue
                total += 1
                if not (ROOT / rel).exists():
                    missing[rel] += 1
                    per_doc[md.name] += 1
    return total, missing, per_doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--ci", action="store_true")
    args = ap.parse_args()

    print("=== 文件引用完整性稽核（docs/architecture）===")
    total, missing, per_doc = scan()

    if total == 0:
        # 0 個引用必定是 regex 或路徑設定壞了，不是「文件都很乾淨」
        print("✗ 掃到 0 個路徑引用 —— 檢查 DOC_DIRS / PATH_RE 設定（0 不等於健康）")
        return 2

    bad = sum(missing.values())
    pct = bad / total * 100
    print(f"  引用總數 {total}｜失效 {bad}（{pct:.1f}%）｜去重 {len(missing)} 條｜"
          f"涉及 {len(per_doc)} 份文件")

    if missing:
        print("\n  失效引用（出現次數 / 路徑）：")
        for p, c in missing.most_common(20):
            print(f"    {c:3}x  {p}")
        if len(missing) > 20:
            print(f"    …另 {len(missing) - 20} 條")

    print()
    if pct >= FAIL_PCT:
        print(f"Status: [RED] 失效率 {pct:.1f}% >= {FAIL_PCT}% —— 文件已大幅脫離現實")
        return 2
    if pct >= WARN_PCT:
        print(f"Status: [YELLOW] 失效率 {pct:.1f}% >= {WARN_PCT}% —— 建議排一次清理")
        return 1
    print(f"Status: [GREEN] 失效率 {pct:.1f}% < {WARN_PCT}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
