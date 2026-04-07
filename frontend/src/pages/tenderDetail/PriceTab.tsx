/**
 * PriceTab - Tab5 底價分析
 *
 * Displays budget/floor/award prices, variance analysis, award items,
 * and price estimate based on similar tenders.
 */
import React from 'react';
import {
  Card, Descriptions, Row, Col, Statistic, List, Tag, Typography, Empty,
} from 'antd';
import { DollarOutlined } from '@ant-design/icons';

const { Text } = Typography;

export interface PriceTabProps {
  priceAnalysis?: {
    prices?: {
      budget?: number;
      floor_price?: number;
      award_amount?: number;
      award_date?: string;
    };
    analysis?: Record<string, number | null>;
    award_items?: Array<{ item_no: number; winner: string | null; amount: number | null }>;
  } | null;
  priceEstimate?: {
    avg_ratio: number;
    sample_count: number;
    estimated_award: number;
    budget: number;
  } | null;
}

const PriceTab: React.FC<PriceTabProps> = ({ priceAnalysis: priceData, priceEstimate }) => {
  return (
    <div>
      {priceData?.prices ? (
        <div>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={6}>
              <Card size="small" style={{ borderLeft: '4px solid #1890ff' }}>
                <Statistic title="預算金額" value={priceData.prices.budget ?? '-'}
                  prefix={<DollarOutlined />} styles={{ content: { fontSize: 18, color: '#1890ff' } }} />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small" style={{ borderLeft: '4px solid #faad14' }}>
                <Statistic title="底價" value={priceData.prices.floor_price ?? '-'}
                  styles={{ content: { fontSize: 18, color: '#faad14' } }} />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small" style={{ borderLeft: '4px solid #52c41a' }}>
                <Statistic title="決標金額" value={priceData.prices.award_amount ?? '-'}
                  styles={{ content: { fontSize: 18, color: '#52c41a' } }} />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card size="small" style={{ borderLeft: '4px solid #722ed1' }}>
                <Statistic title="決標日期" value={priceData.prices.award_date ?? '-'}
                  styles={{ content: { fontSize: 14 } }} />
              </Card>
            </Col>
          </Row>

          {priceData.analysis && Object.keys(priceData.analysis).length > 0 && (
            <Card title="差異分析" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={{ xs: 1, sm: 2 }} size="small">
                {priceData.analysis.budget_award_variance_pct != null && (
                  <Descriptions.Item label="預算 vs 決標">
                    <Tag color={priceData.analysis.budget_award_variance_pct < 0 ? 'green' : 'red'}>
                      {priceData.analysis.budget_award_variance_pct}%
                    </Tag>
                  </Descriptions.Item>
                )}
                {priceData.analysis.floor_award_variance_pct != null && (
                  <Descriptions.Item label="底價 vs 決標">
                    <Tag color={priceData.analysis.floor_award_variance_pct < 0 ? 'green' : 'red'}>
                      {priceData.analysis.floor_award_variance_pct}%
                    </Tag>
                  </Descriptions.Item>
                )}
                {priceData.analysis.savings_rate_pct != null && (
                  <Descriptions.Item label="節省率">
                    <Tag color="blue">{priceData.analysis.savings_rate_pct}%</Tag>
                  </Descriptions.Item>
                )}
              </Descriptions>
            </Card>
          )}

          {priceData.award_items && priceData.award_items.length > 0 && (
            <Card title="決標品項明細" size="small">
              <List size="small" dataSource={priceData.award_items}
                renderItem={(item) => (
                  <List.Item extra={item.amount != null ? <Tag color="green">NT$ {item.amount.toLocaleString()}</Tag> : null}>
                    <Text>第 {item.item_no} 品項: {item.winner ?? '未知'}</Text>
                  </List.Item>
                )}
              />
            </Card>
          )}
        </div>
      ) : <Empty description="尚無底價/決標資料 (標案可能尚在招標中)" />}

      {priceEstimate && (
        <Card title="決標金額推估 (基於相似標案歷史)" size="small" style={{ marginTop: 16, borderLeft: '4px solid #faad14' }}>
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6}>
              <Statistic title="本案預算" value={priceEstimate.budget} prefix="NT$" styles={{ content: { fontSize: 18 } }} />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic title="歷史平均折率" value={`${priceEstimate.avg_ratio}%`} styles={{ content: { fontSize: 18, color: '#faad14' } }} />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic title="推估決標金額" value={priceEstimate.estimated_award} prefix="NT$" styles={{ content: { fontSize: 18, color: '#52c41a' } }} />
            </Col>
            <Col xs={12} sm={6}>
              <Statistic title="樣本數" value={`${priceEstimate.sample_count} 筆`} styles={{ content: { fontSize: 14 } }} />
            </Col>
          </Row>
          <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
            * 基於 {priceEstimate.sample_count} 筆相似標案的預算→決標比例推算，僅供參考
          </Text>
        </Card>
      )}
    </div>
  );
};

export default PriceTab;
