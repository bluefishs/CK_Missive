#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""窄螢幕收斂判準：共用表格元件不得只看 `isMobile`。

## 為什麼有這一支（2026-08-29）

`useResponsive` 的 `isMobile = !screens.md`，而 AntD 的 md 斷點**就是 768**
⇒ 恰好 768px 時 `isMobile` 為 **false**，平板（768–991）走的是桌面分支。

於是共用表格元件若用 `isMobile` 當窄螢幕判準，平板會拿到為桌面挑的
固定 `scroll.x`（呼叫端常傳 1100~1530），**設定本身就在製造橫向捲動**。

`EnhancedTable` 2026-08-15 已把判準改成 `isMobile || isTablet`（< 992px），
但**沒有擴散到 `ResponsiveTable`** —— 兩個共用表格包裝各自一套行為，
23 個檔用的是沒修的那一個。實測 768px 外溢：
/taoyuan/dispatch 580px、/documents 586px、/contract-cases 581px、/staff 554px。

這是本 repo 反覆記過的形態：**正確做法存在、卻沒有窗口在問「有沒有擴散」**。
一次性修好一個元件擋不住另一個元件重演。

## 判準

掃 `frontend/src/components/common/` 底下的表格包裝元件（檔名含 Table）：

  RED  同時滿足：(a) 從 useResponsive 取了 isMobile
                 (b) 把 isMobile 用在 scroll / tableLayout / width 收斂上
                 (c) 檔內**沒有** isTablet 或 isNarrow

  ok   用 isNarrow / isMobile || isTablet，或根本不做窄螢幕收斂

## 刻意不做的

**不掃業務頁面自己的 `isMobile` 判斷**。頁面層用 isMobile 決定
「手機要不要顯示某個區塊」是合理的業務判斷（平板空間夠，該顯示）；
本規則要防的是**共用表格元件**把平板誤判成桌面，那是元件契約問題。

## 誰跑它

