/**
 * 土地建物 Tab
 */

import React from 'react';
import {
  Form,
  InputNumber,
  Divider,
  Card,
  Statistic,
} from 'antd';
import { ResponsiveFormRow } from '../../../components/common/ResponsiveFormRow';
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
    <ResponsiveFormRow>
      <Form.Item name="public_land_count" label="公有土地(筆)">
        <InputNumber style={{ width: '100%' }} min={0} />
      </Form.Item>
      <Form.Item name="private_land_count" label="私有土地(筆)">
        <InputNumber style={{ width: '100%' }} min={0} />
      </Form.Item>
      <Form.Item name="rc_count" label="RC數量(棟)">
        <InputNumber style={{ width: '100%' }} min={0} />
      </Form.Item>
      <Form.Item name="iron_sheet_count" label="鐵皮屋數量(棟)">
        <InputNumber style={{ width: '100%' }} min={0} />
      </Form.Item>
    </ResponsiveFormRow>

    {!isEditing && project && (
      <>
        <Divider />
        <ResponsiveFormRow>
          <Card size="small">
            <Statistic title="公有土地" value={project.public_land_count || 0} suffix="筆" />
          </Card>
          <Card size="small">
            <Statistic title="私有土地" value={project.private_land_count || 0} suffix="筆" />
          </Card>
          <Card size="small">
            <Statistic title="RC數量" value={project.rc_count || 0} suffix="棟" />
          </Card>
          <Card size="small">
            <Statistic title="鐵皮屋" value={project.iron_sheet_count || 0} suffix="棟" />
          </Card>
        </ResponsiveFormRow>
      </>
    )}
  </Form>
);
