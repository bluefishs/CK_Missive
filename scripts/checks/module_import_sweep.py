#!/usr/bin/env python
"""每一個模組都必須真的能被匯入 —— 消滅「匯入即失敗但沒有人在匯入它」這個家族。

## 為什麼需要這一支

2026-08-13 覆盤時發現三個彼此無關的缺陷，形狀完全一樣：

| 模組 | 壞在哪 | 壞了多久 | 症狀 |
|---|---|---|---|
| `extended/models/tender_cache.py` | `text` 未定義（`_base` 給的是 `Text` 型別） | 至少 2026-05-27 起 | AI 跨圖譜搜尋、統一圖譜標案分支、案件流程追蹤**全部** 失敗，log 只有一行 `Tool ... failed` |
| `services/wiki/compiler.py` | `from ... import AgentTrace`（該模組只有 `AgentQueryTrace`） | 三個多月 | 模組 wiki 整週沒編譯，而 job 週週 success |
| `repositories/pm/staff_repository.py`＋`services/pm/staff_service.py` | `PMCaseStaff` 於 v5.2.0 移除 | 自 v5.2.0 | 無人使用的孤兒，但會讓任何想用它的人炸掉 |

共通結構是三層疊起來的：

1. 模組**不在** `__init__.py` 的匯出清單裡 → 應用啟動時不會碰到它
2. 消費端用**函式內的延遲匯入** → 只有真的走到那條路徑才會執行 import
3. 上層 `except` 把它 catch 成一行 warning → 使用者看到的是「沒有結果」而不是錯誤

三層都很合理，疊起來的結果是：**一個模組可以壞好幾個月，而所有訊號都是綠的。**
py_compile 抓不到（語法沒錯）、型別檢查抓不到（是執行期名稱解析）、
測試抓不到（沒有測試會 import 它）、走查抓不到（頁面不經過那條路徑）。

唯一能抓到的辦法就是**真的把每個模組都匯入一次**，而那正是本支做的事。

## 判準

- 匯入失敗 = RED。不分「有沒有人在用」——沒有人在用的壞模組，
  是在等下一個想用它的人踩到（上表第三列就是這樣躺了好幾個月）。
- 刻意**不**做「只掃有人 import 的模組」：那會退化成「已知的都沒事」，
  而這個家族的定義就是「沒有人在匯入它」。

## 執行環境

必須在**應用實際執行的環境**跑（容器內），因為它要的是真實依賴。
host 端缺 asyncpg/pgvector 之類的套件會產生一整片假紅 → 本支偵測到
不在應用環境時直接拒絕執行（exit 2），不給假綠也不給假紅。
"""
from __future__ import annotations

import importlib
import os
import pkgutil
import sys
import traceback

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 匯入時本來就會有副作用（連 DB、起 client）的模組不在此列——
# 目前沒有需要豁免的；若將來要加，**理由必須寫在這裡**，
# 而不是留在某次 commit message 裡。
EXEMPT: dict[str, str] = {}


def _app_root() -> str | None:
    """應用套件根目錄。容器內是 /app/app；host 是 <repo>/backend/app。"""
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(here))
    for base, pkg in (("/app", "/app/app"), (repo, os.path.join(repo, "backend", "app"))):
        if os.path.isdir(pkg):
            return base if base == "/app" else os.path.join(repo, "backend")
    return None


def main() -> int:
    print("=" * 70)
    print("模組匯入掃描（每一個模組都必須真的能被匯入）")
    print("=" * 70)

    base = _app_root()
    if base is None:
        print("✗ 找不到 app 套件 —— 無法判定（不視為通過）")
        return 2
    sys.path.insert(0, base)

    # 應用環境探測：缺了真實依賴就會整片假紅，那比不跑更糟
    try:
        importlib.import_module("app.db.database")
    except Exception as e:
        print(f"✗ 這裡不是應用執行環境（app.db.database 匯入失敗：{type(e).__name__}）")
        print("  → 本支必須在 backend 容器內執行；host 端缺套件會產生一整片假紅")
        return 2

    pkg_dir = os.path.join(base, "app")
    failures: list[tuple[str, str, str]] = []
    scanned = 0
    for mod in pkgutil.walk_packages([pkg_dir], prefix="app."):
        name = mod.name
        if name in EXEMPT:
            continue
        scanned += 1
        try:
            importlib.import_module(name)
        except Exception as e:
            failures.append((name, type(e).__name__, str(e).splitlines()[0][:160]))

    print(f"\n掃描 {scanned} 個模組｜豁免 {len(EXEMPT)} 個｜失敗 {len(failures)} 個\n")
    if not failures:
        print("Status: [GREEN] 全部模組皆可匯入")
        return 0

    print(f"Status: [RED] {len(failures)} 個模組匯入即失敗：")
    for name, kind, msg in failures:
        print(f"  [{kind}] {name}")
        print(f"      {msg}")
    print("\n→ 這類缺陷不會讓應用起不來，只會在有人真的走到那條路徑時失敗，")
    print("  而且通常被上層 catch 成一行 warning。壞多久取決於多久沒人走過去。")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
