"""
調試端點 - 測試資料庫連接問題 (優化後)
"""
from fastapi import APIRouter, Depends, Request # Import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_async_db
# 修正: 從 app.extended.models 匯入正確的模型，並使用別名以減少程式碼修改
from app.extended.models import OfficialDocument as Document, User
from app.core.dependencies import require_admin

router = APIRouter()

@router.get("/test")
async def test_debug_endpoint(
    current_user: User = Depends(require_admin())
):
    """Simple test endpoint to verify debug router is working"""
    return {"message": "Debug router is working", "status": "success"}

@router.get("/dev/mapping", summary="動態獲取前端功能與後端 API 對應關係 (樹狀結構)")
async def get_dynamic_api_mapping(
    request: Request,
    current_user: User = Depends(require_admin())
):
    """
    動態生成前端功能與後端 API 的對應關係，並以樹狀結構返回。
    此為開發/調試工具，透過程式碼約定來推斷相關檔案。
    """
    app = request.app # 獲取 FastAPI 應用實例

    all_api_items = []
    
    # 遍歷所有路由
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods") and hasattr(route, "endpoint"):
            path = route.path
            methods = list(route.methods) if route.methods else []
            endpoint_func = route.endpoint
            
            # 嘗試從路由處理函數推斷相關模組和服務
            module_name = endpoint_func.__module__
            func_name = endpoint_func.__name__
            
            # 根據模組名稱和約定推斷相關檔案和分組
            related_backend_files = []
            feature_description = "未知功能"
            group_name = "其他 API" # 預設分組
            
            if "app.api.endpoints." in module_name:
                base_name = module_name.replace("app.api.endpoints.", "")
                
                # Endpoint file
                related_backend_files.append(f"endpoints/{base_name}.py")
                
                if base_name == "documents":
                    group_name = "公文管理 (Documents)"
                    related_backend_files.extend(["services/document_service.py", "services/csv_processor.py", "services/document_import_service.py"])
                    feature_description = "公文的查詢、匯入與管理"
                elif base_name == "document_numbers":
                    group_name = "發文字號管理 (Document Numbers)"
                    # Assuming a service like document_number_service.py exists
                    related_backend_files.append("services/document_number_service.py") 
                    feature_description = "發文字號的清單與管理"
                elif base_name == "projects":
                    group_name = "承攬案件管理 (Projects)"
                    related_backend_files.append("services/project_service.py") 
                    feature_description = "承攬案件的建立、查詢與管理"
                elif base_name == "vendors":
                    group_name = "廠商管理 (Vendors)"
                    related_backend_files.append("services/vendor_service.py") 
                    feature_description = "協力廠商的建立、查詢與管理"
                elif base_name == "project_vendors":
                    group_name = "案件與廠商關聯 (Project-Vendors)"
                    related_backend_files.append("services/project_vendor_service.py") 
                    feature_description = "承攬案件與協力廠商的關聯管理"
                elif base_name == "admin":
                    group_name = "管理後台 (Admin)"
                    related_backend_files.append("services/admin_service.py")
                    feature_description = "資料庫與系統後台管理"
                elif base_name == "agencies":
                    group_name = "機關單位 (Agencies)"
                    related_backend_files.append("services/agency_service.py") # Assuming agency_service.py exists
                    feature_description = "機關單位的統計與管理"
                elif base_name == "auth":
                    group_name = "認證與使用者 (Auth & Users)"
                    related_backend_files.append("services/auth_service.py") # Assuming auth_service.py exists
                    feature_description = "使用者認證與登入"
                elif base_name == "users":
                    group_name = "認證與使用者 (Auth & Users)"
                    related_backend_files.append("services/user_service.py") # Assuming user_service.py exists
                    feature_description = "使用者帳號管理"
                elif base_name == "files":
                    group_name = "檔案管理 (Files)"
                    related_backend_files.append("services/file_service.py") # Assuming file_service.py exists
                    feature_description = "檔案上傳與管理"
                elif base_name == "cases":
                    group_name = "案件管理 (Cases)"
                    related_backend_files.append("services/case_service.py") # Assuming case_service.py exists
                    feature_description = "案件的建立與管理"
                elif base_name == "calendar":
                    group_name = "行事曆 (Calendar)"
                    related_backend_files.append("services/calendar_service.py") # Assuming calendar_service.py exists
                    feature_description = "行事曆事件管理"
                elif base_name == "debug":
                    group_name = "調試與開發工具 (Debug & Dev Tools)"
                    # debug.py itself is the service for debug endpoints
                    feature_description = "系統調試與開發輔助工具"
                
            # 排除內部或非 API 路由
            if (path.startswith("/openapi.json") or
                path.startswith("/docs") or
                path.startswith("/redoc") or
                path.startswith("/static") or
                path.startswith("/health") or
                path.startswith("/favicon.ico") or
                path == "/"): # 排除根路徑
                continue
            
            all_api_items.append({
                "group": group_name,
                "feature": feature_description, # This will be overridden if a specific_api_description exists
                "api": f"{' '.join(methods)} {path}",
                "backendFiles": str.join(", ", sorted(list(set(related_backend_files)))),
                "description": f"由 {module_name}.{func_name} 處理"
            })
            
    # 定義特定 API 的精確功能描述
    specific_api_descriptions = {
        "POST /api/auth/login": "使用者登入",
        "POST /api/auth/refresh": "刷新令牌",
        "POST /api/auth/logout": "使用者登出",
        "GET /api/auth/me": "取得當前使用者資訊",
        "GET /api/documents/count": "調試：文件總數統計",
        "GET /api/documents/raw": "調試：原始文件列表",
        "GET /api/documents/stats": "公文總覽統計",
        "GET /api/documents/export": "公文數據匯出",
        "POST /api/documents/batch-update": "公文批量更新",
        "POST /api/documents/batch-delete": "公文批量刪除",
        "GET /api/documents/analysis/by-year": "公文年度分析",
        "GET /api/documents/analysis/by-type": "公文類型分析",
        "GET /api/documents/analysis/by-agency": "公文機關分析",
        "GET /api/documents-years": "獲取公文年度列表",
        "POST /api/documents/import": "公文 CSV 匯入",
        "GET /api/documents": "公文列表顯示",
        "GET /api/admin/database/info": "資料庫基本資訊",
        "GET /api/admin/database/table/{table_name}": "獲取表格數據",
        "POST /api/admin/database/query": "執行唯讀 SQL 查詢",
        "GET /api/admin/database/health": "資料庫健康檢查",
        "POST /api/files/upload": "檔案上傳",
        "GET /api/files/{file_id}/download": "檔案下載",
        "DELETE /api/files/{file_id}": "檔案刪除",
        "GET /api/agencies": "機關單位列表",
        "GET /api/agencies/statistics": "機關單位統計",
        "GET /api/users": "使用者列表",
        "GET /api/users/{user_id}": "取得使用者詳情",
        "POST /api/users": "建立新使用者",
        "PUT /api/users/{user_id}": "更新使用者",
        "DELETE /api/users/{user_id}": "刪除使用者",
        "PUT /api/users/{user_id}/status": "修改使用者狀態",
        "PUT /api/users/{user_id}/password": "重設使用者密碼",
        "GET /api/projects": "承攬案件列表",
        "POST /api/projects": "建立新承攬案件",
        "GET /api/projects/{project_id}": "取得承攬案件詳情",
        "PUT /api/projects/{project_id}": "更新承攬案件資訊",
        "DELETE /api/projects/{project_id}": "刪除承攬案件",
        "GET /api/projects/{project_id}/vendors": "取得承攬案件關聯廠商",
        "GET /api/projects/years": "取得案件年度列表",
        "GET /api/projects/categories": "取得案件類別列表",
        "GET /api/projects/statuses": "取得案件狀態列表",
        "GET /api/vendors": "廠商列表",
        "POST /api/vendors": "建立新廠商",
        "GET /api/vendors/{vendor_id}": "取得特定廠商詳情",
        "PUT /api/vendors/{vendor_id}": "更新廠商資訊",
        "DELETE /api/vendors/{vendor_id}": "刪除廠商",
        "GET /api/vendors/{vendor_id}/projects": "取得廠商關聯專案",
        "POST /api/project-vendors": "建立案件與廠商關聯",
        "GET /api/project-vendors/project/{project_id}": "取得案件廠商關聯",
        "GET /api/project-vendors/vendor/{vendor_id}": "取得廠商案件關聯",
        "PUT /api/project-vendors/project/{project_id}/vendor/{vendor_id}": "更新案件廠商關聯",
        "DELETE /api/project-vendors/project/{project_id}/vendor/{vendor_id}": "刪除案件廠商關聯",
        "GET /api/project-vendors": "所有案件廠商關聯列表",
        # Add more as needed
    }

    # 進行分組和樹狀結構化
    grouped_data = {}
    for item in all_api_items:
        # 優先使用特定 API 的描述
        api_key = item["api"]
        if api_key in specific_api_descriptions:
            item["feature"] = specific_api_descriptions[api_key]
        
        group = item.pop("group") # 移除 group 屬性，因為它將成為父節點
        if group not in grouped_data:
            grouped_data[group] = {
                "key": group.replace(" ", "_").replace("(", "").replace(")", "").lower() + "_group", # 生成唯一 key
                "feature": group,
                "api": "", # 父節點不顯示 API
                "backendFiles": "", # 父節點不顯示檔案
                "description": f"所有 {group} 相關 API",
                "children": []
            }
        
        # 為子節點生成唯一 key
        item_key_base = item["api"].replace(" ", "_").replace("/", "_").replace(":", "_").lower()
        children_count = len(grouped_data[group]["children"])
        item["key"] = f"{item_key_base}_{children_count}" # 確保子節點 key 唯一
        
        grouped_data[group]["children"].append(item)

    # 將字典轉換為列表，並對組進行排序
    final_tree_data = sorted(list(grouped_data.values()), key=lambda x: x["feature"])
    
    # 對每個組內的子節點進行排序
    for group_item in final_tree_data:
        group_item["children"].sort(key=lambda x: x["api"])
        
    return final_tree_data

