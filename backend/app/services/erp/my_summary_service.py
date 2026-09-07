# -*- coding: utf-8 -*-
"""我的專案統整（個人儀表板用）——2026-09-03 owner：「稽催機制應配合承辦同仁建構通知機制，
個人儀表板核心目標：逐漸建構個人專案相關統整資訊」。

「我的」＝我是承辦（`project_user_assignments.user_id`）。指派有兩條綁法（case_code／project_id→承攬案），
兩條都認（同族缺陷第十處，見 proactive_triggers_erp 同日註解）。

一次 SQL 算完：案件數（執行中／已結案）、未成案報價單、待收（筆數／金額）、逾期（筆數／金額）、
最近 5 筆逾期明細、我的成案但無請款（自動第一期沒接到的）。
數字全部是**全量**（不是分頁），對齊 §2.6 ①。
"""
from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 稽催的時間錨點只有一個定義（見 billing_dunning.py）
from app.services.erp.billing_dunning import EFFECTIVE_BILLING_DATE_SQL

SQL = """
WITH my_cases AS (
  SELECT DISTINCT q.id AS qid, q.case_code, q.case_name, q.total_price, q.project_code, q.quoted_at, q.status AS q_status, c.id AS cid, c.status AS c_status
  FROM project_user_assignments a
  LEFT JOIN contract_projects c ON c.id = a.project_id OR (a.case_code IS NOT NULL AND c.case_code = a.case_code)
  JOIN erp_quotations q ON q.deleted_at IS NULL AND (q.case_code = a.case_code OR q.case_code = c.case_code)
  WHERE a.user_id = :uid
),
bills AS (
  -- 2026-09-07：自動建立的第一期**請款日留白**（沒有請款就沒有請款日期）。
  -- 逾期的時間錨點改用 `eff_billing_date = COALESCE(請款日, 報價單日期)`；
  -- 只認 billing_date 的話那些佔位會因為 NULL 全部從逾期名單消失，
  -- 而它們正是最該被催的一群（成案卻沒請款）。
  -- `billing_date` 本身保留原值（畫面要顯示空白），兩者不混用。
  -- 別名刻意用 `q`：`EFFECTIVE_BILLING_DATE_SQL` 的契約是「b＝請款、q＝報價單」，
  -- 這裡的 my_cases 每一列就帶著該報價單的 quoted_at，符合那個契約。
  SELECT b.*, q.case_code, q.case_name,
         {EFF_DATE} AS eff_billing_date
  FROM erp_billings b JOIN my_cases q ON q.qid = b.erp_quotation_id
)
SELECT json_build_object(
  'cases_active', (SELECT count(DISTINCT cid) FROM my_cases WHERE c_status = '執行中'),
  'cases_closed', (SELECT count(DISTINCT cid) FROM my_cases WHERE c_status = '已結案'),
  'quotes_unawarded', (SELECT count(*) FROM my_cases WHERE project_code IS NULL),
  'pending_count', (SELECT count(*) FROM bills WHERE payment_status IN ('pending','partial')),
  'pending_amount', (SELECT COALESCE(sum(billing_amount - COALESCE(payment_amount,0)),0)::bigint FROM bills WHERE payment_status IN ('pending','partial')),
  'overdue_count', (SELECT count(*) FROM bills WHERE payment_status IN ('pending','partial') AND eff_billing_date < CURRENT_DATE),
  'overdue_amount', (SELECT COALESCE(sum(billing_amount - COALESCE(payment_amount,0)),0)::bigint FROM bills WHERE payment_status IN ('pending','partial') AND eff_billing_date < CURRENT_DATE),
  'overdue_30_count', (SELECT count(*) FROM bills WHERE payment_status IN ('pending','partial') AND eff_billing_date < CURRENT_DATE - 30),
  'received_ytd', (SELECT COALESCE(sum(payment_amount),0)::bigint FROM bills WHERE payment_status = 'paid' AND payment_date >= date_trunc('year', CURRENT_DATE)),
  -- 創案→報價的缺口：我承辦的案裡一張報價單都沒有的（2026-09-07）
  'no_quotation', (SELECT count(DISTINCT a.case_code) FROM project_user_assignments a
                    WHERE a.user_id = :uid AND a.case_code IS NOT NULL
                      AND COALESCE(a.status,'active') <> 'inactive'
                      AND NOT EXISTS (SELECT 1 FROM erp_quotations q2
                                       WHERE q2.case_code = a.case_code AND q2.deleted_at IS NULL)),
  'no_billing', (SELECT count(*) FROM my_cases WHERE project_code IS NOT NULL AND COALESCE(total_price,0) > 0
                   AND NOT EXISTS (SELECT 1 FROM erp_billings b WHERE b.erp_quotation_id = my_cases.qid)),
  'overdue_items', (SELECT COALESCE(json_agg(json_build_object(
        'billing_id', id, 'quotation_id', erp_quotation_id, 'case_code', case_code, 'case_name', case_name,
        'billing_period', billing_period, 'amount', (billing_amount - COALESCE(payment_amount,0))::bigint,
        'billing_date', billing_date::text, 'days_overdue', (CURRENT_DATE - eff_billing_date))
      ORDER BY billing_date), '[]'::json)
     FROM (SELECT * FROM bills WHERE payment_status IN ('pending','partial') AND eff_billing_date < CURRENT_DATE ORDER BY billing_date LIMIT 5) t)
)::text
""".replace("{EFF_DATE}", EFFECTIVE_BILLING_DATE_SQL)


async def get_my_summary(db: AsyncSession, user_id: int) -> Dict[str, Any]:
    import json
    raw = await db.scalar(text(SQL), {"uid": user_id})
    return json.loads(raw) if raw else {}
