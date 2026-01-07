"""
機關名稱匹配策略模組

提供智慧機關名稱匹配功能，用於 CSV 匯入時自動識別和關聯機關資料。

功能特性：
1. 精確匹配 - 完全相符的機關名稱
2. 代碼匹配 - 透過機關代碼識別
3. 簡稱匹配 - 支援機關簡稱對應
4. 模糊匹配 - 包含關係的彈性匹配
5. 自動新增 - 未匹配時自動建立新機關記錄

支援的輸入格式（parse_agency_string 函數）：
- 格式 A: "A01020100G (內政部國土管理署城鄉發展分署)" - 代碼 + 括號名稱
- 格式 B: "EB50819619 乾坤測繪科技有限公司" - 代碼 + 空格 + 名稱
- 格式 C: "376470600A（彰化縣和美地政事務所）" - 代碼 + 全形括號名稱
- 格式 D: "內政部國土測繪中心" - 純名稱（無代碼）

使用方式:
    matcher = AgencyMatcher(db)
    agency_id = await matcher.match_or_create("某某機關")

維護注意事項：
- 機關代碼格式：6-12 位英數字組合（如 A01020100G, 376470600A）
- 快取機制：同一 session 內會快取匹配結果，提升批量匯入效能
- 匹配優先順序：精確名稱 > 解析後名稱 > 代碼 > 簡稱 > 模糊匹配 > 自動建立
- 若需要修復已匯入的錯誤資料，使用 POST /api/agencies/fix-parsed-names API

相關檔案：
- backend/app/api/endpoints/agencies.py - 機關 API 端點（含修復 API）
- backend/app/services/document_service.py - 使用此模組進行 CSV 匯入
- backend/app/extended/models.py - GovernmentAgency 模型定義

更新記錄：
- 2024-01: 初始版本
- 2025-01: 新增 parse_agency_string 函數支援代碼/名稱分離解析
"""
import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from app.extended.models import GovernmentAgency

logger = logging.getLogger(__name__)


def parse_agency_string(raw_string: str) -> Tuple[Optional[str], str]:
    """
    解析機關字串，分離機關代碼和名稱

    此函數用於處理 CSV 匯入時各種格式的機關欄位值，
    自動識別並分離機關代碼和名稱。

    支援格式範例：
    1. "A01020100G (內政部國土管理署城鄉發展分署)" -> ("A01020100G", "內政部國土管理署城鄉發展分署")
    2. "EB50819619 乾坤測繪科技有限公司" -> ("EB50819619", "乾坤測繪科技有限公司")
    3. "376470600A（彰化縣和美地政事務所）" -> ("376470600A", "彰化縣和美地政事務所")
    4. "內政部國土測繪中心" -> (None, "內政部國土測繪中心")

    機關代碼規則：
    - 長度：6-12 位
    - 組成：英文字母（A-Z, a-z）和數字（0-9）的組合
    - 常見格式：
      * 政府機關：A01020100G（10位，英數混合）
      * 地政事務所：376470600A（10位，數字開頭）
      * 公司行號：EB50819619（10位，英文開頭）

    Args:
        raw_string: 原始機關字串（可能包含換行符、空格等）

    Returns:
        Tuple[Optional[str], str]: (機關代碼, 機關名稱)
        - 若無法解析出代碼，第一個元素為 None
        - 第二個元素永遠為處理後的名稱（至少為空字串）

    維護說明：
    - 若發現新的輸入格式，請在此函數新增對應的正規表達式
    - 修改後請確保原有格式仍能正確解析（向後相容）
    - 建議新增單元測試驗證所有格式
    """
    if not raw_string:
        return None, ""

    # 移除前後空白和換行符（CSV 匯入時可能包含 \n）
    raw_string = raw_string.strip().replace('\n', ' ').replace('\r', '')

    # =========================================================================
    # 格式1: "代碼 (名稱)" 或 "代碼（名稱）"
    # 範例: "A01020100G (內政部國土管理署城鄉發展分署)"
    # 正規表達式說明:
    #   ^([A-Za-z0-9]+)  - 開頭為英數字組合（代碼）
    #   \s*              - 可選的空白
    #   [\(（]           - 半形或全形左括號
    #   (.+?)            - 括號內的名稱（非貪婪匹配）
    #   [\)）]$          - 半形或全形右括號，結尾
    # =========================================================================
    match = re.match(r'^([A-Za-z0-9]+)\s*[\(（](.+?)[\)）]$', raw_string)
    if match:
        code = match.group(1).strip()
        name = match.group(2).strip()
        logger.debug(f"解析機關格式1(括號): '{raw_string}' -> 代碼='{code}', 名稱='{name}'")
        return code, name

    # =========================================================================
    # 格式2: "代碼 名稱" - 代碼和名稱之間有空格
    # 範例: "EB50819619 乾坤測繪科技有限公司"
    # 正規表達式說明:
    #   ^([A-Za-z0-9]{6,12})  - 6-12位英數字組合（代碼）
    #   \s+                   - 至少一個空白
    #   (.+)$                 - 剩餘部分為名稱
    # 注意: 代碼長度限制為 6-12 位，避免誤判短字串
    # =========================================================================
    match = re.match(r'^([A-Za-z0-9]{6,12})\s+(.+)$', raw_string)
    if match:
        code = match.group(1).strip()
        name = match.group(2).strip()
        # 安全檢查：確認名稱不是純數字（避免誤判如 "123456 789"）
        if not name.isdigit():
            logger.debug(f"解析機關格式2(空格): '{raw_string}' -> 代碼='{code}', 名稱='{name}'")
            return code, name

    # =========================================================================
    # 格式3: 純名稱（不含代碼）
    # 範例: "內政部國土測繪中心"
    # 此為預設情況，直接返回原始字串作為名稱
    # =========================================================================
    logger.debug(f"解析機關格式3(純名稱): '{raw_string}'")
    return None, raw_string


