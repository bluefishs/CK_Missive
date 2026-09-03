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

SQL = """
WITH my_cases AS (
  SELECT DISTINCT q.id AS qid, q.case_code, q.case_name, q.total_price, q.project_code, q.status AS q_status, c.id AS cid, c.status AS c_status
  FROM project_user_assignments a
  LEFT JOIN contract_projects c ON c.id = a.project_id OR (a.case_code IS NOT NULL AND c.case_code = a.case_code)
  JOIN erp_quotations q ON q.deleted_at IS NULL AND (q.case_code = a.case_code OR q.case_code = c.case_code)
  WHERE a.user_id = :uid
),
bills AS (
  SELECT b.*, m.case_code, m.case_name FROM erp_billings b JOIN my_cases m ON m.qid = b.erp_quotation_id
)
SELECT json_build_object(
  'cases_active', (SELECT count(DISTINCT cid) FROM my_cases WHERE c_status = '執行中'),
  'cases_closed', (SELECT count(DISTINCT cid) FROM my_cases WHERE c_status = '已結案'),
  'quotes_unawarded', (SELECT count(*) FROM my_cases WHERE project_code IS NULL),
  'pending_count', (SELECT count(*) FROM bills WHERE payment_status IN ('pending','partial')),
  'pending_amount', (SELECT COALESCE(sum(billing_amount - COALESCE(payment_amount,0)),0)::bigint FROM bills WHERE payment_status IN ('pending','partial')),
  'overdue_count', (SELECT count(*) FROM bills WHERE payment_status IN ('pending','partial') AND billing_date < CURRENT_DATE),
  'overdue_amount', (SELECT COALESCE(sum(billing_amount - COALESCE(payment_amount,0)),0)::bigint FROM bills WHERE payment_status IN ('pending','partial') AND billing_date < CURRENT_DATE),
  'overdue_30_count', (SELECT count(*) FROM bills WHERE payment_status IN ('pending','partial') AND billing_date < CURRENT_DATE - 30),
  'received_ytd', (SELECT COALESCE(sum(payment_amount),0)::bigint FROM bills WHERE payment_status = 'paid' AND payment_date >= date_trunc('year', CURRENT_DATE)),
  'no_billing', (SELECT count(*) FROM my_cases WHERE project_code IS NOT NULL AND COALESCE(total_price,0) > 0
                   AND NOT EXISTS (SELECT 1 FROM erp_billings b WHERE b.erp_quotation_id = my_cases.qid)),
  'overdue_items', (SELECT COALESCE(json_agg(json_build_object(
        'billing_id', id, 'quotation_id', erp_quotation_id, 'case_code', case_code, 'case_name', case_name,
        'billing_period', billing_period, 'amount', (billing_amount - COALESCE(payment_amount,0))::bigint,
        'billing_date', billing_date::text, 'days_overdue', (CURRENT_DATE - billing_date))
      ORDER BY billing_date), '[]'::json)
     FROM (SELECT * FROM bills WHERE payment_status IN ('pending','partial') AND billing_date < CURRENT_DATE ORDER BY billing_date LIMIT 5) t)
)::text
"""


async def get_my_summary(db: AsyncSession, user_id: int) -> Dict[str, Any]:
    import json
    raw = await db.scalar(text(SQL), {"uid": user_id})
    return json.loads(raw) if raw else {}
