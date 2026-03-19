"""
Agent Pattern Learner — 使用者查詢模式學習

從每次成功問答中學習查詢模式：
- 正規化問題 → 模板 (e.g. "{ORG}的{DOC_TYPE}" )
- 記錄成功的工具呼叫序列 + 參數模板
- 後續相似查詢可直接匹配模式，跳過 LLM 規劃

Phase 3A 升級：語意匹配 fallback
- 精確 MD5 匹配失敗時，使用 embedding 餘弦相似度比對
- 可配置閾值 + kill switch

設計原則：
- Redis 不可用時靜默降級
- 模式數量上限（防止記憶體膨脹）
- 衰減權重（近期模式權重更高）
- 高信心門檻（寧可多走 LLM，不可錯誤路由）

Version: 2.0.0
Created: 2026-03-14
Updated: 2026-03-15 - v2.0.0 新增語意匹配 fallback
"""

import hashlib
import json
import logging
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueryPattern:
    """學習到的查詢模式"""

    pattern_key: str
    template: str
    tool_sequence: List[str]
    params_template: Dict[str, Any]
    hit_count: int = 0
    success_rate: float = 1.0
    avg_latency_ms: float = 0.0
    last_used: float = 0.0
    score: float = 0.0


class QueryPatternLearner:
    """
    查詢模式學習器 — Redis 持久化

    Redis Key 結構:
    - agent:patterns:index — Sorted Set: pattern_key -> score
    - agent:patterns:detail:{key} — Hash: 模式詳情
    """

    _PREFIX = "agent:patterns"
    _TTL = 30 * 86400  # 30 天過期

    def __init__(
        self,
        max_patterns: int = 500,
        decay_half_life: int = 604800,
        match_threshold: float = 0.8,
    ):
        self._max_patterns = max_patterns
        self._decay_half_life = decay_half_life
        self._match_threshold = match_threshold
        self._redis = None

    async def _get_redis(self):
        """取得 Redis 連線"""
        if self._redis is not None:
            try:
                await self._redis.ping()
                return self._redis
            except Exception:
                self._redis = None
        try:
            from app.core.redis_client import get_redis

            self._redis = await get_redis()
            return self._redis
        except Exception:
            return None

    # ── 正規化 ──

    @staticmethod
    def normalize_question(question: str, hints: Optional[Dict] = None) -> str:
        """
        將具體問題正規化為模板。

        例如：
        - "工務局的函有幾件" → "{ORG}的{DOC_TYPE}有幾件"
        - "2026年3月的公文統計" → "{DATE}的公文統計"
        """
        q = question.strip()
        hints = hints or {}

        # 1. 從 hints 取得已辨識的實體，替換為佔位符
        for key in ("sender", "receiver", "agency_name"):
            val = hints.get(key, "")
            if val and len(val) >= 2 and val in q:
                q = q.replace(val, "{ORG}")

        # 2. 日期模式替換
        q = re.sub(r"\d{3,4}[-/年]\d{1,2}[-/月]\d{1,2}[日號]?", "{DATE}", q)
        q = re.sub(r"\d{3,4}[-/年]\d{1,2}[月]?", "{DATE}", q)
        q = re.sub(
            r"(上個月|這個月|今年|去年|本週|本月|上週|最近\d+[天日月])",
            "{DATE_RANGE}",
            q,
        )
        q = re.sub(r"民國\d{2,3}年", "{DATE}", q)

        # 3. 公文文號替換
        q = re.sub(r"[A-Za-z\u4e00-\u9fff]+字第\d+號", "{DOC_NO}", q)

        # 4. 派工單號替換
        q = re.sub(r"派工單[號]?\s*\d+", "派工單{DISPATCH_NO}", q)

        # 5. 數字泛化（保留中文量詞前的數字）
        q = re.sub(r"\d+(?=[筆件篇個份])", "{N}", q)

        # 6. 公文類別 (函/令/公告/書函等) 保留但標記
        doc_types = (
            "函",
            "令",
            "公告",
            "書函",
            "開會通知單",
            "簽",
            "箋函",
            "代電",
        )
        for dt in doc_types:
            if dt in q:
                q = q.replace(dt, "{DOC_TYPE}", 1)
                break

        return q

    @staticmethod
    def _make_key(template: str) -> str:
        """生成模板的穩定 hash key"""
        return hashlib.md5(template.encode("utf-8")).hexdigest()[:12]

    # ── 學習 ──

    async def learn(
        self,
        question: str,
        hints: Optional[Dict],
        tool_calls: List[Dict[str, Any]],
        success: bool,
        latency_ms: float = 0.0,
    ) -> None:
        """從一次問答中學習模式"""
        if not success or not tool_calls:
            return

        redis = await self._get_redis()
        if not redis:
            return

        try:
            template = self.normalize_question(question, hints)
            pattern_key = self._make_key(template)
            detail_key = f"{self._PREFIX}:detail:{pattern_key}"
            index_key = f"{self._PREFIX}:index"

            tool_sequence = [c.get("name", "") for c in tool_calls]
            params_template = {
                c.get("name", ""): c.get("params", {}) for c in tool_calls
            }

            # 檢查是否已有相同模式
            existing = await redis.hgetall(detail_key)

            now = time.time()
            if existing:
                # 更新已有模式
                old_hits = int(
                    existing.get(b"hit_count", existing.get("hit_count", 0))
                )
                old_avg = float(
                    existing.get(
                        b"avg_latency_ms",
                        existing.get("avg_latency_ms", 0),
                    )
                )
                new_hits = old_hits + 1
                new_avg = old_avg + (latency_ms - old_avg) / new_hits
                score = self._calc_score(new_hits, 1.0, now)

                await redis.hset(
                    detail_key,
                    mapping={
                        "hit_count": str(new_hits),
                        "avg_latency_ms": str(round(new_avg, 1)),
                        "last_used": str(now),
                    },
                )
                await redis.zadd(index_key, {pattern_key: score})
            else:
                # 新增模式
                score = self._calc_score(1, 1.0, now)
                await redis.hset(
                    detail_key,
                    mapping={
                        "template": template,
                        "tool_sequence": json.dumps(tool_sequence),
                        "params_template": json.dumps(
                            params_template, ensure_ascii=False
                        ),
                        "hit_count": "1",
                        "success_rate": "1.0",
                        "avg_latency_ms": str(round(latency_ms, 1)),
                        "last_used": str(now),
                    },
                )
                await redis.zadd(index_key, {pattern_key: score})

                # 容量控制：移除最低分模式
                count = await redis.zcard(index_key)
                if count > self._max_patterns:
                    # 移除排名最低的 10%
                    remove_count = max(1, count - self._max_patterns)
                    lowest = await redis.zrange(index_key, 0, remove_count - 1)
                    pipe = redis.pipeline()
                    for key_to_remove in lowest:
                        k = (
                            key_to_remove.decode()
                            if isinstance(key_to_remove, bytes)
                            else key_to_remove
                        )
                        pipe.delete(f"{self._PREFIX}:detail:{k}")
                        pipe.zrem(index_key, k)
                    await pipe.execute()

            await redis.expire(detail_key, self._TTL)

        except Exception as e:
            logger.debug("PatternLearner.learn failed: %s", e)

    def _calc_score(
        self, hit_count: int, success_rate: float, last_used: float
    ) -> float:
        """計算模式的綜合評分（含衰減）"""
        age = time.time() - last_used
        decay = math.exp(-0.693 * age / self._decay_half_life)
        return hit_count * success_rate * decay

    # ── 匹配 ──

    async def match(
        self, question: str, hints: Optional[Dict] = None, top_k: int = 3
    ) -> List[QueryPattern]:
        """
        嘗試匹配已知模式。

        兩階段策略：
        1. 精確 MD5 匹配（0ms，覆蓋完全相同模板）
        2. 語意匹配 fallback（~100ms，Phase 3A 新增）
        """
        redis = await self._get_redis()
        if not redis:
            return []

        try:
            template = self.normalize_question(question, hints)
            pattern_key = self._make_key(template)

            # 1. 精確匹配
            detail_key = f"{self._PREFIX}:detail:{pattern_key}"
            exact = await redis.hgetall(detail_key)
            if exact:
                pattern = self._parse_pattern(pattern_key, exact)
                if pattern and pattern.hit_count >= 2:
                    return [pattern]

            # 2. 語意匹配 fallback (Phase 3A)
            semantic_result = await self._semantic_match(template, redis, top_k)
            if semantic_result:
                return semantic_result

            return []

        except Exception as e:
            logger.debug("PatternLearner.match failed: %s", e)
            return []

    async def _semantic_match(
        self,
        template: str,
        redis: Any,
        top_k: int = 3,
    ) -> List[QueryPattern]:
        """
        語意匹配 fallback — 使用 embedding 餘弦相似度。

        策略：
        1. 取得查詢 template 的 embedding
        2. 與候選模式 template 的 embedding 計算 cosine similarity
        3. 超過閾值且最高分者回傳

        僅在精確匹配失敗時觸發，可配置關閉。
        Embedding 不可用時自動降級為字元 Jaccard。
        """
        try:
            from app.services.ai.ai_config import get_ai_config
            config = get_ai_config()
            if not config.pattern_semantic_enabled:
                return []

            # 中文字符少於 4 個時跳過語意匹配
            cjk_chars = len(re.findall(r'[\u4e00-\u9fff]', template))
            if cjk_chars < 4:
                return []

            # 取得候選模式（top-scored）
            index_key = f"{self._PREFIX}:index"
            candidates = await redis.zrevrange(
                index_key, 0, config.pattern_semantic_top_k - 1,
            )
            if not candidates:
                return []

            # 載入候選模式的 template
            candidate_patterns = []
            for key in candidates:
                k = key.decode() if isinstance(key, bytes) else key
                detail = await redis.hgetall(f"{self._PREFIX}:detail:{k}")
                if detail:
                    pattern = self._parse_pattern(k, detail)
                    if pattern and pattern.hit_count >= 2:
                        candidate_patterns.append(pattern)

            if not candidate_patterns:
                return []

            # 嘗試 embedding cosine similarity
            best_match, best_score = await self._embedding_cosine_match(
                template, candidate_patterns
            )

            # Embedding 不可用時降級為 Jaccard
            if best_match is None:
                best_match, best_score = self._jaccard_match(
                    template, candidate_patterns
                )

            if best_match and best_score >= config.pattern_semantic_threshold:
                logger.debug(
                    "Semantic match: %.2f (%s → %s)",
                    best_score, template[:30], best_match.template[:30],
                )
                return [best_match]

            return []

        except Exception as e:
            logger.debug("_semantic_match failed: %s", e)
            return []

    async def _embedding_cosine_match(
        self,
        template: str,
        candidates: List[QueryPattern],
    ) -> tuple:
        """使用 embedding 餘弦相似度匹配候選模式。回傳 (best_pattern, score) 或 (None, 0)。"""
        try:
            from app.services.ai.embedding_manager import EmbeddingManager
            from app.services.ai.base_ai_service import BaseAIService

            connector = BaseAIService.get_shared_connector()
            if not connector:
                return (None, 0.0)

            # 批次取得 embeddings（查詢 + 所有候選）
            texts = [template] + [p.template for p in candidates]
            embeddings = await EmbeddingManager.get_embeddings_batch(texts, connector)

            query_emb = embeddings[0]
            if not query_emb:
                return (None, 0.0)

            best_match = None
            best_score = 0.0

            for i, p in enumerate(candidates):
                cand_emb = embeddings[i + 1]
                if not cand_emb:
                    continue
                similarity = self._cosine_similarity(query_emb, cand_emb)
                if similarity > best_score:
                    best_score = similarity
                    best_match = p

            return (best_match, best_score)

        except Exception as e:
            logger.debug("_embedding_cosine_match unavailable: %s", e)
            return (None, 0.0)

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """計算兩向量的餘弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _jaccard_match(
        template: str,
        candidates: List[QueryPattern],
    ) -> tuple:
        """Jaccard 字元相似度降級方案"""
        best_match = None
        best_score = 0.0

        template_chars = set(template)
        for p in candidates:
            p_chars = set(p.template)
            intersection = template_chars & p_chars
            union = template_chars | p_chars
            if not union:
                continue
            jaccard = len(intersection) / len(union)
            if jaccard > best_score:
                best_score = jaccard
                best_match = p

        return (best_match, best_score)

    async def get_top_patterns(self, n: int = 20) -> List[QueryPattern]:
        """取得高分模式（監控用）"""
        redis = await self._get_redis()
        if not redis:
            return []

        try:
            index_key = f"{self._PREFIX}:index"
            top_keys = await redis.zrevrange(index_key, 0, n - 1, withscores=True)

            results = []
            for key, score in top_keys:
                k = key.decode() if isinstance(key, bytes) else key
                detail = await redis.hgetall(f"{self._PREFIX}:detail:{k}")
                if detail:
                    pattern = self._parse_pattern(k, detail)
                    if pattern:
                        pattern.score = score
                        results.append(pattern)
            return results

        except Exception as e:
            logger.debug("PatternLearner.get_top_patterns failed: %s", e)
            return []

    @staticmethod
    def _parse_pattern(
        pattern_key: str, raw: Dict
    ) -> Optional[QueryPattern]:
        """解析 Redis hash 為 QueryPattern"""
        try:

            def _get(key: str, default: str = "") -> str:
                val = raw.get(key.encode(), raw.get(key, default))
                return val.decode() if isinstance(val, bytes) else str(val)

            return QueryPattern(
                pattern_key=pattern_key,
                template=_get("template"),
                tool_sequence=json.loads(_get("tool_sequence", "[]")),
                params_template=json.loads(_get("params_template", "{}")),
                hit_count=int(_get("hit_count", "0")),
                success_rate=float(_get("success_rate", "1.0")),
                avg_latency_ms=float(_get("avg_latency_ms", "0")),
                last_used=float(_get("last_used", "0")),
            )
        except Exception:
            return None

    def format_as_few_shot(self, patterns: List[QueryPattern]) -> str:
        """將匹配的模式格式化為 few-shot 範例"""
        if not patterns:
            return ""

        lines = ["# 歷史成功模式（供參考）"]
        for p in patterns[:3]:
            tools = ", ".join(p.tool_sequence)
            lines.append(
                f"- 模式: {p.template}\n"
                f"  工具序列: [{tools}]\n"
                f"  命中 {p.hit_count} 次, 平均 {p.avg_latency_ms:.0f}ms"
            )
        return "\n".join(lines)

    # ── 種子資料載入 ──

    _SEED_FLAG_KEY = "agent:seeds:loaded"

    async def load_seeds_if_empty(self) -> int:
        """
        冷啟動種子載入 — 當 Redis 無任何已學習模式時，載入預設種子。

        Returns:
            載入的種子數量（0 表示已有模式或 Redis 不可用）
        """
        redis = await self._get_redis()
        if not redis:
            return 0

        try:
            # 檢查是否已載入過（冪等保護）
            if await redis.get(self._SEED_FLAG_KEY):
                return 0

            # 檢查是否已有模式
            index_key = f"{self._PREFIX}:index"
            count = await redis.zcard(index_key)
            if count > 0:
                # 已有模式，設定旗標避免後續再檢查
                await redis.set(self._SEED_FLAG_KEY, "1", ex=self._TTL)
                return 0

            # 載入種子
            from app.services.ai.pattern_seeds import SEED_PATTERNS

            loaded = 0
            for seed in SEED_PATTERNS:
                tool_calls = [
                    {"name": name, "params": {}} for name in seed["tools"]
                ]
                await self.learn(
                    question=seed["question"],
                    hints=None,
                    tool_calls=tool_calls,
                    success=True,
                    latency_ms=0.0,
                )

                # 提升 hit_count 至基線值（5），讓種子立即可被 match
                template = self.normalize_question(seed["question"])
                pattern_key = self._make_key(template)
                detail_key = f"{self._PREFIX}:detail:{pattern_key}"
                exists = await redis.exists(detail_key)
                if exists:
                    await redis.hset(detail_key, "hit_count", "5")
                    # 更新 index score
                    import time as _time

                    score = self._calc_score(5, 1.0, _time.time())
                    await redis.zadd(index_key, {pattern_key: score})
                    loaded += 1

            # 設定旗標
            await redis.set(self._SEED_FLAG_KEY, "1", ex=self._TTL)
            logger.info("Pattern seeds loaded: %d patterns", loaded)
            return loaded

        except Exception as e:
            logger.warning("load_seeds_if_empty failed: %s", e)
            return 0


# ── Singleton ──

_learner: Optional[QueryPatternLearner] = None


def get_pattern_learner() -> QueryPatternLearner:
    """取得 QueryPatternLearner 單例"""
    global _learner
    if _learner is None:
        from app.services.ai.ai_config import get_ai_config

        config = get_ai_config()
        _learner = QueryPatternLearner(
            max_patterns=config.pattern_max_count,
            decay_half_life=config.pattern_decay_half_life,
            match_threshold=config.pattern_match_threshold,
        )
    return _learner
