/**
 * 公文建立 - 承案人資 Tab
 *
 * 共用於收文和發文建立頁面
 *
 * @version 1.0.0
 * @date 2026-01-28
 */

import React from 'react';
import { Form, Select, Row, Col } from 'antd';
import type { FormInstance } from 'antd';
import type { Project } from '../../../types/api';

export interface DocumentCreateStaffTabProps {
  form: FormInstance;
  cases: Project[];
  casesLoading: boolean;
  staffLoading: boolean;
  usersLoading: boolean;
  buildAssigneeOptions: () => Array<{ value: string; label: string; key: string }>;
  handleProjectChange: (projectId: number | null | undefined) => Promise<void>;
}

export const DocumentCreateStaffTab: React.FC<DocumentCreateStaffTabProps> = ({
  form,
  cases,
  casesLoading,
  staffLoading,
  usersLoading,
  buildAssigneeOptions,
  handleProjectChange,
}) => {
  return (
    <Form form={form} layout="vertical">
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item label="承攬案件" name="contract_project_id">
            <Select
              placeholder="請選擇承攬案件（選填）"
              loading={casesLoading || staffLoading}
              allowClear
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              onChange={handleProjectChange}
              options={cases.map((case_) => ({
                value: case_.id,
                label: case_.project_name || '未命名案件',
              }))}
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item label="業務同仁" name="assignee">
            <Select
              mode="multiple"
              placeholder="請選擇業務同仁（可複選）"
              loading={staffLoading || usersLoading}
              allowClear
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={buildAssigneeOptions()}
            />
          </Form.Item>
        </Col>
      </Row>
    </Form>
  );
};

export default DocumentCreateStaffTab;
