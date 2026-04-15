# CK_Missive 資安事件應變手冊（IR Playbook）

> **建立**：2026-04-15
> **適用**：CK_Missive 主專案
> **前置**：`SECURITY_THREAT_MODEL.md`、`AUTH_FLOW_DIAGRAM.md`、`SECRET_ROTATION_SOP.md`

---

## 0. 通用原則 — 發現事件的 5 分鐘 SOP

```
1. STOP — 不要急著刪除「證據」。截圖 / 存 log。
2. SCOPE — 影響哪些使用者 / 哪些資料 / 公開了多久？
3. CONTAIN — 切斷攻擊面（撤 session、停服務、封 IP、改密碼）。
4. NOTIFY — 通報決策人（ACL 見下）。
5. DOCUMENT — 時間軸、動作、觀察填入事件單。
```

**通報**：
- P0（資料外洩 / 帳號被盜） → 立即 Telegram 通報 admin_chat_id + 同步 email 備忘
- P1（疑似中）→ 當日通報
- P2（預警）→ 日記錄、每週 review

---

## 1. 場景 A：密碼 / Token 洩漏（`.env` 或 git 歷史）

### 偵測訊號
- GitHub / push 通知含 `.env`
- `gitleaks` / truffleHog CI 觸發
- 外部通報

### 立即行動
```bash
# 1. 輪換相關 secret（按 SECRET_ROTATION_SOP.md）
#    必做：POSTGRES_PASSWORD、REDIS_PASSWORD、MCP_SERVICE_TOKEN、
#          CF_TUNNEL_TOKEN、OPENAI/GROQ/HF KEY、TELEGRAM_BOT_TOKEN

# 2. 撤銷所有 session（強制重登）
docker exec -it ck_missive_postgres_dev psql -U postgres -d ck_missive \
  -c "UPDATE sessions SET revoked_at=NOW() WHERE revoked_at IS NULL;"

# 3. 記錄事件
cat >> d:/CKProject/CK_Missive/docs/incidents/$(date +%Y%m%d)-secret-leak.md <<EOF
Time: $(date -Iseconds)
Leaked: <欄位>
Rotated: yes at <ts>
Sessions revoked: yes
EOF
```

### 7 天內
- Git 歷史清理決策：`git filter-repo` / BFG + force-push（**破壞性**，須所有人 re-clone）
- 審計所有使用該 secret 的 log，確認無異常用量

### 預防
- `scripts/hooks/pre-commit-secret-guard.sh` 已部署（2026-04-15）
- CI 加 gitleaks（尚未實作，列入 P1）

---

## 2. 場景 B：帳號被盜（單一使用者）

### 偵測訊號
- 使用者自述登入異常
- `login_history` 出現陌生 IP / UA
- MFA 驗證失敗次數飆升
- Audit log 見異常權限操作

### 立即行動
```bash
# 1. 撤銷該使用者所有 session
USER_EMAIL=<email>
docker exec -it ck_missive_postgres_dev psql -U postgres -d ck_missive <<EOF
UPDATE sessions SET revoked_at=NOW()
  WHERE user_id=(SELECT id FROM users WHERE email='$USER_EMAIL');
EOF

# 2. 停用帳號（觀察期）
docker exec -it ck_missive_postgres_dev psql -U postgres -d ck_missive \
  -c "UPDATE users SET is_active=false WHERE email='$USER_EMAIL';"

# 3. 查 login_history
docker exec -it ck_missive_postgres_dev psql -U postgres -d ck_missive \
  -c "SELECT * FROM login_history WHERE user_id=(SELECT id FROM users WHERE email='$USER_EMAIL') ORDER BY id DESC LIMIT 20;"
```

### 驗證 / 復原
- 與使用者確認：改 Google 帳號密碼 + 啟用 MFA
- 確認 MFA 設定（若原無）
- 重新啟用：`UPDATE users SET is_active=true`
- 與使用者溝通此期間任何自身發起動作

### 預防
- 強制 MFA（高權角色至少）
- 登入異常告警（geo / device 變動）
- 失敗鎖定策略（P1）

---

## 3. 場景 C：RCE / 後端被接管

### 偵測訊號
- 未授權 process 啟動
- 反向 shell 連線
- 文件系統異動（`/etc`、`/usr/bin`、`ck-backend` 代碼）
- PM2 出現非本人部署

### 立即行動
```powershell
# 1. 隔離
pm2 stop ck-backend
pm2 stop cloudflared   # 切斷公網
docker stop ck_missive_postgres_dev ck_missive_redis_dev

# 2. 快照
docker commit ck_missive_postgres_dev incident-snapshot-$(date +%Y%m%d)
Copy-Item -Recurse -Path "d:\CKProject\CK_Missive\backend\logs" -Destination "d:\incident-evidence\$(Get-Date -Format yyyyMMdd)"

# 3. 斷網（若擴散風險高）
# 拔網路線 / 關閉主機 Wi-Fi

# 4. 通報
# P0 立即通報
```

