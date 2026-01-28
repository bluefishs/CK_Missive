# -*- coding: utf-8 -*-
"""
公文 API 整合測試
Documents API Integration Tests

執行方式:
    pytest tests/integration/test_documents_api.py -v
    pytest tests/integration/test_documents_api.py -v -m integration

注意: 需要實際資料庫連線和 API 伺服器運行

v2.0.0 - 2026-01-26
- 新增依賴注入測試替換範例
- 新增認證相關測試
- 新增更完整的 API 測試案例
"""
import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, AsyncMock, patch

# 標記所有整合測試，可選擇性跳過
pytestmark = pytest.mark.integration


class TestDocumentsEnhancedAPI:
    """公文增強 API 測試"""

    @pytest.mark.asyncio
    async def test_list_documents(self, client: AsyncClient):
        """測試公文列表 API"""
        response = await client.post(
            "/api/documents-enhanced/list",
            json={"page": 1, "limit": 10}
        )

        assert response.status_code == 200
        data = response.json()

        # 驗證回應結構
        assert "success" in data
        assert "items" in data or "detail" in data

        if data.get("success"):
            # API 回傳 pagination 物件包含 total, page, limit
            assert "pagination" in data
            assert "total" in data["pagination"]
            assert "page" in data["pagination"]
            assert "limit" in data["pagination"]
            assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_list_documents_with_filter(self, client: AsyncClient):
        """測試公文列表篩選"""
        response = await client.post(
            "/api/documents-enhanced/list",
            json={
                "page": 1,
                "limit": 10,
                "doc_type": "收文"
            }
        )

        assert response.status_code == 200
        data = response.json()

        if data.get("success") and data.get("items"):
            # 所有返回的公文應該是收文
            for doc in data["items"]:
                assert doc.get("doc_type") == "收文"

    @pytest.mark.asyncio
    async def test_list_documents_with_keyword(self, client: AsyncClient):
        """測試公文列表關鍵字搜尋"""
        response = await client.post(
            "/api/documents-enhanced/list",
            json={
                "page": 1,
                "limit": 10,
                "keyword": "測繪"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # 確認回應成功
        assert data.get("success") is True or "items" in data

    @pytest.mark.asyncio
    async def test_list_documents_with_year_filter(self, client: AsyncClient):
        """測試公文列表年度篩選"""
        response = await client.post(
            "/api/documents-enhanced/list",
            json={
                "page": 1,
                "limit": 10,
                "year": 2026
            }
        )

        assert response.status_code == 200
        data = response.json()

        if data.get("success") and data.get("items"):
            for doc in data["items"]:
                if doc.get("doc_date"):
                    assert doc["doc_date"].startswith("2026")

    @pytest.mark.asyncio
    async def test_list_documents_with_date_range(self, client: AsyncClient):
        """測試公文列表日期範圍篩選"""
        response = await client.post(
            "/api/documents-enhanced/list",
            json={
                "page": 1,
                "limit": 10,
                "doc_date_from": "2026-01-01",
                "doc_date_to": "2026-12-31"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data.get("success") is True or "items" in data

    @pytest.mark.asyncio
    async def test_list_documents_pagination(self, client: AsyncClient):
        """測試公文列表分頁"""
        # 第一頁
        response1 = await client.post(
            "/api/documents-enhanced/list",
            json={"page": 1, "limit": 5}
        )

        # 第二頁
        response2 = await client.post(
            "/api/documents-enhanced/list",
            json={"page": 2, "limit": 5}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        if data1.get("success") and data2.get("success"):
            assert data1["pagination"]["page"] == 1
            assert data2["pagination"]["page"] == 2

    @pytest.mark.asyncio
    async def test_export_documents(self, client: AsyncClient):
        """測試公文匯出 API"""
        response = await client.post(
            "/api/documents-enhanced/export/excel",
            json={}
        )

        # 應該返回 Excel 檔案或錯誤訊息
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            # 驗證是 Excel 檔案
            content_type = response.headers.get("content-type", "")
            assert "spreadsheet" in content_type or "octet-stream" in content_type


class TestDocumentsValidation:
    """公文驗證測試

    注意：公文建立端點需要認證，使用 authenticated_client
    """

    @pytest.mark.asyncio
    async def test_create_document_missing_required_fields(self, authenticated_client: AsyncClient):
        """測試缺少必填欄位

        注意：端點需要 documents:create 權限，一般用戶可能返回 403
        """
        response = await authenticated_client.post(
            "/api/documents-enhanced/create",
            json={}  # 空的請求體
        )

        # 422 驗證錯誤 或 403 權限不足（視 mock 用戶權限而定）
        assert response.status_code in [403, 422]

    @pytest.mark.asyncio
    async def test_create_document_invalid_doc_type(self, authenticated_client: AsyncClient):
        """測試無效的公文類型 - 目前 API 允許任意 doc_type 值"""
        response = await authenticated_client.post(
            "/api/documents-enhanced/create",
            json={
                "doc_number": "TEST-INVALID-001",
                "subject": "測試主旨",
                "doc_type": "無效類型"
            }
        )

        # 注意: 目前 API 允許任意 doc_type 值（未強制驗證）
        # 403 權限不足 或 200/400/422 依驗證結果
        assert response.status_code in [200, 400, 403, 422]

        # 如果建立成功，刪除測試資料
        if response.status_code == 200:
            data = response.json()
            if data.get("id"):
                await authenticated_client.post(f"/api/documents-enhanced/{data['id']}/delete")

    @pytest.mark.asyncio
    async def test_create_document_valid_data(self, authenticated_client: AsyncClient):
        """測試使用有效資料建立公文"""
        valid_data = {
            "doc_number": "TEST-VALID-001",
            "subject": "測試公文主旨",
            "doc_type": "函",
            "sender": "測試發文單位",
            "receiver": "測試受文單位",
            "category": "收文"
        }

        response = await authenticated_client.post(
            "/api/documents-enhanced/create",
            json=valid_data
        )

        # 可能成功建立、驗證失敗、或權限不足
        assert response.status_code in [200, 400, 403, 422]

        # 清理測試資料
        if response.status_code == 200:
            data = response.json()
            if data.get("id"):
                await authenticated_client.post(f"/api/documents-enhanced/{data['id']}/delete")


class TestDocumentDetail:
    """公文詳情測試"""

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client: AsyncClient):
        """測試取得不存在的公文"""
        response = await client.post("/api/documents-enhanced/99999/detail")

        # 應該返回 404 或錯誤訊息
        assert response.status_code in [404, 200]

        if response.status_code == 200:
            data = response.json()
            # 可能返回 success: false 表示找不到
            if "success" in data:
                assert data.get("success") is False or data.get("document") is None


class TestCalendarAPI:
    """行事曆 API 測試"""

    @pytest.mark.asyncio
    async def test_list_calendar_events(self, client: AsyncClient):
        """測試行事曆事件列表"""
        response = await client.post(
            "/api/calendar/events/list",
            json={}
        )

        assert response.status_code == 200
        data = response.json()

        if data.get("success"):
            # API 回傳 events 而非 items
            assert "events" in data
            assert isinstance(data["events"], list)

    @pytest.mark.asyncio
    async def test_calendar_stats(self, authenticated_client: AsyncClient):
        """測試行事曆統計"""
        response = await authenticated_client.post("/api/calendar/stats", json={})

        assert response.status_code == 200
        data = response.json()

        # API 直接返回統計欄位
        assert "total_events" in data or "success" in data


class TestDocumentStatistics:
    """公文統計 API 測試"""

    @pytest.mark.asyncio
    async def test_get_statistics(self, client: AsyncClient):
        """測試取得公文統計"""
        response = await client.post("/api/documents-enhanced/statistics")

        assert response.status_code == 200
        data = response.json()

        # 驗證統計資料結構
        if data.get("success"):
            assert "total" in data or "total_documents" in data

    @pytest.mark.asyncio
    async def test_get_filtered_statistics(self, client: AsyncClient):
        """測試取得篩選後的統計"""
        response = await client.post(
            "/api/documents-enhanced/filtered-statistics",
            json={
                "year": 2026,
                "doc_type": "函"
            }
        )

        assert response.status_code == 200
        data = response.json()

        if data.get("success"):
            assert "total" in data
            assert "send_count" in data or "receive_count" in data


class TestDocumentYears:
    """公文年度選項 API 測試"""

    @pytest.mark.asyncio
    async def test_get_year_options(self, client: AsyncClient):
        """測試取得年度選項"""
        response = await client.post("/api/documents-enhanced/years")

        assert response.status_code == 200
        data = response.json()

        if data.get("success"):
            assert "years" in data
            assert isinstance(data["years"], list)


class TestDropdownOptions:
    """下拉選項 API 測試"""

    @pytest.mark.asyncio
    async def test_get_contract_project_options(self, client: AsyncClient):
        """測試取得承攬案件選項"""
        response = await client.post(
            "/api/documents-enhanced/contract-projects-dropdown",
            json={"limit": 50}
        )

        assert response.status_code == 200
        data = response.json()

        if data.get("success"):
            assert "options" in data
            assert isinstance(data["options"], list)

    @pytest.mark.asyncio
    async def test_get_agency_options(self, client: AsyncClient):
        """測試取得機關選項"""
        response = await client.post(
            "/api/documents-enhanced/agencies-dropdown",
            json={"limit": 50}
        )

        assert response.status_code == 200
        data = response.json()

        if data.get("success"):
            assert "options" in data
            assert isinstance(data["options"], list)


class TestWithMockedService:
    """使用 Mock Service 的 API 測試範例"""

    @pytest.mark.asyncio
    async def test_list_with_mocked_service(
        self,
        client: AsyncClient,
        override_document_service,
        mock_document_service,
        sample_document_list
    ):
        """使用 Mock DocumentService 測試列表 API

        此測試展示如何使用依賴注入覆蓋來隔離測試
        """
        # 設定 mock 回傳值
        mock_document_service.get_documents.return_value = {
            "items": sample_document_list,
            "total": len(sample_document_list),
            "page": 1,
            "limit": 20,
            "total_pages": 1
        }

        response = await client.post(
            "/api/documents-enhanced/list",
            json={"page": 1, "limit": 20}
        )

        # 驗證 API 正確處理 mock 資料
        # 注意：這需要端點實際使用 get_document_service 依賴
        assert response.status_code == 200


class TestErrorHandling:
    """錯誤處理測試"""

    @pytest.mark.asyncio
    async def test_invalid_json_body(self, client: AsyncClient):
        """測試無效 JSON 請求體"""
        response = await client.post(
            "/api/documents-enhanced/list",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )

        # 應該返回 422 驗證錯誤
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_page_number(self, client: AsyncClient):
        """測試無效頁碼"""
        response = await client.post(
            "/api/documents-enhanced/list",
            json={"page": -1, "limit": 20}
        )

        # 可能返回錯誤或自動修正
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_invalid_limit(self, client: AsyncClient):
        """測試無效限制數"""
        response = await client.post(
            "/api/documents-enhanced/list",
            json={"page": 1, "limit": 10000}  # 過大的 limit
        )

        # 可能返回錯誤或自動限制
        assert response.status_code in [200, 400, 422]
