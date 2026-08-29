#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A33 的 91 筆「已承攬未成案」——用邏輯分層，把人要做的事從「判斷」降為「確認」。

## owner 2026-08-29 的問題：「第四批 無邏輯可檢核調整嗎」

答案：**有，但只能分層不能全自動**。實測分層結果（以案件為單位）：

    ① 唯一候選 + 委託單位與金額都相同     4 筆  → 幾乎確定是同一件，可自動接
    ② 唯一候選但委託名或金額有差         77 筆  → 差異型態可再細分（見下）
    ③ 多個同名候選                       10 筆  → 必須人選，邏輯給不出答案
    ④ 無候選                              0 筆

②的 77 筆再拆：只差金額 18／只差委託名 3／兩者皆差 56。
**「只差委託名」的 3 筆最可能是寫法差異**（技師本人 vs 事務所、啓/啟相容字）——
08-28 那次 51 筆誤成案正是這個形態騙過守衛的。
**「只差金額」的 18 筆是真訊號**：同一件工作兩邊記不同金額，那本身就該查。

## 為什麼不做成全自動

08-28 的教訓：機械式成案 136 筆後，發現 51 筆其實已有同名同年既有案，
整批撤回。**「同名」不等於「同案」，而「不同名」也不等於「不同案」。**
本工具只負責把 91 筆分成「幾乎確定」「有具體差異可看」「無從判斷」三堆，
每一堆附上差異在哪 —— 人看的是差異，不是從頭比對。

## 用法

    python scripts/sync/case_link_candidates.py            # 分層報告
    python scripts/sync/case_link_candidates.py --tier1    # 只列第①層（可自動接的）
    python scripts/sync/case_link_candidates.py --csv      # 匯出全部供逐筆勾稽

⚠️ **本工具不寫入任何資料**。要接上請用 `/pm/cases/:id` 畫面操作，
或把確認後的清單交給我執行（那時會走交易＋斷言）。
"""
import argparse
import subprocess
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SQL = """
WITH pend AS (
  SELECT p.id, p.case_code, p.case_name, p.year,
         COALESCE(p.client_name,'') AS pm_client, p.contract_amount AS pm_amt
    FROM pm_cases p
   WHERE p.status = 'contracted' AND p.project_code IS NULL
), joined AS (
  SELECT pend.*, c.project_code, COALESCE(c.client_agency,'') AS cp_client,
         c.contract_amount AS cp_amt,
         (SELECT count(*) FROM contract_projects c2
           WHERE btrim(c2.project_name) = btrim(pend.case_name) AND c2.year = pend.year) AS n_cand
    FROM pend LEFT JOIN contract_projects c
      ON btrim(c.project_name) = btrim(pend.case_name) AND c.year = pend.year
)
SELECT
  CASE WHEN n_cand = 0 THEN '4-無候選'
       WHEN n_cand > 1 THEN '3-多候選'
       WHEN btrim(pm_client) = btrim(cp_client) AND pm_amt IS NOT DISTINCT FROM cp_amt THEN '1-全同'
       ELSE '2-有差異' END AS tier,
  case_code, left(case_name, 34) AS case_name, year,
  COALESCE(project_code,'') AS 候選成案編號,
  CASE WHEN btrim(pm_client) = btrim(cp_client) THEN '' ELSE pm_client || ' ≠ ' || cp_client END AS 委託差異,
  CASE WHEN pm_amt IS NOT DISTINCT FROM cp_amt THEN ''
       ELSE COALESCE(pm_amt::text,'null') || ' ≠ ' || COALESCE(cp_amt::text,'null') END AS 金額差異
FROM joined
ORDER BY tier, case_code
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier1", action="store_true", help="只列第①層（唯一候選且全同）")
    ap.add_argument("--csv", action="store_true", help="輸出 CSV 供逐筆勾稽")
    args = ap.parse_args()

    fmt = ["-A", "-F", ","] if args.csv else []
    r = subprocess.run(
        ["docker", "exec", "ck_missive_postgres", "psql", "-U", "ck_user",
         "-d", "ck_documents"] + fmt + ["-c", SQL],
        capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    if r.returncode != 0:
        print(f"[RED] 查詢失敗（不下結論）：{r.stderr[:300]}", file=sys.stderr)
        return 2

    out = r.stdout
    if args.tier1:
        lines = [l for l in out.splitlines() if l.startswith("1-全同") or "tier" in l]
        print("\n".join(lines) if lines else "第①層沒有案件")
        return 0

    print(out)
    if not args.csv:
        print("""
判讀指引（owner 2026-08-29「無邏輯可檢核調整嗎」的答案）：
  **1-全同**   唯一候選、委託單位與金額都相同 —— 幾乎確定是同一件，確認後可批次接上
  **2-有差異** 唯一候選但有具體差異，**差異就印在上面**：
               · 只差委託名 → 多半是寫法（技師本人 vs 事務所、啓/啟相容字），
                 08-28 那 51 筆誤成案正是這個形態騙過守衛的
               · 只差金額   → **這是真訊號**，同一件工作兩邊記不同金額本身就該查
  **3-多候選** 邏輯給不出答案，必須人選（選錯會產生兩筆代表同一件工作的案件）
  **4-無候選** 應是真的新案，直接成案即可

⚠️ 本工具**不寫入任何資料**。確認後可用畫面操作，或把清單交給我執行
（走交易＋斷言，比照 08-28 那次撤回的做法）。
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
