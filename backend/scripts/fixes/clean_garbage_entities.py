"""
清理知識圖譜中的垃圾實體

功能：
1. 移除 mojibake / 控制字元 / 亂碼實體
2. 移除公文套語實體（檢送本公司、函送...等）
3. 移除代名詞實體（本府、本局 等）
4. 合併重複實體（同名不同 ID）
5. 降級低品質 date/topic 實體（mention_count <= 1 且無關係）
6. 統計清理結果

Usage:
    cd backend
    python -m scripts.fixes.clean_garbage_entities --dry-run   # 預覽
    python -m scripts.fixes.clean_garbage_entities              # 執行
"""

import asyncio
import argparse
import logging
import re
import sys
import unicodedata
from pathlib import Path

# 讓 scripts/ 下的腳本可以匯入 app 模組
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select, func, delete, update, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# 重用 entity_extraction_service 的過濾邏輯
# ============================================================================

def _normalize_nfkc(s: str) -> str:
    return unicodedata.normalize('NFKC', s).strip()


# 代名詞黑名單（與 entity_extraction_service.py 同步）
_PRONOUN_BLACKLIST = {
    '貴公司', '本公司', '該公司', '貴所', '本所', '該所',
    '貴局', '本局', '該局', '貴府', '本府', '該府',
    '貴會', '本會', '該會', '貴處', '本處', '該處',
    '貴署', '本署', '該署', '貴部', '本部', '該部',
    '貴院', '本院', '該院', '貴市', '本市', '該市',
    '貴機關', '本機關', '該機關', '貴單位', '本單位', '該單位',
    '台端', '臺端',
    '檢送', '函送', '檢附', '檢陳', '函復', '函覆', '函請',
    '敬請', '請查照', '查照', '請照辦', '照辦', '惠請', '鑒核',
    '敬陳', '敬會', '敬悉', '如說明', '如主旨', '復如說明',
    '奉核', '奉悉', '如擬', '准予備查', '准予核備',
    '核定', '備查', '鑒察', '鑒查', '轉陳', '轉請',
    '諒達', '敬請鑒核', '敬請查照', '敬請備查',
    '檢送本公司', '函送本公司', '檢附本公司',
    '承辦人', '主管', '機關', '單位',
    # 佔位符 / 簡體 / 無意義亂碼
    '實體名', '服务器',
    '司练南大家八室', '布八室', '服加八室',
}

_BOILERPLATE_PREFIXES = (
    '檢送', '函送', '檢附', '檢陳', '函復', '函覆', '函請',
    '敬請', '請查照', '查照', '請照辦', '惠請',
    '敬陳', '敬會', '敬悉', '奉核', '奉悉',
    '依據', '依照', '茲有', '茲將', '茲因', '茲檢',
    '有關', '關於', '為辦理', '為利', '為配合',
    '復貴', '復請',
)

_SIMPLIFIED_CHARS = set(
    '义组个体与专业严丰临为举么义乐习书买乱争于产亲亿从仅仓付价份众优伤传伦'
    '估体余佣侠侣侦侧侨俩俭债倾偶偿储儿兑党兰关兴养兹冈冲决况冻净凉减凤'
)