class AgencyMatcher:
    """
    機關名稱智慧匹配器

    提供多層級的機關名稱匹配策略：
    1. 精確匹配 agency_name
    2. 精確匹配 agency_short_name
    3. 模糊匹配 (包含關係)
    4. 若都未匹配則新增
    """

    def __init__(self, db: AsyncSession):
        """
        初始化匹配器

        Args:
            db: 資料庫 session
        """
        self.db = db
        self._cache: Dict[str, int] = {}  # 名稱 -> ID 快取

    async def match_or_create(
        self,
        raw_agency_string: Optional[str],
        auto_create: bool = True
    ) -> Optional[int]:
        """
        匹配或建立機關

        支援解析 "代碼 (名稱)" 或 "代碼 名稱" 格式

        Args:
            raw_agency_string: 原始機關字串（可能包含代碼和名稱）
            auto_create: 是否自動建立不存在的機關

        Returns:
            機關 ID，若名稱為空則返回 None
        """
        if not raw_agency_string or not raw_agency_string.strip():
            return None

        raw_agency_string = raw_agency_string.strip()

        # 檢查快取（使用原始字串作為快取鍵）
        if raw_agency_string in self._cache:
            return self._cache[raw_agency_string]

        # 解析機關代碼和名稱
        parsed_code, parsed_name = parse_agency_string(raw_agency_string)

        # 策略1: 先用原始字串進行精確匹配
        agency_id = await self._try_exact_match(raw_agency_string)
        if agency_id:
            self._cache[raw_agency_string] = agency_id
            return agency_id

        # 策略2: 若有解析出名稱且與原始字串不同，用解析後的名稱匹配
        if parsed_name and parsed_name != raw_agency_string:
            agency_id = await self._try_exact_match(parsed_name)
            if agency_id:
                self._cache[raw_agency_string] = agency_id
                return agency_id

        # 策略3: 用機關代碼匹配
        if parsed_code:
            agency_id = await self._try_code_match(parsed_code)
            if agency_id:
                self._cache[raw_agency_string] = agency_id
                return agency_id

        # 策略4: 簡稱匹配（原始字串）
        agency_id = await self._try_short_name_match(raw_agency_string)
        if agency_id:
            self._cache[raw_agency_string] = agency_id
            return agency_id

        # 策略5: 簡稱匹配（解析後名稱）
        if parsed_name and parsed_name != raw_agency_string:
            agency_id = await self._try_short_name_match(parsed_name)
            if agency_id:
                self._cache[raw_agency_string] = agency_id
                return agency_id

        # 策略6: 模糊匹配
        agency_id = await self._try_fuzzy_match(parsed_name or raw_agency_string)
        if agency_id:
            self._cache[raw_agency_string] = agency_id
            return agency_id

        # 若允許自動建立，則新增機關（使用解析後的代碼和名稱）
        if auto_create:
            agency_id = await self._create_agency(parsed_code, parsed_name)
            if agency_id:
                self._cache[raw_agency_string] = agency_id
            return agency_id

        return None

    async def match_only(self, agency_name: Optional[str]) -> Optional[int]:
        """
        僅匹配，不自動建立

        Args:
            agency_name: 機關名稱

        Returns:
            匹配到的機關 ID，若未匹配則返回 None
        """
        return await self.match_or_create(agency_name, auto_create=False)

    async def batch_match_or_create(
        self,
        agency_names: List[str],
        auto_create: bool = True
    ) -> Dict[str, Optional[int]]:
        """
        批次匹配或建立機關

        Args:
            agency_names: 機關名稱列表
            auto_create: 是否自動建立不存在的機關

        Returns:
            名稱 -> ID 的映射字典
        """
        result: Dict[str, Optional[int]] = {}
        for name in agency_names:
            result[name] = await self.match_or_create(name, auto_create)
        return result

    # =========================================================================
    # 私有匹配方法
    # =========================================================================

    async def _try_exact_match(self, agency_name: str) -> Optional[int]:
        """精確匹配 agency_name"""
        result = await self.db.execute(
            select(GovernmentAgency)
            .where(GovernmentAgency.agency_name == agency_name)
        )
        agency = result.scalar_one_or_none()
        if agency:
            logger.debug(f"機關精確匹配成功: '{agency_name}'")
            return agency.id
        return None

    async def _try_short_name_match(self, agency_name: str) -> Optional[int]:
        """匹配 agency_short_name (簡稱)"""
        result = await self.db.execute(
            select(GovernmentAgency)
            .where(GovernmentAgency.agency_short_name == agency_name)
        )
        agency = result.scalar_one_or_none()
        if agency:
            logger.info(f"機關簡稱匹配成功: '{agency_name}' -> '{agency.agency_name}'")
            return agency.id
        return None

    async def _try_code_match(self, agency_code: str) -> Optional[int]:
        """匹配 agency_code (機關代碼)"""
        result = await self.db.execute(
            select(GovernmentAgency)
            .where(GovernmentAgency.agency_code == agency_code)
        )
        agency = result.scalar_one_or_none()
        if agency:
            logger.info(f"機關代碼匹配成功: '{agency_code}' -> '{agency.agency_name}'")
            return agency.id
        return None

    async def _try_fuzzy_match(self, agency_name: str) -> Optional[int]:
        """模糊匹配 (包含關係)"""
        result = await self.db.execute(
            select(GovernmentAgency)
            .where(
                or_(
                    GovernmentAgency.agency_name.ilike(f"%{agency_name}%"),
                    GovernmentAgency.agency_short_name.ilike(f"%{agency_name}%")
                )
            )
            .limit(1)
        )
        agency = result.scalar_one_or_none()
        if agency:
            logger.info(f"機關模糊匹配成功: '{agency_name}' -> '{agency.agency_name}'")
            return agency.id
        return None

    async def _create_agency(
        self,
        agency_code: Optional[str],
        agency_name: str
    ) -> Optional[int]:
        """
        建立新機關

        Args:
            agency_code: 機關代碼（可選）
            agency_name: 機關名稱

        Returns:
            新機關的 ID
        """
        try:
            new_agency = GovernmentAgency(
                agency_name=agency_name,
                agency_code=agency_code
            )
            self.db.add(new_agency)
            await self.db.flush()
            await self.db.refresh(new_agency)
            logger.info(f"新增機關: 代碼='{agency_code}', 名稱='{agency_name}'")
            return new_agency.id
        except Exception as e:
            logger.error(f"建立機關失敗: {agency_name}, 錯誤: {e}")
            return None

    def clear_cache(self):
        """清除快取"""
        self._cache.clear()


