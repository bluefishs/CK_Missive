"""
統一 Embedding 管理器

封裝 AIConnector.generate_embedding 並加入 LRU 快取，
避免相同文字重複呼叫 Ollama。

所有需要 embedding 的服務（搜尋、圖譜入圖、批次回填）
均應透過此管理器取得 embedding。

Version: 1.3.0 - 新增 get_embeddings_batch 批次快取 + 並發產生
Created: 2026-02-24
"""

import asyncio
import hashlib
import logging
import os
import time
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .ai_config import get_ai_config

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """
    Embedding 管理 Singleton

    快取策略：
    - LRU 快取（預設 500 筆，TTL 30 分鐘）
    - 快取 key = SHA256(text[:200])（避免超長 key）
    - 快取 value = (embedding, timestamp)
    - _write_lock (asyncio.Lock) 保護快取寫入/驅逐
    - _embed_semaphore (asyncio.Semaphore) 限制並發 Ollama 呼叫，防止資源耗盡
    """

    _instance: Optional["EmbeddingManager"] = None
    _cache: OrderedDict[str, Tuple[List[float], float]] = OrderedDict()
    _max_cache_size: int = get_ai_config().embedding_cache_max_size
    _cache_ttl: float = float(get_ai_config().embedding_cache_ttl)
    _write_lock: asyncio.Lock = asyncio.Lock()
    _embed_semaphore: asyncio.Semaphore = asyncio.Semaphore(5)

    # 統計
    _hits: int = 0
    _misses: int = 0

    def __new__(cls) -> "EmbeddingManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def _cache_key(cls, text: str) -> str:
        """產生快取 key（全文 SHA256）"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def _evict_expired(cls) -> None:
        """清除過期項目（需在 _write_lock 內呼叫）"""
        now = time.monotonic()
        expired = [
            k for k, (_, ts) in cls._cache.items()
            if now - ts > cls._cache_ttl
        ]
        for k in expired:
            del cls._cache[k]

    @classmethod
    async def get_embedding(
        cls,
        text: str,
        connector: object,
    ) -> Optional[List[float]]:
        """
        取得文字的 embedding（快取優先，async-safe）

        Args:
            text: 要生成 embedding 的文字
            connector: AIConnector 實例（具有 generate_embedding 方法）

        Returns:
            768 維 embedding 向量，或 None
        """
        if not text or not text.strip():
            return None

        key = cls._cache_key(text)

        # 快取命中 (_write_lock 保護讀取 + move_to_end 突變)
        async with cls._write_lock:
            if key in cls._cache:
                embedding, ts = cls._cache[key]
                if time.monotonic() - ts < cls._cache_ttl:
                    cls._hits += 1
                    cls._cache.move_to_end(key)
                    return embedding
                else:
                    del cls._cache[key]

        # 快取未命中 → 呼叫 Ollama
        # _embed_semaphore 限制並發數，防止同時大量請求壓垮 Ollama
        cls._misses += 1
        try:
            async with cls._embed_semaphore:
                embedding = await connector.generate_embedding(text)  # type: ignore[attr-defined]
        except Exception as e:
            logger.warning("Embedding 生成失敗: %s", e)
            return None

        if embedding and isinstance(embedding, list) and len(embedding) > 0:
            # 存入快取 (_write_lock 保護寫入 + 驅逐)
            async with cls._write_lock:
                cls._evict_expired()
                if len(cls._cache) >= cls._max_cache_size:
                    cls._cache.popitem(last=False)  # 移除最舊
                cls._cache[key] = (embedding, time.monotonic())

        return embedding

    @classmethod
    async def get_embeddings_batch(
        cls,
        texts: List[str],
        connector: object,
    ) -> List[Optional[List[float]]]:
        """
        批次取得 embeddings（快取優先，未命中部分並發產生）

        相比逐一呼叫 get_embedding，此方法：
        1. 一次性查詢快取，分離命中/未命中
        2. 未命中部分透過 Semaphore 並發產生
        3. 批次寫入快取

        Args:
            texts: 文字清單
            connector: AIConnector 實例

        Returns:
            與 texts 等長的 embedding 清單（失敗者為 None）
        """
        if not texts:
            return []

        results: List[Optional[List[float]]] = [None] * len(texts)
        to_generate: List[Tuple[int, str, str]] = []  # (index, text, cache_key)

        # Phase 1: 批次快取查詢
        async with cls._write_lock:
            now = time.monotonic()
            for i, text in enumerate(texts):
                if not text or not text.strip():
                    continue
                key = cls._cache_key(text)
                if key in cls._cache:
                    embedding, ts = cls._cache[key]
                    if now - ts < cls._cache_ttl:
                        cls._hits += 1
                        cls._cache.move_to_end(key)
                        results[i] = embedding
                        continue
                    else:
                        del cls._cache[key]
                to_generate.append((i, text, key))

        if not to_generate:
            return results

        # Phase 2: 並發產生（受 Semaphore 限制）
        cls._misses += len(to_generate)

        async def _generate_one(idx: int, text: str, key: str) -> Tuple[int, str, Optional[List[float]]]:
            try:
                async with cls._embed_semaphore:
                    emb = await connector.generate_embedding(text)  # type: ignore[attr-defined]
                if emb and isinstance(emb, list) and len(emb) > 0:
                    return (idx, key, emb)
            except Exception as e:
                logger.warning("Batch embedding failed for text[%d]: %s", idx, e)
            return (idx, key, None)

        tasks = [_generate_one(idx, text, key) for idx, text, key in to_generate]
        generated = await asyncio.gather(*tasks)

        # Phase 3: 批次寫入快取
        async with cls._write_lock:
            cls._evict_expired()
            for idx, key, emb in generated:
                results[idx] = emb
                if emb is not None:
                    if len(cls._cache) >= cls._max_cache_size:
                        cls._cache.popitem(last=False)
                    cls._cache[key] = (emb, time.monotonic())

        return results

    @classmethod
    def get_stats(cls) -> Dict[str, int]:
        """快取統計"""
        return {
            "cache_size": len(cls._cache),
            "max_size": cls._max_cache_size,
            "hits": cls._hits,
            "misses": cls._misses,
            "hit_rate_percent": round(
                cls._hits / max(cls._hits + cls._misses, 1) * 100, 1
            ),
        }

    @classmethod
    def invalidate(cls) -> None:
        """清除所有快取"""
        cls._cache.clear()
        cls._hits = 0
        cls._misses = 0
        logger.info("Embedding 快取已清除")

    @classmethod
    def is_available(cls) -> bool:
        """檢查 pgvector 功能是否啟用"""
        return os.environ.get("PGVECTOR_ENABLED", "false").lower() == "true"

    @classmethod
    async def get_coverage_stats(cls, db: AsyncSession) -> Dict:
        """
        取得 Embedding 覆蓋率統計

        Returns:
            {"total": int, "with_embedding": int, "without_embedding": int, "coverage": float}
        """
        from app.extended.models import OfficialDocument

        total_result = await db.execute(
            select(func.count(OfficialDocument.id))
        )
        total = total_result.scalar() or 0

        with_result = await db.execute(
            select(func.count(OfficialDocument.id))
            .where(OfficialDocument.embedding.isnot(None))
        )
        with_emb = with_result.scalar() or 0

        return {
            "total": total,
            "with_embedding": with_emb,
            "without_embedding": total - with_emb,
            "coverage": round((with_emb / total * 100) if total > 0 else 0.0, 2),
        }
