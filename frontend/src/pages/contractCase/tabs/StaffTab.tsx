/**
 * 承辦同仁 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import { Card, Button, Space, Tag, Avatar, Empty } from 'antd';
import { EnhancedTable, type ResponsiveColumn } from '../../../components/common/EnhancedTable';
import { TeamOutlined, PlusOutlined, UserOutlined, PhoneOutlined, MailOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../../router/types';
import type { StaffTabProps, Staff } from './types';
import { STAFF_ROLE_OPTIONS } from './constants';

// 輔助函數
const getStaffRoleColor = (role: string) => {
  const option = STAFF_ROLE_OPTIONS.find(opt => opt.value === role);
  return option?.color || 'default';
};

export const StaffTab: React.FC<StaffTabProps> = ({
  staffList,
  projectId,
}) => {
  const navigate = useNavigate();
  const columns: ResponsiveColumn<Staff>[] = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: getStaffRoleColor(record.role) === 'red' ? '#f5222d' : '#1890ff' }} />
          <span style={{ fontWeight: 500 }}>{name}</span>
        </Space>
      ),
    },
    {
      title: '角色/職責',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      // 2026-08-04：就地編輯一併移除 —— 詳情頁 tab 只呈現，角色變更在填報頁。
      render: (role: string) => <Tag color={getStaffRoleColor(role)}>{role}</Tag>,
    },
    {
      title: '部門', hideOnMobile: true,
      dataIndex: 'department',
      key: 'department',
    },
    {
      title: '聯絡方式', hideOnMobile: true,
      key: 'contact',
      render: (_, record) => (
        <Space vertical size="small">
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
          {record.email && <span><MailOutlined /> {record.email}</span>}
        </Space>
      ),
    },
    {
      title: '加入日期', hideOnMobile: true,
      dataIndex: 'join_date',
      key: 'join_date',
    },
    {
      title: '狀態', hideOnMobile: true,
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status === 'active' ? '在職' : '離職'}
        </Tag>
      ),
    },
  ];

  return (
    <>
      <Card
        title={
          <Space>
            <TeamOutlined />
            <span>承辦同仁</span>
            <Tag color="blue">{staffList.length} 人</Tag>
          </Space>
        }
        extra={
          <Button
            type="primary" icon={<PlusOutlined />}
            onClick={() => navigate(ROUTES.CONTRACT_CASE_STAFF_CREATE.replace(':caseId', String(projectId)))}
          >
            新增同仁
          </Button>
        }
      >
        {staffList.length > 0 ? (
          <EnhancedTable
            columns={columns}
            dataSource={staffList}
            rowKey="id"
            pagination={false}
            size="middle"
            onRow={(row: Staff) => ({
              // 操作欄與 Modal 移除後，這是進到編輯/移除的唯一入口
              onClick: () => navigate(
                ROUTES.CONTRACT_CASE_STAFF_EDIT
                  .replace(':caseId', String(projectId))
                  .replace(':userId', String(row.user_id)),
              ),
              style: { cursor: 'pointer' },
            })}
          />
        ) : (
          <Empty description="尚無承辦同仁" />
        )}
      </Card>

    </>
  );
};

export default StaffTab;
