#!/usr/bin/env python3
"""經費指標的唯一實作守門 —— owner 2026-09-09。

> 「統計應建構統一服務端，不應依各別頁面各自建構。請盤點複查整合，
>   避免如此反覆查核每個頁面是否來源或統計基準等問題。」

問的問題：**有沒有人在 `finance_metrics` 之外自己寫金額算式？**

## 盤點（2026-09-09，這支存在的理由）

| 指標 | 當時幾份實作 | 幾個檔 |
|---|---|---|
| 承攬金額（議價→契約→報價） | 4 | 3 |
| 已請款合計 | 3 | 3 |
| 已收款合計 | 3 | 3 |
| 應付合計 | 3 | 3 |

而且**已經分歧**：「已收款」三份的狀態條件是三種不同的東西 ——
`IN ('paid','partial')`／`= 'paid'`／完全不看狀態。

⚠️ 而當時三者**算出同一個數字**（23,072,409），因為 59 筆有金額的請款狀態剛好全是
`paid`。**那是最危險的狀態**：看起來一致，等到出現第一筆 `partial`，
三個畫面就給三個數字，而不會有任何一方報錯。這正是 owner 說的
「反覆查核每個頁面」——靠人比對是守不住的。

## 判準

掃 `backend/app/`，找**在 `finance_metrics.py` 以外**出現的金額算式樣式。
存量走基線（`.finance_metrics_baseline.json`）：**新增即紅，存量逐一清**。
一天全部改完是不可能的，而「第一天 20 個紅點」的檢核與沒有檢核是同一個下場
（本 repo 在服務層規範上付過這個學費）。

⚠️ **本檢核不判斷算式對不對**，只判斷「有沒有第二份」。
一份寫錯的實作它抓不到 —— 那是 `test_finance_metrics.py` 的判準鎖在守的。

退出碼：0 = 沒有新增的第二份；2 = 有。
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

BS = chr(92)
NL = chr(10)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(ROOT, "backend", "app")
#: 唯一實作的家 —— **兩個**：金額指標在中心服務，身分範圍判定在 `core/case_scope`。
#: （身分判定不搬進 stats：它同時服務「看得到」與「動得了」，不只統計。）
HOMES = ("services/stats/finance.py", "core/case_scope.py", "schemas/erp/case_filters.py")
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".finance_metrics_baseline.json")

_NOTNL = "[^" + BS + "n]"
_NOTPAREN = "[^)" + BS + "n]"
_WS = "[" + BS + "s]"

PATTERNS = {
    "承攬金額（議價→契約→報價）": "NULLIF[(" + _WS + "]*[a-z]*[.]?winning_amount",
    "已請款合計": "SUM[(]" + _NOTPAREN + "{0,24}billing_amount",
    "已收款合計": "SUM[(]" + _NOTPAREN + "{0,24}payment_amount",
    "應付合計": "SUM[(]" + _NOTPAREN + "{0,24}payable_amount",
    "已付合計": "SUM[(]" + _NOTPAREN + "{0,24}paid_amount",
    # 2026-09-09：以上四條只認 SQL 文字，`func.sum(ERPBilling.billing_amount)` 這種 Core 寫法
    # 躲了一天（七處）。owner 當天問「案件皆請款？」才發現「已請款」含成案佔位，而那七處各算各的。
    "已請款合計（Core）": "sum[(]" + _WS + "*ERPBilling[.]billing_amount",
    "已收款合計（Core）": "sum[(]" + _WS + "*ERPBilling[.]payment_amount",
    "應付合計（Core）": "sum[(]" + _WS + "*ERPVendorPayable[.]payable_amount",
    "已付合計（Core）": "sum[(]" + _WS + "*ERPVendorPayable[.]paid_amount",
    "年度＝案號年（應為後備）": "case_code" + _NOTNL + "{0,40}LIKE" + _NOTNL + "{0,24}CK",
    # ⭐ owner 2026-09-09：「同步考量整合配合角色與帳號（承辦同仁）等機制」。
    # 「誰是全公司視角」原本有兩份：`core/case_scope.has_company_wide_scope`（超管＋角色集合）
    # 與 `erp/quotations._quotation_scope`（超管＋跨案查詢權限）。
    # 兩份判準指向同一件事，而實測當下結果相同 —— **因為那三位主管／財務剛好同時符合兩邊**。
    # 分歧存在，只是還沒發作（同「已收款三份實作算出同一個數字」）。
    "全公司視角判定（應只在 case_scope）": "is_superuser_user" + _NOTNL + "{0,20}(or|and)" + _NOTNL + "{0,24}is_admin_user",
    "全公司視角角色集合（應只有一份）": "COMPANY_WIDE_ROLES" + _WS + "*=",
    # ⭐ owner 2026-09-09「整合篩選條件，請擴大各頁面整合評估」：案件類列表的篩選 schema 有四份
    # 各自宣告 year／category／staff_user_id。家＝`schemas/erp/case_filters.CaseListFilters`，
    # 其他 *ListRequest／*ListQuery 要繼承它，不得自己再宣告這三個欄位。
    # 判準：class 名以 ListRequest／ListQuery 結尾、body 內宣告 `staff_user_id:` 且未繼承 CaseListFilters。
    "案件類篩選 schema 自行宣告承辦欄位（應繼承 CaseListFilters）": "class" + _WS + "+" + "[A-Za-z]+(ListRequest|ListQuery)" + BS + "((?!CaseListFilters)[A-Za-z]+" + BS + "):(?:(?!" + BS + "nclass ).)*?" + BS + "n" + _WS + "+staff_user_id:",
}
_MULTILINE_KEYS = {"案件類篩選 schema 自行宣告承辦欄位（應繼承 CaseListFilters）"}


def scan():
    hits = []
    for root, _d, files in os.walk(APP):
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, APP).replace(os.sep, "/")
            if rel in HOMES:
                continue
            raw = io.open(p, encoding="utf-8").read()
            s = _strip_comments(raw)
            for name, pat in PATTERNS.items():
                flags = re.S if name in _MULTILINE_KEYS else 0
                for m in re.finditer(pat, s, flags):
                    line = s[: m.start()].count(NL) + 1
                    if name.startswith("年度") and _has_year_fallback(s, m.start()):
                        continue
                    hits.append({"file": rel, "line": line, "metric": name})
    return hits


def _strip_comments(src: str) -> str:
    """把整行註解換成空行（保留行號）。

    ⚠️ **2026-09-09 首跑就踩到**：判準把
    `financial_summary_repository.py` 裡**我自己寫的那段註解**
    （「而這裡的 01+02 加總只有 91,173,873（用案號年 `case_code LIKE 'CK2026_%'`）」）
    當成一處違規報了出來。**判準的掃描範圍不得包含描述它的文字** ——
    本 repo 今天第四次踩這個坑。
    """
    out = []
    for ln in src.split(NL):
        out.append("" if ln.lstrip().startswith("#") else ln)
    return NL.join(out)


def _has_year_fallback(s: str, at: int) -> bool:
    """案號年**帶著 year 欄後備**時是正確寫法，不算第二份實作。

    正解的形狀是 `q.year = :yr OR (q.year IS NULL AND case_code LIKE ...)` ——
    案號年只在 year 欄為空時才生效。`case_profile.py` 兩處就是這種，
    首版把它們報成違規（過寬）。判準改成看同一段窗口裡有沒有 year 欄比較。
    """
    win = s[max(0, at - 400): at + 200]
    return re.search("[a-z][.]year" + _WS + "*(=|IS NULL)", win) is not None


def key(h):
    # 基線以「檔案＋指標」為鍵，**不含行號** —— 行號會因無關的編輯漂移，
    # 那會讓基線每週都要重簽，而重簽多了就沒有人在看它了。
    return "%s::%s" % (h["file"], h["metric"])


def main() -> int:
    hits = scan()
    base = {}
    if os.path.isfile(BASELINE):
        base = json.load(io.open(BASELINE, encoding="utf-8")).get("allow", {})

    cur = {}
    for h in hits:
        cur.setdefault(key(h), []).append(h["line"])
    new = {k: v for k, v in cur.items() if k not in base}
    gone = [k for k in base if k not in cur]

    print("=" * 70)
    print("經費指標的唯一實作守門（weekly）")
    print("=" * 70)
    for h in HOMES:
        print("唯一實作＝backend/app/%s" % h)
    print("在它以外出現的金額算式：%d 處" % len(hits))
    print("  基線允許（存量待清）：%d" % len(base))
    print("  ⛔ 新增的第二份：%d" % len(new))
    for k, lines in sorted(new.items()):
        f, m = k.split("::")
        print("     %s  %s  行 %s" % (f, m, ", ".join(str(x) for x in lines)))
    if gone:
        print("  ✅ 已清掉（可從基線移除）：%d" % len(gone))
        for k in sorted(gone):
            print("     %s" % k)

    outdir = os.path.join(ROOT, "wiki", "memory", "integration-health")
    if os.path.isdir(outdir):
        io.open(os.path.join(outdir, "finance_metrics_ssot.json"), "w", encoding="utf-8").write(
            json.dumps({"total": len(hits), "baseline": len(base), "new": len(new), "cleared": gone},
                       ensure_ascii=False, indent=2))

    if new:
        print()
        print("⇒ 修法：從中心服務 `app/services/stats/finance` 拿片段，不要自己寫。")
        return 2
    print()
    print("✅ 沒有新增的第二份實作（存量 %d 處待清）" % len(base))
    return 0


if __name__ == "__main__":
    sys.exit(main())