class ProjectMatcher:
    """
    案件名稱智慧匹配器

    提供案件名稱匹配策略：
    1. 精確匹配 project_name
    2. 精確匹配 project_code
    3. 若都未匹配則新增
    """

    def __init__(self, db: AsyncSession):
        """
        初始化匹配器

        Args:
            db: 資料庫 session
        """
        self.db = db
        self._cache: Dict[str, int] = {}

    async def match_or_create(
        self,
        project_name: Optional[str],
        auto_create: bool = True
    ) -> Optional[int]:
        """
        匹配或建立案件

        Args:
            project_name: 案件名稱
            auto_create: 是否自動建立不存在的案件

        Returns:
            案件 ID，若名稱為空則返回 None
        """
        from datetime import datetime
        from app.extended.models import ContractProject

        if not project_name or not project_name.strip():
            return None

        project_name = project_name.strip()

        # 檢查快取
        if project_name in self._cache:
            return self._cache[project_name]

        # 精確匹配 project_name
        result = await self.db.execute(
            select(ContractProject)
            .where(ContractProject.project_name == project_name)
        )
        project = result.scalar_one_or_none()
        if project:
            self._cache[project_name] = project.id
            return project.id

        # 精確匹配 project_code
        result = await self.db.execute(
            select(ContractProject)
            .where(ContractProject.project_code == project_name)
        )
        project = result.scalar_one_or_none()
        if project:
            self._cache[project_name] = project.id
            return project.id

        # 若允許自動建立，則新增案件
        if auto_create:
            new_project = ContractProject(
                project_name=project_name,
                year=datetime.now().year,
                status="進行中"
            )
            self.db.add(new_project)
            await self.db.flush()
            await self.db.refresh(new_project)
            self._cache[project_name] = new_project.id
            logger.info(f"新增案件: '{project_name}'")
            return new_project.id

        return None

    def clear_cache(self):
        """清除快取"""
        self._cache.clear()
