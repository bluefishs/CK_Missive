/**
 * 經費估算 Tab
 */

import React from 'react';
import {
  Form,
  Row,
  Col,
  InputNumber,
  Divider,
  Card,
  Statistic,
} from 'antd';
import type { FormInstance } from 'antd';

import type { TaoyuanProject } from '../../../types/api';

const currencyFormatter = (value: number | string | undefined) =>
  `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',');

interface BudgetEstimateTabProps {
  form: FormInstance;
  isEditing: boolean;
  project: TaoyuanProject | undefined;
}

export const BudgetEstimateTab: React.FC<BudgetEstimateTabProps> = ({
  form,
  isEditing,
  project,
}) => (
  <Form form={form} layout="vertical" disabled={!isEditing}>
    <Row gutter={16}>
      <Col span={6}>
        <Form.Item name="construction_cost" label="工程費(元)">
          <InputNumber style={{ width: '100%' }} min={0} formatter={currencyFormatter} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="land_cost" label="用地費(元)">
          <InputNumber style={{ width: '100%' }} min={0} formatter={currencyFormatter} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="compensation_cost" label="補償費(元)">
          <InputNumber style={{ width: '100%' }} min={0} formatter={currencyFormatter} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="total_cost" label="總經費(元)">
          <InputNumber style={{ width: '100%' }} min={0} formatter={currencyFormatter} />
        </Form.Item>
      </Col>
    </Row>

    {!isEditing && project && (
      <>
        <Divider />
        <Row gutter={16}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="工程費" value={project.construction_cost || 0} prefix="$" precision={0} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="用地費" value={project.land_cost || 0} prefix="$" precision={0} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="補償費" value={project.compensation_cost || 0} prefix="$" precision={0} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="總經費"
                value={project.total_cost || 0}
                prefix="$"
                precision={0}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
        </Row>
      </>
    )}
  </Form>
);
