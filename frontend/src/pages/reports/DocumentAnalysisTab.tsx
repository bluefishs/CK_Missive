/**
 * 公文數量分析 Tab
 *
 * 純 UI 元件，所有資料與邏輯由 useDocumentAnalysis Hook 提供。
 * 功能：收發文統計卡片、公文趨勢圖、來文機關排名、受文者排名。
 *
 * @version 1.2.0 - 整合公文趨勢圖（從 Dashboard 遷移）
 */

import React from 'react';
import {
  Card,
  Typography,
  Row,
  Col,
  Statistic,
  Select,
  Space,
  Table,
  Spin,
  Empty,
} from 'antd';
import {
  FileTextOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import { useDocumentAnalysis } from './hooks/useDocumentAnalysis';
import { useTableSearch } from './hooks/useTableSearch';
import { DocumentTrendsChart } from '../../components/dashboard';

const { Text } = Typography;

// 表格資料型別
interface NameCountRow {
  name: string;
  count: number;
}

interface DocumentAnalysisTabProps {
  isMobile: boolean;
}

const DocumentAnalysisTab: React.FC<DocumentAnalysisTabProps> = ({ isMobile }) => {
  const {
    loading,
    selectedYear,
    setSelectedYear,
    yearOptions,
    documents,
    stats,
  } = useDocumentAnalysis();

  // 表格搜尋功能
  const { getColumnSearchProps: getSenderSearchProps } = useTableSearch<NameCountRow>();
  const { getColumnSearchProps: getReceiverSearchProps } = useTableSearch<NameCountRow>();

  // 來文機關表格欄位（含搜尋篩選）
  const senderColumns = [
    {
      title: '來文機關',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      sorter: (a: NameCountRow, b: NameCountRow) => a.name.localeCompare(b.name, 'zh-TW'),
      ...getSenderSearchProps('name', '機關名稱'),
    },
    {
      title: '收文數',
      dataIndex: 'count',
      key: 'count',
      width: 80,
      sorter: (a: NameCountRow, b: NameCountRow) => a.count - b.count,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '占比',
      key: 'percentage',
      width: 70,
      render: (_: unknown, record: NameCountRow) => {
        const pct = stats.receiveCount > 0 ? (record.count / stats.receiveCount) * 100 : 0;
        return `${pct.toFixed(1)}%`;
      },
    },
  ];

  // 受文者表格欄位（含搜尋篩選）
  const receiverColumns = [
    {
      title: '受文者',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      sorter: (a: NameCountRow, b: NameCountRow) => a.name.localeCompare(b.name, 'zh-TW'),
      ...getReceiverSearchProps('name', '受文者名稱'),
    },
    {
      title: '發文數',
      dataIndex: 'count',
      key: 'count',
      width: 80,
      sorter: (a: NameCountRow, b: NameCountRow) => a.count - b.count,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '占比',
      key: 'percentage',
      width: 70,
      render: (_: unknown, record: NameCountRow) => {
        const pct = stats.sendCount > 0 ? (record.count / stats.sendCount) * 100 : 0;
        return `${pct.toFixed(1)}%`;
      },
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      {/* 年度選擇 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space>
          <Text strong>分析年度：</Text>
          <Select
            value={selectedYear ?? undefined}
            onChange={setSelectedYear}
            style={{ width: 120 }}
            placeholder="載入中..."
            loading={selectedYear === null}
          >
            <Select.Option value="all">全部年度</Select.Option>
            {yearOptions.map((year) => (
              <Select.Option key={year} value={year}>
                {year} 年
              </Select.Option>
            ))}
          </Select>
        </Space>
      </Card>

      {/* 統計卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="公文總數"
              value={stats.totalDocuments}
              prefix={<FileTextOutlined />}
              suffix="件"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="收文數"
              value={stats.receiveCount}
              prefix={<FallOutlined />}
              suffix="件"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="發文數"
              value={stats.sendCount}
              prefix={<RiseOutlined />}
              suffix="件"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 公文趨勢圖（近 12 個月收發文量） */}
      <div style={{ marginBottom: 16 }}>
        <DocumentTrendsChart />
      </div>

      {documents.length === 0 ? (
        <Card>
          <Empty description="暫無資料" />
        </Card>
      ) : (
        <>
          {/* 來文機關統計（收文） */}
          <Card
            title="來文機關統計"
            size="small"
            style={{ marginBottom: 16 }}
            extra={<Text type="secondary">共 {stats.bySender.length} 個機關，{stats.receiveCount} 件收文</Text>}
          >
            <Table
              dataSource={stats.bySender.slice(0, 15)}
              columns={senderColumns}
              pagination={false}
              size="small"
              rowKey="name"
              scroll={{ x: isMobile ? 300 : undefined }}
            />
            {stats.bySender.length > 15 && (
              <div style={{ textAlign: 'center', marginTop: 8 }}>
                <Text type="secondary">僅顯示前 15 筆</Text>
              </div>
            )}
          </Card>

          {/* 受文者統計（發文） */}
          {stats.sendCount > 0 && (
            <Card
              title="受文者統計"
              size="small"
              extra={<Text type="secondary">共 {stats.byReceiver.length} 個受文者，{stats.sendCount} 件發文</Text>}
            >
              <Table
                dataSource={stats.byReceiver.slice(0, 15)}
                columns={receiverColumns}
                pagination={false}
                size="small"
                rowKey="name"
                scroll={{ x: isMobile ? 300 : undefined }}
              />
              {stats.byReceiver.length > 15 && (
                <div style={{ textAlign: 'center', marginTop: 8 }}>
                  <Text type="secondary">僅顯示前 15 筆</Text>
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default DocumentAnalysisTab;
