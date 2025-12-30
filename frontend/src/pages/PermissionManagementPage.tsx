import React, { useState, useEffect } from 'react';
import {
  Card,
  Typography,
  Space,
  Button,
  Alert,
  Row,
  Col,
  message,
  Select,
  Input,
  Table,
  Modal,
  Form
} from 'antd';
import {
  SecurityScanOutlined,
  UserOutlined,
  EditOutlined,
  PlusOutlined,
  SearchOutlined,
  TeamOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

import PermissionManager from '../components/admin/PermissionManager';
import { 
  PERMISSION_CATEGORIES, 
  getPermissionDisplayName,
  getCategoryDisplayName,
  groupPermissionsByCategory
} from '../constants/permissions';
import authService from '../services/authService';

const { Title, Text } = Typography;
const { Option } = Select;

// 模擬使用者權限數據
interface UserPermissionSummary {
  id: number;
  username: string;
  full_name: string;
  email: string;
  role: string;
  permissions: string[];
  is_active: boolean;
}

const PermissionManagementPage: React.FC = () => {
  const [users, setUsers] = useState<UserPermissionSummary[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserPermissionSummary | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [language, setLanguage] = useState<'zh' | 'en'>('zh');
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadMockUsers();
  }, []);

  const loadMockUsers = () => {
    // 載入模擬使用者數據
    const mockUsers: UserPermissionSummary[] = [
      {
        id: 1,
        username: 'admin',
        full_name: '系統管理員',
        email: 'admin@ck-missive.com',
        role: 'superuser',
        permissions: [
          'documents:read', 'documents:create', 'documents:edit', 'documents:delete',
          'projects:read', 'projects:create', 'projects:edit', 'projects:delete',
          'agencies:read', 'agencies:create', 'agencies:edit', 'agencies:delete',
          'vendors:read', 'vendors:create', 'vendors:edit', 'vendors:delete',
          'calendar:read', 'calendar:edit',
          'reports:view', 'reports:export',
          'admin:users', 'admin:settings', 'admin:site_management'
        ],
        is_active: true
      },
      {
        id: 2,
        username: 'manager',
        full_name: '專案經理',
        email: 'manager@ck-missive.com',
        role: 'admin',
        permissions: [
          'documents:read', 'documents:create', 'documents:edit',
          'projects:read', 'projects:create', 'projects:edit',
          'agencies:read', 'vendors:read',
          'calendar:read', 'calendar:edit',
          'reports:view'
        ],
        is_active: true
      },
      {
        id: 3,
        username: 'user1',
        full_name: '一般使用者',
        email: 'user1@ck-missive.com',
        role: 'user',
        permissions: [
          'documents:read',
          'projects:read',
          'agencies:read',
          'calendar:read'
        ],
        is_active: true
      }
    ];

    setUsers(mockUsers);
  };

  const handleEditPermissions = (user: UserPermissionSummary) => {
    setSelectedUser(user);
    setModalVisible(true);
  };

  const handlePermissionUpdate = (permissions: string[]) => {
    if (!selectedUser) return;

    // 更新使用者權限
    const updatedUsers = users.map(user => 
      user.id === selectedUser.id 
        ? { ...user, permissions }
        : user
    );

    setUsers(updatedUsers);
    setSelectedUser({ ...selectedUser, permissions });
    
    message.success(
      language === 'zh' 
        ? `已更新 ${selectedUser.full_name} 的權限` 
        : `Updated permissions for ${selectedUser.full_name}`
    );
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = !searchText || 
      user.full_name.toLowerCase().includes(searchText.toLowerCase()) ||
      user.email.toLowerCase().includes(searchText.toLowerCase());
    
    const matchesRole = !roleFilter || user.role === roleFilter;
    
    return matchesSearch && matchesRole;
  });

  const getPermissionSummary = (permissions: string[]) => {
    const grouped = groupPermissionsByCategory(permissions);
    const totalCategories = Object.keys(PERMISSION_CATEGORIES).length;
    const userCategories = Object.keys(grouped).length;
    
    return `${permissions.length} ${language === 'zh' ? '個權限' : 'permissions'} (${userCategories}/${totalCategories} ${language === 'zh' ? '個分類' : 'categories'})`;
  };

  const getRoleDisplayName = (role: string) => {
    const roleNames = {
      zh: {
        superuser: '超級管理員',
        admin: '管理員',
        user: '一般使用者'
      },
      en: {
        superuser: 'Super Admin',
        admin: 'Administrator',
        user: 'User'
      }
    };
    
    return roleNames[language][role as keyof typeof roleNames.zh] || role;
  };

  const columns: ColumnsType<UserPermissionSummary> = [
    {
      title: language === 'zh' ? '使用者' : 'User',
      key: 'user',
      render: (_, record) => (
        <Space>
          <UserOutlined style={{ fontSize: '16px', color: '#1976d2' }} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.full_name}</div>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.email}
            </Text>
          </div>
        </Space>
      ),
    },
    {
      title: language === 'zh' ? '角色' : 'Role',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => getRoleDisplayName(role),
    },
    {
      title: language === 'zh' ? '權限摘要' : 'Permission Summary',
      key: 'permissions',
      render: (_, record) => (
        <div>
          <Text>{getPermissionSummary(record.permissions)}</Text>
        </div>
      ),
    },
    {
      title: language === 'zh' ? '狀態' : 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <span style={{ 
          color: isActive ? '#52c41a' : '#ff4d4f',
          fontWeight: 500
        }}>
          {isActive 
            ? (language === 'zh' ? '啟用' : 'Active')
            : (language === 'zh' ? '停用' : 'Inactive')
          }
        </span>
      ),
    },
    {
      title: language === 'zh' ? '操作' : 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          icon={<EditOutlined />}
          onClick={() => handleEditPermissions(record)}
        >
          {language === 'zh' ? '管理權限' : 'Manage Permissions'}
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: '24px' }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={3} style={{ margin: 0 }}>
                <SecurityScanOutlined style={{ marginRight: '8px' }} />
                {language === 'zh' ? '權限管理中心' : 'Permission Management Center'}
              </Title>
              <Text type="secondary">
                {language === 'zh' 
                  ? '管理系統使用者的詳細權限設定，支援中英文對照顯示'
                  : 'Manage detailed permission settings for system users with bilingual display support'
                }
              </Text>
            </Col>
            <Col>
              <Space>
                <Select
                  value={language}
                  onChange={setLanguage}
                  style={{ width: 120 }}
                >
                  <Option value="zh">中文</Option>
                  <Option value="en">English</Option>
                </Select>
              </Space>
            </Col>
          </Row>
        </div>

        <Alert
          message={language === 'zh' ? '權限管理說明' : 'Permission Management Guide'}
          description={
            language === 'zh' 
              ? '此頁面提供完整的權限管理功能，包含中英文對照、分類管理、批量操作等功能。點擊「管理權限」按鈕可以詳細設定各使用者的權限。'
              : 'This page provides comprehensive permission management features including bilingual display, category management, and batch operations. Click "Manage Permissions" to configure detailed user permissions.'
          }
          type="info"
          showIcon
          style={{ marginBottom: '24px' }}
        />

        <Row gutter={16} style={{ marginBottom: '16px' }}>
          <Col span={6}>
            <Input
              placeholder={language === 'zh' ? '搜尋使用者' : 'Search users'}
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
          </Col>
          <Col span={4}>
            <Select
              placeholder={language === 'zh' ? '角色篩選' : 'Filter by role'}
              allowClear
              value={roleFilter || undefined}
              onChange={setRoleFilter}
              style={{ width: '100%' }}
            >
              <Option value="superuser">{getRoleDisplayName('superuser')}</Option>
              <Option value="admin">{getRoleDisplayName('admin')}</Option>
              <Option value="user">{getRoleDisplayName('user')}</Option>
            </Select>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={filteredUsers}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              language === 'zh' 
                ? `第 ${range[0]}-${range[1]} 項，共 ${total} 項`
                : `${range[0]}-${range[1]} of ${total} items`,
          }}
        />

        {/* 權限詳細分類摘要 */}
        <div style={{ marginTop: '24px' }}>
          <Title level={4}>
            {language === 'zh' ? '權限分類說明' : 'Permission Categories'}
          </Title>
          <Row gutter={[16, 16]}>
            {Object.entries(PERMISSION_CATEGORIES).map(([key, category]) => (
              <Col xs={24} sm={12} lg={8} key={key}>
                <Card size="small" style={{ height: '100%' }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Text strong>
                      {language === 'zh' ? category.name_zh : category.name_en}
                    </Text>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {category.permissions.length} {language === 'zh' ? '個權限項目' : 'permissions'}
                    </Text>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      </Card>

      {/* 權限管理 Modal */}
      <Modal
        title={
          <Space>
            <SecurityScanOutlined />
            {language === 'zh' ? '詳細權限設定' : 'Detailed Permission Settings'}
            {selectedUser && (
              <Text type="secondary">
                - {selectedUser.full_name}
              </Text>
            )}
          </Space>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setModalVisible(false)}>
            {language === 'zh' ? '取消' : 'Cancel'}
          </Button>,
          <Button 
            key="save" 
            type="primary" 
            onClick={() => setModalVisible(false)}
          >
            {language === 'zh' ? '儲存' : 'Save'}
          </Button>
        ]}
        width={1000}
        style={{ top: '20px' }}
      >
        {selectedUser && (
          <PermissionManager
            userPermissions={selectedUser.permissions}
            onPermissionChange={handlePermissionUpdate}
            readOnly={false}
          />
        )}
      </Modal>
    </div>
  );
};

export default PermissionManagementPage;