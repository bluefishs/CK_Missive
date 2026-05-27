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
 * ⚠️ 2026-05-27 — ck-backend / ck-frontend 已從 PM2 廢除（per OA-3 / L43 路由迷宮根治）
 *    詳見：docs/runbooks/pm2-deprecation-sop.md / pm2-deprecation-execution-20260527.md
 *    現由 docker compose 接管：
 *      docker compose -f docker-compose.production.yml up -d backend frontend
 *    公網 missive.cksurvey.tw 透過 cloudflared 直命中 docker container production image。
 */

module.exports = {
  apps: [
    // ===== ck-backend / ck-frontend 已廢除（2026-05-27 OA-3） =====
    // 業務後端 + 前端改由 docker compose 統一管理（restart: always 自動恢復）
    // Rollback 路徑：pm2 resurrect（會還原 ~/.pm2/dump.pm2 的舊狀態）
    //              + ecosystem.config.js git revert <commit>

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

    // ---- Health Watchdog（常駐 loop，每 2 分鐘偵測假死，連續 2 次失敗自動 restart）----
    {
      name: 'health-watchdog',
      script: 'scripts/health/health-watchdog.sh',
      interpreter: 'bash',
      cwd: __dirname,
      autorestart: true,        // 常駐模式（v2.0 — 修復 PM2 cron 在 Windows 不穩定）
      watch: false,
      max_memory_restart: '64M',

      error_file: './logs/watchdog-error.log',
      out_file: './logs/watchdog-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      max_size: '5M',
    },

    // ---- Synthetic Baseline Inject Loop（每 4 小時注入 20 筆合成查詢，累積 Phase 0 shadow baseline）----
    // 同 health-watchdog：常駐 while-true（避免 PM2 cron 在 Windows 不穩定）
    {
      name: 'synthetic-baseline',
      script: 'scripts/checks/synthetic-baseline-loop.sh',
      interpreter: 'bash',
      cwd: __dirname,
      autorestart: true,
      watch: false,
      max_memory_restart: '128M',
      env: {
        BACKEND_URL: 'http://localhost:8001',
        INTERVAL: '14400',       // 4 小時（每日 6 輪 × 20 筆 = 120 筆基線）
        COUNT: '20',
      },

      error_file: './logs/synthetic-baseline-error.log',
      out_file: './logs/synthetic-baseline-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true,
      max_size: '10M',
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
