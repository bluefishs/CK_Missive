# 重啟前狀態固定與復原指引 — 2026-09-09 晚（v6.76 晚間基線）

> `lifecycle: status=current reviewed=2026-09-09 owner=CK_Missive`
>
> 用途：**今晚的重啟不是例行重啟，是主機層記憶體故障（A127）的實驗**。
> 重啟後要能分辨三種東西：本來就有的／重啟造成的／實驗改變的。
> 09-08 那份（`reboot-pre-flight-20260908.md`）的通用檢查照用；本檔只寫今晚特有的。

## 0. 今天主機層發生了什麼（給做決定的人）

| 時間 | 事實（誰量的） |
|---|---|
| 12:04 | 主動重啟（事件 1074）；開機後 8 分鐘內 6 次段錯誤，swap 一位元組沒用（CK_Website） |
| 12:12–14:47 | 安靜 2h35m |
| 14:47–15:58 | 12 次段錯誤，五個容器四個 repo（lvrland 重啟 5、tunnel exporter 5、missive 4、hermes ×2）（CK_Website 全量 dmesg） |
| 15:58:58 | 公網 502 約半分鐘（本 repo 視覺走查拍到） |
| 16:0x–16:44 | dmesg 18 → 46；missive RestartCount 4 → 11（本 repo） |
| 16:40–16:55 | **應用層放大**：容器被拉回後 mapper 懶配置競態毒化 ⇒ 每個 ORM 請求 500（含 Google 登入）15 分鐘（本 repo，已修 `2ccfe1d5`） |
| 16:44–17:05 | 安靜 21 分鐘（dmesg 仍 46） |

結論不變：**與程式無關、與記憶體壓力無關**（swap 未用即發作）。候選＝RAM 硬體／08-12 Windows 累積更新。

## 1. 重啟前必做（owner）

```
# ① 推送（本機 32 個 commit 未推送；重啟後若磁碟／WSL 出事就沒了）
git push origin main

# ② 確認線上＝HEAD（1p 部署完成後 build 欄應為 2ccfe1d5，不是 -dirty）
curl -s http://localhost:8001/api/health/detailed | python -c "import sys,json;print(json.load(sys.stdin)['build'])"

# ③ 固定證據（dmesg 全文與艦隊重啟數，重啟就沒了）
docker run --rm --privileged alpine dmesg > docs/health/kernel/dmesg_20260909_evening_pre_reboot.txt
docker ps -a --format '{{.Names}} {{.Status}}' > docs/health/kernel/containers_20260909_evening.txt
```

## 2. 今晚的實驗（二選一，不要同時做——同時做就無法歸因）

### 選項 A：mdsched **Extended**（整夜，電腦不能用）
```
mdsched.exe   → 選「立即重新啟動並檢查問題」→ 開機測試畫面按 F1 → Test mix: Extended, Pass count: 2
```
結果在事件檢視器 `MemoryDiagnostics-Results`（事件 1201 乾淨／1102 有錯）。
⚠️ 09-08 21:27 跑過一次 **Standard** 乾淨——Standard 不足以排除（弱否定）。

### 選項 B：08-12 累積更新回退對照
```powershell
Get-HotFix | Where-Object HotFixID -in 'KB5121003','KB5120708','KB5123304'
wusa /uninstall /kb:5121003 /quiet /norestart   # 三筆依序，最後一筆才重啟
```
⚠️ 回退後**至少觀察 4 小時**（已知最長安靜期 3.51 h，今天最長 2h35m）才能說「有差」；
少於 4 小時的安靜不構成證據。回退對照只在 A 乾淨之後做才有歸因力（CK_Website P2-4）。

## 3. 重啟後檢查（依序；前五步同 09-08 §2）

```bash
docker ps --format "{{.Names}}\t{{.Status}}"                     # Missive 5 個 Up
curl -s http://localhost:8001/api/health/detailed | python -c "import sys,json;d=json.load(sys.stdin);print(d['build'])"   # 2ccfe1d5
for i in 1 2 3; do curl -s -o /dev/null -w "%{http_code} " https://missive.cksurvey.tw/health; sleep 2; done   # 200 ×3
python scripts/checks/deploy_verify.py                             # GREEN
# ⭐ 今晚新增：mapper 在啟動期配置（沒有這一行＝映像不是 2ccfe1d5）
docker logs ck_missive_backend 2>&1 | grep -c "mappers configured at startup"   # 1
# ⭐ 段錯誤基線歸零，之後每小時看一次（實驗驗收就是看這個數字 4 小時不動）
docker run --rm --privileged alpine sh -c 'dmesg | grep -cE "segfault|general protection"; cut -d. -f1 /proc/uptime'
docker inspect ck_missive_backend --format 'RestartCount={{.RestartCount}}'     # 0
```

## 4. 已知會紅、不是重啟造成的

| 項目 | 狀態 |
|---|---|
| weekly 134 R1 | RED 3 筆（788／793／794 總表發票掛在無日期佔位）＝A135，等 owner 補日期 |
| weekly 133 基線 7 組 | 機關／廠商／專案全域統計等，待 owner 判是否算列表卡片 |
| weekly 132 | 兩處永久豁免（上限／超支要含佔位），GREEN |
| `CKProject_DailyBackup` rc=0xC000013A | 09-08 那次被關機中止，CKProject 層排程 |

## 5. 這次重啟前剛改過、要特別看的

| 改動 | 重啟後怎麼確認 |
|---|---|
| 啟動期 `configure_mappers()`（`2ccfe1d5`） | 上面第 5 步那一行；再打 `POST /api/auth/refresh` 應 401 不是 500 |
| 六個列表頁翻頁修正 | 流程走查 `--only=quotation-pagination` PASS |
| `CaseFilterBar` 四頁 | `/erp/quotations`、`/erp/client-accounts`、`/erp/vendor-accounts`、`/contract-cases` 篩選列都在 |
| 已請款＝有請款日期 | `/erp/client-accounts` 2026：承攬 108,108,873／已請款 40,888,276／已收 11,389,413／應收未收 96,719,460 |
| 部署腳本髒工作樹守門 | `git status` 乾淨時 `deploy-public.sh` 正常起跑；髒時 exit 3 |
