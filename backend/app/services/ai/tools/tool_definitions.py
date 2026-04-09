"""
Agent 工具定義資料

從 tool_registry.py 拆分 (v1.2.0)
包含系統內建 32+ 個工具的聲明式定義。

v1.4.0: 拆分為 3 檔案
  - tool_definitions_search.py    — 搜尋類 (9 個)
  - tool_definitions_analysis.py  — 分析/圖譜/視覺化 (11 個)
  - tool_definitions.py (本檔)    — PM/ERP/業務工具 (22 個) + 組裝入口

Updated: v1.4.0 (2026-04-09) 拆分為 3 個子檔案
"""

import logging

from .tool_registry import ToolDefinition, ToolRegistry
from .tool_definitions_search import register_search_tools
from .tool_definitions_analysis import register_analysis_tools

logger = logging.getLogger(__name__)


def register_default_tools(registry: ToolRegistry) -> None:
    """註冊系統內建工具 (搜尋 + 分析 + 業務)"""

    # --- 搜尋類工具 (9 個) ---
    register_search_tools(registry)

    # --- 分析/圖譜/視覺化工具 (11 個) ---
    register_analysis_tools(registry)

    # --- PM/ERP/業務工具 (22 個) ---
    _register_business_tools(registry)

    logger.info("Tool registry initialized: %d manual tools registered", registry.get_tool_count())

    # === NemoClaw Stage 3: 自動從 Skills 目錄發現並註冊工具 ===
    try:
        from app.services.ai.skill_scanner import scan_skills
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


def _register_business_tools(registry: ToolRegistry) -> None:
    """註冊 PM/ERP/業務工具 (22 個)"""

    # === PM 專案管理工具 ===

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

    # === Finance Tools ===

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

    # 28. get_dispatch_progress — 派工進度彙整
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

    # === Asset Tools ===

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

    # === Invoice/Expense Tools ===

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

    # === Dispatch Tools ===

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

    # === PM Risk Tool ===

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
