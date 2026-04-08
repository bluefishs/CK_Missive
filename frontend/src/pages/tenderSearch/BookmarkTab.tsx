/**
 * 收藏 Tab - 收藏標案列表
 */
import React from 'react';
import {
  Tag, Button, Typography, Empty, Popconfirm,
} from 'antd';
import { EnhancedTable } from '../../components/common/EnhancedTable';
import { BankOutlined, DeleteOutlined } from '@ant-design/icons';
import type { UseMutationResult } from '@tanstack/react-query';

const { Text } = Typography;

const BOOKMARK_STATUS_MAP: Record<string, { color: string; label: string }> = {
  tracking: { color: 'blue', label: '追蹤中' },
  applied: { color: 'orange', label: '已投標' },
  won: { color: 'green', label: '得標' },
  lost: { color: 'default', label: '未得標' },
};

interface Bookmark {
  id: number;
  unit_id: string;
  job_number: string;
  title: string;
  unit_name: string | null;
  status: string;
  case_code: string | null;
  created_at: string | null;
}

export interface BookmarkTabProps {
  bookmarks: Bookmark[] | undefined;
  deleteBm: UseMutationResult<void, Error, number>;
  onRowClick: (record: Bookmark) => void;
}

const BookmarkTab: React.FC<BookmarkTabProps> = ({ bookmarks, deleteBm, onRowClick }) => {
  if (!bookmarks?.length) {
    return <Empty description="在搜尋結果中點擊 ★ 即可收藏標案" />;
  }

  return (
    <EnhancedTable
      dataSource={bookmarks}
      rowKey="id"
      size="middle"
      pagination={false}
      onRow={(record) => ({
        onClick: () => onRowClick(record),
        style: { cursor: 'pointer' },
      })}
      columns={[
        {
          title: '標案名稱', dataIndex: 'title', ellipsis: true,
          render: (title: string) => <Text strong>{title}</Text>,
        },
        {
          title: '招標機關', dataIndex: 'unit_name', width: 180, ellipsis: true,
          render: (v: string | null) => v && v !== '(未知機關)'
            ? <><BankOutlined style={{ marginRight: 4, color: '#8c8c8c' }} />{v}</>
            : <Text type="secondary">-</Text>,
        },
        {
          title: '狀態', dataIndex: 'status', width: 90, align: 'center' as const,
          render: (v: string) => <Tag color={BOOKMARK_STATUS_MAP[v]?.color}>{BOOKMARK_STATUS_MAP[v]?.label ?? v}</Tag>,
        },
        {
          title: '案號', dataIndex: 'case_code', width: 150,
          render: (v: string | null) => v ? <Tag color="green">{v}</Tag> : <Text type="secondary">-</Text>,
        },
        {
          title: '收藏時間', dataIndex: 'created_at', width: 110,
          render: (v: string | null) => v ? <Text type="secondary" style={{ fontSize: 12 }}>{new Date(v).toLocaleDateString('zh-TW')}</Text> : '-',
        },
        {
          title: '', key: 'action', width: 50, align: 'center' as const,
          render: (_: unknown, record: Bookmark) => (
            <Popconfirm title="移除收藏？" onConfirm={(e) => { e?.stopPropagation(); deleteBm.mutate(record.id); }}>
              <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={e => e.stopPropagation()} />
            </Popconfirm>
          ),
        },
      ]}
    />
  );
};

export default BookmarkTab;
