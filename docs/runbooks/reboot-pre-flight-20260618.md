# 重啟 Pre-Flight 與驗收 — 2026-06-18

> 觸發：整體覆盤後完善（每日巡檢 LINE 中文化 + 治理 metric 完整性 + SSO 護欄 + CK_Website 跨專案拓樸閉環）後準備重啟電腦。
> 體例沿用 `reboot-pre-flight-20260617.md`。

---

## A. Pre-Flight（重啟前，已全數通過 ✅）

| # | 檢查 | 結果 |
|---|---|---|
| 1 | git 已 commit/push（無遺失風險） | ✅ `main` ahead/behind origin **0/0**；尾段 `bbdc91e6`(LINE中文化)→`7a21b4c7`(§9.5誠實化)→`c8e6b5f4`(SSO護欄)→`ca8f3d34`(diary) |
| 2 | 容器全 healthy | ✅ backend/frontend/postgres/redis/cloudflared 全 Up healthy |
| 3 | **backend image 為含修法版（今日 rebuild）** | ✅ rebuilt 2026-06-17 23:13（每日巡檢 LINE 中文化 + overall 誤標 INFO 修；L76 驗證 host/公網 200 已通過） |
| 4 | frontend dist 一致 | ✅ 本輪**無 prod 前端變更**（僅新增 SSO 元件測試檔，不入 dist）；dist 同 06-17 |
| 5 | **DB volume 正確（L43）** | ✅ postgres mount = `ck_missive_postgres_dev_data`（非空殼） |
| 6 | 業務量在位（healthcheck 依此） | ✅ **1,858 docs / 28,010 KG**、db connected、ok=true |
| 7 | alembic head 一致 | ✅ `20260617a001`（無待跑遷移；本輪未動 schema） |
| 8 | L76 公網關卡 | ✅ host→8001=200、公網 `/api/health`=200 |

### 重啟會「自動生效」的待生效項
- backend 新 image（含 LINE 中文化）+ frontend dist 已在運行/serve；重啟後 Docker `unless-stopped` 自動恢復同版。
- 每日巡檢 LINE 中文推播於下次 **03:00** cron 即以中文/分區（需處理｜注意｜已知限制）格式推給管理端。
- L73 非 clobber：02:30 容器內 dashboard regen 不再洗白 §3/§4（保留前次 host 值）。

### 工作樹殘留（無害、可再生、不阻斷重啟）
- `wiki/memory`（diary/patterns/integration-health/pipeline-reports/self-retrospective）、`wiki/SOUL.md`、`GOVERNANCE_INTEGRATED_DASHBOARD.md`：cron 每日/每週自動再生副產物，重啟後 cron 重建，無資料遺失風險。

---

## B. 重啟後驗收（開機後執行）

```bash
# 1) 容器自動恢復
docker ps --format '{{.Names}} {{.Status}}' | grep missive   # 5 容器 healthy

# 2) DB volume 仍為 dev_data + 業務量在位（L43 防空殼）
docker inspect ck_missive_postgres --format '{{range .Mounts}}{{.Name}}{{end}}' | grep dev_data
curl -s localhost:8001/health | python -c "import sys,json;d=json.load(sys.stdin)['business_data'];print('docs',d['documents'],'KG',d['canonical_entities'])"  # ≈1858 / 28010

# 3) ★L76 關卡：host→8001 + 公網（容器內 health≠公網可達；殭屍埠轉發風險）
curl -s -o /dev/null -w "host8001=%{http_code}\n" http://localhost:8001/health      # 必 200
curl -s -o /dev/null -w "public=%{http_code}\n" https://missive.cksurvey.tw/api/health  # 必 200
#   若 public 502 而容器 healthy → docker restart ck_missive_backend（L76 殭屍埠轉發修）

# 4) alembic head
docker exec ck_missive_backend sh -c 'cd /app && alembic current'   # 20260617a001

# 5) 每日巡檢中文推播渲染自檢（部署後程式碼）
docker exec ck_missive_backend sh -c 'cd /app && python -c "import json;from app.services.optimization_pipeline_orchestrator import format_line_digest,display_overall_zh;import glob;f=sorted(glob.glob(\"/app/wiki/memory/pipeline-reports/*.json\"))[-1];r=json.load(open(f,encoding=\"utf-8\"));print(display_overall_zh(r))"'  # 應印中文整體狀態
```

### ⚠️ 重啟後需 owner 親驗（不可代行）
- **SSO+reload 端到端**：`www.cksurvey.tw` → `missive.cksurvey.tw` 應第一次就穩定落 dashboard、不停 entry（L74 治本最終驗收；前端宣告式導向已加元件護欄）。
- **每日巡檢 LINE**：下次 03:00 應收到中文「系統每日巡檢｜整體：…」分區訊息（取代英文 `[Pipeline INFO]`）。
- **DR drill #4**：第二裝置登入測試（CK_Website 提；Missive 側 session/SSO 已就緒，待 owner 執行）。
- **標案 `/tender` UI**：自維面板/卡片週單元/官方直連（v6.20 既有待辦）。

---

## C. 若重啟後異常的回滾錨點
- 後端：image 對應 git HEAD；如需回滾 LINE 中文化/overall 修，`git revert bbdc91e6` + rebuild（走 L76 驗證）。注意 overall 修法同時影響 exit code 與 dashboard §8.5；回滾前確認管理端是否能接受誤標 INFO。
- DB：volume `ck_missive_postgres_dev_data` 為唯一真實資料源；**切勿**指回 `ck_missive_postgres_data`（L43 空殼）。本輪未動 schema。
- 治理生成器：`generate_governance_dashboard.py` 為純 host 工具，回滾不影響 runtime。

---

## D. 本輪重點（2026-06-18，供覆盤）
- **每日巡檢 LINE 中文化 + 修真 bug**：`overall` 計算缺 `info` + 預設 4 → precommit 的 info 蓋過 red，管理端誤見「INFO」（底下其實有紅燈）；改 info 最低優先。中文標籤 + 白話 + 三區（需處理｜注意｜已知限制）；shadow_baseline 僅延遲紅(成功率OK)=本地模型上限歸「無需處理」不誤報。已部署 live（commit `bbdc91e6`）。
- **治理 metric 完整性**：L73 非 clobber（§3/§4 不再每日洗白）+ Hermes baseline #4/#5 標「已接受限制」+ wiki_pages metric 範疇正名（`3e276f0b`）；§9.5 表頭誠實化（週級 job 重啟後缺非中斷，指向 scheduler_liveness_audit）（`7a21b4c7`）。
- **SSO 護欄**：補 EntryPage 公網宣告式導向元件測試（鎖 L74/L66 修法行，2/2 綠）（`c8e6b5f4`）。
- **CK_Website 跨專案閉環**：① missive 拓樸矛盾——docker 實證**純 docker 單 backend**（PM2 無 Missive 進程、host:8001=com.docker.backend→容器、公網 200），舊「PM2 native vs docker 雙 backend」矛盾已根除；cloudflared 為 token tunnel（ingress 在 CF dashboard）。② DR drill #4 需第二裝置登入＝owner-only。
- **查證更正（誠實記）**：週自傳（weekly_evolution/memory_weekly_autobiography）與其他 cron 推播**早已納管/中文**，先前「盲區/待做」判斷有誤已更正，只做真正缺的小修。
- **lessons 沿用**：L73(in-container writer 盲視)、L74(SSO bootstrap 競態)、L76(Windows 殭屍埠轉發)。
