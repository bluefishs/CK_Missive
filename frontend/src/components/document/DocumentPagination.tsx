import React from 'react';
import {
  Pagination,
  Select,
  Typography,
  Space,
  Card,
  Statistic,
  Row,
  Col,
  Divider,
} from 'antd';
import {
  FileTextOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import type { OfficialDocument } from '../../types/api';

const { Text } = Typography;
const { Option } = Select;

interface DocumentPaginationProps {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onLimitChange: (limit: number) => void;
  documents?: OfficialDocument[];
}

export const DocumentPagination: React.FC<DocumentPaginationProps> = ({
  page,
  limit,
  total,
  totalPages,
  onPageChange,
  onLimitChange,
  documents = [],
}) => {
  const startItem = (page - 1) * limit + 1;
  const endItem = Math.min(page * limit, total);

  // 計算統計數據
  const getDocumentStats = () => {
    if (!documents || documents.length === 0) {
      return {
        receiveCount: 0,
        sendCount: 0,
        completedCount: 0,
      };
    }

    const receiveCount = documents.filter(doc => doc.category === 'receive').length;
    const sendCount = documents.filter(doc => doc.category === 'send').length;
    const completedCount = documents.filter(doc => doc.status === '收文完成').length;

    return {
      receiveCount,
      sendCount,
      completedCount,
    };
  };

  const stats = getDocumentStats();

  return (
    <Card 
      style={{ 
        marginTop: 16,
        borderRadius: 8,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
      }}
      styles={{ body: { padding: '16px 24px' } }}
    >
      {/* 統計信息區域 */}
      <Row gutter={[24, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Statistic
            title="總計"
            value={total}
            prefix={<FileTextOutlined />}
            valueStyle={{ color: '#1890ff', fontSize: '18px' }}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Statistic
            title="收文"
            value={stats.receiveCount}
            valueStyle={{ color: '#52c41a', fontSize: '16px' }}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Statistic
            title="發文"
            value={stats.sendCount}
            valueStyle={{ color: '#722ed1', fontSize: '16px' }}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Statistic
            title="已完成"
            value={stats.completedCount}
            valueStyle={{ color: '#fa8c16', fontSize: '16px' }}
          />
        </Col>
      </Row>

      <Divider style={{ margin: '16px 0' }} />

      {/* 分頁控制區域 */}
      <Row justify="space-between" align="middle">
        <Col xs={24} sm={12} md={8}>
          <Space wrap>
            <Text type="secondary">
              顯示第 {startItem} - {endItem} 筆，共 {total} 筆
            </Text>
            
            <Select
              value={limit}
              onChange={onLimitChange}
              style={{ width: 110 }}
              size="small"
            >
              <Option value={5}>5 筆/頁</Option>
              <Option value={10}>10 筆/頁</Option>
              <Option value={20}>20 筆/頁</Option>
              <Option value={50}>50 筆/頁</Option>
              <Option value={100}>100 筆/頁</Option>
            </Select>
          </Space>
        </Col>

        <Col xs={24} sm={12} md={16} style={{ textAlign: 'right' }}>
          {totalPages > 1 && (
            <Pagination
              current={page}
              total={total}
              pageSize={limit}
              onChange={onPageChange}
              showSizeChanger={false}
              showQuickJumper
              showTotal={(total, range) => 
                `第 ${range[0]}-${range[1]} 筆，共 ${total} 筆`
              }
              size="small"
              responsive
            />
          )}
        </Col>
      </Row>
    </Card>
  );
};