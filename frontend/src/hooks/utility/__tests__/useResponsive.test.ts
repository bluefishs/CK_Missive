/**
 * useResponsive Hook 測試
 * useResponsive Hook Tests
 */
import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';

// Mock Ant Design Grid.useBreakpoint
const { mockUseBreakpoint } = vi.hoisted(() => ({
  mockUseBreakpoint: vi.fn(() => ({})),
}));
vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>();
  return {
    ...actual,
    Grid: {
      ...actual.Grid,
      useBreakpoint: mockUseBreakpoint,
    },
  };
});

import {
  useResponsive,
  BREAKPOINTS,
  RESPONSIVE_COLUMNS,
  RESPONSIVE_SPACING,
  RESPONSIVE_TABLE,
} from '../useResponsive';

describe('useResponsive', () => {
  describe('BREAKPOINTS 常數', () => {
    it('應包含所有 6 個斷點', () => {
      expect(BREAKPOINTS).toHaveProperty('xs');
      expect(BREAKPOINTS).toHaveProperty('sm');
      expect(BREAKPOINTS).toHaveProperty('md');
      expect(BREAKPOINTS).toHaveProperty('lg');
      expect(BREAKPOINTS).toHaveProperty('xl');
      expect(BREAKPOINTS).toHaveProperty('xxl');
    });

    it('斷點值應遞增', () => {
      expect(BREAKPOINTS.xs).toBeLessThan(BREAKPOINTS.sm);
      expect(BREAKPOINTS.sm).toBeLessThan(BREAKPOINTS.md);
      expect(BREAKPOINTS.md).toBeLessThan(BREAKPOINTS.lg);
      expect(BREAKPOINTS.lg).toBeLessThan(BREAKPOINTS.xl);
      expect(BREAKPOINTS.xl).toBeLessThan(BREAKPOINTS.xxl);
    });
  });

  describe('RESPONSIVE_COLUMNS 預設配置', () => {
    it('standard 配置應為 1/2/3/4', () => {
      expect(RESPONSIVE_COLUMNS.standard).toEqual({ xs: 1, sm: 2, md: 3, lg: 4 });
    });

    it('compact 配置應為 2/3/4/6', () => {
      expect(RESPONSIVE_COLUMNS.compact).toEqual({ xs: 2, sm: 3, md: 4, lg: 6 });
    });

    it('relaxed 配置應為 1/1/2/3', () => {
      expect(RESPONSIVE_COLUMNS.relaxed).toEqual({ xs: 1, sm: 1, md: 2, lg: 3 });
    });

    it('cards 配置應包含 xl 斷點', () => {
      expect(RESPONSIVE_COLUMNS.cards).toEqual({ xs: 1, sm: 2, md: 2, lg: 3, xl: 4 });
    });
  });

  describe('RESPONSIVE_SPACING 預設配置', () => {
    it.each(['small', 'medium', 'large', 'gutter'] as const)('%s 間距的所有值應為正數', (key) => {
      const config = RESPONSIVE_SPACING[key];
      for (const val of Object.values(config)) {
        expect(val).toBeGreaterThan(0);
      }
    });

    it('間距應遞增：small < medium < large', () => {
      expect(RESPONSIVE_SPACING.small.lg!).toBeLessThan(RESPONSIVE_SPACING.medium.lg!);
      expect(RESPONSIVE_SPACING.medium.lg!).toBeLessThan(RESPONSIVE_SPACING.large.lg!);
    });
  });

  describe('RESPONSIVE_TABLE 預設配置', () => {
    it('pageSize 應為正數', () => {
      for (const val of Object.values(RESPONSIVE_TABLE.pageSize)) {
        if (val !== undefined) expect(val).toBeGreaterThan(0);
      }
    });

    it('scrollX 在大螢幕應為 undefined', () => {
      expect(RESPONSIVE_TABLE.scrollX.lg).toBeUndefined();
    });
  });

  describe('Hook 行為 — 手機模式', () => {
    it('當所有斷點為 false 時應為 mobile', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true });
      const { result } = renderHook(() => useResponsive());

      expect(result.current.isMobile).toBe(true);
      expect(result.current.isTablet).toBe(false);
      expect(result.current.isDesktop).toBe(false);
      expect(result.current.deviceType).toBe('mobile');
      expect(result.current.isTouchDevice).toBe(true);
    });
  });

  describe('Hook 行為 — 平板模式', () => {
    it('md=true, lg=false 應為 tablet', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true });
      const { result } = renderHook(() => useResponsive());

      expect(result.current.isMobile).toBe(false);
      expect(result.current.isTablet).toBe(true);
      expect(result.current.isDesktop).toBe(false);
      expect(result.current.deviceType).toBe('tablet');
      expect(result.current.isTouchDevice).toBe(true);
    });
  });

  describe('Hook 行為 — 桌面模式', () => {
    it('lg=true 應為 desktop', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true, lg: true });
      const { result } = renderHook(() => useResponsive());

      expect(result.current.isMobile).toBe(false);
      expect(result.current.isTablet).toBe(false);
      expect(result.current.isDesktop).toBe(true);
      expect(result.current.deviceType).toBe('desktop');
      expect(result.current.isTouchDevice).toBe(false);
    });

    it('xl=true 應為 widescreen', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true, lg: true, xl: true });
      const { result } = renderHook(() => useResponsive());

      expect(result.current.isWidescreen).toBe(true);
      expect(result.current.isUltraWide).toBe(false);
    });

    it('xxl=true 應為 ultraWide', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true, lg: true, xl: true, xxl: true });
      const { result } = renderHook(() => useResponsive());

      expect(result.current.isUltraWide).toBe(true);
    });
  });

  describe('responsive() 函數', () => {
    it('應根據當前斷點返回對應值', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true });
      const { result } = renderHook(() => useResponsive());

      const value = result.current.responsive({ xs: 'a', sm: 'b', md: 'c', lg: 'd' });
      expect(value).toBe('c');
    });

    it('桌面模式應返回 lg 值', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true, lg: true });
      const { result } = renderHook(() => useResponsive());

      const value = result.current.responsive({ xs: 1, sm: 2, md: 3, lg: 4 });
      expect(value).toBe(4);
    });

    it('未定義斷點值時應回退到 xs', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true });
      const { result } = renderHook(() => useResponsive());

      const value = result.current.responsive({ xs: 'fallback' });
      expect(value).toBe('fallback');
    });
  });

  describe('responsiveValue() 語意化函數', () => {
    it('手機模式應返回 mobile 值', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true });
      const { result } = renderHook(() => useResponsive());

      const value = result.current.responsiveValue({ mobile: 8, tablet: 16, desktop: 24 });
      expect(value).toBe(8);
    });

    it('平板模式應返回 tablet 值', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true });
      const { result } = renderHook(() => useResponsive());

      const value = result.current.responsiveValue({ mobile: 8, tablet: 16, desktop: 24 });
      expect(value).toBe(16);
    });

    it('桌面模式應返回 desktop 值', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true, lg: true });
      const { result } = renderHook(() => useResponsive());

      const value = result.current.responsiveValue({ mobile: 8, tablet: 16, desktop: 24 });
      expect(value).toBe(24);
    });

    it('寬螢幕模式應返回 widescreen 值', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true, lg: true, xl: true });
      const { result } = renderHook(() => useResponsive());

      const value = result.current.responsiveValue({ mobile: 8, desktop: 24, widescreen: 32 });
      expect(value).toBe(32);
    });
  });

  describe('currentBreakpoint', () => {
    it('手機模式應為 xs', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true });
      const { result } = renderHook(() => useResponsive());
      expect(result.current.currentBreakpoint).toBe('xs');
    });

    it('桌面模式應為 lg', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true, lg: true });
      const { result } = renderHook(() => useResponsive());
      expect(result.current.currentBreakpoint).toBe('lg');
    });

    it('超寬螢幕應為 xxl', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true, lg: true, xl: true, xxl: true });
      const { result } = renderHook(() => useResponsive());
      expect(result.current.currentBreakpoint).toBe('xxl');
    });
  });

  describe('isGte() / isLte()', () => {
    it('lg 模式下 isGte(md) 應為 true', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true, lg: true });
      const { result } = renderHook(() => useResponsive());
      expect(result.current.isGte('md')).toBe(true);
      expect(result.current.isGte('lg')).toBe(true);
      expect(result.current.isGte('xl')).toBe(false);
    });

    it('md 模式下 isLte(lg) 應為 true', () => {
      mockUseBreakpoint.mockReturnValue({ xs: true, sm: true, md: true });
      const { result } = renderHook(() => useResponsive());
      expect(result.current.isLte('lg')).toBe(true);
      expect(result.current.isLte('md')).toBe(true);
      expect(result.current.isLte('sm')).toBe(false);
    });
  });
});
