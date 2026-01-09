/**
 * 響應式設計工具 Hook
 *
 * 提供統一的響應式斷點檢測與工具函數，
 * 封裝 Ant Design Grid.useBreakpoint 並擴展更多便利功能。
 *
 * @version 1.0.0
 * @date 2026-01-09
 *
 * @example
 * ```tsx
 * const { isMobile, isDesktop, responsive } = useResponsive();
 *
 * // 使用布林值
 * if (isMobile) {
 *   return <MobileLayout />;
 * }
 *
 * // 使用響應式值
 * const columns = responsive({ xs: 1, sm: 2, md: 3, lg: 4 });
 *
 * // 使用響應式樣式
 * const padding = responsiveValue({ mobile: 8, tablet: 16, desktop: 24 });
 * ```
 */

import { useMemo } from 'react';
import { Grid } from 'antd';
import type { Breakpoint } from 'antd/es/_util/responsiveObserver';

const { useBreakpoint } = Grid;

/**
 * Ant Design 斷點大小 (單位: px)
 */
export const BREAKPOINTS = {
  xs: 480,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
} as const;

/**
 * 響應式值配置 (依照 Ant Design 斷點)
 */
export interface ResponsiveConfig<T> {
  xs?: T;
  sm?: T;
  md?: T;
  lg?: T;
  xl?: T;
  xxl?: T;
}

/**
 * 響應式值配置 (使用語意化名稱)
 */
export interface SemanticResponsiveConfig<T> {
  mobile?: T;
  tablet?: T;
  desktop?: T;
  widescreen?: T;
}

/**
 * 響應式 Hook 回傳值
 */
export interface UseResponsiveResult {
  /** 當前啟用的斷點狀態 (來自 Ant Design) */
  screens: Partial<Record<Breakpoint, boolean>>;

  /** 是否為手機尺寸 (< 768px) */
  isMobile: boolean;

  /** 是否為平板尺寸 (768px - 991px) */
  isTablet: boolean;

  /** 是否為桌面尺寸 (>= 992px) */
  isDesktop: boolean;

  /** 是否為寬螢幕尺寸 (>= 1200px) */
  isWidescreen: boolean;

  /** 是否為超寬螢幕尺寸 (>= 1600px) */
  isUltraWide: boolean;

  /** 是否為觸控裝置 (手機或平板) */
  isTouchDevice: boolean;

  /** 當前視窗寬度類型 */
  deviceType: 'mobile' | 'tablet' | 'desktop';

  /**
   * 根據斷點獲取對應值 (使用 Ant Design 斷點)
   *
   * @example
   * const columns = responsive({ xs: 1, sm: 2, md: 3, lg: 4 });
   */
  responsive: <T>(config: ResponsiveConfig<T>) => T | undefined;

  /**
   * 根據語意化斷點獲取對應值
   *
   * @example
   * const padding = responsiveValue({ mobile: 8, tablet: 16, desktop: 24 });
   */
  responsiveValue: <T>(config: SemanticResponsiveConfig<T>) => T | undefined;

  /**
   * 獲取當前斷點名稱
   */
  currentBreakpoint: Breakpoint | undefined;

  /**
   * 檢查是否大於等於指定斷點
   */
  isGte: (breakpoint: Breakpoint) => boolean;

  /**
   * 檢查是否小於等於指定斷點
   */
  isLte: (breakpoint: Breakpoint) => boolean;
}

/**
 * 斷點優先順序 (從大到小)
 */
const BREAKPOINT_ORDER: Breakpoint[] = ['xxl', 'xl', 'lg', 'md', 'sm', 'xs'];

/**
 * 斷點數值映射
 */
const BREAKPOINT_VALUES: Record<Breakpoint, number> = {
  xs: 0,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
};

/**
 * 響應式設計工具 Hook
 *
 * 封裝 Ant Design 的 useBreakpoint 並提供更多便利功能。
 */
