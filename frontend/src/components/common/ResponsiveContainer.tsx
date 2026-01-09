/**
 * 響應式容器組件
 *
 * 提供基於斷點的條件渲染與響應式佈局功能。
 *
 * @version 1.0.0
 * @date 2026-01-09
 */

import React, { ReactNode } from 'react';
import { Row, Col, Space } from 'antd';
import type { SpaceProps } from 'antd';
import { useResponsive, RESPONSIVE_SPACING } from '../../hooks/useResponsive';
import type { ResponsiveConfig } from '../../hooks/useResponsive';

/**
 * 響應式顯示組件 Props
 */
interface ShowOnProps {
  /** 子組件 */
  children: ReactNode;
  /** 在手機上顯示 */
  mobile?: boolean;
  /** 在平板上顯示 */
  tablet?: boolean;
  /** 在桌面上顯示 */
  desktop?: boolean;
}

/**
 * 響應式顯示組件
 *
 * 根據當前視窗大小決定是否渲染子組件。
 *
 * @example
 * ```tsx
 * <ShowOn mobile>
 *   <MobileNavigation />
 * </ShowOn>
 *
 * <ShowOn desktop>
 *   <DesktopSidebar />
 * </ShowOn>
 * ```
 */
export function ShowOn({ children, mobile, tablet, desktop }: ShowOnProps): JSX.Element | null {
  const { isMobile, isTablet, isDesktop } = useResponsive();

  const shouldShow =
    (mobile && isMobile) ||
    (tablet && isTablet) ||
    (desktop && isDesktop);

  return shouldShow ? <>{children}</> : null;
}

/**
 * 響應式隱藏組件 Props
 */
interface HideOnProps {
  /** 子組件 */
  children: ReactNode;
  /** 在手機上隱藏 */
  mobile?: boolean;
  /** 在平板上隱藏 */
  tablet?: boolean;
  /** 在桌面上隱藏 */
  desktop?: boolean;
}

/**
 * 響應式隱藏組件
 *
 * 根據當前視窗大小決定是否隱藏子組件。
 *
 * @example
 * ```tsx
 * <HideOn mobile>
 *   <ComplexChart />
 * </HideOn>
 * ```
 */
export function HideOn({ children, mobile, tablet, desktop }: HideOnProps): JSX.Element | null {
  const { isMobile, isTablet, isDesktop } = useResponsive();

  const shouldHide =
    (mobile && isMobile) ||
    (tablet && isTablet) ||
    (desktop && isDesktop);

  return shouldHide ? null : <>{children}</>;
}

/**
 * 響應式 Space Props
 */
interface ResponsiveSpaceProps extends Omit<SpaceProps, 'size' | 'direction'> {
  /** 子組件 */
  children: ReactNode;
  /** 間距大小配置 */
  size?: 'small' | 'medium' | 'large' | ResponsiveConfig<number>;
  /** 是否在手機上垂直排列 */
  verticalOnMobile?: boolean;
}

/**
 * 響應式間距組件
 *
 * 自動根據視窗大小調整間距與排列方向。
 *
 * @example
 * ```tsx
 * <ResponsiveSpace size="medium" verticalOnMobile>
 *   <Button>按鈕 1</Button>
 *   <Button>按鈕 2</Button>
 * </ResponsiveSpace>
 * ```
 */
export function ResponsiveSpace({
  children,
  size = 'medium',
  verticalOnMobile = false,
  ...props
}: ResponsiveSpaceProps): JSX.Element {
  const { isMobile, responsive } = useResponsive();

  // 計算間距
  let spacing: number;
  if (typeof size === 'string') {
    const configMap = {
      small: RESPONSIVE_SPACING.small,
      medium: RESPONSIVE_SPACING.medium,
      large: RESPONSIVE_SPACING.large,
    };
    spacing = responsive(configMap[size]) ?? 16;
  } else {
    spacing = responsive(size) ?? 16;
  }

  // 計算方向
  const direction = verticalOnMobile && isMobile ? 'vertical' : 'horizontal';

  return (
    <Space
      size={spacing}
      direction={direction}
      {...props}
    >
      {children}
    </Space>
  );
}

/**
 * 響應式 Grid Row Props
 */
interface ResponsiveRowProps {
  /** 子組件 */
  children: ReactNode;
  /** Gutter 大小 */
  gutter?: 'small' | 'medium' | 'large' | 'default';
  /** 是否垂直 gutter */
  verticalGutter?: boolean;
  /** 其他 Row props */
  className?: string;
  style?: React.CSSProperties;
  justify?: 'start' | 'end' | 'center' | 'space-around' | 'space-between' | 'space-evenly';
  align?: 'top' | 'middle' | 'bottom' | 'stretch';
  wrap?: boolean;
}

/**
 * 響應式 Grid Row 組件
 *
 * 自動根據視窗大小調整 gutter。
 *
 * @example
 * ```tsx
 * <ResponsiveRow gutter="medium">
 *   <Col xs={24} md={12}>...</Col>
 *   <Col xs={24} md={12}>...</Col>
 * </ResponsiveRow>
 * ```
 */
