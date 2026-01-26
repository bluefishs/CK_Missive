/**
 * PM2 Ecosystem Configuration
 * CK_Missive 公文管理系統
 *
 * 使用方式：
 *   啟動全部服務: pm2 start ecosystem.config.js
 *   停止全部服務: pm2 stop all
 *   重啟全部服務: pm2 restart all
 *   查看狀態: pm2 list
 *   查看日誌: pm2 logs
 *   監控面板: pm2 monit
 */

module.exports = {
  apps: [
    // ===== 後端 FastAPI 服務 =====
    {
      name: 'ck-backend',
      cwd: './backend',
      script: 'python',
      args: '-m uvicorn main:app --host 0.0.0.0 --port 8001',
      interpreter: 'none',

      // 環境變數
      env: {
        PYTHONUNBUFFERED: '1',
        PYTHONIOENCODING: 'utf-8',
      },

      // 進程管理
      instances: 1,
      autorestart: true,
      watch: false,  // 開發時可設為 true 啟用熱重載
      max_memory_restart: '1G',

      // 日誌配置
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HHmm:ss',
      merge_logs: true,

      // 重啟策略
      restart_delay: 10000,  // 增加到 10 秒，讓端口有時間釋放
      max_restarts: 5,
      min_uptime: '30s',
    },

    // ===== 前端 Vite 開發服務 =====
    {
      name: 'ck-frontend',
      cwd: './frontend',
      script: 'node_modules/vite/bin/vite.js',
      args: '--host 0.0.0.0',
      interpreter: 'node',

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

      // 重啟策略
      restart_delay: 3000,
      max_restarts: 10,
      min_uptime: '10s',
    },
  ],
};
