/**
 * Header 頂部欄元件
 * 從 Layout.tsx 拆分出來
 */

import React from 'react';
import { Layout, Typography, Button, Avatar, Dropdown, Space } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  ProfileOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { UserInfo } from '../../services/authService';
import authService from '../../services/authService';
import { NotificationCenter } from '../common';
import { logger } from '../../services/logger';

const { Header: AntHeader } = Layout;
const { Title } = Typography;

interface HeaderProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  currentUser: UserInfo | null;
  onUserLogout: () => void;
}

const Header: React.FC<HeaderProps> = ({
  collapsed,
  onToggleCollapse,
  currentUser,
  onUserLogout
}) => {
  const navigate = useNavigate();

  // 取得角色顯示名稱
  const getRoleDisplayName = (role?: string): string => {
    switch (role) {
      case 'superuser': return '超級管理員';
      case 'admin': return '管理員';
      default: return '一般使用者';
    }
  };

  // 使用者下拉選單項目
  const userMenuItems = [
    {
      key: 'user-info',
      icon: <UserOutlined />,
      label: `角色：${getRoleDisplayName(currentUser?.role)}`,
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
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          onClick={onToggleCollapse}
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

      {/* 右側：通知中心 + 使用者選單 */}
      <Space size="large">
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
            <span style={{ color: '#666' }}>
              {currentUser?.full_name || currentUser?.username || '訪客'}
            </span>
          </Space>
        </Dropdown>
      </Space>
    </AntHeader>
  );
};

export default Header;