export function ResponsiveRow({
  children,
  gutter = 'default',
  verticalGutter = true,
  ...props
}: ResponsiveRowProps): JSX.Element {
  const { responsive } = useResponsive();

  // 計算 gutter
  const gutterConfigMap = {
    small: RESPONSIVE_SPACING.small,
    medium: RESPONSIVE_SPACING.medium,
    large: RESPONSIVE_SPACING.large,
    default: RESPONSIVE_SPACING.gutter,
  };

  const horizontalGutter = responsive(gutterConfigMap[gutter]) ?? 16;
  const rowGutter: [number, number] = verticalGutter
    ? [horizontalGutter, horizontalGutter]
    : [horizontalGutter, 0];

  return (
    <Row gutter={rowGutter} {...props}>
      {children}
    </Row>
  );
}

/**
 * 響應式卡片 Grid Props
 */
interface ResponsiveCardGridProps {
  /** 子組件 (卡片) */
  children: ReactNode;
  /** 每行卡片數量配置 */
  columns?: ResponsiveConfig<number>;
  /** Gutter 大小 */
  gutter?: 'small' | 'medium' | 'large' | 'default';
}

/**
 * 響應式卡片 Grid 組件
 *
 * 自動根據視窗大小調整卡片佈局。
 *
 * @example
 * ```tsx
 * <ResponsiveCardGrid columns={{ xs: 1, sm: 2, md: 3, lg: 4 }}>
 *   {items.map(item => (
 *     <Card key={item.id}>{item.name}</Card>
 *   ))}
 * </ResponsiveCardGrid>
 * ```
 */
export function ResponsiveCardGrid({
  children,
  columns = { xs: 1, sm: 2, md: 3, lg: 4 },
  gutter = 'default',
}: ResponsiveCardGridProps): JSX.Element {
  const { responsive } = useResponsive();

  // 計算 gutter
  const gutterConfigMap = {
    small: RESPONSIVE_SPACING.small,
    medium: RESPONSIVE_SPACING.medium,
    large: RESPONSIVE_SPACING.large,
    default: RESPONSIVE_SPACING.gutter,
  };

  const gutterSize = responsive(gutterConfigMap[gutter]) ?? 16;
  const colCount = responsive(columns) ?? 1;
  const colSpan = Math.floor(24 / colCount);

  // 將子組件包裝在 Col 中
  const childArray = React.Children.toArray(children);

  return (
    <Row gutter={[gutterSize, gutterSize]}>
      {childArray.map((child, index) => (
        <Col key={index} span={colSpan}>
          {child}
        </Col>
      ))}
    </Row>
  );
}

/**
 * 響應式內容容器 Props
 */
interface ResponsiveContentProps {
  /** 子組件 */
  children: ReactNode;
  /** 最大寬度 */
  maxWidth?: number | 'sm' | 'md' | 'lg' | 'xl' | 'full';
  /** 內邊距 */
  padding?: 'none' | 'small' | 'medium' | 'large';
  /** 是否居中 */
  centered?: boolean;
  /** 其他樣式 */
  className?: string;
  style?: React.CSSProperties;
}

/**
 * 預設最大寬度值
 */
const MAX_WIDTH_VALUES = {
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  full: '100%',
};

/**
 * 響應式內容容器組件
 *
 * 提供統一的內容區域佈局，支援最大寬度與響應式內邊距。
 *
 * @example
 * ```tsx
 * <ResponsiveContent maxWidth="lg" padding="medium" centered>
 *   <PageContent />
 * </ResponsiveContent>
 * ```
 */
export function ResponsiveContent({
  children,
  maxWidth = 'xl',
  padding = 'medium',
  centered = true,
  className,
  style,
}: ResponsiveContentProps): JSX.Element {
  const { responsive } = useResponsive();

  // 計算最大寬度
  const width = typeof maxWidth === 'number'
    ? maxWidth
    : MAX_WIDTH_VALUES[maxWidth];

  // 計算內邊距
  const paddingConfigMap = {
    none: { xs: 0, sm: 0, md: 0, lg: 0 },
    small: RESPONSIVE_SPACING.small,
    medium: RESPONSIVE_SPACING.medium,
    large: RESPONSIVE_SPACING.large,
  };

  const paddingSize = responsive(paddingConfigMap[padding]) ?? 0;

  const containerStyle: React.CSSProperties = {
    maxWidth: typeof width === 'number' ? `${width}px` : width,
    margin: centered ? '0 auto' : undefined,
    padding: paddingSize,
    ...style,
  };

  return (
    <div className={className} style={containerStyle}>
      {children}
    </div>
  );
}

export default {
  ShowOn,
  HideOn,
  ResponsiveSpace,
  ResponsiveRow,
  ResponsiveCardGrid,
  ResponsiveContent,
};
