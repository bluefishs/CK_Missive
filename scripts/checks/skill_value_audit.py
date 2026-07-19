#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能系統真價值稽核（Skill-System Value Audit）— 誠實化「技能演化」KPI

★ 立法（2026-07-18）：owner「聚焦技能樹評估發展方向」。誠實評估揭發技能系統
  價值高度集中，「總學習數」是誤導性 KPI：
  - self_reflection（98%）：avg_hit≈1（用一次就沒了）＝累積噪音，弱模型內省天花板
  - tool_combo（1.5%）：avg_hit≈18、全 graduated＝真操作價值（業務查詢→工具映射，重用）
  - 靜態技能樹（108 skill 實體，v1.0 hardcode，一次性種子）＝裝飾展示非演化

  對齊 AI 重定位（AI_ROLE_REPOSITIONING.md）：技能系統真價值＝tool_combo 的「越用越會
  選工具」（操作型、業務直呼延伸），非 self_reflection 內省（弱模型天花板）。

  ★ 正確 KPI＝tool_combo graduated × hit_rate（操作價值），非總學習數。

host 側執行（DB 讀）。cp950 韌性。
用法：python scripts/checks/skill_value_audit.py [--strict]
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


async def audit():
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch("""
            SELECT learning_type,
                   COUNT(*) total,
                   COUNT(*) FILTER(WHERE graduation_status='graduated') graduated,
                   COALESCE(SUM(hit_count),0) total_hits,
                   ROUND(AVG(hit_count),1) avg_hit
            FROM agent_learnings GROUP BY 1 ORDER BY total_hits DESC
        """)
        ready = await conn.fetchval("""
            SELECT COUNT(*) FROM agent_learnings
            WHERE learning_type='tool_combo' AND graduation_status='graduated' AND hit_count>=5
        """)
        return rows, ready
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    print("=" * 66)
    print("技能系統真價值稽核（誠實化 KPI：操作型 tool_combo vs 內省噪音）")
    print("=" * 66)
    try:
        rows, ready = asyncio.run(audit())
    except Exception as e:
        print(f"[SKIP] DB 不可達：{e}")
        return 0

    print(f"\n{'學習型':<22}{'筆數':>7}{'graduated':>11}{'總hits':>9}{'avg_hit':>9}")
    tool_hits = total_hits = 0
    for r in rows:
        print(f"  {r['learning_type']:<20}{r['total']:>7}{r['graduated']:>11}{r['total_hits']:>9}{str(r['avg_hit']):>9}")
        total_hits += r["total_hits"]
        if r["learning_type"] == "tool_combo":
            tool_hits = r["total_hits"]

    print("\n--- 誠實 KPI ---")
    if total_hits:
        print(f"  tool_combo 貢獻 hit 佔比：{tool_hits}/{total_hits} = {tool_hits/total_hits*100:.0f}%（操作型真價值）")
    print(f"  可接確定性路由的高信心 tool_combo（graduated+hit≥5）：{ready}")
    print("\n→ 發展方向（AI_ROLE_REPOSITIONING）：放大 tool_combo（越用越會選工具，接確定性 Layer 1.5）；")
    print("  淡化 self_reflection（內省噪音、弱模型天花板）；靜態技能樹改稱『能力地圖』非『演化』。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
