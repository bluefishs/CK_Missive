/**
 * PM↔ERP 跨模組關聯卡片
 *
 * 在 PM 詳情頁顯示對應的 ERP 報價資訊（透過 case_code 軟關聯）。
 */
import React from 'react';
import { Card, Statistic, Row, Col, Button, Empty, Spin, Tag } from 'antd';
import { DollarOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useCrossModuleLookup } from '../../hooks/business/usePMCases';

interface CrossModuleCardProps {
  caseCode: string;
}

const CrossModuleCard: React.FC<CrossModuleCardProps> = ({ caseCode }) => {
  const navigate = useNavigate();
  const { data, isLoading } = useCrossModuleLookup(caseCode);

  if (isLoading) return <Spin description="查詢關聯..." style={{ display: 'block', margin: '20px auto' }} />;
  if (!data?.erp) return <Empty description="尚無對應 ERP 報價" image={Empty.PRESENTED_IMAGE_SIMPLE} />;

  const { erp } = data;
  const grossProfit = Number(erp.gross_profit);

  return (
    <Card
      size="small"
      title={<><DollarOutlined style={{ marginRight: 8 }} />ERP 報價關聯</>}
      extra={
        <Button type="link" size="small" onClick={() => navigate(`/erp/quotations/${erp.id}`)}>
          查看詳情 <ArrowRightOutlined />
        </Button>
      }
    >
      <Row gutter={16}>
        <Col span={8}>
          <Statistic title="案名" value={erp.case_name} />
        </Col>
        <Col span={4}>
          <Statistic
            title="狀態"
            value={erp.status}
            formatter={() => (
              <Tag color={erp.status === 'confirmed' ? 'success' : 'default'}>{erp.status}</Tag>
            )}
          />
        </Col>
        <Col span={6}>
          <Statistic title="總價" value={Number(erp.total_price)} precision={0} />
        </Col>
        <Col span={6}>
          <Statistic
            title="毛利"
            value={grossProfit}
            precision={0}
            styles={{ content: { color: grossProfit >= 0 ? '#3f8600' : '#cf1322' } }}
          />
        </Col>
      </Row>
    </Card>
  );
};

export default CrossModuleCard;
