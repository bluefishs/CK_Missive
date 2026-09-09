#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列表 ↔ 統計卡的**篩選參數同構**稽核（weekly 133，2026-09-09）。

## 為什麼要有這一支

owner 2026-09-09：「不要都是我人工復查報錯，自我檢核機制請精進」。
當天的實例：`/erp/quotations` 選承辦「邱元宏」＋02 類，列表 85 張、卡片卻是全公司 112 張的 21,493,663；
`/erp/client-accounts` 同條件是 5,057,835。真因＝列表的請求 schema 有 `staff_user_id`、
損益摘要的請求 schema **沒有** ⇒ 卡片不知道使用者選了誰。

既有兩支守門都看不到這個形狀：
* weekly 108 看前端「卡片有沒有接到篩選」——它接了，只是後端摘要不收那個欄位；
* weekly 131 用**身分**比列表與卡片的數字——身分一致，是**使用者自選的篩選**沒跟上。

## 判準（結構，不猜行為）

**統計卡是列表的分母（§2.6 ①），分母的參數集合必須涵蓋列表的篩選參數集合。**

對每一組（`…/list`，同前綴下的 `statistics|stats|summary|totals|overview|profit-summary|grouped-summary`）：

    缺 = 列表 schema 的篩選欄位 − 分頁／排序欄位 − 列表 schema 宣告的豁免 − 統計 schema 的欄位

缺非空 ⇒ RED。豁免寫在**列表 schema 上**（`STATS_EXEMPT: ClassVar[dict[str, str]] = {欄位: 理由}`），
和欄位宣告在同一個地方，改欄位的人看得到；不用基線檔。
豁免的正當理由只有一種：**那個欄位是卡片自己**（點卡片篩列表，卡片本身不隨之歸零——§2.6 ②）。

從 runtime 的 `app.routes` 讀，不掃字樣（weekly 131 首版就是靜態掃描誤報的）。
在容器內執行；host 上會透過 `lib.docker_exec.python_in` 進容器。

退出碼：0 GREEN／1 跑不起來（不下結論）／2 RED。
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.docker_exec import python_in  # noqa: E402
from lib.result_contract import write_result  # noqa: E402

LAYER = "list_stats_filter_parity"
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".list_stats_filter_baseline.json")

