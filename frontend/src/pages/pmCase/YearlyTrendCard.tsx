/**
 * PM 案件多年度趨勢卡片
 */
import React from 'react';
import { Card, Table, Progress, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { usePMYearlyTrend } from '../../hooks';
import type { PMYearlyTrendItem } from '../../types/pm';

const { Title } = Typography;

const columns: ColumnsType<PMYearlyTrendItem> = [
  {
    title: '年度',
    dataIndex: 'year',
    key: 'year',
    width: 80,
    render: (v: number) => `${v}`,
  },
  {
    title: '案件數',
    dataIndex: 'case_count',
    key: 'case_count',
    width: 90,
    align: 'right',
  },
  {
    title: '合約總額',
    dataIndex: 'total_contract',
    key: 'total_contract',
    width: 140,
    align: 'right',
    render: (v: string) => {
      const num = Number(v);
      return num ? num.toLocaleString() : '0';
    },
  },
  {
    title: '已結案',
    dataIndex: 'closed_count',
    key: 'closed_count',
    width: 80,
    align: 'right',
  },
  {
    title: '進行中',
    dataIndex: 'in_progress_count',
    key: 'in_progress_count',
    width: 80,
    align: 'right',
  },
  {
    title: '平均進度',
    dataIndex: 'avg_progress',
    key: 'avg_progress',
    width: 150,
    render: (v: number) => <Progress percent={v} size="small" />,
  },
];

const YearlyTrendCard: React.FC = () => {
  const { data, isLoading } = usePMYearlyTrend();

  return (
    <Card style={{ marginBottom: 16 }}>
      <Title level={5} style={{ marginBottom: 16 }}>多年度案件趨勢</Title>
      <Table<PMYearlyTrendItem>
        columns={columns}
        dataSource={data ?? []}
        rowKey="year"
        loading={isLoading}
        pagination={false}
        size="small"
        scroll={{ x: 620 }}
      />
    </Card>
  );
};

export default YearlyTrendCard;
