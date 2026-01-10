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

    // Path aliases
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
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
      // HMR 配置：支援內網存取
      hmr: {
        host: '192.168.50.38', // 內網 IP
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
          target: env.VITE_API_URL || 'http://localhost:8002',
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
            // UI 框架
            'antd': ['antd', '@ant-design/icons'],
            // 圖表庫
            'recharts': ['recharts'],
            // 日期處理
            'dayjs': ['dayjs'],
            // 狀態管理與資料請求
            'state': ['zustand', '@tanstack/react-query'],
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