@router.get("/documents/count")
async def debug_document_count(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """調試：直接查詢文件總數 (非同步)"""
    try:
        total_query = select(func.count()).select_from(Document)
        total_res = await db.execute(total_query)
        total = total_res.scalar_one()

        # 修正: 查詢條件 'active' 可能不存在，改為查詢 '待處理' 狀態
        active_query = select(func.count()).where(Document.status == '待處理')
        active_res = await db.execute(active_query)
        active_count = active_res.scalar_one()
        
        first_five_query = select(Document.id, Document.doc_number, Document.status).limit(5)
        first_five_res = await db.execute(first_five_query)
        first_five = first_five_res.all()
        
        return {
            "total_documents": total,
            "pending_documents": active_count, 
            "first_five": [
                {"id": doc.id, "doc_number": doc.doc_number, "status": doc.status} 
                for doc in first_five
            ]
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/documents/raw")
async def debug_raw_documents(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin())
):
    """調試：返回原始文件列表 (非同步)"""
    try:
        query = select(Document).limit(10)
        result = await db.execute(query)
        documents = result.scalars().all()
        
        return {
            "count": len(documents),
            "documents": [
                {
                    "id": doc.id,
                    "doc_number": doc.doc_number,
                    "subject": doc.subject[:50] if doc.subject else "",
                    "status": doc.status,
                    # 修正: 'category' 欄位不存在於 OfficialDocument 模型中，已移除
                } 
                for doc in documents
            ]
        }
    except Exception as e:
        return {"error": str(e)}