"""
技能演化樹服務

掃描系統實際模組（Skills/Agents/AI Services/Tools），
生成技能節點 + 演化路徑 + 融合關係的圖譜數據。

靈感來源：Muse 技能演化樹（版本軌跡 + 融合線 + 分類篩選）

@version 1.0.0
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 專案根目錄
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_CLAUDE_DIR = _PROJECT_ROOT / ".claude"
_BACKEND_DIR = _PROJECT_ROOT / "backend"
_AI_SERVICES_DIR = _BACKEND_DIR / "app" / "services" / "ai"


# ============================================================================
# 分類定義（對應 Muse 的類別色系）
# ============================================================================

CATEGORIES = {
    "perception": {"label": "感知", "color": "#52c41a", "icon": "👁️"},
    "cognition": {"label": "認知", "color": "#1890ff", "icon": "🧠"},
    "knowledge": {"label": "知識", "color": "#722ed1", "icon": "📚"},
    "execution": {"label": "行動", "color": "#fa8c16", "icon": "⚡"},
    "learning": {"label": "學習", "color": "#13c2c2", "icon": "🎯"},
    "inference": {"label": "推理", "color": "#f5222d", "icon": "🔮"},
    "devops": {"label": "工程", "color": "#faad14", "icon": "🔧"},
    "security": {"label": "安全", "color": "#eb2f96", "icon": "🔒"},
    "data": {"label": "資料", "color": "#2f54eb", "icon": "💾"},
    "integration": {"label": "整合", "color": "#a0d911", "icon": "🔗"},
}


def build_skill_tree() -> Dict[str, Any]:
    """
    建構完整的技能演化樹

    Returns:
        {
            "nodes": [...],        # 技能節點
            "edges": [...],        # 演化/融合關係
            "categories": {...},   # 分類定義
            "stats": {...},        # 統計數據
        }
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_id = 0

    def add_node(
        name: str,
        category: str,
        version: str = "v1.0",
        maturity: int = 3,
        source: str = "auto",
        description: str = "",
        children: Optional[List[str]] = None,
        size: int = 10,
    ) -> int:
        nonlocal node_id
        node_id += 1
        nodes.append({
            "id": node_id,
            "name": name,
            "category": category,
            "version": version,
            "maturity": maturity,  # 1-5 星
            "source": source,  # auto/manual/merged
            "description": description,
            "size": size,
            "children": children or [],
            "created_at": "2026-03-19",
        })
        return node_id

    def add_edge(
        source_id: int,
        target_id: int,
        edge_type: str = "evolution",  # evolution/merge/planned
        label: str = "",
    ):
        edges.append({
            "source": source_id,
            "target": target_id,
            "type": edge_type,
            "label": label,
        })

    # ====================================================================
    # 主幹：乾坤智能體
    # ====================================================================
    root = add_node("乾坤智能體", "cognition", "v4.0", 5, "auto",
                     "33 模組 · 23 工具 · ReAct 推理", size=30)

    # ====================================================================
    # 感知層
    # ====================================================================
    perception = add_node("感知層", "perception", "v2.0", 4, "auto",
                          "文字+語音+OCR+PDF 多模態輸入", size=20)
    add_edge(root, perception, "evolution", "v1→v2")

    text_input = add_node("文字輸入", "perception", "v3.0", 5, "auto",
                          "公文/派工/閒聊偵測 8回退模式")
    voice = add_node("語音辨識", "perception", "v1.0", 3, "auto",
                     "Groq Whisper + Ollama 備用")
    ocr = add_node("影像辨識", "perception", "v1.0", 3, "auto",
                   "Tesseract OCR chi_tra+eng")
    pdf = add_node("文件解析", "perception", "v1.0", 3, "auto",
                   "PDF 文字提取 + 附件處理")
    multimodal = add_node("多模態理解", "perception", "v0.1", 1, "planned",
                          "圖片理解·表格OCR（規劃中）", size=8)

    for child in [text_input, voice, ocr, pdf]:
        add_edge(perception, child, "evolution")
    add_edge(perception, multimodal, "planned", "Phase 3")

    # ====================================================================
    # 認知層
    # ====================================================================
    cognition_layer = add_node("認知層", "cognition", "v3.0", 5, "auto",
                               "3層路由+ReAct+6策略修正", size=20)
    add_edge(root, cognition_layer, "evolution", "v2→v3")

    router = add_node("3層路由", "cognition", "v1.0", 5, "auto",
                      "chitchat→pattern→LLM 逐層篩選")
    intent = add_node("意圖解析", "cognition", "v2.4", 5, "auto",
                      "6策略自動修正+工具動態發現")
    react = add_node("ReAct 推理", "cognition", "v2.0", 4, "auto",
                     "max 3 iter · 雙層評估 · Chain-of-Tools")
    supervisor = add_node("多域協調", "cognition", "v1.0", 4, "auto",
                          "Supervisor 多域分解·並行子任務")
    cot = add_node("多步推理", "cognition", "v0.1", 2, "planned",
                   "Chain-of-Thought·自我反思（規劃中）", size=8)

    for child in [router, intent, react, supervisor]:
        add_edge(cognition_layer, child, "evolution")
    add_edge(cognition_layer, cot, "planned", "Phase 3")
    # 融合：意圖解析 + 工具發現 → 合併到 planner
    add_edge(intent, react, "merge", "融合")

    # ====================================================================
    # 知識層
    # ====================================================================
    knowledge_layer = add_node("知識層", "knowledge", "v3.0", 5, "auto",
                               "三圖架構+RAG+文庫", size=22)
    add_edge(root, knowledge_layer, "evolution", "v1→v3")

    kg = add_node("知識圖譜", "knowledge", "v5.0", 5, "auto",
                  "4399實體·5694關係·7-Phase建構", size=18)
    code_graph = add_node("程式碼圖譜", "knowledge", "v3.1", 4, "auto",
                          "3955實體·Python+TS AST分析", size=14)
    db_graph = add_node("DB圖譜", "knowledge", "v2.0", 4, "auto",
                        "253表 Schema反射·ER視覺化", size=12)
    rag = add_node("RAG文庫", "knowledge", "v2.4", 5, "auto",
                   "1641chunks·BM25+Vector·Graph-RAG", size=16)
    kb = add_node("知識庫", "knowledge", "v2.0", 3, "auto",
                  "371 markdown·向量搜尋·ADR", size=12)

    for child in [kg, code_graph, db_graph, rag, kb]:
        add_edge(knowledge_layer, child, "evolution")

    # 融合關係
    unified_search = add_node("跨圖譜統一查詢", "knowledge", "v1.0", 4, "merged",
                              "KG+Code+DB 並行查詢", size=10)
    add_edge(kg, unified_search, "merge", "融合")
    add_edge(code_graph, unified_search, "merge", "融合")
    add_edge(db_graph, unified_search, "merge", "融合")

    graph_rag = add_node("Graph-RAG 融合", "knowledge", "v1.0", 4, "merged",
                         "KG實體擴展→RAG向量檢索", size=10)
    add_edge(kg, graph_rag, "merge", "融合")
    add_edge(rag, graph_rag, "merge", "融合")

    # ====================================================================
    # 行動層
    # ====================================================================
    exec_layer = add_node("行動層", "execution", "v2.0", 4, "auto",
                          "23工具·矩陣對照·6層匹配", size=18)
    add_edge(root, exec_layer, "evolution", "v1→v2")

    search_tools = add_node("搜尋工具群", "execution", "v2.0", 5, "auto",
                            "doc/dispatch/entity/similar/correspondence")
    analysis_tools = add_node("分析工具群", "execution", "v1.5", 4, "auto",
                              "stats/detail/health/diagram/parse/KB搜尋")
    graph_tools = add_node("圖譜工具群", "execution", "v1.0", 4, "auto",
                           "navigate/explore/summarize")
    domain_tools = add_node("PM/ERP工具群", "execution", "v1.0", 4, "auto",
                            "project/vendor/contract/milestone/billing")
    ext_tools = add_node("外部整合", "execution", "v0.5", 2, "planned",
                         "LINE推播·Email·Webhook（規劃中）", size=8)

    for child in [search_tools, analysis_tools, graph_tools, domain_tools]:
        add_edge(exec_layer, child, "evolution")
    add_edge(exec_layer, ext_tools, "planned", "Phase 4")

    # ====================================================================
    # 學習層
    # ====================================================================
    learn_layer = add_node("學習層", "learning", "v2.0", 4, "auto",
                           "模式學習+自評+進化+記憶", size=16)
    add_edge(root, learn_layer, "evolution", "v1→v2")

    pattern = add_node("模式學習", "learning", "v2.0", 4, "auto",
                       "MD5+cosine 0.85·500模式·29種子")
    self_eval = add_node("自我評估", "learning", "v1.0", 4, "auto",
                         "5維度加權·50次/24h進化")
    memory = add_node("跨會話記憶", "learning", "v1.0", 4, "auto",
                      "Redis 1h TTL + DB持久化")
    user_profile = add_node("使用者畫像", "learning", "v0.1", 2, "planned",
                            "偏好學習·行為分析（規劃中）", size=8)

    for child in [pattern, self_eval, memory]:
        add_edge(learn_layer, child, "evolution")
    add_edge(learn_layer, user_profile, "planned", "Phase 3")

    # ====================================================================
    # 推理層
    # ====================================================================
    inference_layer = add_node("推理層", "inference", "v3.0", 5, "auto",
                               "vLLM+Groq+NVIDIA+Ollama 4層", size=18)
    add_edge(root, inference_layer, "evolution", "v1→v3")

    vllm = add_node("vLLM Local", "inference", "v1.0", 4, "auto",
                    "Qwen2.5-7B-AWQ·5.2GB·P0優先")
    groq = add_node("Groq Cloud", "inference", "v2.0", 5, "auto",
                    "llama-3.3-70b·免費30K/day·P1")
    nvidia = add_node("NVIDIA Cloud", "inference", "v1.0", 4, "auto",
                      "Nemotron-49B·高品質·P1")
    ollama = add_node("Ollama Local", "inference", "v3.0", 5, "auto",
                      "qwen3:4b+nomic-embed·P2備援")
    nim = add_node("NIM Local", "inference", "v0.5", 2, "planned",
                   "待TRT-LLM profile支援", size=8)
    nvidia_embed = add_node("NVIDIA Embedding", "inference", "v0.1", 1, "planned",
                            "nemotron-embed 2048D（規劃中）", size=8)

    for child in [vllm, groq, nvidia, ollama]:
        add_edge(inference_layer, child, "evolution")
    add_edge(inference_layer, nim, "planned", "待NIM更新")
    add_edge(inference_layer, nvidia_embed, "planned", "Phase 3")

    # 融合：vLLM 從 NIM 演化
    add_edge(nim, vllm, "merge", "NIM→vLLM")

    # ====================================================================
    # 工程/DevOps 支線
    # ====================================================================
    devops_branch = add_node("工程能力", "devops", "v2.0", 4, "auto",
                             "CI/CD·Docker·PM2·Alembic", size=14)
    add_edge(root, devops_branch, "evolution")

    service_split = add_node("服務拆分", "devops", "v3.0", 5, "auto",
                             "13→6 >500L·11新模組")
    n1_fix = add_node("N+1修復", "devops", "v1.0", 4, "auto",
                      "batch fuzzy·FK合併")
    testing = add_node("測試套件", "devops", "v2.0", 5, "auto",
                       "5503測試·80%+ coverage")

    for child in [service_split, n1_fix, testing]:
        add_edge(devops_branch, child, "evolution")

    # ====================================================================
    # 安全支線
    # ====================================================================
    security_branch = add_node("安全能力", "security", "v1.5", 4, "auto",
                               "CSRF+Rate Limit+RLS", size=12)
    add_edge(root, security_branch, "evolution")

    # ====================================================================
    # 整合支線
    # ====================================================================
    integration_branch = add_node("外部整合", "integration", "v1.0", 3, "auto",
                                  "OpenClaw·LINE·Calendar", size=12)
    add_edge(root, integration_branch, "evolution")

    openclaw = add_node("OpenClaw 聯邦", "integration", "v0.5", 2, "planned",
                        "CK_Missive ↔ CK_OpenClaw", size=8)
    line = add_node("LINE Bot", "integration", "v1.0", 3, "auto",
                    "LINE Webhook + 推播排程")
    calendar = add_node("Google Calendar", "integration", "v1.2", 4, "auto",
                        "雙向同步·截止日追蹤")

    add_edge(integration_branch, line, "evolution")
    add_edge(integration_branch, calendar, "evolution")
    add_edge(integration_branch, openclaw, "planned", "Phase 4")

    # ====================================================================
    # 統計
    # ====================================================================
    active = sum(1 for n in nodes if n["source"] != "planned")
    planned = sum(1 for n in nodes if n["source"] == "planned")
    merged = sum(1 for n in nodes if n["source"] == "merged")
    evolution_edges = sum(1 for e in edges if e["type"] == "evolution")
    merge_edges = sum(1 for e in edges if e["type"] == "merge")

    return {
        "nodes": nodes,
        "edges": edges,
        "categories": CATEGORIES,
        "stats": {
            "total": len(nodes),
            "active": active,
            "planned": planned,
            "merged": merged,
            "evolution_count": evolution_edges,
            "merge_count": merge_edges,
            "generated_at": datetime.now().isoformat(),
        },
    }
