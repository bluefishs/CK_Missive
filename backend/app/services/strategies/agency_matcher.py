"""
機關/案件名稱匹配策略模組

提供 AgencyMatcher 和 ProjectMatcher 智慧匹配器。
字串解析邏輯見 agency_parser.py。

使用方式:
    matcher = AgencyMatcher(db)
    agency_id = await matcher.match_or_create("某某機關")
"""
import logging
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.extended.models import GovernmentAgency
from app.services.strategies.agency_parser import parse_agency_string  # noqa: F401 — re-export

logger = logging.getLogger(__name__)


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
    3. 模糊匹配 (包含關係)
    4. 關鍵字匹配 (委託機關)
    5. 若都未匹配且允許自動建立則新增
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

        # 策略1: 精確匹配 project_name
        result = await self.db.execute(
            select(ContractProject)
            .where(ContractProject.project_name == project_name)
        )
        project = result.scalar_one_or_none()
        if project:
            self._cache[project_name] = project.id
            return project.id

        # 策略2: 精確匹配 project_code
        result = await self.db.execute(
            select(ContractProject)
            .where(ContractProject.project_code == project_name)
        )
        project = result.scalar_one_or_none()
        if project:
            self._cache[project_name] = project.id
            return project.id

        # 策略3: 模糊匹配 (案件名稱包含輸入字串)
        project_id = await self._try_fuzzy_match(project_name)
        if project_id:
            self._cache[project_name] = project_id
            return project_id

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

    async def match_only(self, project_name: Optional[str]) -> Optional[int]:
        """
        僅匹配，不自動建立

        Args:
            project_name: 案件名稱

        Returns:
            匹配到的案件 ID，若未匹配則返回 None
        """
        return await self.match_or_create(project_name, auto_create=False)

    async def match_by_keywords(
        self,
        keywords: List[str],
        client_agency: Optional[str] = None
    ) -> Optional[int]:
        """
        根據關鍵字匹配案件

        用於公文主旨沒有明確案件名稱時，嘗試透過關鍵字或委託機關匹配。

        Args:
            keywords: 關鍵字列表 (如 ['桃園', '工程', '測量'])
            client_agency: 委託機關名稱

        Returns:
            匹配到的案件 ID
        """
        from app.extended.models import ContractProject

        # 先嘗試委託機關匹配
        if client_agency:
            result = await self.db.execute(
                select(ContractProject)
                .where(ContractProject.client_agency.ilike(f"%{client_agency}%"))
                .order_by(ContractProject.id.desc())
                .limit(1)
            )
            project = result.scalar_one_or_none()
            if project:
                logger.info(f"案件委託機關匹配成功: '{client_agency}' -> '{project.project_name}'")
                return project.id

        # 使用關鍵字模糊匹配
        for keyword in keywords:
            if len(keyword) >= 2:  # 至少 2 個字元
                result = await self.db.execute(
                    select(ContractProject)
                    .where(ContractProject.project_name.ilike(f"%{keyword}%"))
                    .order_by(ContractProject.id.desc())
                    .limit(1)
                )
                project = result.scalar_one_or_none()
                if project:
                    logger.info(f"案件關鍵字匹配成功: '{keyword}' -> '{project.project_name}'")
                    return project.id

        return None

    # Minimum input length required for fuzzy matching to avoid false positives
    FUZZY_MIN_LENGTH = 8
    # Maximum ratio of matched name length to input length
    FUZZY_MAX_LENGTH_RATIO = 3.0

    async def _try_fuzzy_match(self, project_name: str) -> Optional[int]:
        """
        模糊匹配 (包含關係)

        匹配邏輯：
        1. 案件名稱包含輸入字串（需通過品質檢查）
        2. 輸入字串包含案件名稱的關鍵部分（需通過品質檢查）

        安全措施：
        - 輸入長度 < FUZZY_MIN_LENGTH (8) 時跳過模糊匹配
        - 匹配結果名稱長度超過輸入長度 FUZZY_MAX_LENGTH_RATIO (3x) 時拒絕
        """
        from app.extended.models import ContractProject

        # Guard: skip fuzzy match for short inputs to prevent false positives
        if len(project_name) < self.FUZZY_MIN_LENGTH:
            logger.debug(
                "案件模糊匹配跳過: 輸入 '%s' 長度 %d < 最低門檻 %d",
                project_name, len(project_name), self.FUZZY_MIN_LENGTH,
            )
            return None

        # 策略1: 案件名稱包含輸入字串
        result = await self.db.execute(
            select(ContractProject)
            .where(ContractProject.project_name.ilike(f"%{project_name}%"))
            .order_by(ContractProject.id.desc())
            .limit(1)
        )
        project = result.scalar_one_or_none()
        if project:
            if self._is_fuzzy_match_acceptable(project_name, project.project_name):
                logger.info(
                    "案件模糊匹配成功 (包含): '%s' -> '%s' "
                    "(輸入長度=%d, 匹配長度=%d, 比率=%.1f)",
                    project_name, project.project_name,
                    len(project_name), len(project.project_name),
                    len(project.project_name) / max(len(project_name), 1),
                )
                return project.id
            else:
                logger.warning(
                    "案件模糊匹配拒絕 (長度比率過大): '%s' -> '%s' "
                    "(輸入長度=%d, 匹配長度=%d, 比率=%.1f, 上限=%.1f)",
                    project_name, project.project_name,
                    len(project_name), len(project.project_name),
                    len(project.project_name) / max(len(project_name), 1),
                    self.FUZZY_MAX_LENGTH_RATIO,
                )

        # 策略2: 若輸入字串較長，嘗試取前 10 個字匹配
        if len(project_name) >= 10:
            short_name = project_name[:10]
            result = await self.db.execute(
                select(ContractProject)
                .where(ContractProject.project_name.ilike(f"%{short_name}%"))
                .order_by(ContractProject.id.desc())
                .limit(1)
            )
            project = result.scalar_one_or_none()
            if project:
                if self._is_fuzzy_match_acceptable(project_name, project.project_name):
                    logger.info(
                        "案件模糊匹配成功 (前綴): '%s' -> '%s' "
                        "(輸入長度=%d, 匹配長度=%d, 比率=%.1f)",
                        short_name, project.project_name,
                        len(project_name), len(project.project_name),
                        len(project.project_name) / max(len(project_name), 1),
                    )
                    return project.id
                else:
                    logger.warning(
                        "案件模糊匹配拒絕 (前綴, 長度比率過大): '%s' -> '%s' "
                        "(輸入長度=%d, 匹配長度=%d, 比率=%.1f, 上限=%.1f)",
                        short_name, project.project_name,
                        len(project_name), len(project.project_name),
                        len(project.project_name) / max(len(project_name), 1),
                        self.FUZZY_MAX_LENGTH_RATIO,
                    )

        return None

    def _is_fuzzy_match_acceptable(
        self, input_name: str, matched_name: str
    ) -> bool:
        """檢查模糊匹配結果是否在合理長度比率範圍內"""
        input_len = len(input_name)
        matched_len = len(matched_name)

        if input_len == 0:
            return False

        ratio = matched_len / input_len
        return ratio <= self.FUZZY_MAX_LENGTH_RATIO

    def clear_cache(self):
        """清除快取"""
        self._cache.clear()
