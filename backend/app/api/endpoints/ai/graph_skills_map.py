"""
Skills 能力圖譜與技能演化樹 API 端點

提供靜態技能能力圖譜（3 層階層式架構）與技能演化樹。

Refactored from: graph_unified.py
Version: 1.0.0
Created: 2026-04-09
"""

from fastapi import APIRouter, Depends

from app.core.dependencies import require_auth
from app.extended.models import User

router = APIRouter()


@router.post("/graph/skill-evolution")
async def get_skill_evolution_tree(
    current_user: User = Depends(require_auth()),
):
    """
    取得技能演化樹資料

    返回系統所有技能節點、演化路徑、融合關係，
    供前端渲染互動式技能演化視覺化。
    """
    from app.services.skill_evolution_service import build_skill_tree
    return build_skill_tree()


@router.post("/graph/skills-map")
async def get_skills_capability_map(
    current_user: User = Depends(require_auth()),
):
    """
    回傳乾坤智能體能力圖譜 — 3 層階層式架構。

    Level 1: 能力分層 (5 層)
    Level 2: 核心能力 (10 個, 含成熟度 ★1-5)
    Level 3: 具體技能/工具 + 演進方向

    節點與邊為靜態定義，不需資料庫查詢。
    mention_count 編碼成熟度: ★N × 20
    """

    # -- 節點色彩定義 --
    C_LAYER      = "#434343"   # 深灰 — 能力分層
    C_CAPABILITY = "#1890ff"   # 藍   — 核心能力
    C_SKILL      = "#52c41a"   # 綠   — 具體技能
    C_FUTURE     = "#ff85c0"   # 粉   — 演進方向

    nodes = [
        # ================================================================
        # Level 1: 能力分層 (5 層)
        # ================================================================
        {"id": "layer:input",   "label": "感知層 Input",   "type": "layer", "color": C_LAYER, "mention_count": 30},
        {"id": "layer:think",   "label": "認知層 Think",   "type": "layer", "color": C_LAYER, "mention_count": 30},
        {"id": "layer:know",    "label": "知識層 Know",    "type": "layer", "color": C_LAYER, "mention_count": 30},
        {"id": "layer:execute", "label": "行動層 Execute", "type": "layer", "color": C_LAYER, "mention_count": 30},
        {"id": "layer:learn",   "label": "學習層 Learn",   "type": "layer", "color": C_LAYER, "mention_count": 30},

        # ================================================================
        # Level 2: 核心能力 (10 個, ★ = maturity)
        # ================================================================
        # ★5 成熟 (mention_count=100)
        {"id": "cap:crud",       "label": "公文CRUD ★★★★★",    "type": "capability", "color": C_CAPABILITY, "mention_count": 100},
        {"id": "cap:agent",      "label": "Agent問答 ★★★★★",   "type": "capability", "color": C_CAPABILITY, "mention_count": 100},
        {"id": "cap:rag",        "label": "RAG檢索 ★★★★★",    "type": "capability", "color": C_CAPABILITY, "mention_count": 100},
        # ★4 穩定 (mention_count=80)
        {"id": "cap:kg",         "label": "知識圖譜 ★★★★",     "type": "capability", "color": C_CAPABILITY, "mention_count": 80},
        {"id": "cap:learning",   "label": "自我學習 ★★★★",     "type": "capability", "color": C_CAPABILITY, "mention_count": 80},
        # ★3 可用 (mention_count=60)
        {"id": "cap:voice",      "label": "語音辨識 ★★★",      "type": "capability", "color": C_CAPABILITY, "mention_count": 60},
        {"id": "cap:ocr",        "label": "影像OCR ★★★",       "type": "capability", "color": C_CAPABILITY, "mention_count": 60},
        {"id": "cap:discovery",  "label": "工具發現 ★★★",      "type": "capability", "color": C_CAPABILITY, "mention_count": 60},
        # ★2 實驗 (mention_count=40)
        {"id": "cap:nim",        "label": "NIM推理 ★★",        "type": "capability", "color": C_CAPABILITY, "mention_count": 40},
        {"id": "cap:federation", "label": "聯邦查詢 ★★",       "type": "capability", "color": C_CAPABILITY, "mention_count": 40},

        # ================================================================
        # Level 3a: 具體技能 (15 個)
        # ================================================================
        {"id": "skill:ner",           "label": "NER 實體提取",       "type": "skill", "color": C_SKILL, "mention_count": 15},
        {"id": "skill:entity_norm",   "label": "實體正規化",         "type": "skill", "color": C_SKILL, "mention_count": 12},
        {"id": "skill:graph_rag",     "label": "Graph-RAG",         "type": "skill", "color": C_SKILL, "mention_count": 14},
        {"id": "skill:pattern_learn", "label": "模式學習",           "type": "skill", "color": C_SKILL, "mention_count": 12},
        {"id": "skill:self_eval",     "label": "自我評分",           "type": "skill", "color": C_SKILL, "mention_count": 10},
        {"id": "skill:evolution",     "label": "自動進化",           "type": "skill", "color": C_SKILL, "mention_count": 10},
        {"id": "skill:cross_session", "label": "跨會話記憶",         "type": "skill", "color": C_SKILL, "mention_count": 11},
        {"id": "skill:whisper",       "label": "Whisper 轉錄",      "type": "skill", "color": C_SKILL, "mention_count": 8},
        {"id": "skill:tesseract",     "label": "Tesseract OCR",     "type": "skill", "color": C_SKILL, "mention_count": 8},
        {"id": "skill:tool_suggest",  "label": "工具自動推薦",       "type": "skill", "color": C_SKILL, "mention_count": 9},
        {"id": "skill:upsert",        "label": "圖譜入圖管線",       "type": "skill", "color": C_SKILL, "mention_count": 12},
        {"id": "skill:matrix",        "label": "公文配對矩陣",       "type": "skill", "color": C_SKILL, "mention_count": 10},
        {"id": "skill:auto_link",     "label": "實體自動連結",       "type": "skill", "color": C_SKILL, "mention_count": 11},
        {"id": "skill:bm25",          "label": "BM25 混合搜尋",     "type": "skill", "color": C_SKILL, "mention_count": 13},
        {"id": "skill:chunking",      "label": "文件分段",           "type": "skill", "color": C_SKILL, "mention_count": 11},

        # ================================================================
        # Level 3b: 演進方向 (6 個)
        # ================================================================
        {"id": "future:multimodal",    "label": "多模態RAG",         "type": "future", "color": C_FUTURE, "mention_count": 20},
        {"id": "future:causal",        "label": "因果推理",           "type": "future", "color": C_FUTURE, "mention_count": 20},
        {"id": "future:proactive",     "label": "主動式學習",         "type": "future", "color": C_FUTURE, "mention_count": 20},
        {"id": "future:voice_stream",  "label": "即時語音串流",       "type": "future", "color": C_FUTURE, "mention_count": 20},
        {"id": "future:table_ocr",     "label": "表格辨識",           "type": "future", "color": C_FUTURE, "mention_count": 20},
        {"id": "future:cross_org",     "label": "跨組織聯邦",         "type": "future", "color": C_FUTURE, "mention_count": 20},
    ]

    edges = [
        # ================================================================
        # Layer → Capability (contains) — 灰色
        # ================================================================
        {"source": "layer:input",   "target": "cap:crud",       "type": "contains",    "label": "包含"},
        {"source": "layer:input",   "target": "cap:voice",      "type": "contains",    "label": "包含"},
        {"source": "layer:input",   "target": "cap:ocr",        "type": "contains",    "label": "包含"},
        {"source": "layer:think",   "target": "cap:agent",      "type": "contains",    "label": "包含"},
        {"source": "layer:think",   "target": "cap:rag",        "type": "contains",    "label": "包含"},
        {"source": "layer:think",   "target": "cap:nim",        "type": "contains",    "label": "包含"},
        {"source": "layer:know",    "target": "cap:kg",         "type": "contains",    "label": "包含"},
        {"source": "layer:know",    "target": "cap:discovery",  "type": "contains",    "label": "包含"},
        {"source": "layer:execute", "target": "cap:crud",       "type": "contains",    "label": "包含"},
        {"source": "layer:execute", "target": "cap:federation", "type": "contains",    "label": "包含"},
        {"source": "layer:learn",   "target": "cap:learning",   "type": "contains",    "label": "包含"},

        # ================================================================
        # Capability → Skill (implements) — 藍色
        # ================================================================
        {"source": "cap:rag",       "target": "skill:bm25",          "type": "implements", "label": "實現"},
        {"source": "cap:rag",       "target": "skill:chunking",      "type": "implements", "label": "實現"},
        {"source": "cap:rag",       "target": "skill:graph_rag",     "type": "implements", "label": "實現"},
        {"source": "cap:kg",        "target": "skill:ner",           "type": "implements", "label": "實現"},
        {"source": "cap:kg",        "target": "skill:entity_norm",   "type": "implements", "label": "實現"},
        {"source": "cap:kg",        "target": "skill:upsert",        "type": "implements", "label": "實現"},
        {"source": "cap:kg",        "target": "skill:auto_link",     "type": "implements", "label": "實現"},
        {"source": "cap:learning",  "target": "skill:pattern_learn", "type": "implements", "label": "實現"},
        {"source": "cap:learning",  "target": "skill:self_eval",     "type": "implements", "label": "實現"},
        {"source": "cap:learning",  "target": "skill:evolution",     "type": "implements", "label": "實現"},
        {"source": "cap:learning",  "target": "skill:cross_session", "type": "implements", "label": "實現"},
        {"source": "cap:voice",     "target": "skill:whisper",       "type": "implements", "label": "實現"},
        {"source": "cap:ocr",       "target": "skill:tesseract",     "type": "implements", "label": "實現"},
        {"source": "cap:discovery", "target": "skill:tool_suggest",  "type": "implements", "label": "實現"},
        {"source": "cap:crud",      "target": "skill:matrix",        "type": "implements", "label": "實現"},

        # ================================================================
        # Capability → Capability (depends_on) — 紅色
        # ================================================================
        {"source": "cap:agent",      "target": "cap:rag",        "type": "depends_on", "label": "依賴"},
        {"source": "cap:agent",      "target": "cap:kg",         "type": "depends_on", "label": "依賴"},
        {"source": "cap:agent",      "target": "cap:discovery",  "type": "depends_on", "label": "依賴"},
        {"source": "cap:rag",        "target": "cap:crud",       "type": "depends_on", "label": "依賴"},
        {"source": "cap:nim",        "target": "cap:rag",        "type": "depends_on", "label": "依賴"},
        {"source": "cap:federation", "target": "cap:agent",      "type": "depends_on", "label": "依賴"},

        # ================================================================
        # Capability ← Capability (enhances) — 綠色
        # ================================================================
        {"source": "cap:learning",   "target": "cap:agent",      "type": "enhances",   "label": "強化"},
        {"source": "cap:kg",         "target": "cap:rag",        "type": "enhances",   "label": "強化"},
        {"source": "cap:discovery",  "target": "cap:agent",      "type": "enhances",   "label": "強化"},
        {"source": "cap:voice",      "target": "cap:crud",       "type": "enhances",   "label": "強化"},
        {"source": "cap:ocr",        "target": "cap:crud",       "type": "enhances",   "label": "強化"},

        # ================================================================
        # Skill → Skill (feeds) — 橘色
        # ================================================================
        {"source": "skill:ner",           "target": "skill:entity_norm",   "type": "feeds",      "label": "資料流"},
        {"source": "skill:entity_norm",   "target": "skill:upsert",       "type": "feeds",      "label": "資料流"},
        {"source": "skill:upsert",        "target": "skill:auto_link",    "type": "feeds",      "label": "資料流"},
        {"source": "skill:chunking",      "target": "skill:bm25",         "type": "feeds",      "label": "資料流"},
        {"source": "skill:self_eval",     "target": "skill:evolution",    "type": "feeds",      "label": "資料流"},
        {"source": "skill:pattern_learn", "target": "skill:cross_session","type": "feeds",      "label": "資料流"},
        {"source": "skill:ner",           "target": "skill:graph_rag",    "type": "feeds",      "label": "資料流"},
        {"source": "skill:auto_link",     "target": "skill:matrix",       "type": "feeds",      "label": "資料流"},

        # ================================================================
        # Skill + Skill (integrates) — 紫色
        # ================================================================
        {"source": "skill:graph_rag",     "target": "skill:bm25",         "type": "integrates", "label": "整合"},
        {"source": "skill:graph_rag",     "target": "skill:upsert",       "type": "integrates", "label": "整合"},
        {"source": "skill:cross_session", "target": "skill:tool_suggest", "type": "integrates", "label": "整合"},

        # ================================================================
        # Current → Future (evolves_to) — 粉色
        # ================================================================
        {"source": "cap:rag",        "target": "future:multimodal",   "type": "evolves_to", "label": "演進"},
        {"source": "cap:agent",      "target": "future:causal",       "type": "evolves_to", "label": "演進"},
        {"source": "cap:learning",   "target": "future:proactive",    "type": "evolves_to", "label": "演進"},
        {"source": "cap:voice",      "target": "future:voice_stream", "type": "evolves_to", "label": "演進"},
        {"source": "cap:ocr",        "target": "future:table_ocr",    "type": "evolves_to", "label": "演進"},
        {"source": "cap:federation", "target": "future:cross_org",    "type": "evolves_to", "label": "演進"},

        # ================================================================
        # Cross-layer connections (enhances / feeds / depends_on)
        # ================================================================
        # Skills enhancing capabilities they don't directly belong to
        {"source": "skill:bm25",          "target": "cap:agent",      "type": "enhances",   "label": "強化"},
        {"source": "skill:cross_session", "target": "cap:agent",      "type": "enhances",   "label": "強化"},
        {"source": "skill:tool_suggest",  "target": "cap:agent",      "type": "enhances",   "label": "強化"},
        {"source": "skill:entity_norm",   "target": "cap:rag",        "type": "enhances",   "label": "強化"},

        # Future nodes feeding back
        {"source": "future:multimodal",   "target": "future:table_ocr",    "type": "integrates", "label": "整合"},
        {"source": "future:proactive",    "target": "future:causal",       "type": "depends_on", "label": "依賴"},
        {"source": "future:cross_org",    "target": "future:voice_stream", "type": "integrates", "label": "整合"},
    ]

    return {
        "success": True,
        "nodes": nodes,
        "edges": edges,
    }
