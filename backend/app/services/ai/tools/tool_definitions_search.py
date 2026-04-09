"""
Agent 工具定義 — 搜尋類工具

從 tool_definitions.py 拆分 (v1.4.0)
包含 9 個搜尋/查詢類工具的聲明式定義。
"""

from .tool_registry import ToolDefinition, ToolRegistry


def register_search_tools(registry: ToolRegistry) -> None:
    """註冊搜尋類工具 (9 個)"""

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
