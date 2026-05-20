import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import { resolve } from 'path';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file from project root (parent of frontend/).
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const envDir = resolve(__dirname, '..');
  const env = loadEnv(mode, envDir, '');

  return {
    root: __dirname,
    envDir,
    plugins: [
      react(),
    ],

    // Define global variables and environment variable types
    define: {
      'process.env.NODE_ENV': JSON.stringify(env.NODE_ENV || 'development'),
    },

    // Path aliases (同步 tsconfig.json paths)
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
        '@/components': resolve(__dirname, './src/components'),
        '@/pages': resolve(__dirname, './src/pages'),
        '@/services': resolve(__dirname, './src/services'),
        '@/types': resolve(__dirname, './src/types'),
        '@/utils': resolve(__dirname, './src/utils'),
        '@/hooks': resolve(__dirname, './src/hooks'),
        '@/api': resolve(__dirname, './src/api'),
        '@/config': resolve(__dirname, './src/config'),
        '@/store': resolve(__dirname, './src/store'),
        '@ck-shared/ui-components': resolve(__dirname, '../../shared-modules/ui-components'),
      },
      // 確保本地模組使用主專案的依賴（解決 peerDependencies）
      dedupe: ['react', 'react-dom', 'antd', '@ant-design/icons'],
    },

    // 優化配置：確保本地模組的依賴被正確處理
    optimizeDeps: {
      include: ['antd', '@ant-design/icons', 'react', 'react-dom'],
    },

    // Development server settings
    server: {
      // HTTPS: 自簽憑證含 SAN (localhost + 192.168.50.x)
      // 讓內網手機可使用相機掃描 QR Code
      // 首次連線需接受自簽憑證 (進階 → 繼續前往)
      https: fs.existsSync(resolve(__dirname, 'certs/dev-cert.pem'))
        ? {
            cert: fs.readFileSync(resolve(__dirname, 'certs/dev-cert.pem')),
            key: fs.readFileSync(resolve(__dirname, 'certs/dev-key.pem')),
          }
        : undefined,
      // Use environment variable or fallback to 3000
      // CK_Missive 專案指定端口：3000
      port: parseInt(env.VITE_PORT) || 3000,
      host: true, // Listen on all addresses
      open: true, // Automatically open in browser
      cors: true,
      strictPort: true, // 強制使用指定端口，避免自動切換造成混淆
      // 允許的主機名稱
      // 'all' 允許所有主機（開發環境適用）
      // 生產環境應限制為特定域名
      allowedHosts: 'all',
      // HMR 配置：使用 clientPort 讓瀏覽器自動用目前 hostname 連線
      // 不指定 host，Vite 會使用瀏覽器位址列的 hostname，支援區網 IP 存取
      hmr: {
        port: 3000,
        protocol: 'wss',
      },
      proxy: {
        // Proxy API requests to the backend server
        '/api': {
          target: 'http://127.0.0.1:8001',
          changeOrigin: true,
          secure: false,
          rewrite: path => path,
          // SSE 串流需要禁用 response buffering + 轉發真實 IP
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq, req) => {
              // 轉發真實客戶端 IP 到後端
              const clientIp = req.socket.remoteAddress?.replace('::ffff:', '') || '';
              if (clientIp && clientIp !== '127.0.0.1') {
                proxyReq.setHeader('X-Forwarded-For', clientIp);
                proxyReq.setHeader('X-Real-IP', clientIp);
              }
            });
            proxy.on('proxyRes', (proxyRes) => {
              if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
                proxyRes.headers['cache-control'] = 'no-cache';
                proxyRes.headers['x-accel-buffering'] = 'no';
              }
            });
          },
        },
        // Proxy uploaded files to backend
        '/uploads': {
          target: 'http://127.0.0.1:8001',
          changeOrigin: true,
          secure: false,
        },
        // Proxy OpenAPI specification for API documentation
        '/openapi.json': {
          target: env.VITE_API_BASE_URL || 'http://127.0.0.1:8001',
          changeOrigin: true,
          secure: false,
          rewrite: path => path,
        },
      },
    },

    // Build settings
    build: {
      outDir: 'dist',
      sourcemap: process.env.NODE_ENV === 'development',
      chunkSizeWarningLimit: 600, // 提高警告閾值
      rollupOptions: {
        input: {
          main: resolve(__dirname, 'index.html'),
        },
        output: {
          // v6.10.2 (2026-05-20): 移除 Date.now() 改用 Vite 預設 content hash
          // 起因：5/20 用戶報 chunk 404 + CSS MIME 錯（cached 舊 index.html 引用
          // 已不存在的時間戳 hash）。Date.now() 強制每次 build 換 hash 雖防 CDN cache
          // 但副作用：deploy 後舊用戶 100% 必爆 chunk 404 直到 hard refresh。
          // 改 content hash：內容不變則 hash 不變，避免無謂 cache miss + 用戶體驗連續。
          // 配套：index.html 仍 no-cache（F23 5/04 修法保留）確保拿到最新 chunk 引用。
          entryFileNames: `assets/[name]-[hash].js`,
          chunkFileNames: `assets/[name]-[hash].js`,
          assetFileNames: `assets/[name]-[hash].[ext]`,
          // 手動分割打包，優化載入效能
          manualChunks: {
            // React 核心庫
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            // UI 框架
            'antd-core': ['antd'],
            'antd-icons': ['@ant-design/icons'],
            // 圖表庫
            'recharts': ['recharts'],
            // 日期處理
            'dayjs': ['dayjs'],
            // 狀態管理與資料請求
            'state': ['zustand', '@tanstack/react-query'],
            // Excel 處理
            'xlsx': ['xlsx'],
            // 3D 圖譜引擎（lazy-loaded）
            'three': ['three', 'three-spritetext'],
            'react-force-graph-3d': ['react-force-graph-3d'],
            // 2D 圖譜引擎
            'react-force-graph-2d': ['react-force-graph-2d'],
            // Mermaid 圖表（lazy-loaded）
            'mermaid': ['mermaid'],
            // Markdown 渲染
            'markdown': ['react-markdown', 'remark-gfm'],
            // HTTP 客戶端
            'axios': ['axios'],
            // Swagger API 文件
            'swagger-ui': ['swagger-ui-react'],
          }
        }
      },
    },

    // Test settings
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
    },
  };
});