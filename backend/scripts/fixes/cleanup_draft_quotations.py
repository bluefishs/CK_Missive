"""
清理 draft 報價資料

2026-04-01: 刪除 22 筆 draft (無 project_code) 報價，含 1 筆異常有請款的 B114-B051。
保留 48 筆 confirmed 報價 (全部有 project_code)。

此腳本僅供記錄，操作已透過直接 SQL 完成。
"""
# 已執行的 SQL:
# DELETE FROM erp_quotations WHERE status = 'draft'
#   AND id NOT IN (SELECT DISTINCT erp_quotation_id FROM erp_billings)
#   AND id NOT IN (SELECT DISTINCT erp_quotation_id FROM erp_invoices)
#   AND id NOT IN (SELECT DISTINCT erp_quotation_id FROM erp_vendor_payables);
# -- 21 rows deleted
#
# DELETE FROM erp_invoices WHERE erp_quotation_id = 121;  -- B114-B051
# DELETE FROM erp_billings WHERE erp_quotation_id = 121;
# DELETE FROM erp_quotations WHERE id = 121;
# -- 1 row each
