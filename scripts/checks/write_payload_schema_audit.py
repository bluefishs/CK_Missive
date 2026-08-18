#!/usr/bin/env python
"""前端送出的寫入欄位，寫入端 schema 收得到嗎。

## 為什麼需要這一支（2026-08-18 事故）

08-17 我把 `schemas/erp/` 的 Create/Update 全部開了 `extra='forbid'`
（治「Pydantic 靜默丟棄」那個家族）。開之前有掃前端 payload，
掃出來是「0 個欄位缺失」。

**那次掃描找錯了比對對象。**

它用「欄位交集最大」去猜 payload 對應哪個 schema，而應收/應付填報頁
的 Create 與 Update **共用同一個 payload 物件**——交集最大的永遠是
Create（欄位比較多），於是 Update 缺 `erp_quotation_id` 這件事
完全沒有被看見。結果是：owner 一編輯任何一筆應收/應付就 422。

> **掃描找錯了比對對象，就等於沒掃。**
> 而它還會回一個「✅ 未發現問題」，比不掃更糟。

## 這一支怎麼做得不一樣

不猜。以 **API 端點常數**為錨：`*_UPDATE` 出現在哪個檔，
那個檔裡的 payload 就要對 **Update** schema 比對；`*_CREATE` 對 Create。
同一個 payload 若兩種都送，就必須同時滿足兩邊
（那正是這次的情形，而它不滿足 Update）。

## 判準邊界（刻意不做的事）

- **不掃非 ERP 模組**：其餘 schema 尚未開 `extra='forbid'`，
  多送的欄位會被靜默丟棄而不是 422 —— 那是另一個問題
  （由 `model_response_field_reach_audit` 的鏡像面處理），
  在這裡報出來只會是一長串沒有人能處理的清單。
- **不報「schema 有而前端沒送」**：那多半是選填欄位，正常。

判 RED：`extra='forbid'` 已經生效的模組裡，前端會送出而 schema
收不到的欄位 —— 那是**現在就會 422 的功能**，不是風險。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
BE = ROOT / "backend" / "app" / "schemas" / "erp"
FE = ROOT / "frontend" / "src"

# 這支要讀前端原始碼與後端 schema，兩者只在 repo 工作區裡。
# 容器內拿不到 → 明講不是這裡該跑的，而不是把每一項判成違規
# （2026-08-18 `enum_storage_convention_audit` 才踩過同型：
#  路徑問題被說成「清單過期」，看到的人會去改一份本來正確的清單）。
IN_REPO = FE.is_dir() and BE.is_dir()


def load_write_schemas() -> tuple[dict[str, set[str]], set[str]]:
    """回傳 ({schema 名: 欄位集}, {已開 forbid 的 schema 名})。"""
    fields: dict[str, set[str]] = {}
    forbid: set[str] = set()
    for f in sorted(BE.glob("*.py")):
        src = f.read_text(encoding="utf-8")
        for m in re.finditer(
            r"class (?P<n>\w*(?:Create|Update))\((?P<base>[^)]*)\):(?P<body>.*?)(?=\nclass |\Z)",
            src, re.S,
        ):
            name, body = m.group("n"), m.group("body")
            fs = set(re.findall(r"^\s{4}(\w+)\s*:", body, re.M))
            base = m.group("base").split(",")[0].strip()
            if base and base != "BaseModel":
                bm = re.search(rf"class {base}\([^)]*\):(?P<b>.*?)(?=\nclass |\Z)", src, re.S)
                if bm:
                    fs |= set(re.findall(r"^\s{4}(\w+)\s*:", bm.group("b"), re.M))
            fields[name] = fs
            if 'extra="forbid"' in body or "extra='forbid'" in body:
                forbid.add(name)
    return fields, forbid


def _payload_objects(src: str) -> list[str]:
    r"""抓出每個 `const payload ... ;` 宣告裡的**所有**物件字面值。

    ⚠️ 第一版用 `const payload[^=]*=\s*\{` 一條正則，要求 `=` 後面直接接 `{`。
    而實際寫法是**三元運算式**：

        const payload = isReceivable
          ? { erp_quotation_id: qid, ... }
          : { erp_quotation_id: qid, ... };

    於是它一個 payload 都沒抓到，然後印 GREEN ——
    **負向測試當場抓到：把修法還原它照樣說沒問題。**
    一支找不到東西就回綠的檢核，比沒有檢核更糟：它會讓人以為有人在看。

    改為掃到分號為止、逐字元配對大括號，把每個 top-level 物件都取出來。
    """
    out: list[str] = []
    for m in re.finditer(r"const\s+payload", src):
        i = m.end()
        depth = 0
        start = None
        while i < len(src):
            ch = src[i]
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    out.append(src[start + 1:i])
                    start = None
            elif ch == ";" and depth == 0:
                break
            i += 1
    return out


def main() -> int:
    print("=" * 74)
    print("寫入 payload vs 寫入端 schema（extra='forbid' 生效範圍）")
    print("=" * 74)
    print()

    if not IN_REPO:
        print("  ⊘ 此環境不含 repo 工作區（frontend/src 或 backend/app/schemas/erp 不在）")
        print("     本稽核須在 host 執行 —— 未判定，不代表通過。")
        return 0

    fields, forbid = load_write_schemas()
    if not forbid:
        print("  ⊘ 沒有任何寫入端 schema 開了 extra='forbid' —— 這支沒有管轄對象")
        return 0

    print(f"  寫入端 schema {len(fields)} 個，其中 {len(forbid)} 個已開 extra='forbid'")
    print()

    bad: list[tuple[str, str, str]] = []
    for tsx in list(FE.rglob("*.tsx")) + list(FE.rglob("*.ts")):
        if ".test." in tsx.name or "__tests__" in str(tsx):
            continue
        src = tsx.read_text(encoding="utf-8")
        if "ERP_ENDPOINTS" not in src:
            continue

        # 以端點常數為錨決定要比對哪一種 schema —— **不用欄位交集猜**
        kinds = []
        if re.search(r"ERP_ENDPOINTS\.\w*_UPDATE", src):
            kinds.append("Update")
        if re.search(r"ERP_ENDPOINTS\.\w*_CREATE", src):
            kinds.append("Create")
        if not kinds:
            continue

        for body in _payload_objects(src):
            keys = set(re.findall(r"^\s*(\w+)\s*:", body, re.M))
            if len(keys) < 3:
                continue
            for kind in kinds:
                # 在該類別裡挑欄位交集最大的（同類別內挑最像的是合理的；
                # 跨類別猜才是上次出錯的地方）
                cands = {n: f for n, f in fields.items() if n.endswith(kind)}
                best, sc = None, 0
                for n, f2 in cands.items():
                    ov = len(keys & f2)
                    if ov > sc:
                        best, sc = n, ov
                if not best or sc < 3 or best not in forbid:
                    continue
                extra = sorted(keys - fields[best])
                if extra:
                    rel = str(tsx.relative_to(FE)).replace("\\", "/")
                    bad.append((rel, best, ", ".join(extra)))

    if bad:
        print("🔴 前端會送出、而寫入端 schema 收不到的欄位（現在就會 422）：")
        for rel, name, extra in dict.fromkeys(bad):
            print(f"      ✗ {rel}")
            print(f"          → {name} 缺：{extra}")
        print()
        print("  二選一：①該欄位真的可寫 → 加進 schema；")
        print("          ②該欄位不該在此情境送出（如更新時送 erp_quotation_id）→ 前端別送。")
        print()
        print("  ⚠️ 這不是風險是**現行故障** —— extra='forbid' 之下，")
        print("     使用者按下儲存就是 422，而錯誤訊息指向一個他沒動過的欄位。")
        print("\nStatus: [RED] 有欄位送得出去但收不到")
        return 2

    print("  🟢 forbid 生效範圍內，前端送出的欄位 schema 都收得到")
    print("\nStatus: [GREEN] 寫入契約一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
