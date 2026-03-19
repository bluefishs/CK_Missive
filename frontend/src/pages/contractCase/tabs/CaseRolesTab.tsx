/**
 * 案件角色 Tab - 統一顯示內部同仁與機關承辦
 *
 * @version 1.0.0
 * @date 2026-03-17
 */

import React from 'react';
import {
  Card,
  Table,
  Tag,
  Avatar,
  Space,
  Empty,
} from 'antd';
import {
  TeamOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { Staff } from './types';
import type { ProjectAgencyContact } from '../../../api/projectAgencyContacts';
import { STAFF_ROLE_OPTIONS } from './constants';

/** Unified role row for display */
interface CaseRoleRow {
  key: string;
  name: string;
  role: string;
  source: 'internal' | 'external';
  department?: string;
  phone?: string;
  email?: string;
  isPrimary?: boolean;
}

export interface CaseRolesTabProps {
  staffList: Staff[];
  agencyContacts: ProjectAgencyContact[];
}

const getStaffRoleColor = (role: string) => {
  const option = STAFF_ROLE_OPTIONS.find(opt => opt.value === role);
  return option?.color || 'default';
};

export const CaseRolesTab: React.FC<CaseRolesTabProps> = ({
  staffList,
  agencyContacts,
}) => {
  const rows: CaseRoleRow[] = [
    ...staffList.map((s): CaseRoleRow => ({
      key: `staff-${s.id}`,
      name: s.name,
      role: s.role,
      source: 'internal',
      department: s.department,
      phone: s.phone,
      email: s.email,
    })),
    ...agencyContacts.map((c): CaseRoleRow => ({
      key: `agency-${c.id}`,
      name: c.contact_name,
      role: c.position || '機關承辦',
      source: 'external',
      department: c.department,
      phone: c.phone || c.mobile,
      email: c.email,
      isPrimary: c.is_primary,
    })),
  ];

  const columns: ColumnsType<CaseRoleRow> = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space>
          <Avatar
            icon={<UserOutlined />}
            style={{
              backgroundColor: record.source === 'internal'
                ? (getStaffRoleColor(record.role) === 'red' ? '#f5222d' : '#1890ff')
                : '#87d068',
            }}
          />
          <span style={{ fontWeight: 500 }}>{name}</span>
          {record.isPrimary && <Tag color="blue">主要</Tag>}
        </Space>
      ),
    },
    {
      title: '來源',
      dataIndex: 'source',
      key: 'source',
      width: 100,
      filters: [
        { text: '內部', value: 'internal' },
        { text: '外部', value: 'external' },
      ],
      onFilter: (value, record) => record.source === value,
      render: (source: 'internal' | 'external') => (
        <Tag color={source === 'internal' ? 'blue' : 'green'}>
          {source === 'internal' ? '內部' : '外部'}
        </Tag>
      ),
    },
    {
      title: '角色/職稱',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      render: (role: string, record) => (
        <Tag color={record.source === 'internal' ? getStaffRoleColor(role) : 'cyan'}>
          {role}
        </Tag>
      ),
    },
    {
      title: '部門/單位',
      dataIndex: 'department',
      key: 'department',
      render: (text?: string) => text || '-',
    },
    {
      title: '聯絡方式',
      key: 'contact',
      render: (_: unknown, record: CaseRoleRow) => (
        <Space direction="vertical" size={0}>
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
          {record.email && <span><MailOutlined /> {record.email}</span>}
          {!record.phone && !record.email && '-'}
        </Space>
      ),
    },
  ];

  const internalCount = staffList.length;
  const externalCount = agencyContacts.length;

  return (
    <Card
      title={
        <Space>
          <TeamOutlined />
          <span>案件角色</span>
          <Tag color="blue">{internalCount} 內部</Tag>
          <Tag color="green">{externalCount} 外部</Tag>
        </Space>
      }
    >
      {rows.length > 0 ? (
        <Table
          columns={columns}
          dataSource={rows}
          rowKey="key"
          pagination={false}
          size="middle"
          scroll={{ x: 700 }}
        />
      ) : (
        <Empty description="尚無案件角色資料" />
      )}
    </Card>
  );
};

export default CaseRolesTab;