def is_garbage_entity(name: str, entity_type: str) -> str | None:
    """判斷實體是否為垃圾，回傳原因字串或 None"""
    if not name or len(name.strip()) == 0:
        return "empty"

    normalized = _normalize_nfkc(name)

    # 控制字元 / U+FFFD
    if '\ufffd' in normalized:
        return "mojibake(FFFD)"
    for ch in normalized:
        cp = ord(ch)
        if (0x00 <= cp <= 0x08) or (0x0B <= cp <= 0x0C) or (0x0E <= cp <= 0x1F) or (0x7F <= cp <= 0x9F):
            return f"control_char(U+{cp:04X})"

    # 同一字元重複 4+
    if re.search(r'(.)\1{3,}', normalized):
        return "repetition"

    # 隱私遮蔽符號
    if '○' in normalized or '〇' in normalized:
        return "privacy_mask"

    # 簡體字混入
    cjk_count = sum(1 for c in normalized if '\u4e00' <= c <= '\u9fff')
    simplified_count = sum(1 for c in normalized if c in _SIMPLIFIED_CHARS)
    if cjk_count > 0 and simplified_count / cjk_count > 0.3:
        return "simplified_chinese"

    # 代名詞黑名單
    if normalized in _PRONOUN_BLACKLIST:
        return "pronoun_blacklist"

    # 公文套語前綴
    if len(normalized) > 4 and any(normalized.startswith(p) for p in _BOILERPLATE_PREFIXES):
        return "boilerplate_phrase"

    # 過短（1 字元，人名除外）
    if len(normalized) <= 1 and entity_type != 'person':
        return "too_short"

    # 純代碼字串（機關代碼等，非實體名稱）
    if re.match(r'^[A-Z0-9]{6,}$', normalized, re.IGNORECASE):
        return "alphanumeric_code"

    # 金額（含全形數字、逗號、「萬」、「元整」等變體）
    if re.match(r'^[\d\d,，.．]+萬?[\d\d,，.．]*元', normalized):
        return "amount"
    # 「XX萬X,XXX元整」格式
    if re.search(r'\d+萬[\d,]+元', normalized):
        return "amount"

    # 工期 / 天數（不應歸為 date）
    if entity_type == 'date' and re.search(r'\d+日曆天|\d+工作天|\d+天|\d+個月', normalized):
        return "duration_not_date"

    # 過於通用的 topic 名稱（文件名/表單名/計畫書名）
    if entity_type == 'topic' and re.search(
        r'(修訂本|工作計畫書|回覆表|修正表|紀錄表|對照表|彙整表|統計表|清冊|明細表|一覽表)$',
        normalized
    ):
        return "generic_topic"

    return None