export function useResponsive(): UseResponsiveResult {
  const screens = useBreakpoint();

  return useMemo(() => {
    // 計算當前斷點
    const currentBreakpoint = BREAKPOINT_ORDER.find(bp => screens[bp]);

    // 計算設備類型
    const isMobile = !screens.md;
    const isTablet = !!screens.md && !screens.lg;
    const isDesktop = !!screens.lg;
    const isWidescreen = !!screens.xl;
    const isUltraWide = !!screens.xxl;
    const isTouchDevice = isMobile || isTablet;

    const deviceType: 'mobile' | 'tablet' | 'desktop' = isMobile
      ? 'mobile'
      : isTablet
        ? 'tablet'
        : 'desktop';

    // 響應式值獲取函數
    const responsive = <T>(config: ResponsiveConfig<T>): T | undefined => {
      for (const bp of BREAKPOINT_ORDER) {
        if (screens[bp] && config[bp] !== undefined) {
          return config[bp];
        }
      }
      // 回退到最小斷點
      return config.xs;
    };

    // 語意化響應式值獲取函數
    const responsiveValue = <T>(config: SemanticResponsiveConfig<T>): T | undefined => {
      if (isWidescreen && config.widescreen !== undefined) {
        return config.widescreen;
      }
      if (isDesktop && config.desktop !== undefined) {
        return config.desktop;
      }
      if (isTablet && config.tablet !== undefined) {
        return config.tablet;
      }
      return config.mobile;
    };

    // 檢查是否大於等於指定斷點
    const isGte = (breakpoint: Breakpoint): boolean => {
      const currentValue = BREAKPOINT_VALUES[currentBreakpoint || 'xs'];
      const targetValue = BREAKPOINT_VALUES[breakpoint];
      return currentValue >= targetValue;
    };

    // 檢查是否小於等於指定斷點
    const isLte = (breakpoint: Breakpoint): boolean => {
      const currentValue = BREAKPOINT_VALUES[currentBreakpoint || 'xs'];
      const targetValue = BREAKPOINT_VALUES[breakpoint];
      return currentValue <= targetValue;
    };

    return {
      screens,
      isMobile,
      isTablet,
      isDesktop,
      isWidescreen,
      isUltraWide,
      isTouchDevice,
      deviceType,
      responsive,
      responsiveValue,
      currentBreakpoint,
      isGte,
      isLte,
    };
  }, [screens]);
}

/**
 * 響應式欄位數量工具
 *
 * 常用於 Grid 或 List 組件的欄位數設定。
 */
export const RESPONSIVE_COLUMNS = {
  /** 標準列數: 1/2/3/4 */
  standard: { xs: 1, sm: 2, md: 3, lg: 4 } as ResponsiveConfig<number>,

  /** 緊湊列數: 2/3/4/6 */
  compact: { xs: 2, sm: 3, md: 4, lg: 6 } as ResponsiveConfig<number>,

  /** 寬鬆列數: 1/1/2/3 */
  relaxed: { xs: 1, sm: 1, md: 2, lg: 3 } as ResponsiveConfig<number>,

  /** 卡片列數: 1/2/2/3/4 */
  cards: { xs: 1, sm: 2, md: 2, lg: 3, xl: 4 } as ResponsiveConfig<number>,
};

/**
 * 響應式間距工具
 */
export const RESPONSIVE_SPACING = {
  /** 小間距: 8/12/16/20 */
  small: { xs: 8, sm: 12, md: 16, lg: 20 } as ResponsiveConfig<number>,

  /** 中間距: 12/16/20/24 */
  medium: { xs: 12, sm: 16, md: 20, lg: 24 } as ResponsiveConfig<number>,

  /** 大間距: 16/20/24/32 */
  large: { xs: 16, sm: 20, md: 24, lg: 32 } as ResponsiveConfig<number>,

  /** Ant Design Gutter */
  gutter: { xs: 8, sm: 16, md: 24, lg: 32 } as ResponsiveConfig<number>,
};

/**
 * 響應式表格配置
 */
export const RESPONSIVE_TABLE = {
  /** 預設 scroll.x */
  scrollX: { xs: 800, sm: 1000, md: 1200, lg: undefined } as ResponsiveConfig<number | undefined>,

  /** 預設 pageSize */
  pageSize: { xs: 10, sm: 15, md: 20, lg: 25 } as ResponsiveConfig<number>,
};

export default useResponsive;
