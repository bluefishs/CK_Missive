"""
Agent 工具定義 — 分析/圖譜/視覺化工具

從 tool_definitions.py 拆分 (v1.4.0)
包含 11 個分析、詳情、圖譜導航類工具的聲明式定義。
"""

from .tool_registry import ToolDefinition, ToolRegistry


def register_analysis_tools(registry: ToolRegistry) -> None:
    """註冊分析/圖譜/視覺化工具 (11 個)"""

    # 3. get_entity_detail
    registry.register(ToolDefinition(
        name="get_entity_detail",
        description="取得知識圖譜中某個實體的詳細資訊，包含別名、關係、關聯公文。適合深入了解特定機關、人員或專案。",
        parameters={
            "entity_id": {"type": "integer", "description": "實體 ID (從 search_entities 取得)"},
        },
        priority=3,
    ))

    # 4. find_similar (公文助理專用)
    registry.register(ToolDefinition(
        name="find_similar",
        description="根據指定公文 ID 查找語意相似的公文。適合找出相關或類似主題的公文。",
        parameters={
            "document_id": {"type": "integer", "description": "公文 ID (從 search_documents 取得)"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5)"},
        },
        priority=2,
        contexts=["doc"],
    ))

    # 6. get_statistics (公文+開發共用)
    registry.register(ToolDefinition(
        name="get_statistics",
        description="取得系統統計資訊：知識圖譜實體/關係數量、高頻實體排行等。適合回答「系統有多少」「最常見的」之類的問題。",
        parameters={},
        few_shot={
            "question": "系統裡有多少公文和實體？",
            "response_json": '{"reasoning": "查詢系統統計資訊", "tool_calls": [{"name": "get_statistics", "params": {}}]}',
        },
        priority=1,
    ))

    # 7. navigate_graph — 導航 Agent 工具
    registry.register(ToolDefinition(
        name="navigate_graph",
        description="在 3D 知識圖譜中導航至指定實體或叢集。搜尋實體後回傳座標與鄰居資訊，前端可據此執行 fly-to 動畫。",
        parameters={
            "query": {"type": "string", "description": "搜尋關鍵字或實體名稱"},
            "entity_type": {"type": "string", "description": "限定實體類型 (org/person/project/location)"},
            "expand_neighbors": {"type": "boolean", "description": "是否展開鄰居節點 (預設 true)"},
        },
        few_shot={
            "question": "帶我看淨零排碳相關的公文叢集",
            "response_json": '{"reasoning": "導航至圖譜中淨零排碳相關的實體叢集", "tool_calls": [{"name": "navigate_graph", "params": {"query": "淨零排碳", "expand_neighbors": true}}]}',
        },
        priority=7,
    ))

    # 8. summarize_entity — 摘要 Agent 工具
    registry.register(ToolDefinition(
        name="summarize_entity",
        description="對指定實體生成智能摘要簡報：包含基本資訊、上下游關係、關聯公文時間軸、關鍵事件。",
        parameters={
            "entity_id": {"type": "integer", "description": "實體 ID (從 search_entities 取得)"},
            "include_timeline": {"type": "boolean", "description": "是否包含時間軸 (預設 true)"},
            "include_upstream_downstream": {"type": "boolean", "description": "是否包含上下游分析 (預設 true)"},
        },
        few_shot={
            "question": "這個工程案件的來龍去脈是什麼？",
            "response_json": '{"reasoning": "需要生成實體的完整摘要包含上下游關係", "tool_calls": [{"name": "summarize_entity", "params": {"entity_id": 42, "include_timeline": true, "include_upstream_downstream": true}}]}',
        },
        priority=6,
    ))

    # 9. draw_diagram — 視覺化圖表生成
    registry.register(ToolDefinition(
        name="draw_diagram",
        description="根據查詢主題自動生成 Mermaid 圖表（ER圖、流程圖、架構圖、關聯圖）。圖表以 Mermaid 語法返回，前端會自動渲染。",
        parameters={
            "diagram_type": {"type": "string", "description": "圖表類型: erDiagram/flowchart/classDiagram/graph (預設自動判斷)"},
            "scope": {"type": "string", "description": "範圍限定，如表名、模組名、實體名 (可選)"},
            "detail_level": {"type": "string", "description": "詳細程度: brief/normal/full (預設 normal)"},
        },
        few_shot={
            "question": "畫出派工單相關的資料庫結構圖",
            "response_json": '{"reasoning": "需要生成資料庫 ER 圖，範圍限定在派工單相關表", "tool_calls": [{"name": "draw_diagram", "params": {"diagram_type": "erDiagram", "scope": "taoyuan", "detail_level": "normal"}}]}',
        },
        priority=6,
    ))

    # 10. find_correspondence — 派工單收發文對照查詢
    registry.register(ToolDefinition(
        name="find_correspondence",
        description="查詢派工單的收發文對應關係，回傳 confirmed/high/medium/low 信心度的配對建議。",
        parameters={
            "dispatch_id": {"type": "integer", "description": "派工單 ID"},
        },
        few_shot={
            "question": "派工單號014的來文和覆文配對狀況如何？",
            "response_json": '{"reasoning": "查詢派工單的收發文對照關係", "tool_calls": [{"name": "search_dispatch_orders", "params": {"dispatch_no": "014", "limit": 1}}, {"name": "find_correspondence", "params": {"dispatch_id": 14}}]}',
        },
        priority=7,
        contexts=["doc", "dispatch"],
    ))

    # 11. explore_entity_path — 圖譜路徑探索
    registry.register(ToolDefinition(
        name="explore_entity_path",
        description="探索兩個實體之間的知識圖譜最短路徑，找出關聯鏈和中間節點。",
        parameters={
            "entity_a": {"type": "string", "description": "起始實體名稱或 ID"},
            "entity_b": {"type": "string", "description": "目標實體名稱或 ID"},
            "max_hops": {"type": "integer", "description": "最大跳數 (預設3, 最大6)"},
        },
        few_shot={
            "question": "桃園市政府工務局和養護工程處有什麼關聯？",
            "response_json": '{"reasoning": "探索兩個機關在圖譜中的關聯路徑", "tool_calls": [{"name": "explore_entity_path", "params": {"entity_a": "桃園市政府工務局", "entity_b": "養護工程處", "max_hops": 3}}]}',
        },
        priority=4,
    ))

    # 12. get_system_health — 系統健康分析
    registry.register(ToolDefinition(
        name="get_system_health",
        description="取得系統健康報告，包含資料庫狀態、連線池、系統資源、資料品質指標、備份狀態。",
        parameters={
            "include_benchmarks": {"type": "boolean", "description": "是否包含效能基準測試 (預設 false)"},
        },
        few_shot={
            "question": "本系統目前的健康狀態如何？",
            "response_json": '{"reasoning": "使用者詢問系統健康狀態，需要取得真實系統數據", "tool_calls": [{"name": "get_system_health", "params": {"include_benchmarks": false}}]}',
        },
        priority=8,
        contexts=["agent"],
    ))

    # 31. analyze_diagram — 工程圖/測量圖 Vision 分析
    registry.register(ToolDefinition(
        name="analyze_diagram",
        description="分析工程圖、測量圖或地籍圖，提取座標、面積、標註等資訊。支援測量圖(survey)、地籍圖(cadastral)、工程圖(engineering)、藍圖(blueprint)四種類型。",
        parameters={
            "image_path": {"type": "string", "description": "附件路徑或 URL"},
            "diagram_type": {"type": "string", "description": "圖面類型: survey|cadastral|engineering|blueprint (預設 survey)"},
            "context": {"type": "string", "description": "可選背景資訊（如專案名稱、位置）"},
        },
        few_shot={
            "question": "幫我分析這張測量圖的座標",
            "response_json": '{"reasoning": "使用 Vision 分析測量圖提取座標和面積", "tool_calls": [{"name": "analyze_diagram", "params": {"image_path": "attachments/survey_001.png", "diagram_type": "survey"}}]}',
        },
        priority=5,
        contexts=["doc", "pm"],
    ))

    # 41. analyze_document_intent — 公文意圖分析
    registry.register(ToolDefinition(
        name="analyze_document_intent",
        description="分析公文意圖：判斷是否需要回覆、需要轉發、還是僅供備查。使用 Gemma 4 AI 分析公文內容並給出建議動作。",
        parameters={
            "document_id": {"type": "integer", "description": "公文 ID"},
        },
        few_shot={
            "question": "這封公文需要回覆嗎？",
            "response_json": '{"reasoning": "分析公文意圖判斷需要的動作", "tool_calls": [{"name": "analyze_document_intent", "params": {"document_id": 123}}]}',
        },
        priority=5,
        contexts=["doc"],
    ))

    # === LLM Wiki 工具 (v5.5.4) ===

    # 12. wiki_search — Agent 搜尋 wiki 知識庫
    registry.register(ToolDefinition(
        name="wiki_search",
        description="搜尋 LLM Wiki 知識頁面，包含實體、主題、來源摘要、綜合分析。用於查詢已整理的結構化知識。",
        parameters={
            "query": {"type": "string", "description": "搜尋關鍵字"},
        },
        few_shot={
            "question": "我們跟桃園市政府有什麼合作？",
            "response_json": '{"reasoning": "搜尋 wiki 中桃園市政府相關頁面", "tool_calls": [{"name": "wiki_search", "params": {"query": "桃園市政府"}}]}',
        },
        priority=6,
        contexts=["agent", "doc", "pm"],
    ))

    # 13. wiki_read — Agent 讀取特定 wiki 頁面
    registry.register(ToolDefinition(
        name="wiki_read",
        description="讀取指定的 wiki 頁面完整內容。路徑格式: entities/X.md, topics/X.md, sources/X.md, synthesis/X.md",
        parameters={
            "page_path": {"type": "string", "description": "wiki 頁面路徑 (如 entities/桃園市政府.md)"},
        },
        priority=6,
        contexts=["agent"],
    ))

    # 14. wiki_ingest — Agent 將知識寫入 wiki
    registry.register(ToolDefinition(
        name="wiki_ingest",
        description="將新知識寫入 wiki。Agent 在回答問題後，若產出有價值的分析或發現，應主動存入 wiki 供未來查詢。",
        parameters={
            "title": {"type": "string", "description": "頁面標題"},
            "content": {"type": "string", "description": "Markdown 內容"},
            "page_type": {"type": "string", "description": "頁面類型: entity/topic/source/synthesis"},
            "tags": {"type": "string", "description": "標籤 (逗號分隔)"},
        },
        priority=4,
        contexts=["agent"],
    ))