_PROBE = r'''
import json, re, importlib
from fastapi.routing import APIRoute
app = None
for _path, _mod in (("/app", "main"), ("/app/backend", "main"), ("/app", "app.main")):
    if _path not in sys.path:
        sys.path.insert(0, _path)
    try:
        _m = importlib.import_module(_mod)
        if getattr(_m, "app", None) is not None and hasattr(_m.app, "routes"):
            app = _m.app
            break
    except Exception as e:  # noqa: BLE001
        print("import fail", _mod, e, file=sys.stderr)
if app is None:
    print("@@JSON@@" + json.dumps({"error": "app not importable"}))
    raise SystemExit(0)

PAGING = {"page", "limit", "skip", "offset", "page_size", "size", "cursor",
          "sort_by", "sort_order", "order_by", "order", "sort", "sort_field", "sort_direction"}
STAT_LEAVES = {"statistics", "stats", "summary", "totals", "overview", "profit-summary", "grouped-summary", "filtered-statistics"}

def body_model(route):
    # FastAPI 0.135／pydantic v2：ModelField 沒有 type_，型別在 field_info.annotation。
    # 首版用 type_ ⇒ 13 組全部 None → None 而印 GREEN（假綠，2026-09-09 當場抓到）。
    for p in getattr(route.dependant, "body_params", []) or []:
        ann = getattr(getattr(p, "field_info", None), "annotation", None) or getattr(p, "type_", None)
        if ann is not None and hasattr(ann, "model_fields"):
            return ann
    return None

def fields(model):
    return set(model.model_fields.keys()) if model is not None else set()

groups = {}
for r in app.routes:
    if not isinstance(r, APIRoute) or "POST" not in r.methods:
        continue
    pre, _, leaf = r.path.rpartition("/")
    groups.setdefault(pre, {})[leaf] = r

pairs = []
for pre, leaves in sorted(groups.items()):
    if "list" not in leaves:
        continue
    stats = [l for l in leaves if l in STAT_LEAVES]
    if not stats:
        continue
    # 同前綴同時有 statistics（全域、無 body、儀表板用）與 filtered-statistics（列表卡片的分母）時，
    # 分母是後者；把全域那支拿掉，否則 documents 永遠報「statistics 缺 12 欄」而那不是卡片在用的端點。
    if "filtered-statistics" in stats and "statistics" in stats:
        stats.remove("statistics")
    lm = body_model(leaves["list"])
    exempt = dict(getattr(lm, "STATS_EXEMPT", {}) or {}) if lm is not None else {}
    lfields = fields(lm) - PAGING
    for leaf in sorted(stats):
        sm = body_model(leaves[leaf])
        sfields = fields(sm)
        missing = sorted(lfields - set(exempt) - sfields)
        pairs.append({
            "prefix": pre, "stat_leaf": leaf,
            "list_model": getattr(lm, "__name__", None), "stat_model": getattr(sm, "__name__", None),
            "list_filters": sorted(lfields), "stat_fields": sorted(sfields),
            "exempt": exempt, "missing": missing,
        })
print("@@JSON@@" + json.dumps({"pairs": pairs}, ensure_ascii=False))
'''


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    print("=== 列表 ↔ 統計卡 篩選參數同構（weekly 133）===")
    out = python_in(_PROBE, timeout=180)
    data = None
    for line in (out or "").splitlines():
        if line.startswith("@@JSON@@"):
            data = json.loads(line[len("@@JSON@@"):])
    if not data or "pairs" not in data:
        print("  ⚠️ 容器內探測沒有回傳結果（容器不在／app 載入失敗）—— 不下結論")
        write_result(LAYER, 1, "probe failed", {"raw": (out or "")[-300:]})
        return 1

    pairs = data["pairs"]
    if pairs and all(p["list_model"] is None for p in pairs):
        print("  ⚠️ 每一組的列表 schema 都讀不到 —— probe 失效，不下結論（這正是首版的假綠）")
        write_result(LAYER, 1, "probe read no models", {"pairs": len(pairs)})
        return 1
    # 存量走基線（新增即紅、存量逐一清；同 weekly 132 的作法）
    base = {}
    if os.path.isfile(BASELINE):
        base = json.load(open(BASELINE, encoding="utf-8")).get("allow", {})
    cleared = []
    for p in pairs:
        key = f"{p['prefix']}/{p['stat_leaf']}"
        allowed = set((base.get(key) or {}).keys())
        p["baseline"] = sorted(allowed & set(p["missing"]))
        gone = sorted(allowed - set(p["missing"]))
        if gone:
            cleared.append(f"{key}: {', '.join(gone)}")
        p["missing"] = sorted(set(p["missing"]) - allowed)
    red = [p for p in pairs if p["missing"]]
    print(f"  端點對：{len(pairs)}（有 list 且同前綴下有統計端點）")
    for p in pairs:
        mark = "⛔" if p["missing"] else "✅"
        ex = f"  豁免={','.join(p['exempt'])}" if p["exempt"] else ""
        print(f"  {mark} {p['prefix']}/list → /{p['stat_leaf']}  [{p['list_model']} → {p['stat_model']}]{ex}")
        if p["missing"]:
            print(f"       ⛔ 新缺：{', '.join(p['missing'])}")
        if p.get("baseline"):
            print(f"       （基線存量待清：{', '.join(p['baseline'])}）")
    if cleared:
        print("  ✅ 已清掉（可從基線移除）：")
        for c in cleared:
            print(f"     {c}")
    print()
    if red:
        print(f"Status: [RED] {len(red)} 組統計端點收不到列表的篩選欄位 —— 卡片的分母比列表寬。")
        print("  修法：統計請求 schema 補上該欄位並在 service 套用；若那個欄位是「卡片自己」，")
        print("  在列表 schema 加 `STATS_EXEMPT = {欄位: 理由}` 宣告（與欄位放在一起，不用基線檔）。")
        rc = 2
    else:
        print("Status: [GREEN] 所有統計端點的參數都涵蓋列表的篩選欄位")
        rc = 0
    write_result(LAYER, rc, f"{len(red)}/{len(pairs)} pairs missing filters (baseline {sum(1 for p in pairs if p.get('baseline'))})",
                 {"pairs": pairs, "red": [f"{p['prefix']}/{p['stat_leaf']}: {p['missing']}" for p in red]})
    return rc


if __name__ == "__main__":
    sys.exit(main())
