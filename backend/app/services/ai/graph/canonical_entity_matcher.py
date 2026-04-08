"""
正規化實體匹配與合併服務

從 canonical_entity_service.py 提取：
- CanonicalEntityMatcher: trigram 相似度、虛假匹配偵測、模糊匹配
- CanonicalEntityMerger: 實體合併邏輯

Version: 1.0.0
Created: 2026-03-23
"""

import logging
import re
from typing import Dict, List, Optional

from sqlalchemy import select, update, delete as sa_delete, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import (
    CanonicalEntity,
    EntityAlias,
    DocumentEntityMention,
)

logger = logging.getLogger(__name__)

# 閾值由 AIConfig 統一管理
from app.services.ai.ai_config import get_ai_config
FUZZY_SIMILARITY_THRESHOLD = get_ai_config().kg_fuzzy_threshold


class CanonicalEntityMatcher:
    """正規化實體匹配器 — trigram 相似度 + 虛假匹配偵測"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def compute_similarity(a: str, b: str) -> float:
        """計算兩個字串的 trigram 相似度（Python 端，替代 pg_trgm）"""
        if not a or not b:
            return 0.0
        a_lower, b_lower = a.lower(), b.lower()
        if a_lower == b_lower:
            return 1.0
        # Trigram set similarity
        a_trigrams = {a_lower[i:i+3] for i in range(max(len(a_lower) - 2, 1))}
        b_trigrams = {b_lower[i:i+3] for i in range(max(len(b_lower) - 2, 1))}
        if not a_trigrams or not b_trigrams:
            return 0.0
        intersection = len(a_trigrams & b_trigrams)
        union = len(a_trigrams | b_trigrams)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def is_false_fuzzy_match(name: str, candidate_name: str) -> bool:
        """檢查模糊匹配是否為虛假匹配（共同前綴 + 不同內容）

        常見誤匹配：
        - 「115年度苗栗縣...」vs「115年度桃園市...」(年度前綴相同)
        - 「114年度南投縣...」vs「114年度和美鎮...」(年度前綴相同)
        - 「彰化縣...TWD67」vs「和美鎮...TWD67」(後綴相同)
        """
        min_len = min(len(name), len(candidate_name))
        if min_len < 8:
            return False  # 短名稱不檢查

        # 計算共同前綴
        common_prefix = 0
        for i in range(min_len):
            if name[i] == candidate_name[i]:
                common_prefix += 1
            else:
                break

        # 計算前綴之後的差異核心
        name_rest = name[common_prefix:]
        cand_rest = candidate_name[common_prefix:]

        # 若共同前綴 <= 6 字元（如「115年度」）且剩餘部分差異大 -> 拒絕
        if common_prefix <= 6 and len(name_rest) > 5 and len(cand_rest) > 5:
            # 比較差異部分的前 8 字元
            diff_head_n = name_rest[:8]
            diff_head_c = cand_rest[:8]
            shared_chars = sum(1 for a, b in zip(diff_head_n, diff_head_c) if a == b)
            if shared_chars <= 2:
                return True  # 前綴後的內容完全不同 -> 虛假匹配

        # 長名稱額外檢查：兩者長度都 > 15 但差異核心無交集
        if len(name) > 15 and len(candidate_name) > 15:
            # 取去掉年度前綴的核心部分
            year_re = re.compile(r'^\d{2,4}年度')
            core_n = year_re.sub('', name)
            core_c = year_re.sub('', candidate_name)
            # 取核心的前 10 字元比較
            if len(core_n) > 10 and len(core_c) > 10:
                if core_n[:10] not in candidate_name and core_c[:10] not in name:
                    return True  # 核心內容不同 -> 虛假匹配

        return False

    async def fuzzy_match_batch(
        self, names: List[str], entity_type: str,
    ) -> Dict[str, CanonicalEntity]:
        """Stage 2: 批次 pg_trgm 模糊匹配（每個 entity_type 1 次查詢）"""
        matched: Dict[str, CanonicalEntity] = {}
        if not names:
            return matched

        try:
            # 取得該 entity_type 所有 canonical entities（通常 <500 筆）
            all_candidates_result = await self.db.execute(
                select(CanonicalEntity)
                .where(CanonicalEntity.entity_type == entity_type)
            )
            all_candidates = all_candidates_result.scalars().all()

            if not all_candidates:
                return matched

            # 逐名字在記憶體中匹配（避免 N 次 DB 查詢）
            for name in names:
                best_match: Optional[CanonicalEntity] = None
                best_score = 0.0
                for candidate in all_candidates:
                    # 簡化的相似度計算（trigram-like）
                    score = self.compute_similarity(name, candidate.canonical_name)
                    if score >= FUZZY_SIMILARITY_THRESHOLD and score > best_score:
                        if not self.is_false_fuzzy_match(name, candidate.canonical_name):
                            best_match = candidate
                            best_score = score
                if best_match:
                    matched[name] = best_match

            return matched
        except Exception as e:
            logger.debug(f"批次模糊匹配失敗: {e}")
            # 降級為逐筆匹配
            for name in names:
                result = await self.fuzzy_match(name, entity_type)
                if result:
                    matched[name] = result
            return matched

    async def fuzzy_match(
        self, name: str, entity_type: str,
    ) -> Optional[CanonicalEntity]:
        """單筆 pg_trgm 模糊匹配（批次匹配的降級路徑）"""
        try:
            result = await self.db.execute(
                select(CanonicalEntity)
                .where(CanonicalEntity.entity_type == entity_type)
                .where(
                    sa_func.similarity(CanonicalEntity.canonical_name, name)
                    >= FUZZY_SIMILARITY_THRESHOLD
                )
                .order_by(
                    sa_func.similarity(CanonicalEntity.canonical_name, name).desc()
                )
                .limit(5)
            )
            candidates = result.scalars().all()

            for candidate in candidates:
                if self.is_false_fuzzy_match(name, candidate.canonical_name):
                    continue
                return candidate
            return None
        except Exception as e:
            logger.debug(f"pg_trgm 模糊匹配失敗 (擴展可能未安裝): {e}")
            return None


class CanonicalEntityMerger:
    """正規化實體合併器 — 別名/提及轉移 + 統計更新"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def merge_entities(
        self,
        keep_id: int,
        merge_id: int,
    ) -> CanonicalEntity:
        """合併兩個正規實體（將 merge 的所有別名和提及轉移到 keep）"""
        keep_entity = await self.db.get(CanonicalEntity, keep_id)
        merge_entity = await self.db.get(CanonicalEntity, merge_id)

        if not keep_entity or not merge_entity:
            raise ValueError("實體不存在")

        # 轉移別名（先去重：若 keep_entity 已有同名別名則刪除 merge 的重複項）
        keep_alias_result = await self.db.execute(
            select(EntityAlias.alias_name)
            .where(EntityAlias.canonical_entity_id == keep_id)
        )
        keep_alias_names = {row[0] for row in keep_alias_result.all()}

        merge_alias_result = await self.db.execute(
            select(EntityAlias)
            .where(EntityAlias.canonical_entity_id == merge_id)
        )
        merge_aliases = merge_alias_result.scalars().all()

        dup_ids = []
        transfer_ids = []
        for alias in merge_aliases:
            if alias.alias_name in keep_alias_names:
                dup_ids.append(alias.id)
            else:
                transfer_ids.append(alias.id)

        if dup_ids:
            await self.db.execute(
                sa_delete(EntityAlias).where(EntityAlias.id.in_(dup_ids))
            )
        if transfer_ids:
            await self.db.execute(
                update(EntityAlias)
                .where(EntityAlias.id.in_(transfer_ids))
                .values(canonical_entity_id=keep_id)
            )

        # 轉移提及
        await self.db.execute(
            update(DocumentEntityMention)
            .where(DocumentEntityMention.canonical_entity_id == merge_id)
            .values(canonical_entity_id=keep_id)
        )

        # 更新統計
        keep_entity.mention_count = (keep_entity.mention_count or 0) + (merge_entity.mention_count or 0)
        # 重新計算 alias_count（去重後的實際數量）
        actual_alias_count = await self.db.scalar(
            select(sa_func.count())
            .select_from(EntityAlias)
            .where(EntityAlias.canonical_entity_id == keep_id)
        ) or 0
        keep_entity.alias_count = actual_alias_count

        if merge_entity.first_seen_at and (
            not keep_entity.first_seen_at or merge_entity.first_seen_at < keep_entity.first_seen_at
        ):
            keep_entity.first_seen_at = merge_entity.first_seen_at

        # 刪除被合併的實體
        await self.db.delete(merge_entity)
        await self.db.flush()
        # 快取失效：合併實體影響圖譜
        try:
            from app.services.ai.graph_query_service import invalidate_graph_cache
            await invalidate_graph_cache()
        except Exception:
            pass

        logger.info(f"實體合併: {merge_entity.canonical_name} → {keep_entity.canonical_name}")
        return keep_entity
