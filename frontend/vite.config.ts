import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env regardless of the `VITE_` prefix.
  const env = loadEnv(mode, process.cwd(), '');

  return {
    root: __dirname,
    plugins: [react()],

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
        protocol: 'ws',
      },
      proxy: {
        // Proxy API requests to the backend server
        '/api': {
          target: 'http://localhost:8001',
          changeOrigin: true,
          secure: false,
          rewrite: path => path,
        },
        // Proxy OpenAPI specification for API documentation
        '/openapi.json': {
          target: env.VITE_API_URL || 'http://localhost:8001',
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
          // 強制緩存破壞
          entryFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
          chunkFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
          assetFileNames: `assets/[name]-[hash]-${Date.now()}.[ext]`,
          // 手動分割打包，優化載入效能
          manualChunks: {
            // React 核心庫
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            // UI 框架（拆分 core / icons 降低單一 chunk 體積）
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
            // 3D 圖譜引擎（lazy-loaded，各自獨立 chunk）
            'three': ['three', 'three-spritetext'],
            'react-force-graph-3d': ['react-force-graph-3d'],
            // 2D 圖譜引擎（知識圖譜頁面載入）
            'react-force-graph-2d': ['react-force-graph-2d'],
            // 圖譜引擎
            'cytoscape': ['cytoscape'],
            // Mermaid 圖表（lazy-loaded）
            'mermaid': ['mermaid'],
            // Markdown 渲染
            'markdown': ['react-markdown', 'remark-gfm'],
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