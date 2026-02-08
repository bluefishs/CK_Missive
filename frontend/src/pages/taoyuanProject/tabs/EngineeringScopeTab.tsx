/**
 * 工程範圍 Tab
 */

import React from 'react';
import {
  Form,
  Input,
  InputNumber,
  Divider,
  Card,
  Statistic,
} from 'antd';
import { ResponsiveFormRow } from '../../../components/common/ResponsiveFormRow';
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
    <ResponsiveFormRow>
      <Form.Item name="start_point" label="工程起點">
        <Input placeholder="例: 永安路與中山路口" />
      </Form.Item>
      <Form.Item name="start_coordinate" label="起點坐標(經緯度)">
        <Input placeholder="例: 24.9876,121.1234" />
      </Form.Item>
    </ResponsiveFormRow>
    <ResponsiveFormRow>
      <Form.Item name="end_point" label="工程迄點">
        <Input placeholder="例: 永安路與民生路口" />
      </Form.Item>
      <Form.Item name="end_coordinate" label="迄點坐標(經緯度)">
        <Input placeholder="例: 24.9888,121.1256" />
      </Form.Item>
    </ResponsiveFormRow>
    <ResponsiveFormRow>
      <Form.Item name="road_length" label="道路長度(公尺)">
        <InputNumber style={{ width: '100%' }} min={0} />
      </Form.Item>
      <Form.Item name="current_width" label="現況路寬(公尺)">
        <InputNumber style={{ width: '100%' }} min={0} />
      </Form.Item>
      <Form.Item name="planned_width" label="計畫路寬(公尺)">
        <InputNumber style={{ width: '100%' }} min={0} />
      </Form.Item>
    </ResponsiveFormRow>
    <Form.Item name="urban_plan" label="都市計畫">
      <Input />
    </Form.Item>

    {!isEditing && project && (
      <>
        <Divider />
        <ResponsiveFormRow>
          <Card size="small">
            <Statistic title="道路長度" value={project.road_length || 0} suffix="公尺" />
          </Card>
          <Card size="small">
            <Statistic title="現況路寬" value={project.current_width || 0} suffix="公尺" />
          </Card>
          <Card size="small">
            <Statistic title="計畫路寬" value={project.planned_width || 0} suffix="公尺" />
          </Card>
        </ResponsiveFormRow>
      </>
    )}
  </Form>
);
