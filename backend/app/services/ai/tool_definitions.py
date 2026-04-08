"""
Agent 工具定義資料

從 tool_registry.py 拆分 (v1.2.0)
包含系統內建 32+ 個工具的聲明式定義。

新增工具時只需在此檔案加入 ToolDefinition 即可。
Updated: v1.3.0 (2026-04-05) 新增 10 個業務模組工具 (asset/expense/dispatch/pm/document)
"""

import logging

from .tool_registry import ToolDefinition, ToolRegistry

logger = logging.getLogger(__name__)


def register_default_tools(registry: ToolRegistry) -> None:
    """註冊系統內建的 22 個工具"""

    # 1. search_documents (公文助理專用)
    registry.register(ToolDefinition(
        name="search_documents",
        description="搜尋公文資料庫，支援關鍵字、發文單位、受文單位、日期範圍、公文類型等條件。回傳匹配的公文列表。",
        parameters={
            "keywords": {"type": "array", "description": "搜尋關鍵字列表"},
            "sender": {"type": "string", "description": "發文單位 (模糊匹配)"},
            "receiver": {"type": "string", "description": "受文單位 (模糊匹配)"},
            "doc_type": {"type": "string", "description": "公文類型 (函/令/公告/書函/開會通知單/簽等)"},
            "date_from": {"type": "string", "description": "起始日期 YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "結束日期 YYYY-MM-DD"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5, 最大10)"},
        },
        few_shot={
            "question": "工務局上個月發的函有哪些？",
            "response_json": '{"reasoning": "查詢特定機關的近期公文，使用日期和發文單位篩選", "tool_calls": [{"name": "search_documents", "params": {"sender": "桃園市政府工務局", "doc_type": "函", "date_from": "2026-01-01", "date_to": "2026-01-31", "limit": 8}}]}',
        },
        priority=10,
        contexts=["doc"],
    ))

    # 2. search_entities (公文+開發共用)
    registry.register(ToolDefinition(
        name="search_entities",
        description="在知識圖譜中搜尋實體（機關、人員、專案、地點、程式碼模組、類別、函數、資料表等）。回傳匹配的正規化實體列表。",
        parameters={
            "query": {"type": "string", "description": "搜尋文字"},
            "entity_type": {"type": "string", "description": "篩選實體類型: org/person/project/location/date/py_module/py_class/py_function/db_table"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5)"},
        },
        few_shot={
            "question": "桃園市政府工務局相關的專案有哪些？",
            "response_json": '{"reasoning": "查詢機關相關的實體關係，使用知識圖譜搜尋", "tool_calls": [{"name": "search_entities", "params": {"query": "桃園市政府工務局", "entity_type": "organization", "limit": 5}}, {"name": "search_documents", "params": {"keywords": ["桃園市政府工務局", "專案"], "limit": 5}}]}',
        },
        priority=5,
    ))

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

    # 5. search_dispatch_orders (公文助理專用)
    registry.register(ToolDefinition(
        name="search_dispatch_orders",
        description="搜尋派工單紀錄（桃園市政府工務局委託案件）。支援派工單號、工程名稱、作業類別等條件。適合查詢「派工單號XXX」「道路工程派工」「測量作業」等問題。",
        parameters={
            "dispatch_no": {"type": "string", "description": "派工單號 (模糊匹配，如 '014' 會匹配 '115年_派工單號014')"},
            "search": {"type": "string", "description": "關鍵字搜尋 (同時搜尋派工單號 + 工程名稱)"},
            "work_type": {"type": "string", "description": "作業類別 (如 地形測量/控制測量/協議價購/用地取得 等)"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5, 最大20)"},
        },
        few_shot={
            "question": "查詢派工單號014紀錄",
            "response_json": '{"reasoning": "查詢特定派工單號，使用派工單搜尋", "tool_calls": [{"name": "search_dispatch_orders", "params": {"dispatch_no": "014", "limit": 5}}]}',
        },
        priority=8,
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

    # === PM 專案管理工具 (v1.83.0) ===

    # 13. search_projects — PM 角色
    registry.register(ToolDefinition(
        name="search_projects",
        description="搜尋承攬案件（專案），支援關鍵字、狀態、年度、委託單位等條件。回傳匹配的案件列表（含金額/進度）。",
        parameters={
            "keywords": {"type": "array", "description": "搜尋關鍵字列表"},
            "status": {"type": "string", "description": "案件狀態 (執行中/已完工/驗收中/保固中/已結案)"},
            "year": {"type": "integer", "description": "年度篩選 (民國年或西元年)"},
            "client_agency": {"type": "string", "description": "委託單位 (模糊匹配)"},
            "limit": {"type": "integer", "description": "最大結果數 (預設10, 最大20)"},
        },
        few_shot={
            "question": "目前執行中的案件有哪些？",
            "response_json": '{"reasoning": "查詢執行中的承攬案件", "tool_calls": [{"name": "search_projects", "params": {"status": "執行中", "limit": 10}}]}',
        },
        priority=8,
        contexts=["pm"],
    ))

    # 14. get_project_detail — PM 角色
    registry.register(ToolDefinition(
        name="get_project_detail",
        description="取得承攬案件的詳細資訊，包含案件基本資料、關聯工程數、派工單數。",
        parameters={
            "project_id": {"type": "integer", "description": "案件 ID (從 search_projects 取得)"},
        },
        priority=5,
        contexts=["pm"],
    ))

    # 15. get_project_progress — PM 角色
    registry.register(ToolDefinition(
        name="get_project_progress",
        description="取得案件進度與里程碑概要，包含派工批次統計、工程進度摘要、是否逾期、剩餘天數。",
        parameters={
            "project_id": {"type": "integer", "description": "案件 ID"},
        },
        few_shot={
            "question": "這個案件的進度如何？",
            "response_json": '{"reasoning": "查詢案件進度與里程碑", "tool_calls": [{"name": "get_project_progress", "params": {"project_id": 5}}]}',
        },
        priority=6,
        contexts=["pm"],
    ))

    # === ERP 企業資源工具 (v1.83.0) ===

    # 16. search_vendors — ERP 角色
    registry.register(ToolDefinition(
        name="search_vendors",
        description="搜尋協力廠商，支援名稱關鍵字和業務類型篩選。",
        parameters={
            "keywords": {"type": "array", "description": "搜尋關鍵字列表 (廠商名稱)"},
            "business_type": {"type": "string", "description": "業務類型 (模糊匹配)"},
            "limit": {"type": "integer", "description": "最大結果數 (預設10, 最大20)"},
        },
        few_shot={
            "question": "有哪些測量相關的協力廠商？",
            "response_json": '{"reasoning": "搜尋測量相關廠商", "tool_calls": [{"name": "search_vendors", "params": {"keywords": ["測量"], "limit": 10}}]}',
        },
        priority=5,
        contexts=["erp"],
    ))

    # 17. get_vendor_detail — ERP 角色
    registry.register(ToolDefinition(
        name="get_vendor_detail",
        description="取得協力廠商的詳細資訊，包含聯絡人、電話、地址、評等。",
        parameters={
            "vendor_id": {"type": "integer", "description": "廠商 ID (從 search_vendors 取得)"},
        },
        priority=3,
        contexts=["erp"],
    ))

    # 18. get_contract_summary — ERP 角色
    registry.register(ToolDefinition(
        name="get_contract_summary",
        description="取得合約金額統計概要，包含案件總數、契約總金額、得標總金額、平均進度、狀態分佈、年度分佈。",
        parameters={
            "year": {"type": "integer", "description": "年度篩選 (可選)"},
            "status": {"type": "string", "description": "狀態篩選 (可選)"},
        },
        few_shot={
            "question": "今年度的合約金額統計是多少？",
            "response_json": '{"reasoning": "查詢合約金額統計", "tool_calls": [{"name": "get_contract_summary", "params": {"year": 115}}]}',
        },
        priority=7,
        contexts=["erp", "pm"],
    ))

    # 19. get_overdue_milestones — PM 角色
    registry.register(ToolDefinition(
        name="get_overdue_milestones",
        description="查詢逾期里程碑 — 找出所有已過期但未完成的里程碑，含逾期天數和所屬案件。",
        parameters={
            "limit": {"type": "integer", "description": "最多回傳筆數 (預設20, 最大50)"},
        },
        few_shot={
            "question": "有哪些逾期的里程碑？",
            "response_json": '{"reasoning": "查詢所有逾期未完成的里程碑", "tool_calls": [{"name": "get_overdue_milestones", "params": {"limit": 20}}]}',
        },
        priority=7,
        contexts=["pm"],
    ))

    # 20. get_unpaid_billings — ERP 角色
    registry.register(ToolDefinition(
        name="get_unpaid_billings",
        description="查詢未收款/逾期請款 — 找出所有尚未收款或逾期的請款單，含未付金額和所屬案件。",
        parameters={
            "limit": {"type": "integer", "description": "最多回傳筆數 (預設20, 最大50)"},
        },
        few_shot={
            "question": "有哪些未收款的請款單？",
            "response_json": '{"reasoning": "查詢所有未收款或逾期的請款單", "tool_calls": [{"name": "get_unpaid_billings", "params": {"limit": 20}}]}',
        },
        priority=7,
        contexts=["erp"],
    ))

    # 21. parse_document — 公文附件文字提取 (含 OCR)
    registry.register(ToolDefinition(
        name="parse_document",
        description="解析公文附件（PDF/DOCX/TXT/圖片），提取文字內容供 RAG 問答使用。支援掃描 PDF 和圖片的 OCR 文字辨識。",
        parameters={
            "document_id": {"type": "integer", "description": "公文 ID"},
        },
        few_shot={
            "question": "幫我看一下公文 123 的附件內容",
            "response_json": '{"reasoning": "使用者想了解公文附件的文字內容，需要解析附件", "tool_calls": [{"name": "parse_document", "params": {"document_id": 123}}]}',
        },
        priority=4,
        contexts=["doc"],
    ))

    # 23. search_knowledge_base — 知識庫文件搜尋
    registry.register(ToolDefinition(
        name="search_knowledge_base",
        description="搜尋系統知識庫文件（包含 API 規格、架構文件、ADR 決策記錄、開發規範等技術文件）。適用於查詢系統架構、開發標準、技術決策相關問題。",
        parameters={
            "query": {"type": "string", "description": "搜尋關鍵字"},
            "limit": {"type": "integer", "description": "最大結果數 (預設5)"},
        },
        few_shot={
            "question": "系統的 API 認證機制是什麼？",
            "response_json": '{"reasoning": "這是關於系統架構的技術問題，需要查詢知識庫文件", "tool_calls": [{"name": "search_knowledge_base", "params": {"query": "API 認證 auth", "limit": 5}}]}',
        },
        priority=3,
        contexts=["dev", "agent"],
    ))

    # 24. ask_external_system — 聯邦式外部 AI 系統查詢
    registry.register(ToolDefinition(
        name="ask_external_system",
        description="詢問外部 AI 系統（如 CK_OpenClaw）處理超出本系統專業範圍的查詢。僅在已設定外部系統時可用。",
        parameters={
            "system_id": {"type": "string", "description": "目標系統 ID (目前支援: openclaw)"},
            "question": {"type": "string", "description": "要轉發的問題"},
        },
        few_shot={
            "question": "OpenClaw 有哪些頻道？",
            "response_json": '{"reasoning": "這是關於 OpenClaw 系統的問題，超出本系統範圍，委派給外部系統", "tool_calls": [{"name": "ask_external_system", "params": {"system_id": "openclaw", "question": "有哪些頻道？"}}]}',
        },
        priority=1,
        contexts=["agent"],
    ))

    # === Finance Tools (Phase 3, v5.1.1) ===

    # 25. get_financial_summary — 財務總覽
    registry.register(ToolDefinition(
        name="get_financial_summary",
        description="查詢專案或全公司的財務總覽，包含收入、支出、結餘。可指定案件代碼查詢單一專案，或不指定查詢公司整體（含 Top N 專案排行）。",
        parameters={
            "case_code": {"type": "string", "description": "案件代碼 (如 A-115-001)，不提供則查詢全公司"},
            "year": {"type": "integer", "description": "民國年度篩選 (如 115)"},
            "top_n": {"type": "integer", "description": "公司總覽時回傳前 N 專案 (預設10)"},
        },
        few_shot={
            "question": "公司今年的財務狀況如何？",
            "response_json": '{"reasoning": "查詢公司整體財務概況，使用民國年篩選", "tool_calls": [{"name": "get_financial_summary", "params": {"year": 115, "top_n": 10}}]}',
        },
        priority=8,
        contexts=["erp", "pm"],
    ))

    # 26. get_expense_overview — 費用報銷總覽
    registry.register(ToolDefinition(
        name="get_expense_overview",
        description="查詢費用報銷發票列表，可依案件代碼或審核狀態篩選。狀態包含: pending(待審核)、verified(已審核)、rejected(已駁回)、pending_receipt(待核銷)。",
        parameters={
            "case_code": {"type": "string", "description": "案件代碼篩選"},
            "status": {"type": "string", "description": "狀態篩選 (pending/verified/rejected/pending_receipt)"},
            "limit": {"type": "integer", "description": "最大結果數 (預設20)"},
        },
        few_shot={
            "question": "目前有哪些待審核的報銷單？",
            "response_json": '{"reasoning": "查詢待審核狀態的報銷發票", "tool_calls": [{"name": "get_expense_overview", "params": {"status": "pending", "limit": 20}}]}',
        },
        priority=6,
        contexts=["erp"],
    ))

    # 27. check_budget_alert — 預算超支警報
    registry.register(ToolDefinition(
        name="check_budget_alert",
        description="檢查各專案是否有預算超支或接近超支的情況。回傳超過閾值的專案警報清單，含使用率百分比。",
        parameters={
            "threshold_pct": {"type": "number", "description": "警報閾值百分比 (預設80，即支出超過收入80%時警報)"},
            "year": {"type": "integer", "description": "民國年度篩選 (如 115)"},
        },
        few_shot={
            "question": "有沒有快超支的案件？",
            "response_json": '{"reasoning": "檢查預算使用率超標的案件", "tool_calls": [{"name": "check_budget_alert", "params": {"threshold_pct": 80}}]}',
        },
        priority=7,
        contexts=["erp", "pm"],
    ))

    # 28. get_dispatch_progress — 派工進度彙整（對標 OpenClaw 進度摘要）
    registry.register(ToolDefinition(
        name="get_dispatch_progress",
        description="生成派工進度彙整報告：已完成/進行中/逾期分類 + 負責人統計 + 關鍵提醒。適合回答「派工進度如何」「有哪些逾期」「某人負責的案件」之類的問題。",
        parameters={
            "year": {"type": "integer", "description": "民國年度（如 115），預設當前年度"},
        },
        few_shot={
            "question": "目前派工進度如何？有哪些逾期的？",
            "response_json": '{"reasoning": "生成派工進度彙整報告", "tool_calls": [{"name": "get_dispatch_progress", "params": {}}]}',
        },
        priority=8,
        contexts=["dispatch", "pm"],
    ))

    # 29. search_tender — 政府標案搜尋
    registry.register(ToolDefinition(
        name="search_tender",
        description="搜尋政府電子採購網標案。可用關鍵字搜尋標案名稱，回傳招標機關、預算金額、公告日期、得標廠商等資訊。支援依乾坤核心業務（測量、空拍、透地雷達等）自動推薦相關標案。",
        parameters={
            "query": {"type": "string", "description": "搜尋關鍵字（如 測量、空拍、透地雷達）"},
            "page": {"type": "integer", "description": "頁碼 (預設1)"},
        },
        few_shot={
            "question": "最近有什麼測量相關的標案？",
            "response_json": '{"reasoning": "搜尋政府採購網中與測量相關的標案", "tool_calls": [{"name": "search_tender", "params": {"query": "測量", "page": 1}}]}',
        },
        priority=7,
        contexts=["doc", "pm"],
    ))

    # 30. auto_tender_to_case — Multi-Agent: 標案自動建案
    registry.register(ToolDefinition(
        name="auto_tender_to_case",
        description="Multi-Agent 標案自動建案：搜尋符合乾坤業務的政府標案，自動篩選公開招標公告，一次建立多筆 PM 案件和 ERP 報價。適合回答「幫我把最近的測量標案建成案件」之類的指令。",
        parameters={
            "query": {"type": "string", "description": "搜尋關鍵字（如 測量、空拍）"},
            "max_create": {"type": "integer", "description": "最多建立幾筆 (預設3, 最大5)"},
        },
        few_shot={
            "question": "幫我把最近的測量標案建成案件",
            "response_json": '{"reasoning": "使用 auto_tender_to_case 自動搜尋測量標案並批次建案", "tool_calls": [{"name": "auto_tender_to_case", "params": {"query": "測量", "max_create": 3}}]}',
        },
        priority=6,
        contexts=["pm"],
    ))

    # 31. analyze_diagram — 工程圖/測量圖 Vision 分析 (v5.4.1)
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

    # === Asset Tools (v5.4.1) ===

    # 32. list_assets — 資產清單查詢
    registry.register(ToolDefinition(
        name="list_assets",
        description="查詢資產清單，可依類別（電腦設備/測量儀器/交通工具/辦公家具等）、狀態（in_use/idle/repair/disposed）或案件代碼篩選。",
        parameters={
            "category": {"type": "string", "description": "資產類別篩選 (如 電腦設備/測量儀器/交通工具)"},
            "status": {"type": "string", "description": "狀態篩選 (in_use/idle/repair/disposed)"},
            "case_code": {"type": "string", "description": "關聯案件代碼"},
        },
        few_shot={
            "question": "目前有哪些測量儀器？",
            "response_json": '{"reasoning": "查詢測量儀器類別的資產清單", "tool_calls": [{"name": "list_assets", "params": {"category": "測量儀器"}}]}',
        },
        priority=5,
        contexts=["erp"],
    ))

    # 33. get_asset_detail — 資產詳情
    registry.register(ToolDefinition(
        name="get_asset_detail",
        description="查詢資產詳情，包含折舊資訊、行為紀錄（領用/歸還/維修/盤點）和關聯發票。",
        parameters={
            "asset_id": {"type": "integer", "description": "資產 ID"},
        },
        priority=3,
        contexts=["erp"],
    ))

    # 34. get_asset_stats — 資產統計
    registry.register(ToolDefinition(
        name="get_asset_stats",
        description="資產統計摘要：類別分布、總值、各狀態數量、待盤點數。",
        parameters={},
        few_shot={
            "question": "公司資產概況如何？",
            "response_json": '{"reasoning": "查詢資產統計摘要", "tool_calls": [{"name": "get_asset_stats", "params": {}}]}',
        },
        priority=4,
        contexts=["erp"],
    ))

    # === Invoice/Expense Tools (v5.4.1) ===

    # 35. list_pending_expenses — 待審核費用
    registry.register(ToolDefinition(
        name="list_pending_expenses",
        description="查詢待審核費用清單，可依審核狀態或案件代碼篩選。快速總覽哪些費用需要處理。",
        parameters={
            "status": {"type": "string", "description": "狀態篩選 (pending/verified/rejected)"},
            "case_code": {"type": "string", "description": "案件代碼篩選"},
        },
        few_shot={
            "question": "有哪些待審核的費用？",
            "response_json": '{"reasoning": "查詢待審核狀態的費用清單", "tool_calls": [{"name": "list_pending_expenses", "params": {"status": "pending"}}]}',
        },
        priority=6,
        contexts=["erp"],
    ))

    # 36. get_expense_detail — 費用報銷詳情
    registry.register(ToolDefinition(
        name="get_expense_detail",
        description="查詢費用報銷詳情，包含發票明細項目和審核歷程。",
        parameters={
            "expense_id": {"type": "integer", "description": "費用報銷 ID"},
        },
        priority=3,
        contexts=["erp"],
    ))

    # 37. suggest_expense_category — AI 費用分類建議
    registry.register(ToolDefinition(
        name="suggest_expense_category",
        description="根據品名和廠商，使用 Gemma 4 AI 建議最適合的費用類別（交通/餐飲/文具/設備/其他）。",
        parameters={
            "description": {"type": "string", "description": "品名或費用描述"},
            "vendor": {"type": "string", "description": "廠商名稱 (可選，輔助分類)"},
        },
        few_shot={
            "question": "計程車費該歸到什麼類別？",
            "response_json": '{"reasoning": "使用 AI 分析費用描述來建議類別", "tool_calls": [{"name": "suggest_expense_category", "params": {"description": "計程車費"}}]}',
        },
        priority=4,
        contexts=["erp"],
    ))

    # === Dispatch Tools (v5.4.1) ===

    # 38. get_dispatch_timeline — 派工單作業時間軸
    registry.register(ToolDefinition(
        name="get_dispatch_timeline",
        description="查詢派工單完整作業時間軸，包含公文收發、工作紀錄和里程碑事件，以時間順序排列。",
        parameters={
            "dispatch_id": {"type": "integer", "description": "派工單 ID"},
        },
        few_shot={
            "question": "派工單 14 的完整作業紀錄？",
            "response_json": '{"reasoning": "查詢派工單的完整時間軸", "tool_calls": [{"name": "get_dispatch_timeline", "params": {"dispatch_id": 14}}]}',
        },
        priority=5,
        contexts=["doc", "dispatch"],
    ))

    # 39. detect_dispatch_anomaly — 派工異常偵測
    registry.register(ToolDefinition(
        name="detect_dispatch_anomaly",
        description="偵測派工異常狀況：逾期未回文、進度停滯、缺少工作紀錄等。使用 Gemma 4 AI 分析並給出風險等級。",
        parameters={
            "contract_project_id": {"type": "integer", "description": "承攬案件 ID (可選，不提供則掃描全部)"},
        },
        few_shot={
            "question": "有沒有異常的派工案件？",
            "response_json": '{"reasoning": "偵測所有派工案件的異常狀況", "tool_calls": [{"name": "detect_dispatch_anomaly", "params": {}}]}',
        },
        priority=6,
        contexts=["dispatch", "pm"],
    ))

    # === PM Risk Tool (v5.4.1) ===

    # 40. detect_project_risk — 專案風險偵測
    registry.register(ToolDefinition(
        name="detect_project_risk",
        description="偵測專案風險：里程碑延遲、預算偏差、資源衝突。使用 Gemma 4 AI 分析並給出風險評分和建議。",
        parameters={
            "case_code": {"type": "string", "description": "案件代碼 (如 A-115-001)"},
        },
        few_shot={
            "question": "A-115-001 這個案件有什麼風險？",
            "response_json": '{"reasoning": "分析指定案件的多維度風險", "tool_calls": [{"name": "detect_project_risk", "params": {"case_code": "A-115-001"}}]}',
        },
        priority=7,
        contexts=["pm"],
    ))

    # === Document Intent Tool (v5.4.1) ===

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

    # === 跨圖譜工具 (v5.5.4) ===

    # search_across_graphs — 7 大圖譜統一搜尋
    registry.register(ToolDefinition(
        name="search_across_graphs",
        description="跨 7 大圖譜統一搜尋：知識圖譜(公文實體)、公文關係、代碼圖譜、業務實體、標案圖譜、ERP 財務圖譜、跨域連結。一次查詢即可觸及所有圖譜的實體和關係。適合回答涉及多個業務領域的問題。",
        parameters={
            "query": {"type": "string", "description": "搜尋關鍵字"},
            "limit": {"type": "integer", "description": "每個圖譜最大結果數 (預設5)"},
        },
        few_shot={
            "question": "跟台灣測量公司相關的所有資訊",
            "response_json": '{"reasoning": "使用跨圖譜搜尋查找廠商在公文、標案、ERP 中的所有關聯", "tool_calls": [{"name": "search_across_graphs", "params": {"query": "台灣測量公司", "limit": 5}}]}',
        },
        priority=9,
        contexts=["doc", "pm", "erp", "agent"],
    ))

    # search_erp_entities — ERP 財務圖譜搜尋
    registry.register(ToolDefinition(
        name="search_erp_entities",
        description="搜尋 ERP 財務圖譜：報價案件、開票、請款、費用報銷、資產、廠商應付。可查詢案件金額、廠商帳款、費用歸屬等財務資訊。",
        parameters={
            "query": {"type": "string", "description": "搜尋關鍵字 (案件名稱/廠商名稱/發票號碼)"},
            "entity_type": {"type": "string", "description": "限定類型: erp_quotation/erp_vendor/erp_expense/erp_asset (可選)"},
        },
        few_shot={
            "question": "查一下南港測量案的報價和費用",
            "response_json": '{"reasoning": "搜尋 ERP 圖譜中南港測量案的財務實體", "tool_calls": [{"name": "search_erp_entities", "params": {"query": "南港測量"}}]}',
        },
        priority=7,
        contexts=["erp", "pm", "agent"],
    ))

    logger.info("Tool registry initialized: %d manual tools registered", registry.get_tool_count())

    # === NemoClaw Stage 3: 自動從 Skills 目錄發現並註冊工具 ===
    try:
        from .skill_scanner import scan_skills
        skills = scan_skills()
        auto_count = 0
        for skill in skills:
            name = f"skill_{skill['name'].replace('-', '_')}"
            # Skip if already registered (manual tools take precedence)
            if name in registry.valid_tool_names:
                continue
            registry.register(ToolDefinition(
                name=name,
                description=f"[Skill] {skill['description']}",
                parameters={
                    "query": {"type": "string", "description": "相關問題或查詢"},
                },
                priority=1,  # Lower than manual tools
                contexts=["agent"],
            ))
            auto_count += 1
        logger.info(
            "Auto-discovered %d skills from .claude/skills/ (%d total tools)",
            auto_count, registry.get_tool_count(),
        )
    except Exception as e:
        logger.debug("Skill auto-discovery failed (non-critical): %s", e)
