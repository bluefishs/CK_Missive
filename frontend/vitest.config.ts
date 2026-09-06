/// <reference types="vitest" />
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: [
      'src/**/*.{test,spec}.{ts,tsx}',
      'tests/**/*.{test,spec}.{ts,tsx}'
    ],
    exclude: ['node_modules', 'dist'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/index.ts',
      ],
      thresholds: {
        // 目標覆蓋率 80% (根據 .claude/rules/testing.md 規範)
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
    testTimeout: 10000,
    // file: 連結的 sso-js 在測試裡被當外部套件走 Node 解析（resolve.dedupe 管不到）⇒ 強制走 vite 管線，
    // 否則它自帶的 zustand 會拿到第二份 React ⇒ 「Cannot read properties of null (reading 'useRef')」
    server: {
      deps: {
        inline: [/shared-modules[\/]sso-js/, /zustand/, /use-sync-external-store/],
      },
    },
    retry: 1,
    maxConcurrency: 8,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      react: path.resolve(__dirname, 'node_modules/react'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom'),
      zustand: path.resolve(__dirname, 'node_modules/zustand'),
      'use-sync-external-store': path.resolve(__dirname, 'node_modules/use-sync-external-store'),
    },
    // 2026-09-06：shared-modules/sso-js 自帶一份 react 18.3.1，vite.config 有 dedupe 而這份沒有
    // ⇒ 測試裡 hook 用的 React 與 renderer 不是同一份 ⇒ 「Cannot read properties of null (reading 'useRef')」×76
    // zustand 也要：sso-js 的 src 直接 import 'zustand'，最近的 node_modules 是它自己那份 ⇒ 連帶拿到它自己的 react
    dedupe: ['react', 'react-dom', 'antd', '@ant-design/icons', 'zustand', 'use-sync-external-store'],
  },
});
