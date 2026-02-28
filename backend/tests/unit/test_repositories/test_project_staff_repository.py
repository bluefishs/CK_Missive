"""
ProjectStaffRepository 單元測試

測試專案人員關聯 Repository 的 CRUD 和查詢方法。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from collections import namedtuple

from app.repositories.project_staff_repository import ProjectStaffRepository


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def repo(mock_db):
    return ProjectStaffRepository(mock_db)


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
# check_project_exists
# ============================================================================

class TestCheckProjectExists:
    @pytest.mark.asyncio
    async def test_returns_project_when_found(self, repo, mock_db):
        mock_project = MagicMock(id=1, project_name="Test Project")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_db.execute.return_value = mock_result

        result = await repo.check_project_exists(1)
        assert result == mock_project

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.check_project_exists(999)
        assert result is None


# ============================================================================
# check_user_exists
# ============================================================================

class TestCheckUserExists:
    @pytest.mark.asyncio
    async def test_returns_user_when_found(self, repo, mock_db):
        mock_user = MagicMock(id=1, username="testuser")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await repo.check_user_exists(1)
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.check_user_exists(999)
        assert result is None


# ============================================================================
# check_assignment_exists
# ============================================================================

class TestCheckAssignmentExists:
    @pytest.mark.asyncio
    async def test_returns_row_when_exists(self, repo, mock_db):
        mock_row = MagicMock(id=1, project_id=1, user_id=2)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        result = await repo.check_assignment_exists(1, 2)
        assert result == mock_row

    @pytest.mark.asyncio
    async def test_returns_none_when_not_exists(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        result = await repo.check_assignment_exists(1, 999)
        assert result is None


# ============================================================================
# create_assignment
# ============================================================================

class TestCreateAssignment:
    @pytest.mark.asyncio
    async def test_inserts_and_flushes(self, repo, mock_db):
        await repo.create_assignment(
            project_id=1,
            user_id=2,
            role='主辦',
            is_primary=True,
        )
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()


# ============================================================================
# get_staff_for_project
# ============================================================================

class TestGetStaffForProject:
    @pytest.mark.asyncio
    async def test_returns_joined_rows(self, repo, mock_db):
        rows = [
            StaffRow(1, 10, 20, '主辦', True, None, None, 'active', None, '王小明', 'wang@test.com', 'wang'),
            StaffRow(2, 10, 30, '協辦', False, None, None, 'active', None, '李大華', 'lee@test.com', 'lee'),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = rows
        mock_db.execute.return_value = mock_result

        result = await repo.get_staff_for_project(10)
        assert len(result) == 2
        assert result[0].full_name == '王小明'
        assert result[1].role == '協辦'


# ============================================================================
# get_all_assignments
# ============================================================================

class TestGetAllAssignments:
    @pytest.mark.asyncio
    async def test_returns_data_and_total(self, repo, mock_db):
        rows = [
            AllAssignmentRow(1, 10, 20, '主辦', True, None, None, 'active', None, 'P-001', 'PRJ001', '王小明', 'wang@test.com', 'wang'),
        ]
        # First call returns data rows, second returns count
        count_result = MagicMock()
        count_result.scalar.return_value = 5
        data_result = MagicMock()
        data_result.fetchall.return_value = rows

        mock_db.execute.side_effect = [count_result, data_result]

        result_rows, total = await repo.get_all_assignments(page=1, limit=20)
        assert total == 5
        assert len(result_rows) == 1

    @pytest.mark.asyncio
    async def test_filters_by_project_id(self, repo, mock_db):
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        data_result = MagicMock()
        data_result.fetchall.return_value = []
        mock_db.execute.side_effect = [count_result, data_result]

        result_rows, total = await repo.get_all_assignments(project_id=10, page=1, limit=20)
        assert total == 0
        assert len(result_rows) == 0
        assert mock_db.execute.call_count == 2


# ============================================================================
# update_assignment
# ============================================================================

class TestUpdateAssignment:
    @pytest.mark.asyncio
    async def test_updates_with_data(self, repo, mock_db):
        await repo.update_assignment(1, 2, {"role": "協辦", "status": "inactive"})
        mock_db.execute.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_empty_update(self, repo, mock_db):
        await repo.update_assignment(1, 2, {})
        mock_db.execute.assert_not_called()
        mock_db.flush.assert_not_called()


# ============================================================================
# delete_assignment
# ============================================================================

class TestDeleteAssignment:
    @pytest.mark.asyncio
    async def test_deletes_existing(self, repo, mock_db):
        mock_row = MagicMock(id=42)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result

        deleted_id = await repo.delete_assignment(1, 2)
        assert deleted_id == 42
        assert mock_db.execute.call_count == 2  # check + delete
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent(self, repo, mock_db):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        deleted_id = await repo.delete_assignment(1, 999)
        assert deleted_id is None
        mock_db.flush.assert_not_called()
