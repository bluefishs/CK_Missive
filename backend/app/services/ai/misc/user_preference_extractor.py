"""
雙層使用者記憶 — 從對話中萃取使用者偏好並持久化

偏好類型：
- topic: 常查主題 (如「派工單」「道路工程」)
- format: 回答格式偏好 (如「簡短」「表格」)
- agency: 常關注機關
- tool: 常用工具組合

儲存策略：
- Redis: 快速讀取 (TTL 7 天)
- AgentLearning DB: 長期持久化 (type=preference)

Version: 1.0.0
Created: 2026-03-15
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PREFERENCE_REDIS_PREFIX = "agent:user_pref:"
PREFERENCE_TTL = 7 * 24 * 3600  # 7 days


def extract_preferences_from_history(
    history: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """
    規則式偏好萃取 — 從對話歷史中提取使用者偏好

    無需 LLM，純規則分析 (0ms)
    """
    preferences: List[Dict[str, Any]] = []
    user_messages = [m["content"] for m in history if m.get("role") == "user"]

    if not user_messages:
        return preferences

    # Topic detection: 計算常見主題詞頻
    topic_counts: Dict[str, int] = {}
    topic_keywords = {
        "派工": "dispatch",
        "公文": "document",
        "道路": "road",
        "工程": "engineering",
        "廠商": "vendor",
        "專案": "project",
        "機關": "agency",
        "預算": "budget",
        "合約": "contract",
        "圖譜": "graph",
        "知識": "knowledge",
        "統計": "statistics",
    }

    for msg in user_messages:
        for keyword, topic in topic_keywords.items():
            if keyword in msg:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:3]:
        if count >= 2:
            preferences.append({
                "type": "topic",
                "value": topic,
                "confidence": min(1.0, count / len(user_messages)),
            })

    # Format detection
    for msg in user_messages:
        if any(w in msg for w in ("簡短", "簡單", "一句話")):
            preferences.append({"type": "format", "value": "concise", "confidence": 0.8})
            break
        if any(w in msg for w in ("詳細", "完整", "報告")):
            preferences.append({"type": "format", "value": "detailed", "confidence": 0.8})
            break
        if any(w in msg for w in ("表格", "列表", "清單")):
            preferences.append({"type": "format", "value": "tabular", "confidence": 0.8})
            break

    return preferences


async def save_preferences(
    session_id: str,
    preferences: List[Dict[str, Any]],
    db=None,
) -> int:
    """儲存偏好到 Redis + DB (雙寫)"""
    if not preferences:
        return 0

    saved = 0

    # Redis write
    try:
        import redis
        r = redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)
        key = f"{PREFERENCE_REDIS_PREFIX}{session_id}"
        r.setex(key, PREFERENCE_TTL, json.dumps(preferences, ensure_ascii=False))
        saved += len(preferences)
    except Exception as e:
        logger.debug("Redis preference save skipped: %s", e)

    # DB write (via AgentLearning)
    if db:
        try:
            from app.repositories.agent_learning_repository import AgentLearningRepository
            repo = AgentLearningRepository(db)
            for pref in preferences:
                await repo.upsert_learning(
                    session_id=session_id,
                    learning_type="preference",
                    content=json.dumps(pref, ensure_ascii=False),
                    source="preference_extractor",
                )
            await db.flush()
        except Exception as e:
            logger.debug("DB preference save skipped: %s", e)

    return saved


async def load_preferences(session_id: str) -> List[Dict[str, Any]]:
    """從 Redis 載入使用者偏好"""
    try:
        import redis
        r = redis.Redis(host="localhost", port=6380, db=0, decode_responses=True)
        key = f"{PREFERENCE_REDIS_PREFIX}{session_id}"
        data = r.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.debug("Redis preference load skipped: %s", e)
    return []


def format_preferences_for_prompt(preferences: List[Dict[str, Any]]) -> str:
    """格式化偏好為 LLM prompt 注入文字"""
    if not preferences:
        return ""

    lines = []
    for pref in preferences:
        ptype = pref.get("type", "")
        value = pref.get("value", "")
        if ptype == "topic":
            lines.append(f"- 使用者常查主題: {value}")
        elif ptype == "format":
            format_map = {
                "concise": "簡短回答",
                "detailed": "詳細報告",
                "tabular": "表格/清單格式",
            }
            lines.append(f"- 回答格式偏好: {format_map.get(value, value)}")
        elif ptype == "agency":
            lines.append(f"- 常關注機關: {value}")

    if lines:
        return "使用者偏好：\n" + "\n".join(lines)
    return ""
