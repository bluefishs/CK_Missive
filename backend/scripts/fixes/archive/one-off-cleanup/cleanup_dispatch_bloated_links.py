"""
cleanup_dispatch_bloated_links.py - 清理派工單爆量公文關聯

精確排除策略：
1. 剝離通用合約名稱前綴
2. 檢查剩餘文字是否提及其他派工單的專屬地名
3. 純通用合約文件（無地名）保留
4. 被作業紀錄引用的關聯永遠保留

用法:
    cd backend
    python -m scripts.fixes.cleanup_dispatch_bloated_links --dry-run
    python -m scripts.fixes.cleanup_dispatch_bloated_links --apply

@date 2026-03-12
"""

import asyncio
import argparse
import logging
import re
import sys
from pathlib import Path

# 確保 backend 目錄在 sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir.parent / '.env')

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# 與 dispatch_order_service.py 相同的常數
GENERIC_DOC_PATTERNS = [
    r'契約書', r'教育訓練', r'系統建置', r'開口契約',
    r'履約保證', r'保險', r'印鑑', r'投標', r'決標',
    r'簽約', r'工作計畫書', r'採購案',
]

# 剝離通用合約名稱前綴
CONTRACT_PREFIX_RE = re.compile(
    r'(?:檢送|請領|有關|為)?(?:本公司|貴公司|本局)?'
    r'(?:辦理|承攬|所提|提送|檢送)?'
    r'[「『]?'
    r'115年度桃園市[^\u3000-\u303F」』）)]*?(?:開口契約)[」』）)]*'
    r'[」』）)]*'
    r'[案之的一]*[，,\-\s]*'
)

RELEVANCE_THRESHOLD = 0.15


def extract_core_identifiers(project_name: str) -> list[str]:
    """從 project_name 提取核心辨識詞"""
    ids: list[str] = []
    if not project_name:
        return ids

    m = re.search(r'派工單[號]?\s*(\d{2,4})', project_name)
    if m:
        ids.append(f"派工單{m.group(1)}")

    for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:路|街))', project_name):
        name = m.group(1)
        if name not in ids and len(name) >= 3:
            ids.append(name)

    for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:公園|廣場|用地))', project_name):
        if m.group(1) not in ids:
            ids.append(m.group(1))

    m = re.search(r'([\u4e00-\u9fff]{1,3}[區鄉鎮市])', project_name)
    if m and m.group(1) not in ids:
        ids.append(m.group(1))

    return ids


def extract_location_identifiers(project_name: str) -> list[str]:
    """只提取路名/公園/派工單號（用於反向排除，不含行政區）"""
    ids: list[str] = []
    if not project_name:
        return ids

    m = re.search(r'派工單[號]?\s*[（(]?\s*(\d{2,4})\s*[）)]?', project_name)
    if m:
        ids.append(f"派工單({m.group(1).lstrip('0') or '0'})")
        ids.append(f"派工單{m.group(1)}")

    for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:路|街))', project_name):
        name = m.group(1)
        if name not in ids and len(name) >= 3:
            ids.append(name)

    for m in re.finditer(r'([\u4e00-\u9fff]{2,6}(?:公園|廣場|用地))', project_name):
        if m.group(1) not in ids:
            ids.append(m.group(1))

    return ids


def score_document_relevance(
    subject: str,
    core_ids: list[str],
    other_ids: list[str] | None = None,
) -> float:
    """計算公文相關性分數（含反向排除）"""
    if not subject:
        return 0.0

    # 1. 本派工單號完全匹配
    for cid in core_ids:
        if cid.startswith('派工單') and cid in subject:
            return 1.0

    # 2. 剝離合約前綴
    stripped = CONTRACT_PREFIX_RE.sub('', subject).strip()

    # 3. 其他派工單專屬地名 → 排除
    if other_ids:
        for oid in other_ids:
            if oid in subject:
                # 同時命中本派工單核心辨識詞 → 保留
                if any(cid in subject for cid in core_ids
                       if not cid.endswith('區')):
                    break
                return 0.0

    # 4. 通用合約文件判定
    is_generic = any(re.search(p, subject) for p in GENERIC_DOC_PATTERNS)
    if is_generic:
        remaining_locations = re.findall(
            r'[\u4e00-\u9fff]{2,6}(?:路|街|公園|廣場)', stripped
        )
        if not remaining_locations:
            return 0.5  # 純通用合約文件
        # 有地名但不是本派工單的
        if not any(cid in subject for cid in core_ids if not cid.endswith('區')):
            return 0.0
        return 0.5

    # 5. 核心辨識詞命中比率
    if not core_ids:
        return 0.0

    matched = sum(1 for cid in core_ids if cid in subject)
    return matched / len(core_ids)


