/**
 * 機關承辦 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import {
  Card, Button, Space, Tag, Avatar, Empty,
} from 'antd';
import { EnhancedTable, type ResponsiveColumn } from '../../../components/common/EnhancedTable';
import {
  BankOutlined,
  PlusOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../../router/types';
import type { AgencyContactTabProps } from './types';
import type { ProjectAgencyContact } from '../../../api/projectAgencyContacts';

export const AgencyContactTab: React.FC<AgencyContactTabProps> = ({
  agencyContacts,
  projectId,
}) => {
  const navigate = useNavigate();
  const columns: ResponsiveColumn<ProjectAgencyContact>[] = [
    {
      title: '姓名',
      dataIndex: 'contact_name',
      key: 'contact_name',
      render: (name: string, record: ProjectAgencyContact) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: record.is_primary ? '#1890ff' : '#87d068' }} />
          <span>{name}</span>
          {record.is_primary && <Tag color="blue">主要</Tag>}
        </Space>
      ),
    },
    {
      title: '職稱', hideOnMobile: true,
      dataIndex: 'position',
      key: 'position',
      render: (text: string) => text || '-',
    },
    {
      title: '單位/科室', hideOnMobile: true,
      dataIndex: 'department',
      key: 'department',
      render: (text: string) => text || '-',
    },
    {
      title: '聯絡電話',
      key: 'phones',
      render: (_: unknown, record: ProjectAgencyContact) => (
        <Space vertical size={0}>
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
          {record.mobile && <span><PhoneOutlined /> {record.mobile}</span>}
          {!record.phone && !record.mobile && '-'}
        </Space>
      ),
    },
    {
      title: 'Email', hideOnMobile: true,
      dataIndex: 'email',
      key: 'email',
      render: (email: string) => email ? <a href={`mailto:${email}`}><MailOutlined /> {email}</a> : '-',
    },
  ];

  return (
    <Card
      title={
        <Space>
          <BankOutlined />
          <span>機關承辦</span>
          <Tag color="blue">{agencyContacts.length} 人</Tag>
        </Space>
      }
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate(
            ROUTES.CONTRACT_CASE_AGENCY_CONTACT_CREATE.replace(':caseId', String(projectId)),
          )}
        >
          新增承辦人
        </Button>
      }
    >
      {agencyContacts.length > 0 ? (
        <EnhancedTable
          columns={columns}
          dataSource={agencyContacts}
          rowKey="id"
          pagination={false}
          size="middle"
          onRow={(row: ProjectAgencyContact) => ({
            // 2026-08-04：操作欄與 Modal 一併移除（詳情頁 tab 只呈現，比照 /documents/:id；
            // 且專案規約本就是 CRUD 導頁不用 Modal）——編輯與刪除都在填報頁的標題列。
            onClick: () => navigate(
              ROUTES.CONTRACT_CASE_AGENCY_CONTACT_EDIT
                .replace(':caseId', String(projectId))
                .replace(':contactId', String(row.id)),
            ),
            style: { cursor: 'pointer' },
          })}
        />
      ) : (
        <Empty description="尚無機關承辦資料" />
      )}

    </Card>
  );
};

export default AgencyContactTab;
