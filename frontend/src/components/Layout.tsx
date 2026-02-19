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
 *
 * v1.44.0 (2026-02-08):
 * - 新增行動裝置 Drawer 側邊欄模式
 * - 螢幕寬度 < 768px 時隱藏固定 Sider，改用 Drawer 覆蓋
 * - Header 左側漢堡按鈕切換 Drawer 開關
 * - 點擊選單項目後自動關閉 Drawer
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Layout as AntLayout, Drawer, App, Alert, Button as AntButton } from 'antd';
import { useLocation } from 'react-router-dom';
import Sidebar from './layout/Sidebar';
import LayoutHeader from './layout/Header';
import { useNavigationData } from './layout/hooks/useNavigationData';
import { useIdleTimeout, useResponsive } from '../hooks';
import { AIAssistantButton } from './ai';
import { sendVerificationEmail } from '../api/authApi';
import SidebarContent from './layout/SidebarContent';

const { Content } = AntLayout;

interface LayoutProps {
  children: React.ReactNode;
}

// 不需要布局的公開頁面路徑
const PUBLIC_ROUTES = ['/entry', '/login', '/register', '/forgot-password', '/verify-email'];

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { message } = App.useApp();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [verificationSending, setVerificationSending] = useState(false);
  const location = useLocation();
  const { isMobile } = useResponsive();

  // 使用導覽資料 Hook
  const {
    menuItems,
    navigationLoading,
    permissionsLoading,
    currentUser,
  } = useNavigationData();

  // 路由變更時自動關閉 Drawer
  useEffect(() => {
    if (isMobile && drawerVisible) {
      setDrawerVisible(false);
    }
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  // 檢查是否為公開頁面
  const isPublicRoute = PUBLIC_ROUTES.some(
    route => location.pathname === route || location.pathname.startsWith(route + '/')
  );

  // 處理使用者登出
  const handleUserLogout = () => {
    // 清除使用者狀態會由 useNavigationData 內部處理
  };

  // 行動版選單項目點擊後關閉 Drawer
  const handleMobileMenuClick = useCallback(() => {
    setDrawerVisible(false);
  }, []);

  // 重新發送驗證信
  const handleResendVerification = useCallback(async () => {
    setVerificationSending(true);
    try {
      await sendVerificationEmail();
      message.success('驗證信已發送，請檢查您的信箱');
    } catch {
      message.error('驗證信發送失敗，請稍後再試');
    } finally {
      setVerificationSending(false);
    }
  }, [message]);

  // 判斷是否需要顯示 Email 驗證提醒
  const showEmailVerificationBanner =
    currentUser && currentUser.email_verified === false;

  // 閒置超時自動登出（僅在非公開頁面啟用）
  useIdleTimeout({ enabled: !isPublicRoute });

  // 公開頁面直接渲染內容
  if (isPublicRoute) {
    return <>{children}</>;
  }

  return (
    <>
      <AntLayout style={{ minHeight: '100vh' }}>
        {/* 桌面版側邊欄 - 行動版隱藏 */}
        {!isMobile && (
          <Sidebar
            collapsed={collapsed}
            menuItems={menuItems}
            loading={navigationLoading || permissionsLoading}
          />
        )}

        {/* 行動版 Drawer 側邊欄 */}
        {isMobile && (
          <Drawer
            placement="left"
            width={256}
            open={drawerVisible}
            onClose={() => setDrawerVisible(false)}
            aria-label="導覽選單"
            styles={{
              body: { padding: 0, background: '#001529' },
              header: { display: 'none' },
            }}
          >
            <SidebarContent
              menuItems={menuItems}
              loading={navigationLoading || permissionsLoading}
              onMenuClick={handleMobileMenuClick}
            />
          </Drawer>
        )}

        {/* 主內容區 */}
        <AntLayout style={{
          marginLeft: isMobile ? 0 : (collapsed ? 80 : 200),
          transition: 'margin-left 0.2s'
        }}>
          {/* 頂部欄 */}
          <LayoutHeader
            collapsed={collapsed}
            onToggleCollapse={isMobile
              ? () => setDrawerVisible(!drawerVisible)
              : () => setCollapsed(!collapsed)
            }
            currentUser={currentUser}
            onUserLogout={handleUserLogout}
            isMobile={isMobile}
          />

          {/* Email 驗證提醒 Banner */}
          {showEmailVerificationBanner && (
            <Alert
              message="您的 Email 尚未驗證"
              description="部分功能可能受限。請檢查您的信箱並點擊驗證連結，或點擊按鈕重新發送驗證信。"
              type="warning"
              showIcon
              banner
              action={
                <AntButton
                  size="small"
                  type="primary"
                  loading={verificationSending}
                  onClick={handleResendVerification}
                >
                  重新發送驗證信
                </AntButton>
              }
              style={{ borderBottom: '1px solid #ffe58f' }}
            />
          )}

          {/* 內容區 */}
          <Content style={{
            padding: isMobile ? '12px' : '24px',
            background: '#f5f5f5',
            minHeight: 'calc(100vh - 64px)',
          }}>
            {children}
          </Content>
        </AntLayout>
      </AntLayout>

      {/* AI 公文搜尋浮動按鈕 */}
      <AIAssistantButton />
    </>
  );
};

export default Layout;