weekly step 81（`run_fitness_weekly.sh`）。
"""
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "frontend" / "src" / "components" / "common"

# ⚠️ 判準必須在**去掉註解之後**比對。
# 首版沒有去註解，負向對照當場揭穿：把 ResponsiveTable 的 isNarrow 改回
# isMobile 之後它**仍然回綠** —— 因為該檔的說明註解裡就寫著「isTablet」，
# `"isTablet" in t` 恆為真。判準命中的是我自己寫的散文，不是程式碼。
# 這正是本 repo 記過的「驗證訊號的粒度比被驗證的性質粗」。
COMMENT = re.compile(r"/\*[\s\S]*?\*/|//[^\n]*")


def _strip_comments(t: str) -> str:
    return COMMENT.sub("", t)


# 窄螢幕收斂的三個著力點 —— 用 isMobile 決定這些就是把平板當桌面
CONVERGENCE = re.compile(
    r"(scroll\s*=\s*\{[^}]*isMobile"
    r"|tableLayout\s*=\s*\{\s*isMobile"
    r"|isMobile\s*\?\s*\{[^}]*x:\s*undefined"
    r"|if\s*\(\s*isMobile\s*\)[\s\S]{0,120}width)"
)


def main() -> int:
    if not COMMON.is_dir():
        print(f"✗ 找不到 {COMMON} —— 無法判定（不視為通過）")
        return 2

    reds, checked = [], []
    for f in sorted(COMMON.glob("*.tsx")):
        if "Table" not in f.name or ".test." in f.name:
            continue
        t = _strip_comments(f.read_text(encoding="utf-8", errors="ignore"))
        if "useResponsive" not in t:
            continue
        checked.append(f.name)
        if not CONVERGENCE.search(t):
            continue  # 沒有做窄螢幕收斂，不在本規則範圍
        if "isTablet" in t or "isNarrow" in t:
            continue  # 已用 < 992px 判準
        reds.append(f.name)

    # 2026-08-29 擴大：**這個 bug 不只出現在共用元件**。
    # `MorningReportTrackingTable`（/taoyuan/dispatch 預設分頁）自己就寫著
    # `scroll={isMobile ? undefined : { x: 1050 }}` —— 同一個形狀、同樣在 768px
    # 強制橫向捲（實測外溢 580px），而它刻意不使用共用元件（理由已註明）。
    # 只掃 components/common/ 的話，這種**自己處理 RWD 的表格**永遠不會被看到。
    #
    # 判準收得很緊：只抓 `scroll` 或 `tableLayout` 用 isMobile 三元式且
    # 桌面分支帶固定 x 的寫法 —— 那是明確的「把平板當桌面」，不是風格問題。
    SRC = ROOT / "frontend" / "src"
    inline = re.compile(
        r"scroll=\{\s*isMobile\s*\?[^}]*\}|tableLayout=\{\s*isMobile\s*\?"
    )
    for f in sorted(SRC.rglob("*.tsx")):
        rel = str(f.relative_to(SRC)).replace("\\", "/")
        if "__tests__" in rel or ".test." in f.name or rel.startswith("components/common/"):
            continue
        t = _strip_comments(f.read_text(encoding="utf-8", errors="ignore"))
        if not inline.search(t):
            continue
        checked.append(rel)
        if "isTablet" not in t and "isNarrow" not in t:
            reds.append(rel)

    # 2026-08-29 第二次擴大：**同一個檔裡兩個判準不一致**。
    # `MorningReportTrackingTable` 把 scroll/tableLayout 改成 isNarrow 之後，
    # 底下「窄螢幕拿掉欄位固定 width + 藏次要欄」那一段**仍然是 isMobile** ——
    # 於是 768px 只做了一半：scroll.x 拿掉了，欄寬照樣加總到 1197px。
    # 走查的「哪個元素在撐寬」診斷指著 `<col>` 才抓到。
    #
    # 判準：檔內已經有 isNarrow（代表作者知道要含平板），卻仍用 isMobile
    # 決定欄位過濾或欄寬移除 ⇒ 半套。
    half = re.compile(
        r"isMobile[\s\S]{0,80}?(\.filter\(|\bwidth:\s*_|width:\s*_unusedWidth|HIDE_ON_MOBILE)"
        r"|(\.filter\(|HIDE_ON_MOBILE)[\s\S]{0,80}?isMobile"
    )
    for f in sorted(SRC.rglob("*.tsx")):
        rel = str(f.relative_to(SRC)).replace("\\", "/")
        if "__tests__" in rel or ".test." in f.name:
            continue
        t = _strip_comments(f.read_text(encoding="utf-8", errors="ignore"))
        if "isNarrow" not in t or "isMobile" not in t:
            continue
        if not half.search(t):
            continue
        if rel not in reds:
            reds.append(rel + "（同檔兩個判準不一致：scroll 用 isNarrow、欄寬/欄位過濾仍用 isMobile）")

    print("=" * 74)
    print("窄螢幕收斂判準：共用表格元件不得只看 isMobile（weekly 81）")
    print("=" * 74)
    print(f"\n  檢視 {len(checked)} 個共用表格元件：{', '.join(checked) or '（無）'}")

    if not checked:
        print("\n✗ 一個都沒掃到 —— 元件可能改了位置或命名，本檢核已失效")
        return 2

    for r in reds:
        print(f"\n  [RED  ] {r}")
        print("           用 isMobile 當窄螢幕判準 ⇒ 768–991px 的平板走桌面分支，")
        print("           會拿到為桌面挑的固定 scroll.x（呼叫端常傳 1100~1530）。")
        print("           改法：`const isNarrow = isMobile || isTablet;`（對照 EnhancedTable）")

    if reds:
        print(f"\nStatus: [RED] {len(reds)} 個共用表格元件把平板當桌面")
        return 1

    print("\n  （皆用 isMobile || isTablet，平板與手機同走窄螢幕分支）")
    print("\nStatus: [GREEN] 窄螢幕收斂判準一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
