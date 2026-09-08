"""ERP API Endpoints — 全部端點需認證"""
from fastapi import APIRouter, Depends
from app.core.dependencies import require_any_permission, require_auth, require_permission
from app.core.capabilities import require_page_permission
from . import case_finance, quotations, invoices, billings, vendor_payables, vendor_accounts
from . import client_accounts
from . import expenses, expenses_io, ledger, financial_summary, einvoice_sync, filing_gaps, quotation_items
from . import assets
from . import operational
from . import my_summary

# ⚠️ 2026-08-29 owner 裁示「ERP 權限收斂」：由 `require_auth()`（只問有沒有登入）
# 提升為 `require_permission("reports:erp:view")`。
#
# ## 為什麼
#
# 在此之前，**系統內任何登入者**（含一般同仁 staff）直接打 API 就能拉取
# 統一帳本、營運帳目、報價單與財務總覽 —— 前端選單把按鈕藏起來，
# 但那不是防禦（security through obscurity）。
#
# ## 前置條件已實測滿足（不是假設）
#
#   role_permissions 的 `reports:erp:view`：admin ✓ exec ✓ finance ✓ ops ✓ staff ✗
#   現有使用者：admin 5 人、staff 6 人、superuser 1 人
#   `require_permission` 對 superuser **短路放行**（dependencies.py:289）
#
# ⇒ 收斂後 **staff 6 人失去 ERP API 存取**，那正是目的；
#   admin/superuser 不受影響。外部評估文件說「admin 僅有 6 項權限、
#   同步前不可收斂」—— **實測 admin 有 33 項，那個前置警告已經過期**。
#
# ## 為什麼在 router 層而不是逐支端點
#
# ERP 目錄下 107 支端點，逐支改會漏（今天已經看過「同一條規則掃所有寫入
# 路徑」漏掉一支的代價）。router 層是單一收斂點，新增端點自動繼承。
# ⚠️ 反面風險：**同一個 router 底下若有真正該公開的端點，會被一起擋掉** ——
# 已由 weekly 65 `router_level_auth_mixing_audit` 守這件事。
# ⚠️ 2026-08-29 修正：**不在頂層掛單一權限**。
#
# 我第一版把整個 ERP router 鎖在 `reports:erp:view`，而實測後發現那會造成
# 回歸：`site_navigation_items` 裡各 ERP 頁面**要求的權限本來就不同** ——
#
#   /erp/client-accounts  → reports:finance:view
#   /erp/vendor-accounts  → reports:finance:view
#   /erp/quotations       → reports:finance:view
#   /erp/assets           → reports:assets:view
#   其餘（ledger／operational／expenses…）→ reports:erp:view
#
# 而 `staff` **有 reports:finance:view、沒有 reports:erp:view**
# ⇒ 他們看得到「委託單位帳款」選單、點下去卻會 403。
#
# ⇒ 權限改掛在各子 router，**用該頁面本來就宣告的那一個** ——
#   不是我另外發明一套。導覽表是既有的 SSOT，API 對齊它。
# ⭐ 2026-09-07 收斂 B（owner：「整個系統四分五裂」）：
#   API 不再自己硬寫權限碼。每支子路由宣告的是「**我屬於哪個頁面**」，
#   權限碼從選單表讀（`app/core/capabilities.py`）—— 選單管理頁改一次，
#   選單、路由守衛、API 三邊同時生效。此前三邊各寫各的，改一邊另兩邊不動。
#   程式碼裡只留路由結構（前綴 → 頁面），那本來就只能寫在這裡。
router = APIRouter(dependencies=[Depends(require_auth())])
router.include_router(quotations.router, prefix="/quotations", dependencies=[Depends(require_page_permission("/erp/quotations"))], tags=["ERP 報價管理"])
# ⭐ 2026-09-07 owner：「ERP 仍無法獨立區分選取」。
#
# 這 6 頁原本共用 `reports:erp:view` 一個碼 ⇒ 權限管理頁勾任一個等於開 6 個
# （粒度是**碼的數量**，不是頁面的數量）。⇒ 一頁一碼。
#
# ⚠️ 但只換成新碼會讓既有持有 `reports:erp:view` 的人當場被擋 ——
# 角色層與使用者層要同步，任一沒跟上就是 403（09-07 拆委託／協力帳款時
# 已經因此讓管理員看不到那兩頁）。⇒ 用 `require_any_permission(新碼, erp:view)`：
#   · 只給新碼的人 → 只進得去那一頁（真正的獨立，網址也擋得住）
#   · 既有 erp:view 的人 → 全部照舊，零回歸
#   · 日後要收緊：把 erp:view 從角色移除即可，不必再動程式碼
# ⭐ 2026-09-08 收斂 B 補完（owner 從 /erp/client-accounts 一路點進去回報 403）：
#
# 收斂 B 讓每支 router 宣告「我屬於哪個頁面」，**但它假設了一個頁面只呼叫自己的 API**。
# 實際上分頁（Tab）會跨 router：報價單詳情的「帳款紀錄」分頁呼叫 `/erp/invoices/list`，
# 而 staff 有 `reports:finance:view`（進得了報價單）、沒有 `reports:invoices:view`
# ⇒ **頁面打得開、分頁一律 403，而畫面上看不出原因**。
# 瀏覽器 console 實證：`/api/erp/invoices/list` 403、`/api/erp/expenses/case-finance` 403。
#
# 修法用 `require_page_permission` 本來就有的聯集能力（見其 docstring：
# 「多個頁面時取聯集 —— 給『一支 API 被兩個頁面共用』的情況」）。
# **刻意不改角色權限碼**：選單與 API 共用同一組碼，補碼會連帶把發票彙總頁、
# 費用報銷頁整頁開給 staff —— 那是放寬選單，不是修好分頁。
#
# 判準：**誰看得到那個「宿主頁面」，誰就能用該頁面上的分頁。**
router.include_router(invoices.router, prefix="/invoices", dependencies=[Depends(require_page_permission("/erp/invoices/summary-view", "/erp/quotations"))], tags=["ERP 發票管理"])
router.include_router(billings.router, prefix="/billings", dependencies=[Depends(require_page_permission("/erp/quotations"))], tags=["ERP 請款管理"])
router.include_router(vendor_payables.router, prefix="/vendor-payables", dependencies=[Depends(require_page_permission("/erp/quotations"))], tags=["ERP 廠商應付"])
# ⭐ 2026-09-07 owner：「委託與協力帳款仍關聯 ERP，**無法正常獨立勾選**」。
#
# 這兩支原本掛 `reports:erp:view`，而那個碼綁著 11 個頁面 ⇒ 在權限管理頁勾
# 「委託帳款」必然連帶開啟統一帳本、營運帳目、財務儀表板等 9 頁。
# 頁面自己的提示就寫著「多 nav 共用同一 perm 時，勾任一即同步全部」——
# **粒度是權限碼的數量，不是頁面的數量。**
#
# ⇒ 各給一個碼：`reports:client_accounts:view`／`reports:vendor_accounts:view`。
#   分開而不是合成一個：委託單位帳款是應收、協力廠商帳款是應付，
#   實務上可能只想開其中一邊。
#
# ⚠️ 這裡改的是 **API**；同一件事還有兩處要一起改，否則就是半接通：
#   ①`site_navigation_items.permission_required`（選單與**路由守衛**都讀它）
#   ②`role_permissions`（原本靠 erp:view 看得到的角色要補新碼，否則管理員自己會被擋）
#
# ⭐ 2026-08-31 owner：「這兩支維持全公司視角，改用權限區分
#    （例如只有 admin／財務角色看得到）」。
#
# 為什麼是權限而不是行級過濾（RLS）：這兩支是**依往來對象彙總**的
# （某委託單位／某廠商的總帳款）。若依案件指派限縮，語意會變成
# 「這個客戶的帳款中屬於我的案子的那部分」—— **那個數字比不限縮更容易誤導**。
#
# 為什麼從 `reports:finance:view` 換成 `reports:erp:view`：實測
# 12 位在職使用者裡 **11 位持有 finance:view**（含全部 5 位 staff）——
# 那個閘門實際上等於全開。而 `reports:erp:view` 正好是 **5 位 admin、
# 0 位 staff**，就是要的範圍，且它已經在用（filing-gaps 走同一個），
# **不新增權限代碼**。superuser 由 require_permission 自身旁路。
router.include_router(vendor_accounts.router, prefix="/vendor-accounts", dependencies=[Depends(require_page_permission("/erp/vendor-accounts"))], tags=["ERP 廠商帳款"])
# 2026-09-08 收斂 B 補完：報價單詳情與 PM 案件詳情各有「費用」分頁，兩者呼叫
# `/erp/expenses/case-finance`（console 實證 403）。**但只有那一支**——
# 費用報銷的列表／建立／審核／退回／全公司總覽仍然只屬於 `/erp/expenses`。
# ⇒ 把 `case-finance` 拆成獨立 router 掛聯集，其餘兩支維持原門檻。
# **放寬的範圍要剛好等於問題的範圍**，不能因為修法方便就整個 router 放寬。
router.include_router(expenses.router, prefix="/expenses", dependencies=[Depends(require_page_permission("/erp/expenses"))], tags=["費用報銷"])
router.include_router(expenses_io.router, prefix="/expenses", dependencies=[Depends(require_page_permission("/erp/expenses"))], tags=["費用報銷 IO"])
router.include_router(case_finance.router, prefix="/expenses", dependencies=[Depends(require_page_permission("/erp/expenses", "/erp/quotations", "/pm/cases"))], tags=["案件整合財務"])
router.include_router(ledger.router, prefix="/ledger", dependencies=[Depends(require_page_permission("/erp/ledger"))], tags=["統一帳本"])
router.include_router(financial_summary.router, prefix="/financial-summary", dependencies=[Depends(require_page_permission("/erp/financial-dashboard"))], tags=["財務彙總"])
# 2026-08-16 owner：「承攬報價案件對應填報人員通報管控」
#
# ⭐ 2026-09-08：**這裡不能掛 router 層的頁面權限**。這支底下有兩種端點：
#   · `/list` 全公司填報缺口 → 屬於 `/erp`（reports:erp:view，5 admin／0 staff）
#   · `/mine` **只查 current_user.id 自己的** → 每個承辦的個人儀表板都在打它
# 掛在 router 層等於用 `/erp` 的門檻擋住 `/mine` ⇒ **每一位 staff 打開自己的
# 儀表板，「我的填報缺口」卡都是 403**，而那張卡正是 owner 09-03 指定
# 「承辦個人的稽催資訊落點＝個人儀表板」的那一張。
# ⇒ 頁面權限下放到 `/list`（見 filing_gaps.py），`/mine` 只要求登入 ——
#   與同檔下方 `my_summary` 的處理一致（那支 09-03 就已經是這個形狀）。
router.include_router(filing_gaps.router, prefix="/filing-gaps", tags=["填報缺口"])
# 2026-09-03：我的專案統整——承辦看自己的待收／逾期是稽催機制的一部分，只要登入（require_auth 在端點內），不掛 reports 權限
router.include_router(my_summary.router, prefix="/my-summary", tags=["個人儀表板"])
# 2026-08-16 owner：「線上報價單機制」
router.include_router(quotation_items.router, prefix="/quotation-items", dependencies=[Depends(require_page_permission("/erp/quotations"))], tags=["報價明細"])
router.include_router(einvoice_sync.router, prefix="/einvoice-sync", dependencies=[Depends(require_page_permission("/erp/einvoice-sync"))], tags=["電子發票同步"])
router.include_router(client_accounts.router, prefix="/client-accounts", dependencies=[Depends(require_page_permission("/erp/client-accounts"))], tags=["ERP 委託單位帳款"])
router.include_router(assets.router, prefix="/assets", dependencies=[Depends(require_page_permission("/erp/assets"))], tags=["ERP 資產管理"])
router.include_router(operational.router, prefix="/operational", dependencies=[Depends(require_page_permission("/erp/operational"))], tags=["ERP 營運帳目"])