### 調查
- 檢視 nginx / uvicorn / pm2 log 時間軸
- `git status` / `git log` 查可疑變更
- Redis / Postgres 資料完整性檢查
- 若確認 RCE：所有 secrets 輪換 + 所有 session 撤銷 + 重建機器

### 復原
- 從乾淨 image 重建（**不是**原容器 restart）
- 資料從離線備份還原
- 事後 post-mortem，公告使用者

---

## 4. 場景 D：資料庫洩漏（pg_dump / 備份檔外流）

### 立即行動
- 輪換 `POSTGRES_PASSWORD`（避免殘留 session）
- 評估洩漏範圍（哪些表、哪些欄位）
- 個資盤點（users.email / phone）
- 法規通報評估（個資法 / GDPR）

### 復原 / 通報
- 通知受影響使用者（個資法要求）
- 建議受影響使用者改 Google 密碼（若 oauth_id 本身也外流）
- 審計備份權限：`/backups` 目錄 + cron 排程

### 預防
- 備份加密（pg_dump | gpg --encrypt）
- 備份異地儲存 + 存取控制

---

## 5. 場景 E：DoS / 流量暴增（含 LLM 成本攻擊）

### 偵測訊號
- CF Analytics 流量尖峰
- Prometheus `http_requests_total` 暴增
- LLM 帳單異常（Groq / OpenAI Dashboard）
- ck-backend CPU 100%

### 立即行動
```bash
# 1. CF Dashboard 啟用 "Under Attack Mode"
#    missive.cksurvey.tw → Security → Under Attack Mode: On

# 2. 臨時封 IP（CF WAF Custom Rule）
#    (ip.src eq <惡意 IP>) → Block

# 3. 收緊 rate limit
#    (http.host eq "missive.cksurvey.tw") → Rate Limit: 100/min

# 4. 若 AI 端點被攻擊
#    PM2 設環境變數 AI_DAILY_QUOTA_OVERRIDE=0 臨時關閉
#    pm2 restart ck-backend
```

### 復原
- CF Analytics 鎖定攻擊來源 ASN
- 解除 Under Attack Mode（正常流量恢復後）
- 審視是否需更強 rate limit 永久生效

---

## 6. 場景 F：CF Tunnel / 公網連線失效

### 偵測訊號
- `curl https://missive.cksurvey.tw/api/health` 逾時
- Telegram webhook 持續失敗
- CF Dashboard tunnel 狀態 Red

### 立即行動
```bash
# 1. 診斷
pm2 logs cloudflared --lines 30
cloudflared tunnel info ck-missive

# 2. 重啟
pm2 restart cloudflared

# 3. 若無效 → 重建 tunnel（token 可能過期或被撤）
#    CF Dashboard → Networks → Tunnels → Delete → Create
#    新 token 寫入 .env → pm2 reload ecosystem.config.js

# 4. 過渡方案：ngrok 快速架公網入口（dev 用）
ngrok http 8001
# Webhook 暫時指向 ngrok URL
```

### 復原後
- 確認 webhook 已切回 cksurvey.tw
- 檢查 CF Dashboard 路由設定無誤

---

## 7. 通訊錄（決策 ACL）

| 角色 | 聯絡方式 | 負責 |
|---|---|---|
| 專案 Owner | — | 最終決策 |
| Tech Lead | — | 技術執行 |
| Admin Chat | Telegram `TELEGRAM_ADMIN_CHAT_ID` | 告警接收 |
| CF 帳號管理 | CF Dashboard | tunnel / WAF 變更 |

> 請 Owner 填入實際聯絡資訊後另存私密版本（**不 commit**）。

---

## 8. 事件單模板

```markdown
# 事件單 {YYYYMMDD-NN}

- **發現時間**：
- **發現人**：
- **場景類型**：A/B/C/D/E/F
- **優先級**：P0/P1/P2

## 時間軸
| 時間 | 動作 | 執行人 |

## 影響範圍
- 受影響使用者：
- 受影響資料：
- 服務中斷：X 分鐘

## 根因
（RCA）

## 動作紀錄
- [ ] 輪換 secret
- [ ] 撤銷 session
- [ ] 通報使用者
- [ ] 文件化

## 後續改善
```

---

## 9. 事件紀錄存放

- 目錄：`CK_Missive/docs/incidents/`
- 命名：`YYYYMMDD-短描述.md`
- **不含敏感資訊**（實際密碼、真實 IP）入 git；敏感細節寫另存加密檔

---

## 10. 變更歷史

| 日期 | 變更 |
|---|---|
| 2026-04-15 | 初版 — 六大場景 + 通用 SOP |
