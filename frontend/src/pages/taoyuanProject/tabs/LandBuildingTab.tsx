/**
 * 土地建物 Tab
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

interface LandBuildingTabProps {
  form: FormInstance;
  isEditing: boolean;
  project: TaoyuanProject | undefined;
}

export const LandBuildingTab: React.FC<LandBuildingTabProps> = ({
  form,
  isEditing,
  project,
}) => (
  <Form form={form} layout="vertical" disabled={!isEditing}>
    <Row gutter={16}>
      <Col span={6}>
        <Form.Item name="public_land_count" label="公有土地(筆)">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="private_land_count" label="私有土地(筆)">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="rc_count" label="RC數量(棟)">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name="iron_sheet_count" label="鐵皮屋數量(棟)">
          <InputNumber style={{ width: '100%' }} min={0} />
        </Form.Item>
      </Col>
    </Row>

    {!isEditing && project && (
      <>
        <Divider />
        <Row gutter={16}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="公有土地" value={project.public_land_count || 0} suffix="筆" />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="私有土地" value={project.private_land_count || 0} suffix="筆" />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="RC數量" value={project.rc_count || 0} suffix="棟" />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="鐵皮屋" value={project.iron_sheet_count || 0} suffix="棟" />
            </Card>
          </Col>
        </Row>
      </>
    )}
  </Form>
);
