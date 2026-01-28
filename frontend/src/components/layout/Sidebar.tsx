/**
 * Sidebar 側邊欄元件
 * 從 Layout.tsx 拆分出來
 */

import React from 'react';
import { Layout, Menu, Typography, Spin } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { getCurrentMenuKey, getDefaultOpenKeys } from './hooks/useMenuItems';
import { logger } from '../../utils/logger';

const { Sider } = Layout;
const { Title } = Typography;

interface SidebarProps {
  collapsed: boolean;
  menuItems: any[];
  loading: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  menuItems,
  loading
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  // 查找選單項目
  const findItemByKey = (items: any[], targetKey: string): any => {
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
    logger.debug(`🔗 Menu clicked: ${key}`);
    const clickedItem = findItemByKey(menuItems, key);
    if (clickedItem && clickedItem.path) {
      logger.debug(`🚀 Navigating to: ${clickedItem.path}`);
      navigate(clickedItem.path);
    } else {
      logger.debug(`❌ No path found for key: ${key}`);
    }
  };

  return (
    <Sider
      trigger={null}
      collapsible
      collapsed={collapsed}
      theme="dark"
      style={{
        overflow: 'auto',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
      }}
    >
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
            fontSize: collapsed ? 12 : 16,
          }}
        >
          {collapsed ? 'CK' : '乾坤測繪'}
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
          items={menuItems}
          style={{ borderRight: 0 }}
          onClick={handleMenuClick}
        />
      )}
    </Sider>
  );
};

export default Sidebar;
