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
from dataclasses import dataclass
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

            # Bridge to DB graduation system: update graduation status for
            # any matching DB-persisted learnings tied to this template
            try:
                await self._update_db_graduation(template, success)
            except Exception as grad_err:
                logger.debug("Graduation update skipped: %s", grad_err)

        except Exception as e:
            logger.debug("PatternLearner.learn failed: %s", e)

    async def _update_db_graduation(self, template: str, success: bool) -> None:
        """Bridge Redis pattern learning to DB graduation system."""
        from app.services.ai.agent_pattern_persistence import update_db_graduation
        await update_db_graduation(template, success)

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
        """語意匹配 fallback — 委派至 pattern_semantic_matcher"""
        try:
            from app.services.ai.ai_config import get_ai_config
            config = get_ai_config()

            # 取得候選模式（top-scored）
            index_key = f"{self._PREFIX}:index"
            candidates = await redis.zrevrange(
                index_key, 0, config.pattern_semantic_top_k - 1,
            )
            if not candidates:
                return []

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

            from app.services.ai.pattern_semantic_matcher import semantic_match
            return await semantic_match(
                template, candidate_patterns, redis, self._PREFIX, config,
            )

        except Exception as e:
            logger.debug("_semantic_match failed: %s", e)
            return []

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

    # ── 實體偏好學習 ──

    _ENTITY_PREF_PREFIX = "entity_pref"
    _ENTITY_PREF_TTL = 30 * 86400  # 30 days
    _ENTITY_PREF_THRESHOLD = 5

    async def record_entity_usage(self, entity_ids: List[int]) -> None:
        """記錄使用者查詢涉及的實體，高頻實體自動寫入 AgentLearning。

        For each entity_id:
        1. Increment Redis counter ``entity_pref:{entity_id}`` (TTL 30 days)
        2. If counter >= threshold (5), upsert an AgentLearning record
           with learning_type='entity_preference'
        """
        redis = await self._get_redis()
        if not redis or not entity_ids:
            return

        for entity_id in entity_ids:
            try:
                redis_key = f"{self._ENTITY_PREF_PREFIX}:{entity_id}"
                count = await redis.incr(redis_key)
                await redis.expire(redis_key, self._ENTITY_PREF_TTL)

                if count >= self._ENTITY_PREF_THRESHOLD:
                    await self._persist_entity_preference(entity_id, count)
            except Exception as e:
                logger.debug("record_entity_usage failed for %s: %s", entity_id, e)

    async def _persist_entity_preference(self, entity_id: int, query_count: int) -> None:
        """Upsert entity preference into AgentLearning (DB)."""
        try:
            from app.db.database import AsyncSessionLocal
            from app.extended.models.agent_learning import AgentLearning

            content = f"entity:{entity_id}"
            content_hash = hashlib.md5(content.encode()).hexdigest()

            async with AsyncSessionLocal() as db:
                # Check if already exists
                from sqlalchemy import select
                existing = await db.execute(
                    select(AgentLearning).where(
                        AgentLearning.content_hash == content_hash,
                        AgentLearning.is_active == True,  # noqa: E712
                    )
                )
                record = existing.scalar_one_or_none()

                if record:
                    record.hit_count = record.hit_count + 1
                    record.confidence = min(1.0, 0.5 + query_count * 0.05)
                else:
                    db.add(AgentLearning(
                        session_id="system",
                        learning_type="entity_preference",
                        content=content,
                        content_hash=content_hash,
                        source_question=f"Auto-detected: entity {entity_id} queried {query_count}+ times",
                        confidence=min(1.0, 0.5 + query_count * 0.05),
                        hit_count=1,
                    ))
                await db.commit()
                logger.debug("Persisted entity preference for entity_id=%s (count=%s)", entity_id, query_count)
        except Exception as e:
            logger.debug("_persist_entity_preference failed: %s", e)

    # ── 種子資料載入 ──

    async def load_seeds_if_empty(self) -> int:
        """
        冷啟動種子載入 — 當 Redis 無任何已學習模式時，載入預設種子。

        Returns:
            載入的種子數量（0 表示已有模式或 Redis 不可用）
        """
        from app.services.ai.agent_pattern_persistence import load_seeds_if_empty
        return await load_seeds_if_empty(self)


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
