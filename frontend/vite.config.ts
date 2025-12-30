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
    },

    // Development server settings
    server: {
      // Use environment variable or fallback to 3000
      port: parseInt(env.VITE_PORT) || 3000,
      host: true, // Listen on all addresses
      open: true, // Automatically open in browser
      cors: true,
      strictPort: false, // Allow port fallback for development
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
      rollupOptions: {
        input: {
          main: resolve(__dirname, 'index.html'),
        },
        output: {
          // 強制緩存破壞
          entryFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
          chunkFileNames: `assets/[name]-[hash]-${Date.now()}.js`,
          assetFileNames: `assets/[name]-[hash]-${Date.now()}.[ext]`
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