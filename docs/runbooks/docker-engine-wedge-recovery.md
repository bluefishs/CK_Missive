# Runbook：Docker Engine 運行中卡死 → 公網 1033 復原

> **建立**：2026-06-25（觸發事件：公網 Cloudflare Tunnel Error 1033）
> **適用症狀**：公網回 `Error 1033 Cloudflare Tunnel error`，且本機 Docker 指令異常
> **與 L76 區別**：L76 是「後端容器健康但 host→8001 殭屍埠不通」（502）；本案是「整個 Docker engine 卡死、容器全停」（1033）

---

## 症狀指紋

1. 公網 `missive.cksurvey.tw` → **Error 1033**（Cloudflare Tunnel error＝cloudflared 連線中斷）
2. `docker ps` / `docker ps -a` 回空、卡住、或回 **500 Internal Server Error**
3. PowerShell `docker ps -a` 明確報：`request returned 500 Internal Server Error for ... dockerDesktopLinuxEngine`
4. **機器未必剛重啟**——engine 可能執行中崩壞（檢查 `(Get-CimInstance Win32_OperatingSystem).LastBootUpTime` 與容器 StartedAt 對照）

> 核心判讀：cloudflared 容器沒在跑 → tunnel 無 active 連線 → 1033。而 cloudflared 沒跑是因為 **Docker engine 整個卡死**，不是 cloudflared 本身的問題。

---

## 快速診斷（依序，每步加 timeout 避免 hang）

```powershell
# 1. engine 是否回應（500 = 卡死）
docker ps -a 2>&1 | Select-Object -First 5
docker context ls          # 確認用 desktop-linux context

# 2. WSL / Docker Desktop 進程
wsl --list --verbose       # 通常只有 docker-desktop 一個 distro
Get-Process -Name "Docker Desktop","com.docker.backend" | Select Name,Id,StartTime
(Get-CimInstance Win32_OperatingSystem).LastBootUpTime   # 是否剛重啟
```

```bash
# host backend 是否可達（若 engine 死，這也會失敗）
curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 http://localhost:8001/api/health
```

---

## 修復步驟（本案實證有效，2026-06-25）

### Step 1 — 先試官方 CLI 重啟引擎
```powershell
docker desktop restart
```

### Step 2 — 若 restart 失敗「processes still running: docker-mcp.exe ... context deadline exceeded」
這是**本案真因**：`docker-mcp.exe`（MCP Docker CLI 外掛）進程掛住，擋住 Docker Desktop 正常停止，導致 restart 停了 engine 卻沒能重啟（pipe `dockerDesktopLinuxEngine` 消失＝engine 停在半死）。

```powershell
# 2a. 強制結束卡住的 docker-mcp（安全：只是 CLI 外掛 helper，非 engine/資料）
Get-Process -Name "docker-mcp" -ErrorAction SilentlyContinue | Stop-Process -Force

# 2b. 重新啟動 Docker Desktop（此時 engine 已停，用 start 非 restart）
docker desktop start
```

### Step 3 — 等待容器自動恢復（`unless-stopped` 政策）
```bash
# 輪詢等容器回來（勿用裸 sleep；until-loop）
for i in $(seq 1 48); do
  out=$(timeout 10 docker ps --format "{{.Names}}|{{.Status}}" 2>/dev/null)
  echo "$out" | grep -q ck_missive_backend && { echo "UP after ~$((i*5))s"; echo "$out"; break; }
  sleep 5
done
```

### Step 4 — 驗證（L76 + 業務量，缺一不可）
```bash
curl -s -o /dev/null -w "host:8001=%{http_code}\n" --max-time 6 http://localhost:8001/api/health
curl -s -o /dev/null -w "公網=%{http_code}\n" --max-time 15 https://missive.cksurvey.tw/api/health
curl -s --max-time 10 http://localhost:8001/health | head -c 300   # business_data.ok=true + documents/canonical_entities 數量正常
```
- host 200 + 公網 200 + `business_data.ok=true`（documents > 100、KG > 1000）= 真復原
- 若 host 200 但公網仍 502 → 轉 **L76**（`docker restart ck_missive_backend` 解殭屍埠）

---

## 若 Step 2 仍無效 → 升級（CKProject 既有程序）
`wsl --shutdown` 後再 `docker desktop start`（本機只有 docker-desktop 一個 distro，無其他 WSL 工作會被波及）。再不行＝Docker Desktop 應用層問題，需 GUI 重啟或重裝。
> 重啟後若 GPU 容器（ck-ollama，屬 CK_Hermes/AaaP）起不來，另見 CKProject CLAUDE.md「NVIDIA Container Toolkit prestart hook 崩潰」＝`wsl --shutdown` 重啟 Docker 引擎。

---

## 預防 / 後續

- **docker-mcp.exe 是常見阻擋源**：Docker Desktop 的 MCP Toolkit 外掛；若反覆卡死可考慮在 Docker Desktop 設定停用 MCP Toolkit，或重啟前先 kill docker-mcp。
- 本案 engine 自 06-22 開機後運行中崩壞（非重啟觸發），根因未完全定位（疑 WSL2 backend 資源壓力 / dockerd 內部 hang）；若高頻復發，蒐集 Docker Desktop 診斷（`Troubleshoot → Get support`）。
- 復原後 LINE 額度分配閘門等後端碼隨同一 image 存活，無需重新部署。
