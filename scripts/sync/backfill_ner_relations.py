#!/usr/bin/env python
"""補抽 NER 關係：只針對「有實體卻沒有任何關係」的存量公文。

## 這是什麼

2026-08-03 修好 NER 關係抽取後，新公文都正常抽到關係，
但修法前累積的公文**排程永遠不會回頭處理** ——
待處理判準問的是「有沒有 entities」，要產出的卻是 relations。

現況（2026-08-15 量測）：572 份公文有 >=2 個實體卻零關係，
最新一筆停在 2026-07-31（修法日之前），**不再成長**。

## 為什麼是一次性腳本，而不是改排程判準

把待處理判準改成「沒有 relations」會踩另一個坑：
**真的沒有關係的公文是合法的**（LLM 抽出實體但它們之間確實沒關係），
那些公文會被每一輪重抽、永遠不滿足條件 —— 無限重抽且每次都花 LLM 呼叫。
要改判準得先有「抽過了」的標記，那是另一件事。

一次性補抽跑完之後，`ner_relation_regression_check`（weekly）
會繼續盯著「修法後有沒有又長出新的」。

## 用法

    python scripts/sync/backfill_ner_relations.py            # dry-run，只報數字
    python scripts/sync/backfill_ner_relations.py --apply    # 真的抽
    python scripts/sync/backfill_ner_relations.py --apply --limit 20   # 先試 20 份

**預設 dry-run**：這會發出數百次 LLM 呼叫，屬於有成本的動作，
不該因為誰不小心執行了腳本就發生。

跑完之後 relations 仍為 0 的公文是**正常的** ——
那代表 LLM 判定這些實體之間確實沒有關係，不是失敗。
腳本會把這種情形與「真的抽失敗」分開報。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# host 與容器結構不同，兩個都試（cron_silent_dormant_check 的教訓）
for cand in (Path(__file__).resolve().parents[2] / "backend",
             Path("/app")):
    if (cand / "app").is_dir():
        sys.path.insert(0, str(cand))
        break

GAP_SQL = """
SELECT de.document_id
FROM document_entities de
LEFT JOIN entity_relations er ON er.document_id = de.document_id
WHERE er.id IS NULL
GROUP BY de.document_id
HAVING COUNT(*) >= 2
ORDER BY de.document_id
"""


async def run(apply: bool, limit: int | None) -> int:
    from sqlalchemy import text
    from app.db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text(GAP_SQL))).scalars().all()

    doc_ids = list(rows)[: limit or None]
    print("=" * 70)
    print("補抽 NER 關係（有實體卻零關係的存量公文）")
    print("=" * 70)
    print(f"\n  符合條件：{len(rows)} 份"
          + (f"（本次處理前 {len(doc_ids)} 份）" if limit else ""))

    if not apply:
        print("\n  這是 dry-run，沒有發出任何 LLM 呼叫。")
        print(f"  真的要抽請加 --apply（會發出約 {len(doc_ids)} 次 LLM 呼叫）。")
        print("  建議先 --apply --limit 20 看抽出來的關係品質再全跑。")
        return 0

    from app.services.ai.document.entity_extraction_service import (
        extract_entities_for_document,
    )

    ok = rel_zero = failed = total_rel = 0
    for i, did in enumerate(doc_ids, 1):
        try:
            async with AsyncSessionLocal() as db:
                r = await extract_entities_for_document(db, did, commit=True)
            n = (r or {}).get("relations_count", 0)
            total_rel += n
            if n:
                ok += 1
            else:
                # 不是失敗：LLM 判定這些實體之間確實沒有關係
                rel_zero += 1
        except Exception as e:
            failed += 1
            print(f"  ✗ #{did}: {type(e).__name__}: {e}")
        if i % 25 == 0 or i == len(doc_ids):
            print(f"  ... {i}/{len(doc_ids)}｜抽到關係 {ok}｜確認無關係 {rel_zero}｜失敗 {failed}")

    print(f"\n  抽到關係：{ok} 份（共 {total_rel} 條）")
    print(f"  確認無關係：{rel_zero} 份 —— 這是正常結果不是失敗")
    print(f"  抽取失敗：{failed} 份")
    return 2 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="真的執行抽取（預設只 dry-run，因為會發出 LLM 呼叫）")
    ap.add_argument("--limit", type=int, default=None, help="只處理前 N 份")
    a = ap.parse_args()
    try:
        return asyncio.run(run(a.apply, a.limit))
    except Exception as e:
        print(f"\n✗ 執行失敗：{type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