async def clean_entities(db_url: str, dry_run: bool = True):
    """主清理流程"""
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 取得所有 canonical_entities（排除 code graph 類型）
        code_types = ['py_module', 'py_class', 'py_function', 'db_table', 'ts_module', 'ts_component', 'ts_hook']
        result = await db.execute(
            text("SELECT id, canonical_name, entity_type, mention_count FROM canonical_entities "
                 "WHERE entity_type != ALL(:code_types) ORDER BY id"),
            {"code_types": code_types},
        )
        all_entities = result.fetchall()
        logger.info(f"公文圖譜共 {len(all_entities)} 個正規化實體")

        # 分類
        garbage = []  # (id, name, type, reason)
        low_quality = []  # date/topic with mention_count <= 1

        for eid, name, etype, mention_count in all_entities:
            reason = is_garbage_entity(name, etype)
            if reason:
                garbage.append((eid, name, etype, reason))
            elif etype in ('date', 'topic') and (mention_count or 0) <= 1:
                low_quality.append((eid, name, etype))

        # 重複實體偵測（同名同類型但不同 ID）
        name_type_map: dict[tuple[str, str], list[int]] = {}
        for eid, name, etype, _ in all_entities:
            key = (_normalize_nfkc(name), etype)
            name_type_map.setdefault(key, []).append(eid)
        duplicates = {k: v for k, v in name_type_map.items() if len(v) > 1}

        # 報告
        logger.info(f"\n{'='*60}")
        logger.info(f"清理報告 ({'預覽模式' if dry_run else '執行模式'})")
        logger.info(f"{'='*60}")
        logger.info(f"垃圾實體: {len(garbage)} 個")
        for eid, name, etype, reason in garbage[:30]:
            logger.info(f"  [{reason}] id={eid} type={etype} name='{name}'")
        if len(garbage) > 30:
            logger.info(f"  ... 還有 {len(garbage) - 30} 個")

        logger.info(f"\n低品質實體 (date/topic, mention<=1): {len(low_quality)} 個")
        for eid, name, etype in low_quality[:20]:
            logger.info(f"  id={eid} type={etype} name='{name}'")
        if len(low_quality) > 20:
            logger.info(f"  ... 還有 {len(low_quality) - 20} 個")

        logger.info(f"\n重複實體: {len(duplicates)} 組")
        for (name, etype), ids in list(duplicates.items())[:15]:
            logger.info(f"  '{name}' ({etype}): IDs = {ids}")

        if dry_run:
            logger.info(f"\n{'='*60}")
            logger.info("預覽模式 — 未執行任何刪除。加 --execute 執行清理。")
            return

        # 執行清理
        garbage_ids = [g[0] for g in garbage]
        low_quality_ids = [lq[0] for lq in low_quality]
        all_delete_ids = garbage_ids + low_quality_ids

        if all_delete_ids:
            # 刪除關聯的 aliases
            await db.execute(
                text("DELETE FROM entity_aliases WHERE canonical_entity_id = ANY(:ids)"),
                {"ids": all_delete_ids},
            )
            # 刪除關聯的 mentions
            await db.execute(
                text("DELETE FROM document_entity_mentions WHERE canonical_entity_id = ANY(:ids)"),
                {"ids": all_delete_ids},
            )
            # 刪除關聯的 relationships (source 或 target)
            await db.execute(
                text("DELETE FROM entity_relationships WHERE source_entity_id = ANY(:ids) OR target_entity_id = ANY(:ids)"),
                {"ids": all_delete_ids},
            )
            # 刪除實體本身
            await db.execute(
                text("DELETE FROM canonical_entities WHERE id = ANY(:ids)"),
                {"ids": all_delete_ids},
            )
            await db.commit()
            logger.info(f"\n已刪除 {len(all_delete_ids)} 個實體 (垃圾={len(garbage_ids)}, 低品質={len(low_quality_ids)})")

        # 合併重複實體：保留最小 ID，更新其他 ID 的 references
        merge_count = 0
        for (name, etype), ids in duplicates.items():
            if any(i in all_delete_ids for i in ids):
                continue  # 已被刪除的不處理
            keep_id = min(ids)
            remove_ids = [i for i in ids if i != keep_id]
            if not remove_ids:
                continue
            for rid in remove_ids:
                # 將 mentions 指向保留的 ID
                await db.execute(
                    text("UPDATE document_entity_mentions SET canonical_entity_id = :keep WHERE canonical_entity_id = :remove"),
                    {"keep": keep_id, "remove": rid},
                )
                # 將 aliases 指向保留的 ID
                await db.execute(
                    text("UPDATE entity_aliases SET canonical_entity_id = :keep WHERE canonical_entity_id = :remove"),
                    {"keep": keep_id, "remove": rid},
                )
                # 更新 relationships
                await db.execute(
                    text("UPDATE entity_relationships SET source_entity_id = :keep WHERE source_entity_id = :remove"),
                    {"keep": keep_id, "remove": rid},
                )
                await db.execute(
                    text("UPDATE entity_relationships SET target_entity_id = :keep WHERE target_entity_id = :remove"),
                    {"keep": keep_id, "remove": rid},
                )
                # 刪除重複實體
                await db.execute(
                    text("DELETE FROM canonical_entities WHERE id = :remove"),
                    {"remove": rid},
                )
                merge_count += 1
            # 更新 mention_count
            await db.execute(
                text("UPDATE canonical_entities SET mention_count = "
                     "(SELECT COUNT(*) FROM document_entity_mentions WHERE canonical_entity_id = :id) "
                     "WHERE id = :id"),
                {"id": keep_id},
            )
        if merge_count > 0:
            await db.commit()
            logger.info(f"已合併 {merge_count} 個重複實體")

        logger.info(f"\n{'='*60}")
        logger.info("清理完成！")


def main():
    parser = argparse.ArgumentParser(description="清理知識圖譜垃圾實體")
    parser.add_argument("--execute", action="store_true", help="執行清理（預設為預覽模式）")
    args = parser.parse_args()

    # 從 .env 讀取資料庫連線
    import os
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
    load_dotenv(env_path)

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        logger.error("未找到 DATABASE_URL，請檢查 .env")
        sys.exit(1)

    # 確保使用 async driver
    if "postgresql://" in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    asyncio.run(clean_entities(db_url, dry_run=not args.execute))


if __name__ == "__main__":
    main()
