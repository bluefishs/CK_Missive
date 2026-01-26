/**
 * 關聯公文 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  Tooltip,
  Empty,
} from 'antd';
import {
  FileTextOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';
import type { RelatedDocumentsTabProps, RelatedDocument } from './types';

const { Text } = Typography;

// 解析機關名稱：提取括號內的名稱
const extractAgencyName = (value: string | undefined): string => {
  if (!value) return '-';
  const agencies = value.split(' | ').map(agency => {
    const match = agency.match(/\(([^)]+)\)/);
    return match ? match[1] : agency;
  });
  return agencies.join('、');
};

export const RelatedDocumentsTab: React.FC<RelatedDocumentsTabProps> = ({
  relatedDocs,
  onRefresh,
}) => {
  const navigate = useNavigate();

  const columns: ColumnsType<RelatedDocument> = [
    {
      title: '公文字號',
      dataIndex: 'doc_number',
      key: 'doc_number',
      width: 180,
      ellipsis: true,
      render: (text, record) => (
        <Button
          type="link"
          style={{ padding: 0, fontWeight: 500 }}
          onClick={() => navigate(`/documents/${record.id}`)}
        >
          {text}
        </Button>
      ),
    },
    {
      title: '發文形式',
      dataIndex: 'delivery_method',
      key: 'delivery_method',
      width: 95,
      align: 'center',
      render: (method: string) => {
        const colorMap: Record<string, string> = {
          '電子交換': 'green',
          '紙本郵寄': 'orange',
          '電子+紙本': 'blue',
        };
        return <Tag color={colorMap[method] || 'default'}>{method || '電子交換'}</Tag>;
      },
    },
    {
      title: '收發單位',
      key: 'correspondent',
      width: 160,
      ellipsis: true,
      render: (_: unknown, record: RelatedDocument) => {
        const rawValue = record.category === '收文' ? record.sender : record.receiver;
        const labelPrefix = record.category === '收文' ? '來文：' : '發至：';
        const labelColor = record.category === '收文' ? '#52c41a' : '#1890ff';
        const displayValue = extractAgencyName(rawValue);

        return (
          <Tooltip title={displayValue}>
            <Text ellipsis>
              <span style={{ color: labelColor, fontWeight: 500, fontSize: '11px' }}>
                {labelPrefix}
              </span>
              {displayValue}
            </Text>
          </Tooltip>
        );
      },
    },
    {
      title: '公文日期',
      dataIndex: 'doc_date',
      key: 'doc_date',
      width: 100,
      align: 'center',
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '主旨',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
    },
  ];

  return (
    <Card
      title={
        <Space>
          <FileTextOutlined />
          <span>關聯公文</span>
          <Tag color="blue">{relatedDocs.length} 件</Tag>
        </Space>
      }
      extra={
        <Space>
          <Text type="secondary">自動關聯本專案所有公文</Text>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={onRefresh}
          >
            重新整理
          </Button>
        </Space>
      }
    >
      {relatedDocs.length > 0 ? (
        <Table
          columns={columns}
          dataSource={relatedDocs}
          rowKey="id"
          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (t) => `共 ${t} 筆公文` }}
          size="middle"
        />
      ) : (
        <Empty
          description={
            <span>
              尚無關聯公文<br />
              <Text type="secondary">請在公文管理頁面新增公文時，選擇本專案作為「承攬案件」</Text>
            </span>
          }
        />
      )}
    </Card>
  );
};

export default RelatedDocumentsTab;
