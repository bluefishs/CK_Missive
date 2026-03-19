"""
User Query Graph -- per-user interest profiling from query patterns.

Phase 9.1: Data Collection
- Extracts entity/agency/project/topic mentions from tool results
- Stores hit counts in Redis hash: user_interest:{user_id}
- Uses HINCRBY for atomic increments
- TTL 30 days

Phase 9.2: Interest Topic Auto-Tagging
- Classifies interests into categories: agency, project, document_type, entity, topic
- Simple keyword matching (no LLM)

Version: 1.0.0
Created: 2026-03-16
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

INTEREST_REDIS_PREFIX = "user_interest:"
INTEREST_TTL = 30 * 24 * 3600  # 30 days

# ── Phase 9.2: Category classification keywords ──

_AGENCY_KEYWORDS = (
    "局", "處", "署", "部", "委員會", "所", "院", "廳",
    "中心", "會", "公所", "政府", "市府",
)

_PROJECT_KEYWORDS = (
    "工程", "專案", "計畫", "標案", "案", "建設", "改善",
)

_DOC_TYPE_KEYWORDS = (
    "函", "公告", "令", "書函", "簽", "開會通知", "會議紀錄",
    "收文", "發文", "通知", "報告",
)

_TOPIC_KEYWORDS = (
    "預算", "進度", "品質", "安全", "驗收", "請款", "變更",
    "施工", "監造", "設計", "審查", "招標", "決標", "履約",
)


def classify_interest(name: str) -> str:
    """
    Classify an interest name into a category.

    Categories: agency, project, document_type, entity, topic
    Uses simple keyword matching -- no LLM calls.

    Priority: document_type > topic > agency > project > entity
    (more specific categories checked first)
    """
    if any(kw in name for kw in _DOC_TYPE_KEYWORDS):
        return "document_type"
    if any(kw in name for kw in _TOPIC_KEYWORDS):
        return "topic"
    if any(kw in name for kw in _AGENCY_KEYWORDS):
        return "agency"
    if any(kw in name for kw in _PROJECT_KEYWORDS):
        return "project"
    return "entity"


def _extract_names_from_tool_results(tool_results: List[Dict[str, Any]]) -> List[str]:
    """
    Extract entity/agency/project names from tool results.

    Scans for common field patterns in result dicts:
    - entity_name, name, agency_name, project_name
    - sender, receiver (from document search results)
    - subject keywords
    """
    names: List[str] = []
    seen: set = set()

    def _add(val: str) -> None:
        val = val.strip()
        if val and len(val) >= 2 and val not in seen:
            seen.add(val)
            names.append(val)

    for tr in tool_results:
        result = tr.get("result", {})
        if not isinstance(result, dict):
            continue

        # Direct entity fields
        for field in ("entity_name", "name", "agency_name", "project_name",
                      "canonical_name", "sender", "receiver",
                      "normalized_sender", "normalized_receiver"):
            val = result.get(field)
            if isinstance(val, str) and val:
                _add(val)

        # Lists of items (documents, entities, dispatch_orders, etc.)
        for list_key in ("documents", "entities", "items", "results",
                         "dispatch_orders", "projects"):
            items = result.get(list_key)
            if not isinstance(items, list):
                continue
            for item in items[:20]:  # cap to avoid huge loops
                if not isinstance(item, dict):
                    continue
                for field in ("entity_name", "name", "agency_name",
                              "project_name", "canonical_name",
                              "sender", "receiver",
                              "normalized_sender", "normalized_receiver",
                              "subject"):
                    val = item.get(field)
                    if isinstance(val, str) and val:
                        # For subject, extract short phrases only
                        if field == "subject" and len(val) > 30:
                            continue
                        _add(val)

    return names


class UserQueryTracker:
    """
    Track user query patterns for interest profiling.

    Stores in Redis hash: user_interest:{user_id}
    Keys: category:name (e.g. "agency:桃園市政府工務局")
    Values: hit count (incremented per query)
    TTL: 30 days
    """

    def __init__(self, redis: Optional[Any] = None):
        self._redis = redis

    def _get_redis(self) -> Any:
        """Lazy Redis connection."""
        if self._redis is not None:
            return self._redis
        try:
            import redis as redis_lib
            self._redis = redis_lib.Redis(
                host="localhost", port=6380, db=0, decode_responses=True,
            )
            return self._redis
        except Exception as e:
            logger.debug("UserQueryTracker: Redis unavailable: %s", e)
            return None

    async def track_query(
        self,
        user_id: str,
        question: str,
        tool_results: List[Dict[str, Any]],
    ) -> int:
        """
        Extract entities/agencies/projects from tool results and increment counters.

        Returns number of interests tracked.
        """
        if not user_id or not tool_results:
            return 0

        r = self._get_redis()
        if r is None:
            return 0

        names = _extract_names_from_tool_results(tool_results)
        if not names:
            return 0

        key = f"{INTEREST_REDIS_PREFIX}{user_id}"
        tracked = 0

        try:
            pipe = r.pipeline(transaction=False)
            for name in names:
                category = classify_interest(name)
                field = f"{category}:{name}"
                pipe.hincrby(key, field, 1)
            pipe.expire(key, INTEREST_TTL)
            pipe.execute()
            tracked = len(names)
        except Exception as e:
            logger.debug("UserQueryTracker.track_query failed: %s", e)
            return 0

        logger.debug(
            "UserQueryTracker: tracked %d interests for user=%s",
            tracked, user_id,
        )
        return tracked

    async def get_interests(
        self,
        user_id: str,
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get top-N interests for a user, sorted by hit count.

        Returns:
            [{"category": "agency", "name": "...", "count": 5}, ...]
        """
        if not user_id:
            return []

        r = self._get_redis()
        if r is None:
            return []

        key = f"{INTEREST_REDIS_PREFIX}{user_id}"
        try:
            raw = r.hgetall(key)
            if not raw:
                return []

            interests: List[Dict[str, Any]] = []
            for field, count_str in raw.items():
                try:
                    count = int(count_str)
                except (ValueError, TypeError):
                    continue
                parts = field.split(":", 1)
                if len(parts) == 2:
                    category, name = parts
                else:
                    category, name = "entity", field
                interests.append({
                    "category": category,
                    "name": name,
                    "count": count,
                })

            interests.sort(key=lambda x: x["count"], reverse=True)
            return interests[:top_n]
        except Exception as e:
            logger.debug("UserQueryTracker.get_interests failed: %s", e)
            return []

    async def get_interest_summary(self, user_id: str) -> str:
        """
        Format interests as text for planner injection.

        Returns a short summary like:
            "使用者關注領域：機關[桃園市政府工務局(5), 養護工程處(3)]、專案[道路改善工程(2)]"
        """
        interests = await self.get_interests(user_id, top_n=10)
        if not interests:
            return ""

        category_labels = {
            "agency": "機關",
            "project": "專案",
            "document_type": "公文類型",
            "entity": "實體",
            "topic": "主題",
        }

        # Group by category
        grouped: Dict[str, List[str]] = {}
        for item in interests:
            cat = item["category"]
            label = category_labels.get(cat, cat)
            entry = f"{item['name']}({item['count']})"
            grouped.setdefault(label, []).append(entry)

        parts = []
        for label, entries in grouped.items():
            parts.append(f"{label}[{', '.join(entries[:3])}]")

        return "使用者關注領域：" + "、".join(parts)


# ── Singleton accessor ──

_tracker_instance: Optional[UserQueryTracker] = None


def get_query_tracker() -> UserQueryTracker:
    """Get singleton UserQueryTracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = UserQueryTracker()
    return _tracker_instance
