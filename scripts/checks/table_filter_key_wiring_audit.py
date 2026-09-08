#!/usr/bin/env python3
"""表頭篩選鍵接線稽核 —— owner 2026-09-09 問題 2 的守門。

問的問題：**表格宣告了表頭漏斗，那個勾選值有沒有人讀回去？**

為什麼需要它（存在的理由，不是它做了什麼）：
後端分頁的表格，一條篩選鏈有三處各自寫著它的名字 ——
欄位的 `key`、`filteredValue` 讀的參數名、`onChange` 裡**手寫的字串**。
`/erp/quotations` 的「年度」欄實例：key 是 `case_code`、值存 `params.year`、
onChange 寫 `first('case_code')`。**同一件事三個名字。**
把年度獨立成 `dataIndex: 'year'` 這種再正常不過的欄位調整，第三處立刻對不上
⇒ 漏斗點了沒有反應，而 tsc 全綠、主控台安靜、畫面上漏斗長得一模一樣。

⇒ 正解是 `frontend/src/utils/tableFilters.ts` 的 `buildServerFilters`：
一份宣告產生欄位片段與 onChange 解讀，改欄位鍵只改一個字，打錯字由 tsc 擋。
用了它的欄位本稽核直接放行。

判準的已知寬窄（**先寫下來**，2026-09-09 首跑校準過兩次）：
  * onChange 有四種手寫法（pickFilter / first('k') / pick('k') / filters?.k?.[0]），
    四種都認 —— 第一版只認 pickFilter，對兩個**參考實作**報出 7 個誤報。
  * 只看後端分頁樣式的欄位（有 filteredValue／serverFilter／bind，且無 onFilter）。
    帶 onFilter 的是全量在手，antd 自己處理，不在本稽核範圍。
  * 找不到 onChange 區塊的檔案不判（可能是詳情頁分頁），計入「略過」。

退出碼：0 = 沒有斷鏈；2 = 有斷鏈（真違規）。
"""
import io
import json
import os
import re
import sys

# Windows 主控台預設 cp950，訊息裡的符號會讓 print 直接崩掉（而不是印出亂碼）。
# weekly runner 把輸出導進檔案，那裡要的是 UTF-8。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 舊版 Python 或非 TextIO
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "frontend", "src")

BS = chr(92)
WS = "[" + BS + "s]"

TITLE_START = re.compile("[{]" + WS + "*(?://[^" + BS + "n]*" + BS + "n" + WS + "*)*title:")
KEY_PAT = re.compile("key:[ ]*'([A-Za-z0-9_]+)'")
DATAIDX_PAT = re.compile("dataIndex:[ ]*'([A-Za-z0-9_]+)'")
BIND_PAT = re.compile("[.]bind[(]'([A-Za-z0-9_]+)'[)]")
ONCHANGE_START = re.compile("onChange=[{][(]_?[A-Za-z]*[,]")


def anchors(s):
    """找出每個「篩選宣告」與它所屬的欄位鍵，以及那一欄是不是全量在手。

    ⚠️ **刻意不做大括號配對**：欄位的 render 裡有 JSX 與模板字串（`${a}（${b}）`），
    大括號在字串裡不成對，配對法會把好幾個欄位吞進同一塊。
    2026-09-09 首版就是這樣，三個檔案裡 2/3/5 個宣告只認出 1/2/1 個 ——
    **而它報 0 違規，看起來一切正常**。解析度不足的症狀就是一片綠。

    改用「兩個 title: 之間」當欄位範圍：欄位在陣列裡是一個接一個宣告的，
    相鄰兩個 `title:` 之間就是一欄，不必解析括號。
    """
    titles = [m.start() for m in re.finditer("title:", s)]

    def field_span(i):
        prev = 0
        for t in titles:
            if t < i:
                prev = t
            else:
                return s[prev:t]
        return s[prev : i + 600]

    out = []
    for m in re.finditer("filteredValue:", s):
        i = m.start()
        span = field_span(i)
        km = None
        for km2 in KEY_PAT.finditer(span):
            km = km2
        if km is None:
            for km2 in DATAIDX_PAT.finditer(span):
                km = km2
        out.append((km.group(1) if km else None, "onFilter" in span, False))
    for m in BIND_PAT.finditer(s):
        out.append((m.group(1), False, True))
    return out


