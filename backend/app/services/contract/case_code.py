"""統一案號編碼服務

參照公文系統專案編碼機制 CK{年度}_{類別}_{性質}_{流水號}，擴充為跨模組統一案號。

編碼格式: CK{年度4碼}_{模組2碼}_{類別2碼}_{流水號3碼}

模組代碼:
  PM = 專案管理 (Project Management)
  FN = 財務管理 (Finance/ERP)
  DP = 派工管理 (Dispatch)
  GN = 一般委辦 (General，相容既有 contract_projects)

類別代碼 (依模組):
  PM: 01=委辦招標, 02=承攬報價
  FN: 01=報價單, 02=變更單, 03=追加減, 99=其他
  DP: 01=地上物, 02=土地查估, 03=計畫書, 04=測量, 99=其他
  GN: 01=委辦招標, 02=承攬報價

範例:
  CK2025_PM_01_001 → 2025年 PM 測量案第1號
  CK2025_FN_01_001 → 2025年 ERP 報價單第1號
  CK2025_DP_02_001 → 2025年 派工 土地查估第1號

Version: 1.1.0
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.pm.case_repository import PMCaseRepository
from app.repositories.erp.quotation_repository import ERPQuotationRepository
from app.repositories import ProjectRepository, DocumentRepository

logger = logging.getLogger(__name__)

# ============================================================================
# 模組與類別常數定義 (SSOT)
# ============================================================================

MODULE_CODES = {
    "pm": "PM",
    "erp": "FN",
    "dispatch": "DP",
    "general": "GN",
}

PM_CATEGORY_CODES = {
    "01": "委辦招標",
    "02": "承攬報價",
}

ERP_CATEGORY_CODES = {
    "01": "報價單",
    "02": "變更單",
    "03": "追加減",
    "99": "其他",
}

DISPATCH_CATEGORY_CODES = {
    "01": "地上物查估",
    "02": "土地查估",
    "03": "計畫書",
    "04": "測量作業",
    "99": "其他",
}

GENERAL_CATEGORY_CODES = {
    "01": "委辦招標",
    "02": "承攬報價",
}

MODULE_CATEGORIES = {
    "PM": PM_CATEGORY_CODES,
    "FN": ERP_CATEGORY_CODES,
    "DP": DISPATCH_CATEGORY_CODES,
    "GN": GENERAL_CATEGORY_CODES,
}


class CaseCodeService:
    """統一案號編碼服務"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.pm_repo = PMCaseRepository(db)
        self.erp_repo = ERPQuotationRepository(db)
        self.project_repo = ProjectRepository(db)
        self.doc_repo = DocumentRepository(db)
        #: 同一交易內已發出、但尚未 commit 的流水號 —— 存在
        #: **session 上**（`db.info`）而不是 service 實例上。
        #
        # ⚠️ 2026-08-20 實際事故：報價單彙整匯入用 `generate_case_code()` 產號，
        #    **180 筆全部拿到同一個 `CK2025_FN_02_001`** —— 因為產號器查的是
        #    `MAX(case_code)`，而同一交易內前面那些 INSERT 還沒 commit，
        #    每次都查到一樣的值。那批已回滾。
        #
        # advisory lock 擋得住**跨交易**併發，擋不住**同一交易內**的批次呼叫 ——
        # 兩者是不同的問題，而先前只解了前者。
        #
        # ⚠️ 為什麼綁 session 不綁 self：實測若每筆 `CaseCodeService(db)` 新建一個
        #    實例，實例層的記錄就歸零、5 次全部拿到同一個號 —— 而「批次時要重用
        #    同一個實例」是**呼叫端才知道的隱性契約**，寫錯不會報錯、只會撞號。
        #    綁在 session 上就與呼叫端怎麼寫無關。
        if "case_code_issued_serials" not in db.info:
            db.info["case_code_issued_serials"] = {}

    async def generate_case_code(
        self,
        module: str,
        year: int,
        category: str = "01",
    ) -> str:
        """
        自動產生統一案號

        Args:
            module: 模組代碼 ('pm', 'erp', 'dispatch', 'general')
            year: 年度 (民國年或西元年，自動處理)
            category: 類別代碼 ('01', '02', ...)

        Returns:
            案號字串，例如 CK2025_PM_01_001
        """
        mod_code = MODULE_CODES.get(module.lower())
        if not mod_code:
            raise ValueError(f"未知模組: {module}，可用: {list(MODULE_CODES.keys())}")

        cat_code = category[:2].zfill(2) if category else "01"
        year_str = str(year) if year > 1911 else str(year + 1911)

        prefix = f"CK{year_str}_{mod_code}_{cat_code}_"

        # 查詢所有同 prefix 的案號 (跨 PM + ERP 表)
        next_serial = await self._find_next_serial(prefix)

        return f"{prefix}{str(next_serial).zfill(3)}"

    async def generate_quotation_no(self, year: Optional[int] = None) -> str:
        """產生對外報價單號 QT{年}_{序}（2026-08-17 owner「編號統整」）。

        ⚠️ **同日我曾想改成 `B{民國年}-B{序}` —— 那是誤判，已撤回。**

        庫裡 48 筆歷史列的 `case_code` 是 `B114-B039` 這種形式
        （來源 `docs/templates/import-templates/114報價單彙整.xlsx`，
        工作表名就叫「老闆」與「原始」）。owner 給的解碼是：

            B      114      B         039
            邀標    年度     同仁代號   該同仁的第 39 筆報價紀錄

        **序號是按人各自數的** —— 所以它結構上不可能當公司唯一號：
        同仁 A 與同仁 B 各有自己的 039，兩張不同的報價單尾號一樣。
        那份 xlsx 有兩個工作表也正是這個原因（一人一張表）。

        建構線上報價單系統的目的就是取代這種各自記帳的狀態，
        所以「B 式流進 case_code」不是要沿用的規格、是要被統整掉的現況。
        沿用它等於把個人流水號固化成系統規格，方向剛好相反。

        沿用 `generate_case_code` 的形狀與 **advisory lock 防併發跳號** ——
        不另寫一套產號邏輯（那會是第二份事實，而兩份產號器撞號時
        只有唯一索引會擋，而那時使用者看到的是一個看不懂的 500）。

        版次不進號碼本體：`revision` 另存一欄，
        對外呈現時才組成 `QT2026_018-2`（見 `format_quotation_no`）。
        """
        from datetime import date as _date

        from sqlalchemy import text

        yr = year if (year and year > 1911) else (
            (year + 1911) if year else _date.today().year
        )
        prefix = f"QT{yr}_"

        lock_key = abs(hash(prefix)) % (2**31)
        await self.db.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))

        row = (await self.db.execute(text("""
            SELECT MAX(NULLIF(regexp_replace(quotation_no, '^QT[0-9]{4}_', ''), '')::int)
            FROM erp_quotations
            WHERE quotation_no LIKE :p
        """), {"p": f"{prefix}%"})).scalar()

        return f"{prefix}{str((row or 0) + 1).zfill(3)}"

    @staticmethod
    def format_quotation_no(quotation_no: Optional[str], revision: int = 1) -> str:
        """組成對外呈現的完整單號（含版次後綴）。

        `QT2026_018` + revision 2 → `QT2026_018-2`；revision 1 不加後綴 ——
        這樣「有後綴就是改過的」語意明確，客戶一眼看得出手上是不是最新版。
        （議價後重報是同一件事的第 N 版，不該給新號、否則對帳時
        會被當成兩張不同的報價單。）

        單號為空時回「未編號」而不是空字串：正式文件上留白會被當成漏印。
        """
        if not quotation_no:
            return "未編號"
        return quotation_no if (revision or 1) <= 1 else f"{quotation_no}-{revision}"

    async def _find_next_serial(self, prefix: str) -> int:
        """在 PM/ERP 表中查找最大流水號 (含 advisory lock 防併發跳號)"""
        from sqlalchemy import text

        # Advisory lock: 用 prefix hash 作為 lock key，防止併發產生同一號
        lock_key = abs(hash(prefix)) % (2**31)
        await self.db.execute(text(f"SELECT pg_advisory_xact_lock({lock_key})"))

        max_serial = 0

        # 查 PM
        pm_max = await self.pm_repo.get_max_case_code_by_prefix(prefix)
        if pm_max:
            try:
                serial = int(pm_max.split("_")[-1])
                max_serial = max(max_serial, serial)
            except (IndexError, ValueError):
                pass

        # 查 ERP
        erp_max = await self.erp_repo.get_max_case_code_by_prefix(prefix)
        if erp_max:
            try:
                serial = int(erp_max.split("_")[-1])
                max_serial = max(max_serial, serial)
            except (IndexError, ValueError):
                pass

        # 查承攬案件（2026-07-31 補）
        # 原本只掃 PM + ERP，但 `contract_projects.case_code` 是 **UNIQUE**，
        # 且自 2026-07-31 方案 B 起承攬案件也會自行產號 →
        # 只要有一筆 case_code 只存在於 contract_projects（例如自我修復批次補的），
        # 下一次產號就會重覆而撞 ix_contract_projects_case_code。
        # 實際踩到：自我修復 job 首跑時同批第二筆即 UniqueViolationError。
        cp_max = await self.db.scalar(text(
            "SELECT MAX(case_code) FROM contract_projects WHERE case_code LIKE :p"
        ), {"p": f"{prefix}%"})
        if cp_max:
            try:
                serial = int(str(cp_max).split("_")[-1])
                max_serial = max(max_serial, serial)
            except (IndexError, ValueError):
                pass

        # 同一交易內已發出的號碼 —— DB 查不到它們（尚未 commit）
        issued = self.db.info.setdefault("case_code_issued_serials", {})
        max_serial = max(max_serial, issued.get(prefix, 0))

        next_serial = max_serial + 1
        issued[prefix] = next_serial
        return next_serial

    async def validate_case_code(self, case_code: str) -> bool:
        """驗證案號格式是否合規"""
        parts = case_code.split("_")
        if len(parts) != 4:
            return False
        if not parts[0].startswith("CK") or not parts[0][2:].isdigit():
            return False
        if parts[1] not in MODULE_CODES.values():
            return False
        if not parts[2].isdigit() or len(parts[2]) != 2:
            return False
        if not parts[3].isdigit() or len(parts[3]) != 3:
            return False
        return True

    async def check_duplicate(self, case_code: str) -> bool:
        """檢查案號是否已存在 (跨 PM + ERP)"""
        if await self.pm_repo.exists_by_case_code(case_code):
            return True
        return await self.erp_repo.exists_by_case_code(case_code)

    @staticmethod
    def parse_case_code(case_code: str) -> Optional[dict]:
        """解析案號結構"""
        parts = case_code.split("_")
        if len(parts) != 4:
            return None
        try:
            year = int(parts[0][2:])
            module = parts[1]
            category = parts[2]
            serial = int(parts[3])
            # 查模組標籤
            mod_name = {v: k for k, v in MODULE_CODES.items()}.get(module, "unknown")
            # 查類別標籤
            cat_labels = MODULE_CATEGORIES.get(module, {})
            cat_name = cat_labels.get(category, "未定義")
            return {
                "year": year,
                "module": module,
                "module_name": mod_name,
                "category": category,
                "category_name": cat_name,
                "serial": serial,
                "formatted": case_code,
            }
        except (ValueError, IndexError):
            return None

    async def generate_project_code(
        self, year: int, category: str = "01", case_nature: str = "01",
    ) -> str:
        """產生成案專案編號 (project_code)

        格式: {年度4碼}_{類別2碼}_{性質2碼}_{流水號3碼}
        範例: 2026_01_01_001

        類別: 01委辦招標(政府機關), 02承攬報價
        性質: 01地面測量, 02LiDAR掃描, 03UAV空拍, 04航空測量,
              05安全檢測, 06建物保存, 07建築線測量, 08透地雷達,
              09資訊系統, 10技師簽證, 11其他類別
        """
        year_str = str(year) if year > 1911 else str(year + 1911)
        cat_code = category[:2].zfill(2) if category else "01"
        nat_code = case_nature[:2].zfill(2) if case_nature else "01"
        prefix = f"CK{year_str}_{cat_code}_{nat_code}_"

        # 查最大流水號 (同時查有/無 CK 前綴，相容舊資料)
        max_code = await self.project_repo.get_max_project_code_by_prefix(prefix)
        old_prefix = f"{year_str}_{cat_code}_{nat_code}_"
        old_max = await self.project_repo.get_max_project_code_by_prefix(old_prefix)

        next_serial = 1
        for code in (max_code, old_max):
            if code:
                try:
                    serial = int(code.split("_")[-1])
                    next_serial = max(next_serial, serial + 1)
                except (IndexError, ValueError):
                    pass

        return f"{prefix}{str(next_serial).zfill(3)}"

    async def promote_to_project(self, case_code: str) -> dict:
        """⚠️ **本方法內部會 `await self.db.commit()`** —— 呼叫端在外面包
        `try/finally: await db.rollback()` **不會**讓它變成可回滾的試算。

        2026-08-29：我為了確認「那 91 件待判讀的案件是不是被驗證擋著」，
        寫了一段外層 rollback 的測試並在回報裡寫「（已回滾，未實際成案）」——
        **那句話是錯的，3 件真的成案了**（後由 weekly step 28 的
        「已承攬但無成案編碼 91 → 88」抓到，已逐表還原）。

        要試算請改用**唯讀的方式**推導（查 `_validate_*` 的條件），
        或在一個真的沒有 commit 的分支上做；不要靠外層 rollback。

        成案觸發：從 PM Case 自動建立 ContractProject + 連結 ERP Quotation

        1. 查找 PM Case
        2. 產生 project_code
        3. 建立 ContractProject (繼承基本欄位 + case_code)
        4. 更新 PM Case 的 project_code + status
        5. 更新 ERP Quotation 的 project_code (如存在)

        Returns:
            {'project_code': str, 'contract_project_id': int, 'erp_linked': bool}
        """
        # 1. 查找 PM Case + 狀態檢查
        pm_case = await self.pm_repo.get_by_case_code(case_code)
        if not pm_case:
            raise ValueError(f"找不到案號 {case_code}")
        if pm_case.project_code:
            raise ValueError(f"案號 {case_code} 已成案，project_code={pm_case.project_code}")
        # 僅「已承攬」狀態允許成案 (planning/closed 不可)
        blocked_statuses = ("planning", "closed")
        if pm_case.status in blocked_statuses:
            raise ValueError(f"案號 {case_code} 狀態為 {pm_case.status}，僅已承攬案件可成案")

        # 2026-08-16：成案前檢查「該有的資料齊了嗎」。
        #
        # owner 回報「和美已承攬但頁面資訊仍無同步」。查證後**不是同步失敗** ——
        # 成案有正確複製 `contract_amount`，但 PM 案件那一欄從 07-31 建立起就是空的，
        # 於是複製了一個空值，一路空到承攬案件與財務。
        #
        # 既有把關只有「狀態」與「防重」，**沒有一道在問資料齊不齊** ——
        # 而成案是不可逆動作（產生 project_code、建立承攬案件、連結報價），
        # 缺漏會沿著整條鏈傳下去，事後補要改三個模組。
        #
        # 只擋金額：它是唯一會流進財務的欄位，缺了會讓毛利、應收、預算全部失真。
        # 委託單位刻意不擋 —— PM 端存 `client_vendor_id`（指 partner_vendors）
        # 而承攬端存 `client_agency`（文字），兩邊本來就不是同一個 id 空間，
        # 那是既有的結構分歧，不該由這道守衛順手處理。
        if not pm_case.contract_amount or float(pm_case.contract_amount) <= 0:
            raise ValueError(
                f"案號 {case_code} 尚未填寫合約金額，無法成案 —— "
                "金額會一路帶到承攬案件與財務，缺了會讓毛利與應收失真。"
                "請先在案件資訊填入合約金額。"
            )

        # 防重（2026-08-10）：上面那道只擋「同一個 PM 案件成案兩次」，
        # 擋不住「同一件工作已經有人在承攬案件頁直接建過一筆」。
        # 2026-08-10 實際發生：同一件工作 10:19 直接建立、10:43 成案，兩筆都成功。
        # 判準與 ProjectService.create 相同（同名＋同年度＋同委託單位），
        # 兩條路徑共用同一條規則，否則擋住一邊等於沒擋。
        if pm_case.case_name:
            from sqlalchemy import select, func
            from app.extended.models import ContractProject
            stmt = select(ContractProject).where(
                func.trim(ContractProject.project_name) == pm_case.case_name.strip(),
                ContractProject.year == pm_case.year,
            )
            # ⚠️ 兩張表的委託單位欄位名不同：
            #   pm_cases.client_name  vs  contract_projects.client_agency
            # 比對用名稱字串（PM 端存的 client_vendor_id 指向 partner_vendors，
            # 與承攬端的 client_agency_id 指向 agencies，**不是同一個 id 空間**，
            # 拿來直接比會永遠不命中）。
            client_name = (getattr(pm_case, "client_name", None) or "").strip()
            if client_name:
                stmt = stmt.where(func.trim(ContractProject.client_agency) == client_name)
            dup = (await self.db.execute(stmt.limit(1))).scalar_one_or_none()
            if dup:
                raise ValueError(
                    f"同名承攬案件已存在：{dup.project_code}（{dup.project_name}）。"
                    f"這件工作看起來已經建過案 —— 若要沿用，請直接把 PM 案件 {case_code} "
                    f"的成案編號指向 {dup.project_code}；若確實是不同的兩案，"
                    f"請把名稱或年度改成能分辨的內容再成案。"
                )

        # 2. 產生 project_code —— **建案案號去掉 `_PM_`**
        #
        # owner 2026-08-27 決策：「成案編號無須連號，內部識別」。
        #
        # 舊做法是 `generate_project_code(year, category, case_nature)`，
        # 它有自己的流水號計數器（目的是「只有成案的才領號、且連號」）。
        # 放棄連號換到三件事：
        #   ① **不再需要作業性質碼** —— 而它推導不出來（legacy 編號裡沒有
        #      這個資訊，第 2 組字母是承辦同仁不是性質），先前有 179 筆卡在這
        #   ② **不再需要第二個流水號計數器** —— 也就不會重演 08-20 那次批次撞號
        #   ③ 一眼可回溯：`CK2026_02_007` <-> `CK2026_PM_02_007`
        #
        # ⚠️ legacy 案號（`B115-C020-0`）去 PM 無效 —— 這裡**明確擋下**而不是
        #    悄悄退回舊產號器。退回會讓兩套編碼繼續混生，而混生正是
        #    這一輪要收斂的東西。擋下的訊息會出現在 API 回應裡
        #    （`pm/cases.py` 的 except 已於同日改為回傳訊息而非只寫 log）。
        if "_PM_" not in case_code:
            raise ValueError(
                f"案號 {case_code} 不是建案案號格式（缺 `_PM_`），無法產生成案編號。"
                "成案編號＝建案案號去掉 `_PM_`，所以要先讓這個案子有正式的建案案號。"
                "舊制編號（B115-C020-0 之類）請先執行建案案號轉換。"
            )
        project_code = case_code.replace("_PM_", "_", 1)

        # 唯一性 —— `contract_projects.project_code` 有 UNIQUE 約束，
        # 撞號在 commit 時才爆，訊息是資料庫的，讀不出所以然。這裡先問一次。
        from sqlalchemy import text as _text
        _dup = await self.db.scalar(
            _text("SELECT 1 FROM contract_projects WHERE btrim(project_code) = :p LIMIT 1"),
            {"p": project_code},
        )
        if _dup:
            raise ValueError(
                f"成案編號 {project_code} 已經存在。"
                f"這代表建案案號 {case_code} 對應的案子可能已經成過案 —— "
                "請先確認是否重複，不要另編一個號。"
            )

        # 3. 建立 ContractProject (透過 Repository)
        contract_project = await self.project_repo.create({
            "project_name": pm_case.case_name,
            "project_code": project_code,
            "case_code": case_code,
            "year": pm_case.year,
            "category": pm_case.category,
            "case_nature": getattr(pm_case, 'case_nature', None),
            "client_agency": pm_case.client_name,
            "contract_amount": float(pm_case.contract_amount) if pm_case.contract_amount else None,
            "start_date": pm_case.start_date,
            "end_date": pm_case.end_date,
            "status": "執行中",
            "location": getattr(pm_case, 'location', None),
            "description": pm_case.description,
            "notes": pm_case.notes,
        }, auto_commit=False)

        # 4. 更新 PM Case
        pm_case.project_code = project_code
        # 2026-08-16 owner：「邀標不應有執行中選項」。
        # 成案後邀標案件的正確終態是「已承攬」—— 執行由承攬案件承接
        # （上面剛建的 contract_project 就是 status='執行中'）。
        # 原本兩邊同時設「執行中」，於是同一件工作在兩個模組各有一個
        # 「執行中」而無從分辨誰是誰，這正是 owner 回報的狀態混淆。
        pm_case.status = "contracted"

        # 5. 連結 / 自動建立 ERP Quotation
        erp_linked = False
        erp_quotation = await self.erp_repo.get_by_case_code(case_code)
        if erp_quotation:
            # 已有 → 更新 project_code
            erp_quotation.project_code = project_code
            erp_linked = True
        else:
            # 成案時自動建立 ERP Quotation (確保專案財務紀錄存在)
            from app.extended.models.erp import ERPQuotation
            new_erp = ERPQuotation(
                case_code=case_code,
                case_name=pm_case.case_name,
                project_code=project_code,
                year=pm_case.year,
                total_price=pm_case.contract_amount,
                status="confirmed",
                # 這張不是報價，是讓請款有地方掛的 0 元錨點；XLS 對照與人工報價清單都要排除它
                quote_kind="finance_anchor",
            )
            self.db.add(new_erp)
            erp_linked = True
            logger.info(f"自動建立 ERP Quotation: case_code={case_code}")

        # 6. 承辦同仁：把 PM 階段的指派補上 project_id（2026-08-29）
        #
        # 成案前的指派是以 `case_code` 掛的（PM 側 StaffTab 就是這樣寫的），
        # 而承攬側的查詢用 `project_id`（`/project-staff/project/{id}/list`）
        # ⇒ 成案後同一個人在承攬案件頁**看不到**，要重新指派一次。
        # 實測：94 筆承攬案的承辦裡有 65 筆 `project_id` 是空的、只靠 case_code 掛著。
        #
        # 這裡不新增指派、不改 user，只把已存在的那幾筆補上 project_id ——
        # 「同一件工作換了個編號」不該讓人從頭再指派一次。
        # 用 UPDATE 而非逐筆 ORM：這是機械式回填，且 case_code 已由本方法保證唯一。
        try:
            from sqlalchemy import text as _t
            r = await self.db.execute(_t(
                "UPDATE project_user_assignments SET project_id = :pid "
                "WHERE case_code = :cc AND project_id IS NULL"
            ), {"pid": contract_project.id, "cc": case_code})
            if r.rowcount:
                logger.info("成案承辦同仁承接: case_code=%s 補 project_id=%s 共 %d 筆",
                            case_code, contract_project.id, r.rowcount)
        except Exception as e:
            # 不阻擋成案（案件比關聯重要），但要出聲 —— 靜靜地少接一段
            # 正是這個缺口原本的樣子
            logger.error("成案承辦同仁承接失敗 case_code=%s: %s", case_code, e, exc_info=True)

        await self.db.commit()

        # 審計記錄：成案事件
        try:
            from app.services.audit import AuditService
            audit = AuditService(self.db)
            await audit.log_action(
                action="promote_to_project",
                table_name="pm_cases",
                record_id=pm_case.id,
                changes={
                    "case_code": case_code,
                    "project_code": project_code,
                    "contract_project_id": contract_project.id,
                    "erp_linked": erp_linked,
                },
            )
        except Exception as e:
            logger.debug("成案審計記錄失敗 (非阻擋): %s", e)

        logger.info(
            f"成案完成: case_code={case_code} → project_code={project_code}, "
            f"contract_project_id={contract_project.id}, erp_linked={erp_linked}"
        )
        # 7. 成案即應收（owner 2026-09-03）：有報價總額就自動建第一期請款，
        #    否則夜間吹哨者的「請款逾期」對這個案子永遠不會響。
        try:
            from app.services.erp.billing_service import ERPBillingService
            erp_for_billing = await self.erp_repo.get_by_case_code(case_code)
            if erp_for_billing:
                await ERPBillingService(self.db).ensure_first_period(erp_for_billing.id, reason=f"成案 {project_code}")
        except Exception as e:
            logger.error("成案即應收掛點失敗（不阻擋成案）case_code=%s: %s", case_code, e, exc_info=True)

        # Publish domain event
        try:
            from app.core.event_bus import EventBus
            from app.core.domain_events import project_promoted
            bus = EventBus.get_instance()
            await bus.publish(project_promoted(
                case_code=case_code,
                project_code=project_code,
                contract_project_id=contract_project.id,
                erp_linked=erp_linked,
            ))
        except Exception as e:
            logger.warning(f"Domain event publish failed (non-blocking): {e}")

        return {
            "project_code": project_code,
            "contract_project_id": contract_project.id,
            "erp_linked": erp_linked,
        }

    async def cross_module_lookup(self, code: str) -> dict:
        """跨模組查詢案號 — 回傳該案號在 PM/ERP 各自的記錄。

        兩段式查找（2026-07-29 補 project_code fallback，比照同檔
        `find_linked_documents` 既有模式）：
        1. 以 `case_code` 精確匹配（建案案號，正規流程）
        2. 找不到才回退 `project_code`（成案編號）

        起因：承攬案件詳情頁「財務紀錄」傳入 `case_code || project_code`，
        但本方法原僅比對 case_code → 對「直接建立／歷史匯入、無 case_code」的案件
        永遠回 None（半接通）。實測 71 筆報價中 49 筆兩碼不同值，fallback 有實質必要。
        """
        result: dict = {"case_code": code, "pm": None, "erp": None}

        # PM：case_code 優先，回退 project_code
        result["pm"] = await self.pm_repo.get_lookup_by_case_code(code)
        if not result["pm"]:
            result["pm"] = await self.pm_repo.get_lookup_by_project_code(code)

        # ERP：同上
        result["erp"] = await self.erp_repo.get_lookup_by_case_code(code)
        if not result["erp"]:
            result["erp"] = await self.erp_repo.get_lookup_by_project_code(code)

        return result

    async def find_linked_documents(self, case_code: str, limit: int = 20) -> list:
        """透過 case_code 查找相關公文

        搜尋策略 (優先使用 case_code 欄位，回退 project_code):
        1. ContractProject.case_code 精確匹配
        2. ContractProject.project_code 精確匹配 (向後相容)
        3. OfficialDocument.contract_project_id 指向該 project
        """
        # 優先用 case_code 欄位查找
        project_ids = await self.project_repo.get_ids_by_case_code(case_code)

        # 回退：用 project_code 查找 (向後相容)
        if not project_ids:
            project_ids = await self.project_repo.get_ids_by_project_code(case_code)

        if not project_ids:
            return []

        return await self.doc_repo.get_by_project_ids(project_ids, limit=limit)

    # =========================================================================
    # Asset Code 自動生成 (ADR-0013 Phase 1)
    # =========================================================================

    ASSET_CATEGORY_CODES = {
        "equipment": "EQ",   # 設備
        "vehicle": "VH",     # 車輛
        "instrument": "IN",  # 儀器
        "furniture": "FN",   # 家具
        "other": "OT",       # 其他
    }

    async def generate_asset_code(
        self,
        year: int,
        category: str = "equipment",
    ) -> str:
        """自動產生資產編號

        格式: AT_{yyyy}_{CC}_{NNN}
        範例: AT_2026_EQ_001

        Args:
            year: 年度 (西元年)
            category: 資產類別 (equipment/vehicle/instrument/furniture/other)
        """
        year_str = str(year) if year > 1911 else str(year + 1911)
        cat_code = self.ASSET_CATEGORY_CODES.get(category, "OT")
        prefix = f"AT_{year_str}_{cat_code}_"

        from sqlalchemy import select, func
        from app.extended.models.asset import Asset

        result = await self.db.execute(
            select(func.max(Asset.asset_code))
            .where(Asset.asset_code.like(f"{prefix}%"))
        )
        max_code = result.scalar()

        next_serial = 1
        if max_code:
            try:
                next_serial = int(max_code.split("_")[-1]) + 1
            except (IndexError, ValueError):
                pass

        return f"{prefix}{str(next_serial).zfill(3)}"

    # =========================================================================
    # Billing / Invoice / Ledger Code 自動生成 (ADR-0013 Phase 2)
    # =========================================================================

    async def generate_billing_code(self, year: int) -> str:
        """生成請款編碼 BL_{yyyy}_{NNN}"""
        year_str = str(year) if year > 1911 else str(year + 1911)
        prefix = f"BL_{year_str}_"

        from sqlalchemy import select, func
        from app.extended.models.erp import ERPBilling

        result = await self.db.execute(
            select(func.max(ERPBilling.billing_code))
            .where(ERPBilling.billing_code.like(f"{prefix}%"))
        )
        max_code = result.scalar()

        next_serial = 1
        if max_code:
            try:
                next_serial = int(max_code.split("_")[-1]) + 1
            except (IndexError, ValueError):
                pass

        return f"{prefix}{str(next_serial).zfill(3)}"

    async def generate_invoice_ref(self, year: int) -> str:
        """生成發票參照碼 IV_{yyyy}_{NNN}"""
        year_str = str(year) if year > 1911 else str(year + 1911)
        prefix = f"IV_{year_str}_"

        from sqlalchemy import select, func
        from app.extended.models.erp import ERPInvoice

        result = await self.db.execute(
            select(func.max(ERPInvoice.invoice_ref))
            .where(ERPInvoice.invoice_ref.like(f"{prefix}%"))
        )
        max_code = result.scalar()

        next_serial = 1
        if max_code:
            try:
                next_serial = int(max_code.split("_")[-1]) + 1
            except (IndexError, ValueError):
                pass

        return f"{prefix}{str(next_serial).zfill(3)}"

    async def generate_ledger_code(self, year: int) -> str:
        """生成帳本編碼 FL_{yyyy}_{NNNNN}"""
        year_str = str(year) if year > 1911 else str(year + 1911)
        prefix = f"FL_{year_str}_"

        from sqlalchemy import select, func
        from app.extended.models.finance import FinanceLedger

        result = await self.db.execute(
            select(func.max(FinanceLedger.ledger_code))
            .where(FinanceLedger.ledger_code.like(f"{prefix}%"))
        )
        max_code = result.scalar()

        next_serial = 1
        if max_code:
            try:
                next_serial = int(max_code.split("_")[-1]) + 1
            except (IndexError, ValueError):
                pass

        return f"{prefix}{str(next_serial).zfill(5)}"

    @staticmethod
    def get_module_categories(module: str) -> dict:
        """取得模組可用類別"""
        mod_code = MODULE_CODES.get(module.lower(), module.upper())
        return MODULE_CATEGORIES.get(mod_code, {})
