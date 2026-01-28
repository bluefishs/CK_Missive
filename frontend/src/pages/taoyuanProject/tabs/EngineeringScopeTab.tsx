/**
 * 工程範圍 Tab
 */

import React from 'react';
import {
  Form,
  Input,
  Row,
  Col,
  InputNumber,
  Divider,
  Card,
  Statistic,
} from 'antd';
import type { FormInstance } from 'antd';

import type { TaoyuanProject } from '../../../types/api';

interface EngineeringScopeTabProps {
  form: FormInstance;
  isEditing: boolean;
  project: TaoyuanProject | undefined;
}

export const EngineeringScopeTab: React.FC<EngineeringScopeTabProps> = ({
  form,
  isEditing,
  project,
}) => (
  <Form form={form} layout="vertical" disabled={!isEditing}>
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item name="start_point" label="工程起點">
          <Input placeholder="例: 永安路與中山路口" />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item name="start_coordinate" label="起點坐標(經緯度)">
          <Input placeholder="例: 24.9876,121.1234" />
        </Form.Item>
      </Col>
    </Row>
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item name="end_point" label="工程迄點">
          <Input placeholder="例: 永安路與民生路口" />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item name="end_coordinate" label="迄點坐標(經緯度)">
          <Input placeholder="例: 24.9888,121.1256" />
        </Form.Item>
      </Col>
    </Row>
    <Row gutter={16}>
      <Col span={8}>
        <Form.Item name="road_length" label="道路長度(公尺)">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item name="current_width" label="現況路寬(公尺)">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item name="planned_width" label="計畫路寬(公尺)">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
      </Col>
    </Row>
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item name="urban_plan" label="都市計畫">
          <Input />
        </Form.Item>
      </Col>
    </Row>

    {!isEditing && project && (
      <>
        <Divider />
        <Row gutter={16}>
          <Col span={8}>
            <Card size="small">
              <Statistic title="道路長度" value={project.road_length || 0} suffix="公尺" />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic title="現況路寬" value={project.current_width || 0} suffix="公尺" />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic title="計畫路寬" value={project.planned_width || 0} suffix="公尺" />
            </Card>
          </Col>
        </Row>
      </>
    )}
  </Form>
);
