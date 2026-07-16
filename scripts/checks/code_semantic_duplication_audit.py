#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程式圖譜語意異質同工偵測（Code-Graph Semantic Heterogeneous-Work Detector）

★ 立法緣起（2026-07-17）：owner 質疑「花那麼多時間建程式圖譜，難道不能自我
  優化與追蹤異質同工議題？」——本審計即為此問的正面回答：**活化既有程式圖譜
  （KG graph_domain=code，11.7k entity + 768D embedding）的潛在價值**，用 pgvector
  餘弦相似度自動發現「不同模組卻做同一件事」的異質同工候選。

  為何過去沒自動發現（誠實）：
  - 程式圖譜一直被當「結構地圖」用（L71），沒人對 embedding 下語意查詢
  - fitness/audit 是 pattern/whitelist 型（L71「寫死清單漏網」），無法發現未知重複
  - 學習閉環（crystallizer）只優化對話路由，無架構通道
  → embedding 早就在，只差把語意去重查詢接成機制。

偵測策略（單一相似對常是巧合，故聚合到「鏡像模組對」才是強信號）：
  1. 對指定 entity_type（預設 api_endpoint + service）找跨模組近乎相同的函式對（sim > 門檻）
  2. 聚合為 module-pair，計共享近重複數
  3. 共享 >= MIN_SHARED 的 module-pair ＝ 異質同工候選（供人/LLM triage 進登記表）

★ 能力邊界（誠實）：本審計**自動 surface 候選**（自我發現），但「真重複 vs 合理
  領域拆分」仍需人/LLM 判斷（如 graph_admin[KG域] vs graph_admin_code[code域] 是
  ADR-0031 刻意拆分）。故機制＝「自動撈 → triage → 登記表」，非全自動重構。

登記表：docs/architecture/HETEROGENEOUS_WORK_REGISTRY.md
host 側執行（read-only 查 KG）。cp950 韌性（L49.8）。
用法：
    python scripts/checks/code_semantic_duplication_audit.py            # 觀察（預設 api_endpoint+service）
    python scripts/checks/code_semantic_duplication_audit.py --types py_function --sim 0.96
    python scripts/checks/code_semantic_duplication_audit.py --strict   # 超 baseline exit 1
"""
from __future__ import annotations

import argparse
import asyncio
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import asyncpg
except ImportError:
    print("需要 asyncpg", file=sys.stderr)
    sys.exit(0)

DSN = "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents"

# 已 triage 判定為「合理領域拆分」的 module-pair（非異質同工，不再報）
LEGIT_SPLIT_WHITELIST = {
    # (排序後的 module-pair tuple): 理由
    ("app.api.endpoints.ai.graph_admin", "app.api.endpoints.ai.graph_admin_code"):
        "ADR-0031 GraphHub：KG 域 vs code 域，端點路徑不同、刻意拆分",
}

# 共享近重複函式數 >= 此值才算候選（單一對是巧合）
MIN_SHARED = 4
# 候選 module-pair 數 baseline（新候選出現即應 triage）
BASE_CANDIDATE_PAIRS = 99  # 首跑後由 owner 依實況調整


async def run(entity_types: list[str], sim_threshold: float) -> list[dict]:
    conn = await asyncpg.connect(DSN)
    try:
        type_list = "','".join(entity_types)
        rows = await conn.fetch(f"""
            WITH ce AS (
                SELECT id, canonical_name, embedding,
                       split_part(canonical_name,'::',1) AS mod,
                       split_part(canonical_name,'::',2) AS sym
                FROM canonical_entities
                WHERE graph_domain='code'
                  AND entity_type IN ('{type_list}')
                  AND embedding IS NOT NULL
            )
            SELECT a.mod AS mod_a, b.mod AS mod_b, a.sym AS sym_a, b.sym AS sym_b,
                   (1-(a.embedding <=> b.embedding)) AS sim
            FROM ce a JOIN ce b
              ON a.id < b.id
             AND a.mod <> b.mod
             AND (1-(a.embedding <=> b.embedding)) > $1
        """, sim_threshold)
    finally:
        await conn.close()

    # 聚合到 module-pair
    pairs: dict[tuple, dict] = {}
    for r in rows:
        key = tuple(sorted((r["mod_a"], r["mod_b"])))
        d = pairs.setdefault(key, {"shared": 0, "max_sim": 0.0, "examples": []})
        d["shared"] += 1
        d["max_sim"] = max(d["max_sim"], float(r["sim"]))
        if len(d["examples"]) < 3:
            d["examples"].append(f'{r["sym_a"]}~{r["sym_b"]} ({r["sim"]:.3f})')
    candidates = []
    for key, d in pairs.items():
        if d["shared"] >= MIN_SHARED and key not in LEGIT_SPLIT_WHITELIST:
            candidates.append({"pair": key, **d})
    candidates.sort(key=lambda x: (-x["shared"], -x["max_sim"]))
    return candidates


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", default="api_endpoint,service")
    ap.add_argument("--sim", type=float, default=0.95)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    types = [t.strip() for t in args.types.split(",") if t.strip()]

    print("=" * 68)
    print(f"程式圖譜語意異質同工偵測（types={types}, sim>{args.sim}, 共享>={MIN_SHARED}）")
    print("=" * 68)
    try:
        candidates = asyncio.run(run(types, args.sim))
    except Exception as e:
        print(f"[SKIP] DB 不可達或查詢失敗：{e}")
        return 0

    if not candidates:
        print("\nGREEN: 無新異質同工鏡像模組對候選")
        return 0

    print(f"\n發現 {len(candidates)} 個鏡像模組對候選（供 triage 進登記表）：\n")
    for c in candidates:
        a, b = c["pair"]
        print(f"  🔶 {a}")
        print(f"     ⇄ {b}")
        print(f"     共享 {c['shared']} 個近重複函式，max_sim={c['max_sim']:.3f}")
        print(f"     例：{'; '.join(c['examples'])}")
        print()

    over = len(candidates) > BASE_CANDIDATE_PAIRS
    print("=" * 68)
    print(f"候選 {len(candidates)} (baseline<= {BASE_CANDIDATE_PAIRS})")
    print("→ 這些是【線索非結論】：逐一人工/LLM 核實『真重複 vs 合理拆分』")
    print("→ 判定合理拆分者加入 LEGIT_SPLIT_WHITELIST；真重複者收斂 + 記登記表")
    if over and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
