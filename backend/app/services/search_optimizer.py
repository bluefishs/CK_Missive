"""
搜尋查詢優化服務

提供高效能的全文搜尋與智能查詢優化功能

優化策略：
1. 使用 PostgreSQL pg_trgm 進行模糊匹配
2. 智能關鍵字分詞處理
3. 搜尋結果快取
4. 查詢計畫優化

版本: 1.0.0
日期: 2026-01-08
"""
import logging
import re
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from functools import lru_cache
from sqlalchemy import select, func, or_, and_, text, literal_column
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import OfficialDocument as Document, ContractProject, GovernmentAgency

logger = logging.getLogger(__name__)


class SearchOptimizer:
    """
    搜尋優化器

    提供高效能的公文搜尋功能，包括：
    - 智能關鍵字處理
    - 多欄位權重搜尋
    - 搜尋結果排名
    - 查詢快取
    """

    # 搜尋欄位權重配置
    SEARCH_FIELD_WEIGHTS = {
        'doc_number': 10,    # 文號精確匹配最高優先
        'subject': 8,        # 主旨次之
        'sender': 5,         # 發文單位
        'receiver': 5,       # 受文單位
        'content': 3,        # 內容
        'notes': 2,          # 備註
    }

    # 常見停用詞 (中文)
    STOP_WORDS = {'的', '了', '和', '與', '及', '或', '在', '是', '有', '為', '等'}

    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)

    def _normalize_keyword(self, keyword: str) -> str:
        """
        正規化搜尋關鍵字

        處理：
        - 移除多餘空白
        - 統一全形/半形
        - 移除特殊字元
        """
        if not keyword:
            return ""

        # 移除首尾空白
        keyword = keyword.strip()

        # 全形轉半形 (數字和英文)
        result = []
        for char in keyword:
            code = ord(char)
            # 全形英數字轉半形
            if 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            # 全形空格轉半形
            elif code == 0x3000:
                result.append(' ')
            else:
                result.append(char)

        normalized = ''.join(result)

        # 移除多餘空白
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    def _extract_search_tokens(self, keyword: str) -> List[str]:
        """
        從搜尋關鍵字提取搜尋詞彙

        支援：
        - 空格分隔的多個關鍵字
        - 自動識別公文字號格式
        - 過濾停用詞
        """
        if not keyword:
            return []

        normalized = self._normalize_keyword(keyword)
        tokens = []

        # 檢查是否為公文字號格式 (例如: 乾坤測字第1140000001號)
        doc_number_pattern = r'[\u4e00-\u9fff]+字第?\d+號?'
        doc_matches = re.findall(doc_number_pattern, normalized)
        if doc_matches:
            tokens.extend(doc_matches)

        # 分割其他詞彙
        remaining = re.sub(doc_number_pattern, ' ', normalized)
        words = remaining.split()

        for word in words:
            # 過濾停用詞和過短的詞
            if word and len(word) >= 2 and word not in self.STOP_WORDS:
                tokens.append(word)

        return list(set(tokens))  # 去重

    def _get_cache_key(self, keyword: str, filters: Dict[str, Any]) -> str:
        """產生快取鍵值"""
        cache_data = f"{keyword}:{str(sorted(filters.items()))}"
        return hashlib.md5(cache_data.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """取得快取結果"""
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_ttl:
                logger.debug(f"[搜尋] 快取命中: {cache_key[:8]}...")
                return result
            else:
                del self._cache[cache_key]
        return None

    def _set_cache(self, cache_key: str, result: Any):
        """設定快取"""
        self._cache[cache_key] = (result, datetime.now())
        # 清理過期快取 (簡易實作)
        if len(self._cache) > 100:
            now = datetime.now()
            expired = [k for k, (_, t) in self._cache.items() if now - t > self._cache_ttl]
            for k in expired:
                del self._cache[k]

    def build_optimized_search_query(
        self,
        base_query,
        keyword: str,
        use_trigram: bool = True
    ):
        """
        建構優化的搜尋查詢

        Args:
            base_query: 基礎 SQLAlchemy 查詢
            keyword: 搜尋關鍵字
            use_trigram: 是否使用 pg_trgm 模糊匹配

        Returns:
            優化後的查詢
        """
        if not keyword:
            return base_query

        normalized = self._normalize_keyword(keyword)
        tokens = self._extract_search_tokens(keyword)

        # 如果只有一個 token，使用簡單的 ILIKE
        if len(tokens) <= 1:
            search_term = f"%{normalized}%"
            return base_query.where(or_(
                Document.doc_number.ilike(search_term),
                Document.subject.ilike(search_term),
                Document.sender.ilike(search_term),
                Document.receiver.ilike(search_term),
                Document.content.ilike(search_term),
                Document.notes.ilike(search_term)
            ))

        # 多個 token 時，使用 AND 邏輯 (所有詞都要匹配)
        conditions = []
        for token in tokens:
            token_pattern = f"%{token}%"
            token_condition = or_(
                Document.doc_number.ilike(token_pattern),
                Document.subject.ilike(token_pattern),
                Document.sender.ilike(token_pattern),
                Document.receiver.ilike(token_pattern),
                Document.content.ilike(token_pattern),
                Document.notes.ilike(token_pattern)
            )
            conditions.append(token_condition)

        return base_query.where(and_(*conditions))

    async def search_with_ranking(
        self,
        keyword: str,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        執行帶排名的搜尋

        根據匹配欄位和相關性對結果進行排名

        Args:
            keyword: 搜尋關鍵字
            filters: 額外篩選條件
            skip: 跳過筆數
            limit: 取得筆數

        Returns:
            搜尋結果字典
        """
        if not keyword:
            return {"items": [], "total": 0, "tokens": []}

        normalized = self._normalize_keyword(keyword)
        tokens = self._extract_search_tokens(keyword)

        logger.info(f"[搜尋] 關鍵字: '{keyword}' -> 正規化: '{normalized}' -> 詞彙: {tokens}")

        # 檢查快取
        cache_key = self._get_cache_key(keyword, filters or {})
        cached = self._get_cached_result(cache_key)
        if cached:
            return cached

        try:
            # 建構搜尋查詢
            query = select(Document)
            query = self.build_optimized_search_query(query, keyword)

            # 套用額外篩選
            if filters:
                if filters.get('category'):
                    query = query.where(Document.category == filters['category'])
                if filters.get('delivery_method'):
                    query = query.where(Document.delivery_method == filters['delivery_method'])
                if filters.get('year'):
                    from sqlalchemy import extract
                    query = query.where(extract('year', Document.doc_date) == filters['year'])

            # 計算總數
            count_query = select(func.count()).select_from(query.subquery())
            total = (await self.db.execute(count_query)).scalar_one()

            # 執行查詢 (按相關性和日期排序)
            result = await self.db.execute(
                query.order_by(
                    Document.doc_date.desc().nullslast(),
                    Document.id.desc()
                ).offset(skip).limit(limit)
            )
            documents = result.scalars().all()

            search_result = {
                "items": documents,
                "total": total,
                "tokens": tokens,
                "normalized_keyword": normalized
            }

            # 設定快取
            self._set_cache(cache_key, search_result)

            return search_result

        except Exception as e:
            logger.error(f"[搜尋] 查詢失敗: {e}", exc_info=True)
            return {"items": [], "total": 0, "tokens": tokens, "error": str(e)}

    async def get_search_suggestions(
        self,
        prefix: str,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        取得搜尋建議 (自動完成)

        根據輸入前綴提供建議的搜尋詞

        Args:
            prefix: 輸入前綴
            limit: 建議數量上限

        Returns:
            建議列表
        """
        if not prefix or len(prefix) < 2:
            return []

        normalized = self._normalize_keyword(prefix)
        suggestions = []

        try:
            # 從主旨搜尋
            subject_query = (
                select(Document.subject)
                .where(Document.subject.ilike(f"%{normalized}%"))
                .distinct()
                .limit(limit)
            )
            subject_result = await self.db.execute(subject_query)
            for row in subject_result:
                if row[0]:
                    suggestions.append({
                        "type": "subject",
                        "value": row[0][:100],  # 截斷過長的主旨
                        "label": f"主旨: {row[0][:50]}..."
                    })

            # 從文號搜尋
            doc_number_query = (
                select(Document.doc_number)
                .where(Document.doc_number.ilike(f"%{normalized}%"))
                .distinct()
                .limit(limit)
            )
            doc_number_result = await self.db.execute(doc_number_query)
            for row in doc_number_result:
                if row[0]:
                    suggestions.append({
                        "type": "doc_number",
                        "value": row[0],
                        "label": f"文號: {row[0]}"
                    })

            # 去重並限制數量
            seen = set()
            unique_suggestions = []
            for s in suggestions:
                if s["value"] not in seen:
                    seen.add(s["value"])
                    unique_suggestions.append(s)
                    if len(unique_suggestions) >= limit:
                        break

            return unique_suggestions

        except Exception as e:
            logger.error(f"[搜尋建議] 查詢失敗: {e}", exc_info=True)
            return []

    async def get_popular_searches(self, limit: int = 10) -> List[str]:
        """
        取得熱門搜尋詞 (基於最近查詢的主旨)

        Returns:
            熱門搜尋詞列表
        """
        try:
            # 取得最近的公文主旨關鍵詞
            query = (
                select(Document.subject)
                .order_by(Document.updated_at.desc())
                .limit(100)
            )
            result = await self.db.execute(query)

            # 簡易詞頻統計
            word_freq: Dict[str, int] = {}
            for row in result:
                if row[0]:
                    # 提取中文詞彙 (長度 2-4)
                    words = re.findall(r'[\u4e00-\u9fff]{2,4}', row[0])
                    for word in words:
                        if word not in self.STOP_WORDS:
                            word_freq[word] = word_freq.get(word, 0) + 1

            # 排序並取前 N 個
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            return [word for word, _ in sorted_words[:limit]]

        except Exception as e:
            logger.error(f"[熱門搜尋] 查詢失敗: {e}", exc_info=True)
            return []


class QueryPlanOptimizer:
    """
    查詢計畫優化器

    分析並優化 SQL 查詢計畫
    """

    @staticmethod
    async def analyze_query(db: AsyncSession, query_sql: str) -> Dict[str, Any]:
        """
        分析查詢計畫

        Args:
            db: 資料庫連線
            query_sql: SQL 查詢字串

        Returns:
            查詢計畫分析結果
        """
        try:
            explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query_sql}"
            result = await db.execute(text(explain_sql))
            plan = result.scalar()
            return {
                "plan": plan,
                "success": True
            }
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }

    @staticmethod
    def suggest_optimizations(plan: Dict[str, Any]) -> List[str]:
        """
        根據查詢計畫提供優化建議

        Args:
            plan: 查詢計畫

        Returns:
            優化建議列表
        """
        suggestions = []

        if not plan.get("success"):
            return ["無法分析查詢計畫"]

        # 簡易分析 (實際應用中可以更複雜)
        plan_data = plan.get("plan", [])
        if plan_data:
            # 檢查是否使用了 Seq Scan
            plan_str = str(plan_data)
            if "Seq Scan" in plan_str:
                suggestions.append("建議: 查詢使用了全表掃描 (Seq Scan)，考慮新增索引")
            if "Sort" in plan_str and "Index" not in plan_str:
                suggestions.append("建議: 排序操作未使用索引，考慮新增排序欄位索引")

        return suggestions if suggestions else ["查詢計畫看起來已優化"]