def onchange_region(s):
    """取出 Table onChange 的內容（到該 arrow function 的結尾為止）。"""
    out = []
    for m in ONCHANGE_START.finditer(s):
        j = s.index("{", m.start())
        depth = 0
        k = j
        while k < len(s):
            if s[k] == "{":
                depth += 1
            elif s[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        out.append(s[j : k + 1])
    return "".join(out)


def reads_key(region, key):
    """onChange 裡有沒有以任一種寫法讀這個欄位鍵。None = 無從判斷。"""
    if not region:
        return None
    if ("'" + key + "'") in region:
        return True
    if re.search("filters[?]?[.]" + key + "[^A-Za-z0-9_]", region):
        return True
    return False


def main():
    broken = []
    converged = []
    skipped = []
    unresolved = []
    low_res = []
    checked = 0
    for root, _dirs, files in os.walk(SRC):
        for f in files:
            if not f.endswith(".tsx"):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            s = io.open(p, encoding="utf-8").read()
            if "filteredValue" not in s and "serverFilter(" not in s and ".bind(" not in s:
                continue
            region = onchange_region(s)
            declared = s.count("filteredValue:") + len(BIND_PAT.findall(s))
            seen = 0
            for key, has_onfilter, is_bind in anchors(s):
                # 認出來了就算解析成功 —— 「這一欄是全量在手所以不管」是判斷結果，
                # 不是解析失敗。首版把兩者混在一起，解析度被自己的排除規則拉低。
                seen += 1
                if has_onfilter:
                    continue
                checked += 1
                if is_bind:
                    converged.append((rel, key))
                    continue
                if key is None:
                    unresolved.append(rel)
                    continue
                r = reads_key(region, key)
                if r is None:
                    skipped.append((rel, key))
                elif not r:
                    broken.append((rel, key))
            # 解析度下限：認不出來的宣告太多 ⇒ 這一份結果不可信，不得當成綠燈
            if declared and seen < declared * 0.8:
                low_res.append((rel, seen, declared))

    print("=" * 68)
    print("表頭篩選鍵接線稽核（weekly）")
    print("=" * 68)
    print("後端分頁樣式的篩選欄位：%d" % checked)
    print("  已收斂到 buildServerFilters：%d" % len(converged))
    print("  找不到 onChange，不判：%d" % len(skipped))
    print("  ⛔ 宣告了漏斗而 onChange 讀不到那個鍵：%d" % len(broken))
    for rel, key in broken:
        print("     %s  欄位鍵 '%s'" % (rel, key))
    if unresolved:
        print("  找不到所屬欄位鍵：%d（%s）" % (len(unresolved), ", ".join(sorted(set(unresolved))[:3])))
    if low_res:
        print()
        print("⛔ 解析度不足，本次結果不可信：")
        for rel, seen, declared in low_res:
            print("     %s 只認出 %d/%d 個宣告" % (rel, seen, declared))
    if skipped:
        print("  （略過清單，前 10 筆）")
        for rel, key in skipped[:10]:
            print("     %s  '%s'" % (rel, key))

    report = {
        "checked": checked,
        "converged": len(converged),
        "skipped": len(skipped),
        "unresolved": len(unresolved),
        "low_resolution": [{"file": r, "seen": a, "declared": b} for r, a, b in low_res],
        "broken": [{"file": r, "key": k} for r, k in broken],
    }
    outdir = os.path.join(ROOT, "wiki", "memory", "integration-health")
    if os.path.isdir(outdir):
        io.open(
            os.path.join(outdir, "table_filter_key_wiring.json"), "w", encoding="utf-8"
        ).write(json.dumps(report, ensure_ascii=False, indent=2))

    if low_res:
        print()
        print("⛔ 解析度低於下限（80%）—— 綠燈不成立，先修判準再談結論。")
        return 2

    if broken:
        print()
        print("⛔ 修法：改用 frontend/src/utils/tableFilters.ts 的 buildServerFilters ——")
        print("   一份宣告產生欄位片段與 onChange 解讀，欄位鍵打錯字由 tsc 擋下。")
        return 2
    print()
    print("✅ 沒有斷鏈")
    return 0


if __name__ == "__main__":
    sys.exit(main())
