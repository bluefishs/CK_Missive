import React from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Typography,
  Space,
  Tag,
  Progress,
  Divider,
} from 'antd';
import { WarningOutlined } from '@ant-design/icons';
import { DocumentTrendsChart } from '../../components/dashboard';
import type { StatusDistributionItem } from '../../types/api';

const { Title, Text } = Typography;

interface DocumentEfficiency {
  total: number;
  overdue_count: number;
  overdue_rate: number;
  status_distribution: StatusDistributionItem[];
}

interface DocumentStatsSectionProps {
  efficiency: DocumentEfficiency | undefined;
}

const DocumentStatsSection: React.FC<DocumentStatsSectionProps> = ({ efficiency }) => (
  <>
    <Divider />
    <Title level={4}>公文統計</Title>
    <Row gutter={16}>
      <Col xs={24} lg={16}>
        <DocumentTrendsChart />
      </Col>
      <Col xs={24} lg={8}>
        <Card title={<><WarningOutlined style={{ marginRight: 8 }} />處理效率</>} size="small">
          {efficiency ? (
            <Space vertical style={{ width: '100%' }} size="middle">
              <Statistic
                title="公文總數"
                value={efficiency.total}
                suffix="件"
              />
              <div>
                <Text type="secondary">逾期率</Text>
                <Progress
                  percent={Math.round(efficiency.overdue_rate * 100)}
                  status={efficiency.overdue_rate > 0.1 ? 'exception' : 'normal'}
                  format={(percent) => `${percent}%`}
                />
              </div>
              <Statistic
                title="逾期公文"
                value={efficiency.overdue_count}
                suffix="件"
                styles={{ content: { color: efficiency.overdue_count > 0 ? '#f5222d' : '#52c41a' } }}
              />
              {efficiency.status_distribution.length > 0 && (
                <div>
                  <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>狀態分布</Text>
                  {efficiency.status_distribution.map((item: StatusDistributionItem) => (
                    <Tag key={item.status} style={{ marginBottom: 4 }}>
                      {item.status}: {item.count}
                    </Tag>
                  ))}
                </div>
              )}
            </Space>
          ) : (
            <Text type="secondary">載入中...</Text>
          )}
        </Card>
      </Col>
    </Row>
  </>
);

export default DocumentStatsSection;
