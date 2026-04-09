"""
Proactive Recommender -- match new documents against user interest profiles.

When new documents are created that involve entities a user has shown interest in,
generate a recommendation alert.

Flow:
1. Get all active user interest profiles from Redis (SCAN user_interest:*)
2. Get recent documents (last 24h) with their NER entities
3. For each user, check if any document entities match their interests
4. Generate recommendations as structured alerts

Called by: ProactiveTriggerService.scan_all() or standalone via API.

Version: 1.1.0
Created: 2026-03-16
Updated: 2026-04-05 - v1.1.0 新增 Gemma 4 語意相關性評分
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

INTEREST_REDIS_PREFIX = "user_interest:"


class ProactiveRecommender:
    """
    Matches new/recent documents against user interest profiles.

    Usage:
        recommender = ProactiveRecommender(db)
        recs = await recommender.scan_recommendations()
        # recs: [{"user_id": "...", "document_id": 1, "matched_entities": [...], "score": 3}]
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_redis(self):
        """Lazy Redis connection."""
        try:
            import redis
            return redis.Redis(
                host="localhost", port=6380, db=0, decode_responses=True,
            )
        except Exception as e:
            logger.debug("ProactiveRecommender: Redis unavailable: %s", e)
            return None

    async def _get_all_user_interests(self) -> Dict[str, Dict[str, int]]:
        """
        Scan Redis for all user_interest:* hashes.

        Returns:
            {"user_id": {"category:name": count, ...}, ...}
        """
        r = self._get_redis()
        if r is None:
            return {}

        user_interests: Dict[str, Dict[str, int]] = {}
        try:
            cursor = 0
            while True:
                cursor, keys = r.scan(
                    cursor=cursor,
                    match=f"{INTEREST_REDIS_PREFIX}*",
                    count=100,
                )
                for key in keys:
                    user_id = key[len(INTEREST_REDIS_PREFIX):]
                    if not user_id:
                        continue
                    raw = r.hgetall(key)
                    if raw:
                        parsed: Dict[str, int] = {}
                        for field, val in raw.items():
                            try:
                                parsed[field] = int(val)
                            except (ValueError, TypeError):
                                pass
                        if parsed:
                            user_interests[user_id] = parsed
                if cursor == 0:
                    break
        except Exception as e:
            logger.debug("ProactiveRecommender: Redis scan failed: %s", e)

        return user_interests

    async def _get_recent_documents_with_entities(
        self,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Get documents created in the last N hours with their NER entities.

        Returns:
            [{"id": 1, "subject": "...", "sender": "...", "entities": ["name1", "name2"]}, ...]
        """
        from app.extended.models.document import OfficialDocument
        from app.extended.models.entity import DocumentEntity

        cutoff = datetime.utcnow() - timedelta(hours=hours)

        # Get recent documents
        doc_result = await self.db.execute(
            select(
                OfficialDocument.id,
                OfficialDocument.subject,
                OfficialDocument.sender,
                OfficialDocument.receiver,
                OfficialDocument.doc_type,
                OfficialDocument.doc_number,
            )
            .where(OfficialDocument.created_at >= cutoff)
            .order_by(OfficialDocument.created_at.desc())
            .limit(200)
        )
        docs = doc_result.all()
        if not docs:
            return []

        doc_ids = [d.id for d in docs]

        # Get entities for these documents
        entity_result = await self.db.execute(
            select(
                DocumentEntity.document_id,
                DocumentEntity.entity_name,
            )
            .where(DocumentEntity.document_id.in_(doc_ids))
        )
        entity_rows = entity_result.all()

        # Group entities by document
        doc_entities: Dict[int, List[str]] = {}
        for row in entity_rows:
            doc_entities.setdefault(row.document_id, []).append(row.entity_name)

        result = []
        for d in docs:
            entities = doc_entities.get(d.id, [])
            # Also include sender/receiver as matchable names
            extra = []
            if d.sender:
                extra.append(d.sender)
            if d.receiver:
                extra.append(d.receiver)
            all_names = list(set(entities + extra))

            result.append({
                "id": d.id,
                "subject": d.subject or "",
                "sender": d.sender or "",
                "receiver": d.receiver or "",
                "doc_type": d.doc_type or "",
                "doc_number": d.doc_number or "",
                "entities": all_names,
            })

        return result

    def _match_interests(
        self,
        user_interests: Dict[str, int],
        doc_entities: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Match a user's interest keys against a document's entity names.

        Interest keys are formatted as "category:name".
        Matching is substring-based: if interest name is contained in an entity
        or vice versa, it counts as a match.

        Returns:
            [{"interest_key": "agency:...", "matched_entity": "...", "weight": 5}, ...]
        """
        matches = []
        for interest_key, count in user_interests.items():
            parts = interest_key.split(":", 1)
            if len(parts) != 2:
                continue
            _category, interest_name = parts
            if len(interest_name) < 2:
                continue

            for entity in doc_entities:
                if not entity:
                    continue
                # Substring match in both directions
                if interest_name in entity or entity in interest_name:
                    matches.append({
                        "interest_key": interest_key,
                        "matched_entity": entity,
                        "weight": count,
                    })
                    break  # one match per interest is enough

        return matches

    async def scan_recommendations(
        self,
        hours: int = 24,
        min_score: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Scan for new document-interest matches across all users.

        Args:
            hours: Look-back window for recent documents.
            min_score: Minimum total weight to include a recommendation.

        Returns:
            [{"user_id": "...", "document_id": 1, "subject": "...",
              "matched_entities": [...], "score": 5}, ...]
        """
        user_interests = await self._get_all_user_interests()
        if not user_interests:
            logger.debug("ProactiveRecommender: no user interests found")
            return []

        recent_docs = await self._get_recent_documents_with_entities(hours)
        if not recent_docs:
            logger.debug("ProactiveRecommender: no recent documents found")
            return []

        recommendations: List[Dict[str, Any]] = []

        for user_id, interests in user_interests.items():
            # Extract interest names for Gemma 4 semantic scoring
            interest_names = []
            for key in interests.keys():
                parts = key.split(":", 1)
                if len(parts) == 2 and len(parts[1]) >= 2:
                    interest_names.append(parts[1])

            for doc in recent_docs:
                if not doc["entities"]:
                    continue

                matches = self._match_interests(interests, doc["entities"])
                entity_score = sum(m["weight"] for m in matches) if matches else 0

                # Fast filter: skip documents with zero entity overlap
                if entity_score < 1 and not doc.get("subject"):
                    continue

                # Gemma 4 semantic scoring for candidates with partial match
                # or interesting subjects (entity_score > 0 but below threshold)
                semantic_score = 0.0
                if interest_names and doc.get("subject"):
                    if entity_score > 0 or len(interest_names) >= 2:
                        semantic_score = await self._semantic_relevance_score(
                            interest_names[:5], doc["subject"]
                        )

                # Combined scoring: entity overlap + semantic relevance
                combined_score = entity_score + (semantic_score * 3.0)
                if combined_score < min_score:
                    continue

                rec_entry: Dict[str, Any] = {
                    "user_id": user_id,
                    "document_id": doc["id"],
                    "subject": doc["subject"],
                    "doc_type": doc["doc_type"],
                    "doc_number": doc["doc_number"],
                    "matched_entities": [
                        {
                            "interest": m["interest_key"],
                            "entity": m["matched_entity"],
                            "weight": m["weight"],
                        }
                        for m in matches
                    ] if matches else [],
                    "score": round(combined_score, 2),
                }
                if semantic_score > 0:
                    rec_entry["semantic_score"] = round(semantic_score, 2)
                recommendations.append(rec_entry)

        # Sort by score descending
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        logger.info(
            "ProactiveRecommender: %d recommendations for %d users from %d docs",
            len(recommendations),
            len(user_interests),
            len(recent_docs),
        )

        return recommendations

    async def get_user_recommendations(
        self,
        user_id: str,
        limit: int = 5,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations for a specific user.

        Args:
            user_id: The user to get recommendations for.
            limit: Maximum number of recommendations.
            hours: Look-back window for recent documents.

        Returns:
            [{"document_id": 1, "subject": "...", "matched_entities": [...], "score": 5}, ...]
        """
        if not user_id:
            return []

        r = self._get_redis()
        if r is None:
            return []

        key = f"{INTEREST_REDIS_PREFIX}{user_id}"
        try:
            raw = r.hgetall(key)
        except Exception as e:
            logger.debug("ProactiveRecommender: Redis read failed: %s", e)
            return []

        if not raw:
            return []

        interests: Dict[str, int] = {}
        for field, val in raw.items():
            try:
                interests[field] = int(val)
            except (ValueError, TypeError):
                pass

        if not interests:
            return []

        recent_docs = await self._get_recent_documents_with_entities(hours)
        if not recent_docs:
            return []

        results: List[Dict[str, Any]] = []
        for doc in recent_docs:
            if not doc["entities"]:
                continue

            matches = self._match_interests(interests, doc["entities"])
            if not matches:
                continue

            score = sum(m["weight"] for m in matches)
            results.append({
                "document_id": doc["id"],
                "subject": doc["subject"],
                "doc_type": doc["doc_type"],
                "doc_number": doc["doc_number"],
                "matched_entities": [
                    {
                        "interest": m["interest_key"],
                        "entity": m["matched_entity"],
                        "weight": m["weight"],
                    }
                    for m in matches
                ],
                "score": score,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    # ========================================================================
    # Gemma 4 語意相關性評分
    # ========================================================================

    async def _semantic_relevance_score(
        self, user_interests: list, doc_summary: str
    ) -> float:
        """Score document relevance to user interests via Gemma 4.

        Returns a float 0.0-1.0 representing semantic relevance.
        Falls back to 0.0 on any error (never blocks recommendation flow).
        """
        try:
            from app.core.ai_connector import get_ai_connector

            ai = get_ai_connector()
            prompt = (
                f"用戶關注: {', '.join(str(i) for i in user_interests[:5])}\n"
                f"新文件摘要: {doc_summary[:300]}\n\n"
                "這份文件與用戶關注的相關程度 (0.0-1.0)？\n"
                '回覆 JSON: {"relevance": 0.0-1.0, "reason": "一句話原因"}'
            )
            result = await ai.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=64,
                task_type="classify",
            )
            from app.services.ai.agent_utils import parse_json_safe

            parsed = parse_json_safe(result)
            if parsed:
                score = float(parsed.get("relevance", 0.0))
                return max(0.0, min(1.0, score))  # clamp to [0, 1]
            return 0.0
        except Exception as e:
            logger.debug("Gemma4 semantic relevance failed: %s", e)
            return 0.0
