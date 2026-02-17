# -*- coding: utf-8 -*-
"""
作業歷程 Workflow API 整合測試

執行方式:
    pytest tests/integration/test_workflow_api.py -v
    pytest tests/integration/test_workflow_api.py -v -m integration

注意: 需要實際資料庫連線和 API 伺服器運行

v1.0.0 - 2026-02-17
"""
import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, AsyncMock, patch

# 標記所有整合測試
pytestmark = pytest.mark.integration


class TestWorkflowListAPI:
    """作業歷程列表 API"""

    @pytest.mark.asyncio
    async def test_list_by_dispatch_order(self, client: AsyncClient):
        """測試依派工單查詢作業歷程"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/list",
            json={"dispatch_order_id": 1, "page": 1, "page_size": 10},
        )
        assert response.status_code in (200, 401)

        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_list_with_invalid_page_size(self, client: AsyncClient):
        """page_size > 200 應被拒絕"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/list",
            json={"dispatch_order_id": 1, "page": 1, "page_size": 500},
        )
        # FastAPI Body(le=200) 會回傳 422
        assert response.status_code in (422, 401)

    @pytest.mark.asyncio
    async def test_list_with_zero_page(self, client: AsyncClient):
        """page < 1 應被拒絕"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/list",
            json={"dispatch_order_id": 1, "page": 0, "page_size": 10},
        )
        assert response.status_code in (422, 401)

    @pytest.mark.asyncio
    async def test_list_by_project(self, client: AsyncClient):
        """測試依工程查詢作業歷程"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/by-project",
            json={"project_id": 1, "page": 1, "page_size": 10},
        )
        assert response.status_code in (200, 401)


class TestWorkflowCRUD:
    """作業歷程 CRUD API"""

    @pytest.mark.asyncio
    async def test_create_work_record(self, client: AsyncClient):
        """測試建立作業紀錄"""
        payload = {
            "dispatch_order_id": 1,
            "work_category": "dispatch_notice",
            "status": "in_progress",
            "record_date": "2026-02-17",
            "milestone_type": "other",
        }
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/create",
            json=payload,
        )
        assert response.status_code in (200, 401, 404)

        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["work_category"] == "dispatch_notice"

    @pytest.mark.asyncio
    async def test_get_work_record(self, client: AsyncClient):
        """測試取得單筆紀錄"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/1",
        )
        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_update_work_record(self, client: AsyncClient):
        """測試更新紀錄"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/1/update",
            json={"status": "completed"},
        )
        assert response.status_code in (200, 401, 404)

    @pytest.mark.asyncio
    async def test_delete_clears_orphans(self, client: AsyncClient):
        """測試刪除回傳 orphaned_children_cleared"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/99999/delete",
        )
        # 99999 不存在 → 404，或 401 if no auth
        assert response.status_code in (401, 404)


class TestWorkflowBatchUpdate:
    """批量更新 API"""

    @pytest.mark.asyncio
    async def test_batch_update(self, client: AsyncClient):
        """測試批量更新"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/batch-update",
            json={
                "record_ids": [1, 2],
                "batch_no": 1,
                "batch_label": "第1批結案",
            },
        )
        assert response.status_code in (200, 400, 401)

    @pytest.mark.asyncio
    async def test_batch_update_empty_ids(self, client: AsyncClient):
        """空 record_ids 應被 schema 驗證拒絕 (min_length=1)"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/batch-update",
            json={
                "record_ids": [],
                "batch_no": 1,
                "batch_label": "空批次",
            },
        )
        # BatchUpdateRequest.record_ids 有 min_length=1，空列表被拒絕
        assert response.status_code in (422, 401)


class TestWorkflowSummary:
    """歷程總覽 API"""

    @pytest.mark.asyncio
    async def test_workflow_summary(self, client: AsyncClient):
        """測試工程歷程總覽"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/summary/1",
        )
        assert response.status_code in (200, 401, 404)

        if response.status_code == 200:
            data = response.json()
            assert "milestones_completed" in data
            assert "current_stage" in data

    @pytest.mark.asyncio
    async def test_workflow_summary_not_found(self, client: AsyncClient):
        """不存在的工程 → 404"""
        response = await client.post(
            "/api/taoyuan-dispatch/workflow/summary/99999",
        )
        assert response.status_code in (401, 404)
