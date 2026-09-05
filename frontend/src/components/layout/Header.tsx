/**
 * Header 頂部欄元件
 * 從 Layout.tsx 拆分出來
 */

import React from 'react';
import { Layout, Typography, Button, Avatar, Dropdown, Space, Tooltip, Tag } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MenuOutlined,
  UserOutlined,
  LogoutOutlined,
  ProfileOutlined,
  BulbOutlined,
  MobileOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { UserInfo } from '../../services/authService';
import authService from '../../services/authService';
import { NotificationCenter } from '../common';
import { IdleCountdownBadge } from './IdleCountdownBadge';
import { logger } from '../../services/logger';
import { useResponsive } from '../../hooks/utility/useResponsive';
import { getRoleDisplayName } from '../../constants/permissions';

const { Header: AntHeader } = Layout;
const { Title } = Typography;

interface HeaderProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  currentUser: UserInfo | null;
  onUserLogout: () => void;
  /** 是否為行動裝置模式 */
  isMobile?: boolean;
}

const Header: React.FC<HeaderProps> = ({
  collapsed,
  onToggleCollapse,
  currentUser,
  onUserLogout,
  isMobile = false,
}) => {
  const navigate = useNavigate();
  const { layoutMode, setLayoutMode, deviceMobile } = useResponsive();

  // 角色顯示名稱一律走 SSOT（`constants/permissions.ts` 的 USER_ROLES）。
  //
  // ⚠️ 2026-08-27：這裡原本自己定義了一個**同名**的本地函式蓋掉 SSOT 那支，
  //    而它只認得 superuser／admin，其餘一律落到 `default: '一般使用者'`。
  //    於是 `role='staff'` 的同仁在右上角看到的是「一般使用者」，
  //    而 `/profile` 顯示「承辦同仁」—— owner 回報的正是這兩處對不起來。
  //
  //    真正難看的是那個 `default`：它把**任何認不得的角色**都降級成一個
  //    看起來完全正常的值。`staff` 與 `unverified` 都會顯示成「一般使用者」，
  //    而「我不認得這個角色」與「這個人就是一般使用者」在畫面上長得一模一樣
  //    （同「空清單退化成數字」那一族）。SSOT 那支認不得時回 roleKey 本身，
  //    看得出是沒對應到。
  const roleLabel = getRoleDisplayName(currentUser?.role || '');

  // 使用者下拉選單項目
  const userMenuItems = [
    {
      key: 'user-info',
      icon: <UserOutlined />,
      label: `角色：${roleLabel}`,
      disabled: true,
      style: { color: '#666', fontSize: '12px' }
    },
    { type: "divider" as const },
    {
      key: 'profile',
      icon: <ProfileOutlined />,
      label: '個人設定',
      onClick: () => navigate('/profile'),
    },
    { type: "divider" as const },
    {
      // 2026-09-05 owner：偵測登入裝置自動切換 RWD 模式；這裡讓使用者也能強制
      key: 'layout',
      icon: <MobileOutlined />,
      label: `版面：${layoutMode === 'mobile' ? '手機版' : layoutMode === 'desktop' ? '桌面版' : `自動（偵測為${deviceMobile ? '行動裝置' : '桌面'}）`}`,
      children: [
        { key: 'layout-auto', label: `自動${layoutMode === 'auto' ? ' ✓' : ''}`, onClick: () => setLayoutMode('auto') },
        { key: 'layout-mobile', label: `手機版${layoutMode === 'mobile' ? ' ✓' : ''}`, onClick: () => setLayoutMode('mobile') },
        { key: 'layout-desktop', label: `桌面版${layoutMode === 'desktop' ? ' ✓' : ''}`, onClick: () => setLayoutMode('desktop') },
      ],
    },
    { type: "divider" as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '登出',
      onClick: async () => {
        try {
          await authService.logout();
          onUserLogout();
          navigate('/login');
        } catch (error) {
          logger.error('Logout failed:', error);
        }
      },
    },
  ];

  return (
    <AntHeader style={{
      background: '#fff',
      padding: '0 24px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 999,
    }}>
      {/* 左側：折疊按鈕 + 標題 */}
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <Button
          type="text"
          icon={isMobile ? <MenuOutlined /> : (collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />)}
          onClick={onToggleCollapse}
          aria-label={isMobile ? '開啟選單' : (collapsed ? '展開側邊欄' : '收合側邊欄')}
          aria-expanded={isMobile ? undefined : !collapsed}
          style={{
            fontSize: '16px',
            width: 40,
            height: 40,
          }}
        />

        <Title
          level={3}
          style={{
            margin: '0 0 0 16px',
            color: '#1976d2',
            fontSize: 18,
          }}
        >
          公文管理系統
        </Title>
      </div>

      {/* 右側：坤哥入口 + 通知中心 + 使用者選單
          2026-08-02：窄螢幕改小間距。這一列是**全站共用**，在 390px 下右緣落在 476px，
          等於每一頁都被撐開 86px —— 行動觀測量到的 12 頁整頁溢出全部源自這裡。 */}
      <Space size={isMobile ? 'small' : 'large'}>
        <Tooltip title="坤哥 · Missive 意識體：記憶、學習、質疑、進化">
          <Tag
            color="gold"
            style={{
              cursor: 'pointer',
              fontSize: 13,
              padding: '4px 12px',
              borderRadius: 16,
              margin: 0,
              background: 'linear-gradient(90deg, #ffd700 0%, #ffb300 100%)',
              color: '#5c2d00',
              border: 'none',
              fontWeight: 600,
            }}
            onClick={() => navigate('/kunge')}
          >
            <BulbOutlined /> 坤哥
          </Tag>
        </Tooltip>

        <NotificationCenter />

        <Dropdown
          menu={{ items: userMenuItems }}
          placement="bottomRight"
        >
          <Space style={{ cursor: 'pointer' }}>
            <Avatar
              src={currentUser?.avatar_url}
              icon={<UserOutlined />}
              style={{ backgroundColor: '#1976d2' }}
            />
            {/* 手機不顯示名字：Avatar 仍可點開選單，選單第一項就是「角色：…」 */}
            <span style={{ color: '#666', display: isMobile ? 'none' : undefined }}>
              {currentUser?.full_name || currentUser?.username || (
                // F24 (5/04 debug)：訪客 fallback 加 console.warn 協助診斷
                // 出現此 fallback = useNavigationData 拿到 currentUser=null
                // 可能根因：localStorage user_info 缺、saveAuthData race、bundle stale
                (() => {
                  if (typeof window !== 'undefined') {
                    const uinfo = window.localStorage.getItem('user_info');
                    console.warn(
                      '[Header] currentUser=null 顯示「訪客」。',
                      'localStorage.user_info =',
                      uinfo ? uinfo.slice(0, 200) : 'NULL',
                    );
                  }
                  return '訪客';
                })()
              )}
            </span>
          </Space>
        </Dropdown>

        {/* 2026-06-02 閒置登出倒數（使用者名稱後）— 無操作 30 分鐘自動登出，任何操作即重置
            2026-08-02：窄螢幕不顯示（它是最寬的一項），登出行為本身不受影響 */}
        {!isMobile && <IdleCountdownBadge />}
      </Space>
    </AntHeader>
  );
};

export default React.memo(Header);
