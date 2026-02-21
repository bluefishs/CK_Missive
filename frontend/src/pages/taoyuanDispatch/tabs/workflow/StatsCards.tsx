/**
 * StatsCards - 派工單作業歷程統計卡片
 *
 * 純展示元件，顯示作業紀錄的統計摘要：
 * - 紀錄數、已完成、已暫緩
 * - 關聯公文、未指派、來文、發文
 * - 當前階段
 *
 * @version 1.0.0
 * @date 2026-02-21
 */

import React from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import {
  OrderedListOutlined,
  CheckCircleOutlined,
  LinkOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  SendOutlined,
} from '@ant-design/icons';
import type { DispatchWorkStats } from '../../../../components/taoyuan/workflow/useDispatchWorkData';

const { Text } = Typography;

export interface StatsCardsProps {
  /** 統計資料 */
  stats: DispatchWorkStats;
}

const StatsCardsInner: React.FC<StatsCardsProps> = ({ stats }) => {
  return (
    <Card size="small" style={{ marginBottom: 12 }}>
      <Row gutter={[16, 8]} align="middle">
        <Col xs={12} sm={6} md={3}>
          <Statistic
            title="紀錄數"
            value={stats.total}
            prefix={<OrderedListOutlined />}
            valueStyle={{ fontSize: 18 }}
          />
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Statistic
            title="已完成"
            value={stats.completed}
            prefix={<CheckCircleOutlined />}
            valueStyle={{ fontSize: 18, color: '#52c41a' }}
          />
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Statistic
            title="已暫緩"
            value={stats.onHold}
            valueStyle={{ fontSize: 18, color: stats.onHold > 0 ? '#faad14' : undefined }}
          />
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Statistic
            title="關聯公文"
            value={stats.linkedDocCount}
            prefix={<LinkOutlined />}
            valueStyle={{ fontSize: 18 }}
          />
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Statistic
            title="未指派"
            value={stats.unassignedDocCount}
            prefix={<ExclamationCircleOutlined />}
            valueStyle={{
              fontSize: 18,
              color: stats.unassignedDocCount > 0 ? '#faad14' : undefined,
            }}
          />
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Statistic
            title="來文"
            value={stats.incomingDocs}
            prefix={<FileTextOutlined />}
            valueStyle={{ fontSize: 18 }}
          />
        </Col>
        <Col xs={12} sm={6} md={3}>
          <Statistic
            title="發文"
            value={stats.outgoingDocs}
            prefix={<SendOutlined />}
            valueStyle={{ fontSize: 18 }}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            當前階段
          </Text>
          <div>
            <Tag
              color={stats.currentStage === '全部完成' ? 'success' : 'processing'}
              style={{ marginTop: 2 }}
            >
              {stats.currentStage}
            </Tag>
          </div>
        </Col>
      </Row>
    </Card>
  );
};

export const StatsCards = React.memo(StatsCardsInner);
StatsCards.displayName = 'StatsCards';
