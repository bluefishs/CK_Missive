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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402

ROOT = repo_root()  # 不自算路徑（weekly 93）：自算算錯是靜默的，會讀到別的檔
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
# ⚠️ `setStatFilter`／`setActiveCard` 是「卡片自己的底色 state」，不算查詢 setter——負向對照抓到首版把它們也算進去，
#    於是修法前的公文字號頁（四張卡只 setStatFilter）量成 0 張紅。
QUERY_SETTERS = re.compile(r"\b(handle\w*Filter|apply\w*Filter|setParams|set(?!StatFilter\b)(?!ActiveCard\b)[A-Z]\w*Filter|setStatusFilter|setCurrentPage|setPage|setActiveTab|setTypeFilter|navigate|setQuery|toggleCard|setSearch\w*|setYear\w*|setCategory\w*|refetch)\s*\(")


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


#: 統計卡的 <Col> 網格判準（§2.6 ①）。兩種壞法，方向相反：
#:   · `xs={24}` ⇒ 手機每張獨佔一列（規範明文禁止）
#:   · 完全沒有響應式 props（`span={4}`／`span={6}`）⇒ 手機 N 張擠一列，每張只剩幾十 px
#: 後者以前完全沒有判準，而它比前者更難讀（/security 的 6 張在 390px 各約 65px）。
_COL_CARD = re.compile(
    r"<Col([^>]*)>[\s\S]{0,200}?<(ClickableStatCard|Card\b[\s\S]{0,300}?<Statistic)", re.S)
_SPAN_ONLY = re.compile(r"{B}bspan=\{{(\d+)\}}".format(B=chr(92)))


def _grid_violations(src: str, rel: str) -> list:
    out = []
    for m in _COL_CARD.finditer(src):
        props = m.group(1)
        if "xs={24}" in props:
            out.append((rel, "（網格）",
                        "統計卡 Col 用 xs={24}＝手機每張獨立一列；規範＝xs={12}（同 /erp/quotations）"))
            continue
        if "xs=" in props:
            continue
        sp = _SPAN_ONLY.search(props)
        if sp:
            n = int(sp.group(1))
            per = 24 // n if n else 0
            # ⚠️ 只有「手機每列超過 2 張」才是問題。`span={12}` 在手機上就是兩張一列，
            # 正是規範要的形狀（xs={12}）——首版把它一起報，47 筆裡有一半是這種假陽性。
            # 判準要問「使用者在 390px 看到什麼」，不是問「有沒有照著寫 xs=」。
            if per <= 2:
                continue
            out.append((rel, "（網格）",
                        f"統計卡 Col 只有 span={{{n}}}、沒有 xs ⇒ 手機 {per} 張擠一列"
                        f"（390px 下每張約 {390 // per}px）；規範＝xs={{12}} sm={{6}}"))
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
        rel = f.relative_to(PAGES).as_posix()
        # 2026-09-09：原本「沒有 <ClickableStatCard> 就整檔跳過」⇒ 網格判準也一起跳過。
        # 全庫 <ClickableStatCard 81 處，而 <Statistic 有 328 處 —— 用 <Card><Statistic> 寫的
        # 統計卡（/security 的 span={4}×6、UserStatsCards／EvolutionTab 的 xs={24}）
        # **結構上永遠看不見**。網格改成兩種寫法都驗；接線判準仍只驗 ClickableStatCard（它才有 onClick 契約）。
        grid_yels = _grid_violations(src, rel)
        # 依檔聚合：同一個檔的四張卡是同一個問題，逐張列出只是噪音。
        # 「8 個檔 44 處」是可以追的，「44 行一模一樣的字」不是。
        if grid_yels:
            kinds = sorted({g[2] for g in grid_yels})
            yels.append((rel, "（網格）", f"{len(grid_yels)} 處 —— " + "；".join(kinds)))
        if "<ClickableStatCard" not in src:
            continue
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
    print(f"卡片 {total} 張；假互動 {len(reds)}；純顯示未登記／網格不合 {len(yels)}")
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
