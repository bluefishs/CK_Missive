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
      },

      // 進程管理
      instances: 1,
      autorestart: true,
      watch: false,  // 開發時可設為 true 啟用熱重載
      max_memory_restart: '1G',

      // 日誌配置 (cwd 已是 ./backend，路徑相對於 backend/)
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      max_size: '10M',  // 超過 10MB 自動輪替（需 pm2-logrotate 或 PM2 >= 5.x）

      // 重啟策略
      restart_delay: 10000,  // 增加到 10 秒，讓端口有時間釋放
      max_restarts: 10,
      min_uptime: '30s',
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
  ],
};
