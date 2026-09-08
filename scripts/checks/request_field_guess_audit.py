#!/usr/bin/env python3
"""請求物件的「猜」欄位稽核 —— owner 2026-09-09：「為何還有『猜』機制，是否對應架構不完善」。

問的問題：**schema 明明宣告了這個欄位，為什麼還要用 `getattr(..., None)` 去問？**

`getattr(params, "staff_user_id", None)` 對一個 Pydantic 請求物件的意思是
「有就給我，沒有就算了」。而 Pydantic 的請求物件**欄位是固定的** ——
真正會發生的情況只有一種：**有人改了 schema 的欄位名**。
那一刻它不會報錯，只會靜默變成 `None` ⇒ 篩選悄悄失效，畫面顯示全部資料，
而使用者以為自己看到的是篩過的結果。

這與 09-09 同日的兩個事故同型（表頭篩選鍵三處分家、承辦身分合併沒展開）：
**同一件事有兩份宣告，改一份另一份不動，沒有任何一方報錯。**
改成直接屬性存取之後，改名會當場 `AttributeError` —— 會吵的錯誤才修得掉。

判準：`getattr(<請求變數>, "<欄位>", None)` 且該欄位**在對應 schema 類別裡查得到**
⇒ RED。查不到的不判（那可能是多型物件或 ORM 實體，防禦是合理的）。

⚠️ 型別靠函式簽章的註解回推。查不到型別就不判 —— 寧可漏報也不誤報，
因為誤報會讓人把合法的防禦性寫法拆掉。

退出碼：0 = 沒有；2 = 有。
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

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND = os.path.join(ROOT, "backend")
NL = chr(10)
Q = chr(39)


def schema_fields() -> dict:
    """每個 schema 類別在**自己本體**宣告的欄位（不含繼承 —— 寧可漏報）。"""
    out: dict = {}
    base = os.path.join(BACKEND, "app", "schemas")
    for root, _d, files in os.walk(base):
        for f in files:
            if not f.endswith(".py"):
                continue
            s = io.open(os.path.join(root, f), encoding="utf-8").read()
            for m in re.finditer("class ([A-Za-z0-9_]+)[(]", s):
                cls, i = m.group(1), m.end()
                nxt = s.find(NL + "class ", i)
                body = s[i : nxt if nxt > 0 else len(s)]
                out.setdefault(cls, set()).update(
                    re.findall("^ +([a-z_][a-z0-9_]*): ", body, re.M)
                )
    return out


PAT = re.compile(
    "getattr[(](params|req|request|data)[,] *[" + Q + '"]([a-z_]+)[' + Q + '"][,] *None[)]'
)


def main() -> int:
    fields = schema_fields()
    hits = []
    skipped = 0
    for root, _d, files in os.walk(os.path.join(BACKEND, "app")):
        for f in files:
            if not f.endswith(".py"):
                continue
            p = os.path.join(root, f)
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            s = io.open(p, encoding="utf-8").read()
            for m in PAT.finditer(s):
                var, fld = m.group(1), m.group(2)
                head = s[: m.start()]
                tm = None
                for t in re.finditer(var + ": *([A-Za-z_][A-Za-z0-9_]*)", head):
                    tm = t
                typ = tm.group(1) if tm else None
                if typ is None or typ not in fields:
                    skipped += 1
                    continue
                if fld in fields[typ]:
                    hits.append((rel, s[: m.start()].count(NL) + 1, var, fld, typ))

    print("=" * 68)
    print("請求物件的「猜」欄位稽核（weekly）")
    print("=" * 68)
    print("已載入 schema 類別：%d" % len(fields))
    print("型別回推不出來、不判：%d 處" % skipped)
    print("⛔ schema 已宣告卻仍用 getattr 去猜：%d 處" % len(hits))
    for rel, line, var, fld, typ in hits:
        print("     %s:%d  %s.%s（%s 有宣告）" % (rel, line, var, fld, typ))

    outdir = os.path.join(ROOT, "wiki", "memory", "integration-health")
    if os.path.isdir(outdir):
        io.open(os.path.join(outdir, "request_field_guess.json"), "w", encoding="utf-8").write(
            json.dumps({"hits": len(hits), "skipped": skipped}, ensure_ascii=False, indent=2)
        )

    if hits:
        print()
        print("⇒ 修法：改成直接屬性存取（`params.staff_user_id`）。")
        print("   schema 宣告過的欄位不會突然消失 —— 會消失的唯一原因是有人改了名字，")
        print("   而那一刻應該當場 AttributeError，不是靜默變 None 讓篩選失效。")
        return 2
    print()
    print("✅ 沒有對已宣告欄位的猜")
    return 0


if __name__ == "__main__":
    sys.exit(main())