async def main(dry_run: bool = True, threshold: int = 10):
    from sqlalchemy import text
    from app.db.database import engine as async_engine

    async with async_engine.connect() as conn:
        # 找出關聯公文數量超過門檻的派工單
        result = await conn.execute(text("""
            SELECT d.id, d.dispatch_no, d.project_name, d.work_type,
                   d.contract_project_id, cnt.doc_count
            FROM taoyuan_dispatch_orders d
            JOIN (
                SELECT dispatch_order_id, count(*) as doc_count
                FROM taoyuan_dispatch_document_link
                GROUP BY dispatch_order_id
                HAVING count(*) > :threshold
            ) cnt ON cnt.dispatch_order_id = d.id
            ORDER BY cnt.doc_count DESC
        """), {'threshold': threshold})
        bloated = result.fetchall()

        if not bloated:
            logger.info("沒有發現超過 %d 筆關聯的派工單", threshold)
            return

        logger.info("發現 %d 個爆量派工單:", len(bloated))
        for row in bloated:
            logger.info("  id=%d, %s, docs=%d, project=%s",
                        row[0], row[1], row[5], str(row[2])[:50])

        # 預先收集所有派工單的地名辨識詞（按合約分組）
        all_dispatches_result = await conn.execute(text("""
            SELECT id, dispatch_no, project_name, contract_project_id
            FROM taoyuan_dispatch_orders
        """))
        all_dispatches = all_dispatches_result.fetchall()

        # {contract_project_id: {dispatch_id: [location_ids]}}
        contract_dispatch_ids: dict[int | None, dict[int, list[str]]] = {}
        for d in all_dispatches:
            cpid = d[3]  # contract_project_id
            if cpid not in contract_dispatch_ids:
                contract_dispatch_ids[cpid] = {}
            contract_dispatch_ids[cpid][d[0]] = extract_location_identifiers(d[2] or '')

        total_removed = 0

        for row in bloated:
            dispatch_id = row[0]
            dispatch_no = row[1]
            project_name = row[2]
            contract_project_id = row[4]
            doc_count = row[5]

            core_ids = extract_core_identifiers(project_name or '')

            # 收集同合約其他派工單的辨識詞
            other_ids: list[str] = []
            if contract_project_id and contract_project_id in contract_dispatch_ids:
                for did, lids in contract_dispatch_ids[contract_project_id].items():
                    if did != dispatch_id:
                        for lid in lids:
                            if lid not in other_ids:
                                other_ids.append(lid)

            logger.info("\n--- 處理 %s (core=%s, others=%d) ---",
                        dispatch_no, core_ids, len(other_ids))

            # 取得該派工單的所有公文關聯 + 主旨
            links_result = await conn.execute(text("""
                SELECT dl.id as link_id, dl.document_id, d.subject,
                       (SELECT count(*) FROM taoyuan_work_records wr
                        WHERE (wr.document_id = dl.document_id
                               OR wr.incoming_doc_id = dl.document_id
                               OR wr.outgoing_doc_id = dl.document_id)
                          AND wr.dispatch_order_id = :dispatch_id
                       ) as record_refs
                FROM taoyuan_dispatch_document_link dl
                LEFT JOIN documents d ON d.id = dl.document_id
                WHERE dl.dispatch_order_id = :dispatch_id
            """), {'dispatch_id': dispatch_id})
            links = links_result.fetchall()

            to_remove = []
            to_keep = []

            for link in links:
                link_id, doc_id, subject, record_refs = link
                score = score_document_relevance(
                    subject or '', core_ids, other_ids=other_ids
                )

                if record_refs > 0:
                    to_keep.append((link_id, doc_id, score, '作業紀錄引用'))
                elif score >= RELEVANCE_THRESHOLD:
                    to_keep.append((link_id, doc_id, score, '相關'))
                else:
                    to_remove.append((link_id, doc_id, score, subject))

            logger.info("  保留: %d, 移除: %d", len(to_keep), len(to_remove))

            for link_id, doc_id, score, subject in to_remove[:5]:
                logger.info("    移除: link=%d, doc=%d, score=%.2f, %s",
                            link_id, doc_id, score, str(subject)[:60])
            if len(to_remove) > 5:
                logger.info("    ... 及其他 %d 筆", len(to_remove) - 5)

            if not dry_run and to_remove:
                for rid, _, _, _ in to_remove:
                    await conn.execute(text(
                        "DELETE FROM taoyuan_dispatch_document_link WHERE id = :id"
                    ), {'id': rid})
                total_removed += len(to_remove)
                logger.info("  已刪除 %d 筆關聯", len(to_remove))
            else:
                total_removed += len(to_remove)

        if not dry_run:
            await conn.commit()

        mode = "DRY-RUN" if dry_run else "APPLIED"
        logger.info("\n=== %s 完成: 共 %d 筆關聯%s ===",
                    mode, total_removed,
                    "將被移除" if dry_run else "已移除")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='清理派工單爆量公文關聯')
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='預覽模式 (預設)')
    parser.add_argument('--apply', action='store_true',
                        help='實際執行刪除')
    parser.add_argument('--threshold', type=int, default=10,
                        help='關聯數量門檻 (預設 10)')
    args = parser.parse_args()

    asyncio.run(main(dry_run=not args.apply, threshold=args.threshold))
