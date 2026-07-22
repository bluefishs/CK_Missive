/**
 * Missive 前端主題 — 改引 @ck-shared/tokens 單一源（2026-07-22 Phase 3 / L80）。
 *
 * 原硬編 AntD ThemeConfig 已遷入 Tier 1 共享套件 @ck-shared/tokens（色/間距/圓角單一源，
 * 值不變＝視覺不變）。改設計＝改 shared-modules/tokens/index.ts 一處、全平臺同步。
 */
import { ThemeConfig } from 'antd';
import { antdTheme } from '@ck-shared/tokens';

export const theme: ThemeConfig = antdTheme;

export default theme;
