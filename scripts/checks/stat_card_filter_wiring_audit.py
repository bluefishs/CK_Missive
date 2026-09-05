#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""統計卡是否真的接到篩選（weekly 108）——「只換底色」的卡片是假的互動。

owner 2026-09-05：「統計圖卡對應動態篩選與資訊卡片呈現風格應為首要核心」。

## 為什麼

09-04 一天抓到兩頁：`/contract-cases`、`/erp/quotations` 的四張卡 `onClick` 只做 `setStatFilter(...)`，
而 `statFilter` 除了 `active=` 沒有任何地方讀它——點下去只換底色，列表不動。weekly 82 守的是「分母是不是全量」，
守不到「點了有沒有反應」。這支補這一段。

## 判準（靜態，逐張卡）

對每個含 `<ClickableStatCard` 的頁面，抓出每張卡的 `onClick={...}` 內容：
  ok   handler 呼叫了 `setParams`／`set*Filter`／`setCurrentPage`／`setActiveTab`／`navigate`／`setTypeFilter` 之類**會影響查詢或路由**的函式
  ok   handler 只呼叫 `setStatFilter`，但 `statFilter` 在檔內有 `active=` 以外的讀取（例如進了 useMemo 篩 dataSource 或進 params）
  RED  handler 只呼叫 `setStatFilter`（或同型的單一 state setter）且該 state 沒有 `active=`／setter 以外的讀取 ⇒ 假互動
  YELLOW 卡片沒有 `onClick`（純顯示）——彙總類（使用率、總預算）可接受，但要在本檔登記理由
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "frontend" / "src" / "pages"

# 純顯示可接受的卡（檔名 → 卡片標題），要有理由
DISPLAY_ONLY_OK = {
    "ERPOperationalListPage.tsx": {"總預算", "總支出", "使用率"},   # 彙總金額，沒有可對應的列表篩選條件
    "ERPAssetListPage.tsx": {"總價值"},                               # 彙總金額
    "ERPInvoiceSummaryPage.tsx": {"淨額"},                            # 銷項−進項，是算式不是子集合
    "ERPLedgerPage.tsx": {"淨額"},                                    # 收入−支出，同上
    "TenderSearchPage.tsx": {"搜尋結果"},                             # 就是目前列表本身
    "PMCaseListPage.tsx": {"`報價總額"},                              # 金額彙總，跟著狀態卡的篩選走，本身不篩（標題以前綴比對）
}
QUERY_SETTERS = re.compile(r"\b(handle\w*Filter|apply\w*Filter|setParams|set[A-Z]\w*Filter|setStatusFilter|setCurrentPage|setPage|setActiveTab|setTypeFilter|navigate|setQuery|toggleCard|setSearch\w*|setYear\w*|setCategory\w*|refetch)\s*\(")


def cards_in(src: str):
    """回傳 [(title, onclick_body 或 None)]"""
    out = []
    # 卡片結尾＝大括號深度 0 時遇到的 `/>`。首版用正則找第一個 `/>`，會被 icon={<X />} 或
    # icon={cond ? <A /> : <B />} 的自閉合截斷，把有 onClick 的卡全報成「沒有 onClick」。
    pos = 0
    while True:
        start = src.find("<ClickableStatCard", pos)
        if start < 0:
            break
        depth = 0
        i = start + len("<ClickableStatCard")
        end = -1
        while i < len(src):
            ch = src[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif depth == 0 and src.startswith("/>", i):
                end = i
                break
            i += 1
        if end < 0:
            break
        block = src[start + len("<ClickableStatCard"):end]
        pos = end + 2
        t = re.search(r"title=\{?\"?([^\"}\n]*)", block)
        title = (t.group(1).strip() if t else "?")[:24]
        # 允許兩層巢狀大括號（多行 handler：onClick={() => { setX({ ...p }); }}）
        oc = re.search(r"onClick=\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}", block, re.S)
        body = oc.group(1) if oc else None
        out.append((title, body))
    return out


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=== 統計卡是否接到篩選（weekly 108）===")
    reds, yels, total = [], [], 0
    for f in sorted(PAGES.rglob("*.tsx")):
        src = f.read_text(encoding="utf-8", errors="replace")
        if "<ClickableStatCard" not in src:
            continue
        rel = f.relative_to(PAGES).as_posix()
        for title, body in cards_in(src):
            total += 1
            if body is None:
                if any(title.startswith(x) for x in DISPLAY_ONLY_OK.get(f.name, set())):
                    continue
                yels.append((rel, title, "沒有 onClick（純顯示，未登記理由）"))
                continue
            if QUERY_SETTERS.search(body):
                continue
            # 只設了某個 state：那個 state 有沒有被讀（active= 以外）
            setters = re.findall(r"\b(set[A-Z]\w*)\s*\(", body)
            if not setters:
                yels.append((rel, title, f"onClick 沒有呼叫任何 setter：{body.strip()[:60]}"))
                continue
            wired = False
            for st in setters:
                state = st[3].lower() + st[4:]
                reads = [ln for ln in src.splitlines() if re.search(rf"\b{state}\b", ln) and "active=" not in ln and st + "(" not in ln and "useState" not in ln]
                if reads:
                    wired = True
                    break
            if not wired:
                reds.append((rel, title, f"只做 {'/'.join(setters)}，該 state 沒有人讀 ⇒ 點了只換底色"))
    print(f"卡片 {total} 張；假互動 {len(reds)}；純顯示未登記 {len(yels)}")
    for r in reds:
        print(f"  [RED] {r[0]}「{r[1]}」{r[2]}")
    for y in yels:
        print(f"  [YELLOW] {y[0]}「{y[1]}」{y[2]}")
    if reds:
        print(f"[RED] {len(reds)} 張統計卡點了沒反應")
        return 2
    if yels:
        print(f"[YELLOW] {len(yels)} 張純顯示卡未登記理由")
        return 1
    print("[GREEN] 每張統計卡都接到篩選或已登記為純顯示")
    return 0


if __name__ == "__main__":
    sys.exit(main())
