# -*- coding: utf-8 -*-
"""選單父階擋住角色拿得到的子項（weekly 119 判準 ⑤，2026-09-08）。

owner：「業務同仁仍可看到 erp 選單？」量了才知道方向相反——staff 角色有
專案帳款／委託帳款／協力帳款／政府標案四組的碼，但「報表分析」父群組要 `reports:view`，
staff 沒有 ⇒ 前端 `filterNavigationItems` 先問父階、父階不過整棵子樹消失。

每一層宣告單獨看都對（父有碼、子有碼、角色有子的碼），**鏈才是斷的**（L140 同型）。
這支只看資料表，不看前端程式碼：判準是「角色拿得到子項的碼、卻拿不到某個祖先的碼」。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.docker_exec import python_in  # noqa: E402

_QUERY = "\n".join([
    "import asyncio, json",
    "from sqlalchemy import text",
    "from app.db.database import AsyncSessionLocal",
    "async def m():",
    "    async with AsyncSessionLocal() as db:",
    "        roles = (await db.execute(text('SELECT role, permissions::text FROM role_permissions'))).all()",
    "        navs = (await db.execute(text(",
    "            \"SELECT id, parent_id, path, title, COALESCE(permission_required::text,'[]') \"",
    "            'FROM site_navigation_items WHERE is_enabled AND is_visible'))).all()",
    "    def j(v):",
    "        return json.loads(v) if isinstance(v, str) else (v or [])",
    "    print('@@' + json.dumps({'roles': [[r[0], j(r[1])] for r in roles],",
    "        'navs': [[n[0], n[1], n[2], n[3], j(n[4])] for n in navs]}))",
    "asyncio.run(m())",
])


def fetch_rows() -> dict | None:
    """從容器內讀角色權限與選單樹；連不到回 None（不得讀成沒問題）。"""
    out = python_in(_QUERY)
    line = [l for l in (out or "").splitlines() if l.startswith("@@")]
    return json.loads(line[-1][2:]) if line else None


def parent_gate_blocks(rows: dict) -> list[tuple[str, str, str]]:
    """回 [(role, child_path, blocking_parent_title)]，已排序去重。

    admin／superuser 不算（前端對管理員不過濾）；沒有 path 的是群組節點不算子項；
    子項本身角色就拿不到的不算（那是設計不是斷鏈）。
    """
    items = {n[0]: {"parent": n[1], "path": n[2], "title": n[3], "req": n[4] or []} for n in rows["navs"]}
    hits: set[tuple[str, str, str]] = set()
    for role, perms in rows["roles"]:
        if role in ("admin", "superuser"):
            continue
        ps = set(perms or [])
        for x in items.values():
            if not x["path"] or not x["req"] or not all(c in ps for c in x["req"]):
                continue
            pid = x["parent"]
            while pid in items:
                par = items[pid]
                if par["req"] and not all(c in ps for c in par["req"]):
                    hits.add((role, x["path"], par["title"] or str(pid)))
                    break
                pid = par["parent"]
    return sorted(hits)


def self_test() -> None:
    """負向控制：staff 沒有 reports:view 時必須抓到；有了就不能抓。判準壞了這裡先紅。"""
    navs = [
        [4, None, None, "報表分析", ["reports:view"]],
        [95, 4, None, "專案財務", ["reports:finance:view"]],
        [57, 95, "/erp/quotations", "專案帳款", ["reports:finance:view"]],
        [66, 4, None, "ERP財務", ["reports:erp:view"]],
        [92, 66, "/erp/ledger", "統一帳本", ["reports:ledger:view"]],
    ]
    bad = parent_gate_blocks({"roles": [["staff", ["reports:finance:view"]]], "navs": navs})
    assert bad == [("staff", "/erp/quotations", "報表分析")], bad
    ok = parent_gate_blocks({"roles": [["staff", ["reports:finance:view", "reports:view"]]], "navs": navs})
    assert ok == [], ok
    # 子項本身拿不到 ⇒ 不算（設計）
    none = parent_gate_blocks({"roles": [["user", ["reports:view"]]], "navs": navs})
    assert none == [], none
