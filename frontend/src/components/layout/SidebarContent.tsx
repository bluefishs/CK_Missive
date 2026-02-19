/**
 * SidebarContent 側邊欄內容元件
 *
 * 抽取側邊欄的 Logo 和 Menu 內容，
 * 供桌面版 Sider 和行動版 Drawer 共用。
 *
 * @version 1.0.0
 * @date 2026-02-08
 */

import React from 'react';
import { Menu, Typography, Spin } from 'antd';
import type { MenuProps } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { getCurrentMenuKey, getDefaultOpenKeys, MenuItem } from './hooks/useMenuItems';
import { logger } from '../../utils/logger';

const { Title } = Typography;
type AntMenuItem = Required<MenuProps>['items'][number];

interface SidebarContentProps {
  menuItems: MenuItem[];
  loading: boolean;
  /** 選單項目點擊後的回呼（行動版用於關閉 Drawer） */
  onMenuClick?: () => void;
}

const SidebarContent: React.FC<SidebarContentProps> = ({
  menuItems,
  loading,
  onMenuClick,
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  // 查找選單項目
  const findItemByKey = (items: MenuItem[], targetKey: string): MenuItem | null => {
    for (const item of items) {
      if (item.key === targetKey) return item;
      if (item.children) {
        const found = findItemByKey(item.children, targetKey);
        if (found) return found;
      }
    }
    return null;
  };

  // 處理選單點擊
  const handleMenuClick = ({ key }: { key: string }) => {
    logger.debug(`Menu clicked: ${key}`);
    const clickedItem = findItemByKey(menuItems, key);
    if (clickedItem && clickedItem.path) {
      logger.debug(`Navigating to: ${clickedItem.path}`);
      navigate(clickedItem.path);
      onMenuClick?.();
    } else {
      logger.debug(`No path found for key: ${key}`);
    }
  };

  return (
    <div style={{ height: '100%', overflow: 'auto' }} role="navigation" aria-label="主選單">
      {/* Logo 區域 */}
      <div style={{
        padding: '16px',
        textAlign: 'center',
        borderBottom: '1px solid #303030'
      }}>
        <Title
          level={4}
          style={{
            color: 'white',
            margin: 0,
            fontSize: 16,
          }}
        >
          乾坤測繪
        </Title>
      </div>

      {/* 選單區域 */}
      {loading ? (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <Spin size="large" />
        </div>
      ) : (
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[getCurrentMenuKey(location.pathname)]}
          defaultOpenKeys={getDefaultOpenKeys(location.pathname)}
          items={menuItems as AntMenuItem[]}
          style={{ borderRight: 0 }}
          onClick={handleMenuClick}
        />
      )}
    </div>
  );
};

export default SidebarContent;
