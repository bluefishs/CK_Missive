# 端口配置規範 (Port Configuration)

> 版本：1.1.0
> 建立日期：2026-01-08
> 最後更新：2026-01-08
> 用途：避免專案間端口衝突，確保開發環境穩定

---

## 一、問題背景

### 1.1 錯誤案例 (2026-01-08)

```
❌ 錯誤狀況：
CK_Missive 配置 VITE_PORT=3000
但 vite.config.ts 設定 strictPort: false

當 port 3000 被佔用時，Vite 自動切換到 3001, 3002, 3003...
導致前端運行在非預期端口，造成：
- CORS 錯誤 (後端未配置該端口)
- Cookie/Session 問題
- 開發者混淆 (不知道在哪個端口)

結果: 前端運行在 localhost:3003 而非預期的 localhost:3000
```

---

## 二、強制規範

### 2.1 strictPort 必須為 true

**所有專案的 `vite.config.ts` 必須設定：**

```typescript
// vite.config.ts
server: {
  port: parseInt(env.VITE_PORT) || 3000,
  strictPort: true,  // ⚠️ 強制！禁止自動切換端口
  host: true,
}
```

### 2.2 專案端口分配表

| 專案 | 前端端口 | 後端端口 | 資料庫端口 |
|------|----------|----------|------------|
| CK_Missive | 3000 | 8001 | 5434 |
| CK_lvrland_Webmap | 3003 | 8002 | 5433 |
| CK_GPS | 5182 | 3001 | - |
| (預留) | 3004 | 8004 | - |
| (預留) | 3005 | 8005 | - |

### 2.3 環境變數配置

每個專案必須在 `.env` 或 `.env.development` 明確指定：

```env
# CK_Missive/.env.development
VITE_PORT=3000
VITE_API_BASE_URL=http://localhost:8001

# CK_lvrland_Webmap/.env
VITE_PORT=3003
VITE_API_TARGET=http://localhost:8002
```

---

## 三、開發流程

### 3.1 啟動前檢查

```bash
# 1. 檢查端口是否被佔用
netstat -ano | findstr :3000

# 2. 如有佔用，查看進程
tasklist /FI "PID eq <進程ID>"

# 3. 終止佔用進程 (確認是舊的開發伺服器後)
taskkill /PID <進程ID> /F

# 4. 啟動開發伺服器
npm run dev
```

### 3.2 端口衝突處理

當看到錯誤訊息：
```
Error: Port 3000 is already in use
```

**處理步驟：**

1. **確認是否同專案舊進程**
   ```bash
   netstat -ano | findstr :3000
   tasklist /FI "PID eq <PID>"
   ```

2. **如是舊進程 → 終止它**
   ```bash
   taskkill /PID <PID> /F
   ```

3. **如是其他專案 → 關閉其他專案或檢查配置**
   - 確認另一專案是否誤用相同端口
   - 參考端口分配表調整

### 3.3 新專案配置流程

```
步驟 1: 確認可用端口
────────────────────────────────────────────────────
參考 C:\GeminiCli\PORT_ALLOCATION.md 選擇未使用端口

步驟 2: 配置 vite.config.ts
────────────────────────────────────────────────────
server: {
  // 專案名稱 專案指定端口：XXXX
  port: parseInt(env.VITE_PORT) || XXXX,
  strictPort: true,  // 強制使用指定端口
  host: true,
}

步驟 3: 配置 .env.development
────────────────────────────────────────────────────
VITE_PORT=XXXX
VITE_API_BASE_URL=http://localhost:YYYY

步驟 4: 更新端口分配表
────────────────────────────────────────────────────
更新 C:\GeminiCli\PORT_ALLOCATION.md
```

---

## 四、後端 CORS 配置

### 4.1 CORS 允許來源

後端必須配置所有可能的前端端口：

```python
# backend/main.py
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    # ... 其他端口
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4.2 動態 CORS 配置 (建議)

```python
# backend/app/core/config.py
import os

def get_cors_origins() -> list:
    """根據環境變數動態生成 CORS 允許來源"""
    base_ports = [3000, 3001, 3002, 3003, 3004, 3005, 5173, 5182]
    hosts = ["localhost", "127.0.0.1"]

    # 加入環境變數指定的額外來源
    extra = os.getenv("CORS_EXTRA_ORIGINS", "").split(",")

    origins = []
    for host in hosts:
        for port in base_ports:
            origins.append(f"http://{host}:{port}")

    origins.extend([o.strip() for o in extra if o.strip()])
    return origins
```

---

## 五、驗證檢查清單

### 5.1 設定檢查

- [ ] `vite.config.ts` 設定 `strictPort: true`
- [ ] `.env.development` 明確指定 `VITE_PORT`
- [ ] 端口號與分配表一致
- [ ] 後端 CORS 已配置該端口

### 5.2 啟動檢查

- [ ] 前端啟動在預期端口 (觀察終端輸出)
- [ ] 後端 CORS 日誌顯示正確來源
- [ ] 瀏覽器 Console 無 CORS 錯誤

---

## 六、常見錯誤與解決

### 6.1 Vite 自動切換端口

**症狀**：終端顯示 `localhost:3001` 而非 `localhost:3000`

**原因**：`strictPort: false` 且 port 3000 被佔用

**解決**：
```typescript
// vite.config.ts
server: {
  strictPort: true,  // 改為 true
}
```

### 6.2 CORS 錯誤

**症狀**：`Access-Control-Allow-Origin` 錯誤

**原因**：前端端口未在後端 CORS 允許列表

**解決**：
```python
# 新增端口到 CORS 允許列表
CORS_ORIGINS.append("http://localhost:3003")
```

### 6.3 多個相同端口進程

**症狀**：多個 node 進程佔用相同端口

**解決**：
```bash
# 找出所有 node 進程
tasklist | findstr node

# 終止所有相關進程
taskkill /IM node.exe /F
```

---

## 七、相關文件

| 文件 | 說明 |
|------|------|
| `C:\GeminiCli\PORT_ALLOCATION.md` | 全域端口分配表 |
| `docs/DEVELOPMENT_STANDARDS.md` | 統一開發規範總綱 |
| `frontend/vite.config.ts` | Vite 配置 |
| `backend/main.py` | 後端 CORS 配置 |

---

## 八、版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.1.0 | 2026-01-08 | 遷移至 docs/specifications/ |
| 1.0.0 | 2026-01-08 | 初版 - 基於端口自動切換問題建立規範 |

---

*文件維護: Claude Code Assistant*
