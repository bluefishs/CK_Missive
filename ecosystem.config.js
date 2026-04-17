/**
 * PM2 Ecosystem Configuration
 * CK_Missive 公文管理系統
 *
 * 推薦使用統一管理腳本（v1.53.0）：
 *   .\scripts\dev-start.ps1              # 混合模式啟動（推薦）
 *   .\scripts\dev-start.ps1 -Status      # 查看狀態
 *   .\scripts\dev-stop.ps1               # 停止所有服務
 *
 * PM2 直接操作：
 *   啟動全部服務: pm2 start ecosystem.config.js
 *   停止全部服務: pm2 stop all
 *   重啟全部服務: pm2 restart all
 *   查看狀態: pm2 list
 *   查看日誌: pm2 logs
 *   監控面板: pm2 monit
 *
 * 後端啟動流程 (start-backend.ps1 v2.0.0)：
 *   Step 0:   端口 8001 衝突偵測
 *   Step 0.5: 基礎設施依賴檢查 (PostgreSQL + Redis)
 *   Step 1:   pip install -r requirements.txt
 *   Step 2:   alembic upgrade head
 *   Step 3:   uvicorn main:app --host 0.0.0.0 --port 8001
 */

module.exports = {
  apps: [
    // ===== 後端 FastAPI 服務 =====
    // 使用 Python 啟動包裝器（v1.54.0）：
    //   自動執行端口偵測 → 基礎設施檢查 → pip install → alembic upgrade → uvicorn
    //   使用 os.execvp 替換進程，PM2 可正確追蹤 PID
    //   避免 PowerShell cp950 編碼問題
    {
      name: 'ck-backend',
      cwd: './backend',
      script: 'python',
      args: 'startup.py',
      interpreter: 'none',

      // 環境變數 (UTF-8 強制：避免 Windows cp950 編碼錯誤)
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1',
        // Shadow 基線記錄（ADR-0014 Hermes 遷移 Phase 0 基線）
        // 30 天自動清理；PII 遮罩已啟用；採樣 0.3 控制 IO
        SHADOW_ENABLED: '1',
        SHADOW_SAMPLE_RATIO: '0.3',
        SHADOW_RETENTION_DAYS: '30',
      },

      // 進程管理
      instances: 1,
      autorestart: true,
      watch: false,  // 開發時可設為 true 啟用熱重載
      max_memory_restart: '2G',

      // 日誌配置 (cwd 已是 ./backend，路徑相對於 backend/)
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      max_size: '10M',  // 超過 10MB 自動輪替（需 pm2-logrotate 或 PM2 >= 5.x）

      // 重啟策略
      exp_backoff_restart_delay: 1000, // 指數退避：1s→2s→4s...→15s，防止快速重啟競態
      max_restarts: 10,
      min_uptime: '30s',
      treekill: true,        // 殺掉整個進程樹（含 uvicorn 子進程）
      kill_timeout: 10000,   // 等 10 秒讓進程優雅關閉
      wait_ready: false,     // startup.py 自行管理就緒狀態
    },

    // ===== 前端 Vite 開發服務 =====
    // 注意：前端啟動後，若後端尚未就緒，client.ts 會自動重試（指數退避 1s/2s/4s）
    // fork 模式：Vite 開發伺服器為單進程，cluster 模式無益且影響 HMR 即時更新
    {
      name: 'ck-frontend',
      cwd: './frontend',
      script: 'node_modules/vite/bin/vite.js',
      args: '--host 0.0.0.0',
      interpreter: 'node',
      exec_mode: 'fork',

      // 環境變數
      env: {
        NODE_ENV: 'development',
      },

      // 進程管理
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',

      // 日誌配置
      error_file: './logs/frontend-error.log',
      out_file: './logs/frontend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      max_size: '10M',  // 超過 10MB 自動輪替

      // 重啟策略
      restart_delay: 3000,
      max_restarts: 10,
      min_uptime: '10s',
    },

    // ---- Cloudflare Tunnel（ADR-0015，取代 NemoClaw Nginx）----
    // 啟用方式（兩種擇一）：
    //   Token 模式（推薦，Dashboard 建立）：設 CF_TUNNEL_TOKEN 於 .env
    //   Config 模式（CLI 建立）：設 CLOUDFLARED_ENABLED=1 + ~/.cloudflared/config.yml
    // 安全：token 絕不進版控；token 洩漏需至 CF Dashboard 刪 tunnel 重建
    ...(process.env.CF_TUNNEL_TOKEN ? [{
      name: 'cloudflared',
      script: 'cloudflared',
      args: `tunnel run --token ${process.env.CF_TUNNEL_TOKEN}`,
      interpreter: 'none',
      autorestart: true,
      max_restarts: 10,
      min_uptime: '30s',
      restart_delay: 3000,
      error_file: './logs/cloudflared-error.log',
      out_file: './logs/cloudflared-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      max_size: '10M',
    }] : process.env.CLOUDFLARED_ENABLED === '1' ? [{
      name: 'cloudflared',
      script: 'cloudflared',
      args: 'tunnel run ck-missive',
      interpreter: 'none',
      autorestart: true,
      max_restarts: 10,
      min_uptime: '30s',
      restart_delay: 3000,
      error_file: './logs/cloudflared-error.log',
      out_file: './logs/cloudflared-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      max_size: '10M',
    }] : []),

    // ---- Health Watchdog（每 2 分鐘偵測 backend 假死，連續 2 次失敗自動 restart）----
    {
      name: 'health-watchdog',
      script: 'scripts/health/health-watchdog.sh',
      interpreter: 'bash',
      cwd: __dirname,
      autorestart: false,       // 不自動重啟（由 cron 觸發）
      cron_restart: '*/2 * * * *',  // 每 2 分鐘
      watch: false,

      error_file: './logs/watchdog-error.log',
      out_file: './logs/watchdog-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      max_size: '5M',
    },

    // ---- 發票影像 Watchdog 監控 ----
    {
      name: 'invoice-watcher',
      script: 'scripts/dev/invoice-watcher.py',
      interpreter: 'python',
      cwd: __dirname,
      watch: false,
      autorestart: true,

      // 日誌
      error_file: './logs/invoice-watcher-error.log',
      out_file: './logs/invoice-watcher-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      max_size: '10M',

      restart_delay: 5000,
      max_restarts: 5,
      min_uptime: '10s',
    },
  ],
};
