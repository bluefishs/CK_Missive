"""
ProjectStaffService 單元測試

測試業務邏輯：存在性驗證、衝突偵測、回應格式化。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from collections import namedtuple

from app.core.exceptions import NotFoundException, ConflictException
from app.services.project_staff_service import ProjectStaffService
from app.schemas.project_staff import (
    ProjectStaffCreate,
    ProjectStaffUpdate,
    StaffListQuery,
    ProjectStaffListResponse,
)
from app.schemas.common import DeleteResponse


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_db, mock_repo):
    svc = ProjectStaffService(mock_db)
    svc.repo = mock_repo
    return svc


# ============================================================================
# Helper
# ============================================================================

StaffRow = namedtuple('StaffRow', [
    'id', 'project_id', 'user_id', 'role', 'is_primary',
    'start_date', 'end_date', 'status', 'notes',
    'full_name', 'email', 'username',
])

AllAssignmentRow = namedtuple('AllAssignmentRow', [
    'id', 'project_id', 'user_id', 'role', 'is_primary',
    'start_date', 'end_date', 'status', 'notes',
    'project_name', 'project_code',
    'full_name', 'email', 'username',
])


# ============================================================================
# create_assignment
# ============================================================================

class TestCreateAssignment:
    @pytest.mark.asyncio
    async def test_success(self, service, mock_repo, mock_db):
        mock_repo.check_project_exists.return_value = MagicMock(id=1)
        mock_repo.check_user_exists.return_value = MagicMock(id=2)
        mock_repo.check_assignment_exists.return_value = None

        data = ProjectStaffCreate(project_id=1, user_id=2, role='主辦', is_primary=True)
        result = await service.create_assignment(data)

        assert result["project_id"] == 1
        assert result["user_id"] == 2
        mock_repo.create_assignment.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_project_not_found(self, service, mock_repo):
        mock_repo.check_project_exists.return_value = None

        data = ProjectStaffCreate(project_id=999, user_id=2)
        with pytest.raises(NotFoundException):
            await service.create_assignment(data)

    @pytest.mark.asyncio
    async def test_user_not_found(self, service, mock_repo):
        mock_repo.check_project_exists.return_value = MagicMock(id=1)
        mock_repo.check_user_exists.return_value = None

        data = ProjectStaffCreate(project_id=1, user_id=999)
        with pytest.raises(NotFoundException):
            await service.create_assignment(data)

    @pytest.mark.asyncio
    async def test_duplicate_conflict(self, service, mock_repo):
        mock_repo.check_project_exists.return_value = MagicMock(id=1)
        mock_repo.check_user_exists.return_value = MagicMock(id=2)
        mock_repo.check_assignment_exists.return_value = MagicMock(id=10)

        data = ProjectStaffCreate(project_id=1, user_id=2)
        with pytest.raises(ConflictException):
            await service.create_assignment(data)

    @pytest.mark.asyncio
    async def test_defaults_role_and_status(self, service, mock_repo, mock_db):
        mock_repo.check_project_exists.return_value = MagicMock(id=1)
        mock_repo.check_user_exists.return_value = MagicMock(id=2)
        mock_repo.check_assignment_exists.return_value = None

        data = ProjectStaffCreate(project_id=1, user_id=2)
        await service.create_assignment(data)

        call_kwargs = mock_repo.create_assignment.call_args[1]
        assert call_kwargs["role"] == "member"
        assert call_kwargs["status"] == "active"


# ============================================================================
# get_project_staff
# ============================================================================

class TestGetProjectStaff:
    @pytest.mark.asyncio
    async def test_returns_staff_list(self, service, mock_repo):
        mock_repo.check_project_exists.return_value = MagicMock(
            id=10, project_name="測試專案"
        )
        mock_repo.get_staff_for_project.return_value = [
            StaffRow(1, 10, 20, '主辦', True, None, None, 'active', None, '王小明', 'wang@test.com', 'wang'),
            StaffRow(2, 10, 30, '協辦', False, None, None, 'active', None, None, 'lee@test.com', 'lee'),
        ]

        result = await service.get_project_staff(10)

        assert isinstance(result, ProjectStaffListResponse)
        assert result.project_id == 10
        assert result.project_name == "測試專案"
        assert result.total == 2
        assert result.staff[0].user_name == '王小明'
        # full_name is None → falls back to username
        assert result.staff[1].user_name == 'lee'

    @pytest.mark.asyncio
    async def test_project_not_found(self, service, mock_repo):
        mock_repo.check_project_exists.return_value = None

        with pytest.raises(NotFoundException):
            await service.get_project_staff(999)

    @pytest.mark.asyncio
    async def test_empty_staff(self, service, mock_repo):
        mock_repo.check_project_exists.return_value = MagicMock(
            id=10, project_name="空專案"
        )
        mock_repo.get_staff_for_project.return_value = []

        result = await service.get_project_staff(10)
        assert result.total == 0
        assert result.staff == []


# ============================================================================
# get_all_assignments
# ============================================================================

class TestGetAllAssignments:
    @pytest.mark.asyncio
    async def test_returns_paginated_data(self, service, mock_repo):
        rows = [
            AllAssignmentRow(
                1, 10, 20, '主辦', True, None, None, 'active', None,
                '專案A', 'PRJ001', '王小明', 'wang@test.com', 'wang',
            ),
        ]
        mock_repo.get_all_assignments.return_value = (rows, 1)

        query = StaffListQuery(page=1, limit=20)
        result = await service.get_all_assignments(query)

        assert result["success"] is True
        assert len(result["items"]) == 1
        assert result["items"][0]["user_name"] == '王小明'
        assert result["pagination"]["total"] == 1

    @pytest.mark.asyncio
    async def test_empty_result(self, service, mock_repo):
        mock_repo.get_all_assignments.return_value = ([], 0)

        query = StaffListQuery(page=1, limit=20)
        result = await service.get_all_assignments(query)

        assert result["items"] == []
        assert result["pagination"]["total"] == 0

    @pytest.mark.asyncio
    async def test_passes_filters(self, service, mock_repo):
        mock_repo.get_all_assignments.return_value = ([], 0)

        query = StaffListQuery(page=2, limit=10, project_id=5, user_id=3, status='active')
        await service.get_all_assignments(query)

        mock_repo.get_all_assignments.assert_called_once_with(
            project_id=5, user_id=3, status='active', page=2, limit=10,
        )

    @pytest.mark.asyncio
    async def test_user_name_fallback(self, service, mock_repo):
        """full_name 為 None 時回退到 username"""
        rows = [
            AllAssignmentRow(
                1, 10, 20, '主辦', True, None, None, 'active', None,
                '專案A', 'PRJ001', None, 'lee@test.com', 'lee_user',
            ),
        ]
        mock_repo.get_all_assignments.return_value = (rows, 1)

        result = await service.get_all_assignments(StaffListQuery())
        assert result["items"][0]["user_name"] == 'lee_user'


# ============================================================================
# update_assignment
# ============================================================================

class TestUpdateAssignment:
    @pytest.mark.asyncio
    async def test_success(self, service, mock_repo, mock_db):
        mock_repo.check_assignment_exists.return_value = MagicMock(id=1)

        data = ProjectStaffUpdate(role='協辦', status='inactive')
        result = await service.update_assignment(1, 2, data)

        assert result["project_id"] == 1
        assert result["user_id"] == 2
        mock_repo.update_assignment.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found(self, service, mock_repo):
        mock_repo.check_assignment_exists.return_value = None

        data = ProjectStaffUpdate(role='協辦')
        with pytest.raises(NotFoundException):
            await service.update_assignment(1, 999, data)

    @pytest.mark.asyncio
    async def test_empty_update_skips_repo(self, service, mock_repo, mock_db):
        mock_repo.check_assignment_exists.return_value = MagicMock(id=1)

        data = ProjectStaffUpdate()
        result = await service.update_assignment(1, 2, data)

        mock_repo.update_assignment.assert_not_called()
        mock_db.commit.assert_not_called()
        assert "更新成功" in result["message"]


# ============================================================================
# delete_assignment
# ============================================================================

class TestDeleteAssignment:
    @pytest.mark.asyncio
    async def test_success(self, service, mock_repo, mock_db):
        mock_repo.check_assignment_exists.return_value = MagicMock(id=42)
        mock_repo.delete_assignment.return_value = 42

        result = await service.delete_assignment(1, 2)

        assert isinstance(result, DeleteResponse)
        assert result.success is True
        assert result.deleted_id == 42
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_found(self, service, mock_repo):
        mock_repo.check_assignment_exists.return_value = None

        with pytest.raises(NotFoundException):
            await service.delete_assignment(1, 999)
