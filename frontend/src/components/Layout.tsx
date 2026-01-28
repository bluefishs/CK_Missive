/**
 * Layout 主框架元件
 * 整合 Sidebar, Header 等子元件
 *
 * 重構說明 (2026-01-27):
 * - 原始行數: 786 行
 * - 重構後: ~100 行
 * - 拆分至:
 *   - layout/Sidebar.tsx (側邊欄)
 *   - layout/Header.tsx (頂部欄)
 *   - layout/hooks/useNavigationData.ts (導覽資料)
 *   - layout/hooks/useMenuItems.ts (選單轉換)
 */

import React, { useState } from 'react';
import { Layout as AntLayout } from 'antd';
import { useLocation } from 'react-router-dom';
import Sidebar from './layout/Sidebar';
import LayoutHeader from './layout/Header';
import { useNavigationData } from './layout/hooks/useNavigationData';

const { Content } = AntLayout;

interface LayoutProps {
  children: React.ReactNode;
}

// 不需要布局的公開頁面路徑
const PUBLIC_ROUTES = ['/entry', '/login', '/register', '/forgot-password'];

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  // 使用導覽資料 Hook
  const {
    menuItems,
    navigationLoading,
    permissionsLoading,
    currentUser,
  } = useNavigationData();

  // 檢查是否為公開頁面
  const isPublicRoute = PUBLIC_ROUTES.some(
    route => location.pathname === route || location.pathname.startsWith(route + '/')
  );

  // 處理使用者登出
  const handleUserLogout = () => {
    // 清除使用者狀態會由 useNavigationData 內部處理
  };

  // 公開頁面直接渲染內容
  if (isPublicRoute) {
    return <>{children}</>;
  }

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      {/* 側邊欄 */}
      <Sidebar
        collapsed={collapsed}
        menuItems={menuItems}
        loading={navigationLoading || permissionsLoading}
      />

      {/* 主內容區 */}
      <AntLayout style={{
        marginLeft: collapsed ? 80 : 200,
        transition: 'margin-left 0.2s'
      }}>
        {/* 頂部欄 */}
        <LayoutHeader
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed(!collapsed)}
          currentUser={currentUser}
          onUserLogout={handleUserLogout}
        />

        {/* 內容區 */}
        <Content style={{
          padding: '24px',
          background: '#f5f5f5',
          minHeight: 'calc(100vh - 64px)',
        }}>
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout;
