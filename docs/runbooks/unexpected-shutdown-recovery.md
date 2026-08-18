# 異常關機後的復原檢查（Unexpected Shutdown Recovery）

> 建立：2026-08-12（觸發事件：本機凌晨異常關機，cron 事件 02:52 斷至 05:43）
> 更新：2026-08-18（下午 15:36 斷電，16:13 恢復 —— 新增 §0「恢復窗口」與 §5 停用排程）
> 適用：**非計畫性**的關機／斷電／休眠卡死。計畫性重啟走 `reboot-acceptance-checklist.md`。

## §0 先等 20 分鐘再查 —— 恢復窗口內量到的東西不能當證據

⚠️ **這一節放在最前面，是因為它會讓你去追一個不存在的問題。**

2026-08-18 開機後約 17 分鐘（16:30）量測，得到：

```
CK-Missive-Offsite-Backup        | State=Disabled | Settings.Enabled=False
CK_lvrland_Webmap-Offsite-Backup | State=Disabled | Settings.Enabled=False
CK_DigitalTunnel-MinIO-Offsite   | State=Disabled | Settings.Enabled=False
CK_PileMgmt_PM2_Autostart        | State=Disabled | Settings.Enabled=False
```

**三個異地備份同時被停用**看起來像重大事故（而當天 15:26 的 pre-flight 白紙黑字
記著「27 支全部 Ready」，兩相對照更像是斷電把它們弄壞了）。

20 分鐘後（16:49）重新量測 —— **四支全部是 `Ready` / `Enabled=True`，我沒有做任何啟用操作**。

同一個窗口還產生了第二個假訊號：`CK_lvrland_Webmap/docs/health/static-checks.json`
在 **16:25**（開機後 12 分）被寫成 `state: RED, fail: 1`，而同一支檢核重跑
是 **23 步全 PASS / OVERALL=GREEN / exit 0**。

### 規則

| 開機後經過 | 可以相信什麼 |
|---|---|
| < 20 分鐘 | **只相信「服務在不在」**（容器 status、公網 200、`/health` 業務量）。排程狀態、檢核結果檔一律不採信 |
| > 20 分鐘 | 全部重量一次，**以第二次為準** |

判準是「同一件事量兩次，兩次一致才算數」——這比訂一個精確的等待秒數可靠，
因為 Task Scheduler 服務重建的時間不是固定的。

**任何在恢復窗口內產生的結果檔都要重跑覆蓋**，否則它會一直紅著，而下游
（例如 `windows_task_liveness_audit` 會去讀別的 repo 的結果檔）會照著它報 RED，
於是一個早就消失的問題被持續當成現存問題。

## 為什麼需要這一份

計畫性重啟有 pre-flight，異常關機沒有。而異常關機真正的傷害不是「服務沒起來」——
Docker 的 `unless-stopped` 會把容器全部拉回來，公網也會恢復 200，**表面上什麼事都沒有**。

真正的傷害是**那段停機時間內到期的排程，整批沒跑，而且不會自己補**：

| 層級 | 關機時的行為 | 會不會自己補跑 |
|---|---|---|
| Windows 排程 | 到期時機器是關的 → 跳過 | **不會**。`StartWhenAvailable=True` 也不會（2026-08-12 實測） |
| 容器內 APScheduler | 錯過超過 `misfire_grace_time`（多數為 7200s／2h）→ 跳過 | **不會**，且 `cron_events` 連一筆紀錄都沒有 |

其中**異地備份漏跑一天，等於那一天的資料只有一份**——這是唯一不可逆的一項。

## 復原步驟

### 1. 先量出停機窗口（不要靠記憶）

```bash
# 容器啟動時間（RestartCount=0 代表是重新拉起，不是原地重啟）
docker inspect ck_missive_backend --format '{{.State.StartedAt}} restart={{.RestartCount}}'

# cron 事件的斷層——這是最精確的窗口證據
docker exec ck_missive_backend sh -c \
  "grep -oE '\"ts\": \"$(date +%Y-%m-%d)T[0-9]{2}' /app/logs/cron_events.jsonl | sed 's/.*T//' | uniq -c"
```

缺哪幾個小時，那幾個小時到期的排程就是嫌疑名單。

### 2. 讓稽核指出漏跑的是哪幾支

```bash
python scripts/checks/windows_task_liveness_audit.py     # 「應於 MM-DD HH:MM 執行卻沒跑，也沒有補跑」
python scripts/checks/offsite_backup_completeness_audit.py  # 四類異地備份缺一不可
python scripts/checks/producer_output_watchdog.py        # 產出 stale（門檻 30h，比排程層晚一天才紅）
```

### 3. 按後果分級補跑 —— 不是全部都要立刻補

| 優先 | 排程 | 理由 |
|---|---|---|
| **立刻** | `CK-Missive-Offsite-Backup`、`CK_DigitalTunnel-MinIO-Offsite`、`CK_PileMgmt_DB_Backup` | 漏一天＝那天的資料只有一份，不可逆 |
| 當日 | 各 repo 的 `*-SelfAudit-Flow` / `*-SelfAudit-Sweep` | 少一天的頁面健康資料；也順便確認關機沒弄壞什麼 |
| 可等 | `*-StaticChecks`、`*-CapabilityUsage`、容器內的分析類 job | 隔天自己會跑，補跑只是讓數列不缺格 |

```powershell
Start-ScheduledTask -TaskName 'CK-Missive-Offsite-Backup'
# 確認真的跑完且成功（State 會先是 Running）
$t = Get-ScheduledTask -TaskName 'CK-Missive-Offsite-Backup'
"$($t.State) / $(($t | Get-ScheduledTaskInfo).LastTaskResult)"   # 要 Ready / 0
```

⚠️ **DB dump 本身通常還在**：它由容器內排程於 **02:00** 產生，多半早於關機時點。
先看 `backups/database/` 有沒有當天的檔——有的話缺的只是 03:00 的 NAS 同步，補跑同步即可。

⚠️ **補跑要一支一支來，不要一次全部啟動。** 2026-08-12 我同時觸發 7 支，
lvrland 的靜態檢核第 14 步「併發下事件迴圈阻塞」因此 FAIL —— 那是**量測到我自己
造成的機器負載**。單獨重跑立刻 GREEN。漏跑的排程本來就沒有時間壓力，
而一個假 RED 要花掉的追查時間遠比分開跑多（同 08-03「檢核執行期間不要並行 rebuild」）。

### 4. 確認資料層沒有殘留損傷

```bash
curl -s https://missive.cksurvey.tw/health | python -c "import sys,json;print(json.load(sys.stdin)['business_data'])"
docker ps --filter health=unhealthy --format '{{.Names}}'   # 應為空
python scripts/checks/db_transaction_health_check.py        # 中止未 rollback 的交易
```

## 已知限制（不要以為設定好了就沒事）

- **`StartWhenAvailable=True` 不保證補跑。** 2026-08-12 實測：12 支全部設了 True，
  到當日 10:30 一支都沒補跑，`NextRunTime` 直接跳過當天。這個設定只代表
  「沒有把補跑的可能性關掉」，不代表它會發生（L84 家族、詳見 L90）。
- **容器內 APScheduler 漏跑不留任何紀錄。** 不是 failure，是事件根本不存在——
  所以要靠「該有的沒有」來推，不能等它報錯（這正是 `cron_silent_dormant_check`
  改用持久紀錄補判的原因）。
- **排程層的漏跑比產出層早一天可見**：`producer_output_watchdog` 的門檻多為 30h，
  每日產出漏一次要隔天才紅；`windows_task_liveness_audit` 當天就看得出來。
