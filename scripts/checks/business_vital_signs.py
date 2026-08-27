#!/usr/bin/env python
"""生命跡象 —— 問「這個模組今天活著嗎」，不問「機制有沒有動」。

⚠️ 條目數與模組數**不寫死在文案裡**：2026-08-26 加第九條時發現
「八條」「八個模組」各寫死一處，而加條目的人不會想到要改文案 ——
那正是本 repo 由 `doc_baseline_claim_audit` 納管文件數字的同一種漂移，
只是這次漂在程式的輸出裡，沒有任何東西在看。

## 為什麼需要這一支（2026-08-16 owner：「每週都重複檢修…還是修補不完」）

當天量出來的數字說明了原因：

| 事實 | 數字 |
|---|---|
| 檢核腳本總數 | 150 |
| 其中**只看機制**（腳本／註冊／檔案／程序是否存在或跑過） | **131** |
| 其中會碰業務資料的 | 19 |
| 七月至今新增／刪除 | **+47／0** |

而系統存在的目的不是讓機制動，是讓**公文被處理、派工被交付、
款被收到、帳被記下**。同一天有四個「機制綠、業務停」的實證：

- `ezbid_cache_refresh` 記 success **1737 次**，而 job 近 48 小時沒跑
- 核銷四層審批完整運作，**控制效果為 0**（同權限、不記錄、不擋自核）
- 統一帳本機制正確，而**應付 37 筆停在 unpaid 最舊 151 天**
- 報價毛利算得出來，而 **37 筆的成本是 0**

131 支機制檢核沒有一支問得到這些，因為它們問的不是這個。

**機制的組合數是無窮的**（每個 job × 每種豁免 × 每個環境 × 每次重構），
**而業務結果只有幾條** —— 追著機制修，永遠有下一個。
這就是「修補不完」的機制原因。

## 設計原則

1. **一支腳本、八條判準**，不是八支腳本 —— 本專案已有 150 支，
   增生本身就是成本。
2. 每條判準**直接查業務資料**，不查 job 有沒有跑、不查檔案新不新。
3. 每個豁免**必須寫理由**，且理由要能被檢驗（例如「政府週末不發標」
   有 announce_date 分布為證）。
4. **人的問題判 YELLOW，系統的問題判 RED** —— 應付沒推進不是系統壞了，
   判紅只會製造每天都紅的噪音，但它必須看得見。
5. ⚠️ **首月只觀測不告警**：新機制上線當下最不該被信任
   （§3 可信度規則 #15–#17、#19 全是「我自己新加的檢核造成的假訊號」）。
   `--enforce` 才會回非 0。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

IS_WEEKEND = date.today().weekday() >= 5

# ---------------------------------------------------------------------------
# 八條生命跡象。
# sql 一律回單一數字；judge(n) 回 None（活著）或問題字串。
# level: RED = 系統壞了；YELLOW = 人沒推進（不是系統的錯，但要看得見）。
# ---------------------------------------------------------------------------
VITALS = [
    {
        "module": "公文",
        "what": "今日有新公文或有公文被更新",
        "sql": "SELECT count(*) FROM documents WHERE created_at::date = CURRENT_DATE "
               "OR updated_at::date = CURRENT_DATE",
        "level": "YELLOW",
        "weekend_ok": True,
        "why_exempt": "假日不辦公，沒有新公文是正常的",
    },
    {
        "module": "派工",
        "what": "逾期未交付的派工沒有累積到失控",
        # 2026-08-16：`deadline` 原本是**民國年字串**且同時裝著業務條件
        # （「115年02月08日前函覆(發文日起25日歷天内檢送成果)」），
        # 直接比較會型別錯誤，而在檢核裡自己寫一套民國年解析就是異質同工的起點。
        # 遷移 20260816a002 加了 `deadline_date`（原文保留），41/43 解析成功；
        # 解析不出的 2 筆本來就不是日期（「查估日期之次日起25日曆天內」「暫緩」）。
        "sql": "SELECT count(*) FROM taoyuan_dispatch_orders d "
               "WHERE d.deadline_date < CURRENT_DATE "
               "AND NOT EXISTS (SELECT 1 FROM taoyuan_work_records w "
               "WHERE w.dispatch_order_id = d.id AND w.work_category = 'delivery')",
        "level": "YELLOW",
        "max": 40,
        "why_exempt": "逾期是業務現實不是系統故障；設上限只為偵測失控成長",
    },
    {
        "module": "標案",
        "what": "標案庫有在長大",
        "sql": "SELECT COALESCE(EXTRACT(day FROM NOW() - MAX(announce_date))::int, 9999) "
               "FROM tender_records WHERE source = 'ezbid'",
        "level": "RED",
        "max": 5,
        "why_exempt": "政府週末不發標（實測 announce_date：週一至五 480–910 筆／"
                      "週六日 0 筆）。5 天＝跨過一個完整週末仍無新增",
    },
    {
        "module": "標案",
        "what": "標案**寫入端**有在動（平日不得整天沒抓到）",
        # ⚠️ 與上一條的差別是整條檢核的重點：上一條看 `announce_date`
        # （政府公告日），這一條看 `created_at`（我們寫入的日期）。
        #
        # 爬蟲停擺後恢復時會**一次補回前幾天的 announce_date** ⇒
        # `MAX(announce_date)` 看起來完全正常，而那幾天實際上什麼都沒抓到。
        # 公告日回答「政府有沒有發標」，回答不了「我們有沒有抓到」。
        #
        # 2026-08-26 查 B5 時發現：`pcc_today_scrape`（每 2 小時、預期 12 次/日）
        # 在 08-16~08-17 **連續 48 小時 0 次執行**，而同期 health_check_broadcast
        # 跑了 208 次 ⇒ scheduler 是活的、只有這一支停了。當天 daily 的 RED
        # 是別的步驟，`cron_silent_dormant_check`（門檻 4 小時）沒報而**原因查不出來**。
        # ⇒ 這一條刻意不依賴 cron 機制本身，直接問資料庫。
        #
        # 視窗 2 天、只算平日（週六日政府不發標，實測全部 0 筆）。
        # 鑑別力：對過去 14 天逐日模擬 —— 08-18／08-19 會報（08-17 那個空平日），
        # 其餘 12 天全部 0，**零誤報含所有週末**。
        "sql": "SELECT COUNT(*) FROM generate_series("
               "(CURRENT_DATE - 2)::date, (CURRENT_DATE - 1)::date, '1 day') d "
               "WHERE EXTRACT(dow FROM d) BETWEEN 1 AND 5 "
               "AND NOT EXISTS (SELECT 1 FROM tender_records "
               "WHERE created_at::date = d::date)",
        "level": "RED",
        "max": 0,
        "why_exempt": "週六日政府不發標（實測 created_at：週一至五 780–1939 筆／"
                      "週六日 0 筆）⇒ 只算平日。平日整天 0 筆＝抓取端停了，"
                      "不是業務現實",
    },
    {
        "module": "報價單",
        "what": "線上報價明細有人在用（不是只有總額）",
        # owner 2026-08-26：「報價單已有提供範本，需要如 Google Sheet 線上編輯
        # 報價單機制」—— 而那個編輯器 **08-16 就存在**、範本 08-18 就用上了、
        # 後端 items API 08-17（週一）就完成了。
        #
        # **實際使用量：0 筆 / 256 張報價單。**
        #
        # 它掛在 ERP 側（`/erp/quotations/:id`），而使用者的動線是從案件出發，
        # `/pm/cases/:id` 的分頁顯示的是附件面板 ⇒ **能力存在、範本存在、
        # 入口不存在**，而三支既有檢核的座標系裡都沒有這一個維度：
        #   dead_ui_detector      判「後端有端點、前端沒常數」→ 常數有、元件有
        #   capability_usage_audit 只看 Agent 工具與 KG 實體
        #   本檔                   最接近，但先前沒有這一條
        #
        # ⇒ 判準刻意是「**有沒有人用**」而不是「程式在不在」：
        #    程式在不在用 grep 就查得到，而那正是我這一輪連續誤判三次的原因。
        #
        # ⚠️ 首次接通後會需要一段時間累積，所以判 YELLOW 不判 RED ——
        #    零使用是「還沒有人用」不是「壞了」。
        "sql": "SELECT COUNT(*) FROM erp_quotation_items",
        "level": "YELLOW",
        "min": 1,
        "why_exempt": "報價明細是使用者逐案填的，不是系統產生 ⇒ 零使用代表"
                      "入口不通或還沒開始用，兩者都要有人看見，但都不是故障",
    },
    {
        "module": "專案資金",
        "what": "執行中且有合約金額的案子，有在走金流",
        # owner 2026-08-26：「以利掌握公司專案資金管理」。
        #
        # 2026-08-27 量測：88 個承攬專案裡 **37 個（42%）完全沒有任何
        # 請款或應付紀錄**。拆開之後兩群完全不同：
        #   已結案 28 案 → 合約金額**全部是 0**（2025-03~05 舊資料，未填）
        #   執行中  9 案 → 合約金額合計 **$11,555,000**  ← 這一群才是問題
        #
        # 「執行中、有合約金額、卻沒有任何金流」＝ **錢該收而系統裡沒有紀錄**。
        # 那不是系統故障，是**沒有任何東西在問這個問題** ——
        # 帳本層實測完全健康（已收款 38→帳本 0 缺、已付 33→0 缺、孤兒 0），
        # 而健康的帳本回答不了「該進帳本的有沒有進來」。
        #
        # ⚠️ 條件加上「合約金額 > 0」：沒填金額的可能是還沒簽約，
        # 把它們算進來會讓這條每天報一個不能行動的數字。
        #
        # ⚠️ 關聯要走三跳：請款與應付掛在**報價單**（只有 erp_quotation_id），
        # 不是掛在專案 ⇒ project_code → case_code → quotation_id。
        "sql": """
            SELECT COUNT(*) FROM contract_projects p
             WHERE p.status = '執行中'
               AND COALESCE(p.contract_amount, 0) > 0
               AND NOT EXISTS (SELECT 1 FROM erp_billings b
                                 JOIN erp_quotations q ON q.id = b.erp_quotation_id
                                WHERE q.case_code = p.case_code)
               AND NOT EXISTS (SELECT 1 FROM erp_vendor_payables v
                                 JOIN erp_quotations q ON q.id = v.erp_quotation_id
                                WHERE q.case_code = p.case_code)
        """,
        "level": "YELLOW",
        "max": 0,
        "why_exempt": "這是業務推進不是系統故障（可能還沒到請款時點）⇒ 判 YELLOW。"
                      "但它必須每天出現在畫面上，因為沒有人在問這個問題",
    },
    {
        "module": "請款收款",
        "what": "已收款的請款都進了統一帳本",
        "sql": "SELECT count(*) FROM erp_billings b WHERE b.payment_status='paid' "
               "AND COALESCE(b.payment_amount,0) > 0 "
               "AND NOT EXISTS (SELECT 1 FROM finance_ledgers l "
               "WHERE l.source_type IN ('erp_billing','billing') AND l.source_id=b.id)",
        "level": "RED",
        "max": 0,
        "why_exempt": None,   # 沒有豁免：已收款卻沒入帳就是漏帳
    },
    {
        "module": "應付付款",
        "what": "應付有在推進到已付",
        "sql": "SELECT count(*) FROM erp_vendor_payables WHERE payment_status = 'paid'",
        "level": "YELLOW",
        "why_exempt": "沒有人標記已付是流程問題不是系統問題 —— "
                      "但它讓帳本缺了一整面（實測 37 筆停在 unpaid、最舊 151 天）",
    },
    {
        "module": "核銷",
        "what": "有核銷單走完審核",
        "sql": "SELECT count(*) FROM expense_invoices WHERE status = 'verified'",
        "level": "YELLOW",
        "why_exempt": "同上，是人的推進不是系統故障",
    },
    {
        # 2026-08-17：owner 的核心目標是「毛利、核銷、報帳便利性」，
        # 而八條生命跡象裡**沒有一條在問毛利**。
        #
        # 這一條問的不是「毛利多少」（那是業務數字不是生命跡象），
        # 是「**執行中的案子有幾個算得出毛利**」——
        # 算不出來的原因永遠是同一個：沒有總價、或沒有估列成本。
        #
        # ⚠️ 只看**執行中**：實測 78 張報價裡 40 張算得出毛利（51%），
        # 但那 38 張算不出來的多數是已結案的歷史補登。
        # 把歷史案件算進分母，這個數字永遠不會變好，而它變不好就沒有人會看。
        "module": "毛利可算",
        "what": "執行中案件算得出毛利（成本取估列**或**應付／核銷／帳本實際發生）",
        # ⚠️⚠️ 2026-08-17 **當日改過一次判準，因為第一版結構上永遠是 0%**。
        #
        # 第一版問「有總價 **且** 有估列成本四欄」，並把分母限縮到 `category='02'`。
        # 實測揭露兩層問題：
        #
        # ① **分母只有 1 張**。n=1 的百分比只有 0 或 100，沒有級距，
        #    而它印出「0%（下限 50%）」看起來像一個比例。
        #    這正是 BLIND_SPOT_STRATEGY §4.1 五個問句之一：「這個數字的分母是什麼」。
        #
        # ② **估列成本四欄自系統上線後從來沒有人填過一次**。
        #    有值的 40 張報價**全部**是 2026-03-17 一次性 xlsx 匯入
        #    （已結案 64 張中 40 張有、執行中 13 張中 0 張有）——
        #    也就是成本不是「還沒填」，是**這個組織不在執行中填它**。
        #    以它當判準 ⇒ 永遠 0% ⇒ 正是我在下面那行註解寫的
        #    「一上線就紅的檢核活不過兩週」，而我自己訂了一個。
        #    同 L82：「還沒到門檻」與「永遠到不了」在畫面上長得一樣。
        #
        # 改法＝**問一個實務上答得出來的問題**。毛利要的是總價與成本，
        # 而成本除了估列，還有三個他們本來就會填的來源：
        #   · 應付（給廠商的錢，`erp_vendor_payables`）
        #   · 核銷（`expense_invoices`）
        #   · 帳本已入帳支出（`finance_ledgers.entry_type='expense'`）
        # 這三者是**已發生**的成本，執行中案件用它算出的是「目前為止的毛利」——
        # 對進行中的案子而言那比估列更有意義，且**零額外填報**
        # （對上 owner 記錄過的限制：填報成本高）。
        #
        # 因此也**不再限縮 category='02'**：估列成本標案填不了（owner 說的），
        # 但應付與核銷兩類都有 —— 實測執行中 12 張標案裡 3 張已經有。
        # 排除標案等於讓毛利只監控 1/13 的案子，而毛利是 owner 的核心目標。
        "sql": """
            SELECT CASE WHEN count(*) = 0 THEN 100
                   ELSE (100 * count(*) FILTER (
                       WHERE q.total_price > 0
                         AND (
                              COALESCE(q.outsourcing_fee,0) + COALESCE(q.personnel_fee,0)
                            + COALESCE(q.overhead_fee,0)   + COALESCE(q.other_cost,0) > 0
                           OR EXISTS (SELECT 1 FROM erp_vendor_payables vp
                                       WHERE vp.erp_quotation_id = q.id)
                           OR EXISTS (SELECT 1 FROM expense_invoices e
                                       WHERE e.case_code = q.case_code)
                           OR EXISTS (SELECT 1 FROM finance_ledgers l
                                       WHERE l.case_code = q.case_code
                                         AND l.entry_type = 'expense')
                         )
                   ) / count(*))::int END
            FROM erp_quotations q
            JOIN contract_projects p ON p.case_code = q.case_code
            WHERE p.status <> '已結案'
        """,
        "level": "YELLOW",
        # 門檻 20%：實測現況 3/13 = 23%，訂在剛好之下。
        # **刻意不訂 50%** —— 那是第一版的數字，而第一版的分母是 1；
        # 現在分母 13、真實水位 23%，訂 50 就是再造一個「永遠到不了」。
        # 這條要看的是趨勢往哪走：新案有應付或核銷就會往上，
        # 只建報價不記成本就會往下。
        "min": 20,
        "unit": "%",
        "why_exempt": "填報缺口不是系統故障 —— 誰該補由 filing_gap 分派到人，"
                      "這裡只看整體有沒有在往好的方向走",
    },
    {
        "module": "知識圖譜",
        "what": "**關係**有在長大（不是實體）",
        "sql": "SELECT COALESCE(EXTRACT(day FROM NOW() - MAX(extracted_at))::int, 9999) "
               "FROM entity_relations",
        "level": "YELLOW",
        "max": 7,
        "why_exempt": "實體 49,688 一直長而關係近 7 日只新增 18 —— "
                      "看實體會以為圖譜很健康，實際它正在退化成一張清單",
    },
    {
        "module": "學習閉環",
        "what": "有新的 pattern 進來（後段 proposal/crystal 由 owner 人審）",
        "sql": None,   # 檔案型，見 _count_recent_files
        "path": "wiki/memory/patterns",
        "days": 14,
        "level": "YELLOW",
        "why_exempt": "proposal/crystal 需 owner 核准，掛零不必然是故障；"
                      "但 pattern 若也停了，代表輸入端斷了",
    },
]


def _psql(sql: str) -> str | None:
    """host 借道 docker exec；容器內走直連。兩條都不通回 None（不猜）。"""
    import subprocess
    try:
        out = subprocess.run(
            ["docker", "exec", "ck_missive_postgres", "psql", "-U", "ck_user",
             "-d", "ck_documents", "-tA", "-c", sql],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _dsn() -> str:
    return (f"host={os.getenv('POSTGRES_HOST') or os.getenv('PGHOST') or 'localhost'} "
            f"port={os.getenv('POSTGRES_PORT') or os.getenv('PGPORT') or '5434'} "
            f"dbname={os.getenv('POSTGRES_DB') or 'ck_documents'} "
            f"user={os.getenv('POSTGRES_USER') or 'ck_user'} "
            f"password={os.getenv('POSTGRES_PASSWORD') or os.getenv('PGPASSWORD') or ''}")


def _count_recent_files(path: str, days: int) -> int | None:
    from pathlib import Path
    import time
    for base in (Path(__file__).resolve().parents[2], Path("/app")):
        d = base / path
        if d.is_dir():
            cutoff = time.time() - days * 86400
            return sum(1 for f in d.glob("*.md") if f.stat().st_mtime > cutoff)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--enforce", action="store_true",
                    help="依判定回非 0（首月刻意不開：新機制上線當下最不該被信任）")
    args = ap.parse_args()

    print("=" * 74)
    print(f"{len(VITALS)} 條生命跡象（{len({x['module'] for x in VITALS})} 個模組）"
          f" —— 這個模組今天活著嗎")
    print("=" * 74)

    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(_dsn())
    except Exception:
        if _psql("SELECT 1") is None:
            print("\n✗ 直連與 docker exec 都不通 —— 無法判定（不視為通過）")
            return 2

    def num(sql: str) -> int | None:
        try:
            if conn is not None:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    return int(cur.fetchone()[0])
            v = _psql(sql)
            return int(v) if v not in (None, "") else None
        except Exception:
            return None

    red, yellow, unknown = [], [], []
    print()
    for v in VITALS:
        n = (_count_recent_files(v["path"], v["days"])
             if v["sql"] is None else num(v["sql"]))
        mod, level = v["module"], v["level"]

        if n is None:
            unknown.append(mod)
            print(f"  ⚪ {mod:<8} 查不到 —— 不當成通過（{v['what']}）")
            continue

        # 判定：有 max 比上限、有 min 比下限，其餘要求 > 0
        #
        # ⚠️ 2026-08-17：`min` 是這天才加的。在此之前我寫了一條帶 `min` 的
        # 生命跡象，而**腳本根本不認得它** —— 那條會靜靜退化成
        # 「只要不是 0 就通過」，等於一條永遠綠的檢核。
        # 這正是本輪反覆記錄的「寫了等於沒寫」：設定裡多一個鍵不會有人報錯。
        unit = v.get("unit", "")
        if "max" in v:
            bad = n > v["max"]
            shown = f"{n}{unit}（上限 {v['max']}{unit}）"
        elif "min" in v:
            bad = n < v["min"]
            shown = f"{n}{unit}（下限 {v['min']}{unit}）"
        else:
            bad = n == 0
            shown = f"{n}{unit}"

        if bad and v.get("weekend_ok") and IS_WEEKEND:
            print(f"  🟢 {mod:<8} {shown} —— 週末合理（{v['why_exempt']}）")
            continue

        if bad:
            (red if level == "RED" else yellow).append(f"{mod}：{v['what']}（實測 {shown}）")
            print(f"  {'🔴' if level == 'RED' else '🟡'} {mod:<8} {shown} —— {v['what']}")
            if v.get("why_exempt"):
                print(f"       └ {v['why_exempt']}")
        else:
            print(f"  🟢 {mod:<8} {shown} —— {v['what']}")

    if conn is not None:
        conn.close()

    print()
    if unknown:
        print(f"⚪ 查不到 {len(unknown)} 條：{'、'.join(unknown)}")
        print("   查不到不是通過 —— 判準本身可能寫錯了表名或欄位。")
    if red:
        print(f"\nStatus: [RED] {len(red)} 個模組的業務結果停了")
        for r in red:
            print(f"  · {r}")
    elif yellow:
        print(f"\nStatus: [YELLOW] {len(yellow)} 個模組需要人推進")
        for y in yellow:
            print(f"  · {y}")
        print("\n  這些不是系統故障，是流程沒有走完 —— 判 YELLOW 不判 RED。")
    else:
        print(f"Status: [GREEN] {len({x['module'] for x in VITALS})} 個模組今天都活著")

    if not args.enforce:
        print("\n（觀測模式：首月不告警。新機制上線當下最不該被信任 ——")
        print("  §3 可信度表 #15–#17、#19、#21 全是我自己新加的檢核造成的假訊號。）")
        return 0
    return 2 if red or unknown else (1 if yellow else 0)


if __name__ == "__main__":
    sys.exit(main())
