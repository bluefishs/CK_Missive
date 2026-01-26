/**
 * 預覽抽屜容器元件
 *
 * 提供輕量級預覽功能，支援：
 * - RWD 響應式設計（手機版直接跳轉）
 * - 多種內容類型（公文、派工、工程等）
 * - 統一的操作按鈕（檢視完整、新分頁開啟）
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import { Drawer, Button, Space, Spin, Divider, Typography } from 'antd';
import {
  CloseOutlined,
  FullscreenOutlined,
  ExportOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useResponsive } from '../../../hooks';

const { Text } = Typography;

// ============================================================================
// 型別定義
// ============================================================================

export interface PreviewDrawerProps {
  /** 是否開啟 */
  open: boolean;
  /** 關閉回調 */
  onClose: () => void;
  /** 標題 */
  title: React.ReactNode;
  /** 副標題 */
  subtitle?: string;
  /** 完整頁面路徑 (用於「檢視完整」和「新分頁開啟」) */
  detailPath?: string;
  /** 載入中狀態 */
  loading?: boolean;
  /** 自訂寬度 (桌面版) */
  width?: number | string;
  /** 子元件 (預覽內容) */
  children: React.ReactNode;
  /** 額外的底部操作按鈕 */
  extraActions?: React.ReactNode;
  /** 自訂關閉後回調 */
  afterClose?: () => void;
}

// ============================================================================
// 主元件
// ============================================================================

export const PreviewDrawer: React.FC<PreviewDrawerProps> = ({
  open,
  onClose,
  title,
  subtitle,
  detailPath,
  loading = false,
  width,
  children,
  extraActions,
  afterClose,
}) => {
  const navigate = useNavigate();
  const { isMobile, isTablet } = useResponsive();

  // RWD 寬度計算
  const drawerWidth = React.useMemo(() => {
    if (width) return width;
    if (isMobile) return '100%';
    if (isTablet) return '70%';
    return 560; // 桌面版預設寬度
  }, [width, isMobile, isTablet]);

  // 檢視完整詳情
  const handleViewDetail = () => {
    if (detailPath) {
      onClose();
      navigate(detailPath);
    }
  };

  // 新分頁開啟
  const handleOpenNewTab = () => {
    if (detailPath) {
      window.open(detailPath, '_blank');
    }
  };

  return (
    <Drawer
      open={open}
      onClose={onClose}
      afterOpenChange={(visible) => {
        if (!visible && afterClose) {
          afterClose();
        }
      }}
      title={
        <div>
          <div style={{ fontWeight: 600 }}>{title}</div>
          {subtitle && (
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 400 }}>
              {subtitle}
            </Text>
          )}
        </div>
      }
      width={drawerWidth}
      closeIcon={<CloseOutlined />}
      styles={{
        body: {
          padding: isMobile ? 12 : 16,
          display: 'flex',
          flexDirection: 'column',
        },
        header: {
          borderBottom: '1px solid #f0f0f0',
        },
      }}
      footer={
        detailPath && (
          <div style={{ padding: isMobile ? '8px 0' : '12px 0' }}>
            <Space
              style={{ width: '100%', justifyContent: 'space-between' }}
              wrap
            >
              <Space>
                <Button
                  type="primary"
                  icon={<FullscreenOutlined />}
                  onClick={handleViewDetail}
                >
                  檢視完整詳情
                </Button>
                {!isMobile && (
                  <Button
                    icon={<ExportOutlined />}
                    onClick={handleOpenNewTab}
                  >
                    新分頁開啟
                  </Button>
                )}
              </Space>
              {extraActions}
            </Space>
          </div>
        )
      }
      footerStyle={{
        borderTop: '1px solid #f0f0f0',
        padding: isMobile ? '8px 12px' : '12px 16px',
      }}
    >
      <Spin spinning={loading}>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {children}
        </div>
      </Spin>
    </Drawer>
  );
};

export default PreviewDrawer;
