/**
 * 基本資訊 Tab
 */

import React from 'react';
import {
  Form,
  Input,
  Select,
  InputNumber,
  Divider,
  Descriptions,
} from 'antd';
import { ResponsiveFormRow } from '../../../components/common/ResponsiveFormRow';
import type { FormInstance } from 'antd';
import dayjs from 'dayjs';

import type { TaoyuanProject } from '../../../types/api';
import type { ProjectAgencyContact } from '../../../api/projectAgencyContacts';
import type { ProjectVendor } from '../../../api/projectVendorsApi';
import {
  CASE_TYPE_OPTIONS,
  DISTRICT_OPTIONS,
} from '../../../constants/taoyuanOptions';

const { Option } = Select;

interface BasicInfoTabProps {
  form: FormInstance;
  isEditing: boolean;
  project: TaoyuanProject | undefined;
  agencyContacts: ProjectAgencyContact[];
  projectVendors: ProjectVendor[];
}

export const BasicInfoTab: React.FC<BasicInfoTabProps> = ({
  form,
  isEditing,
  project,
  agencyContacts,
  projectVendors,
}) => (
  <Form form={form} layout="vertical" disabled={!isEditing}>
    <Form.Item
      name="project_name"
      label="工程名稱"
      rules={[{ required: true, message: '請輸入工程名稱' }]}
    >
      <Input placeholder="請輸入工程名稱" />
    </Form.Item>

    <ResponsiveFormRow>
      <Form.Item name="review_year" label="審議年度">
        <InputNumber style={{ width: '100%' }} />
      </Form.Item>
      <Form.Item name="case_type" label="案件類型">
        <Select placeholder="選擇案件類型" allowClear>
          {CASE_TYPE_OPTIONS.map((opt) => (
            <Option key={opt.value} value={opt.value}>
              {opt.label}
            </Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item name="district" label="行政區">
        <Select placeholder="選擇行政區" allowClear showSearch>
          {DISTRICT_OPTIONS.map((opt) => (
            <Option key={opt.value} value={opt.value}>
              {opt.label}
            </Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item name="sub_case_name" label="分案名稱">
        <Input />
      </Form.Item>
    </ResponsiveFormRow>

    <ResponsiveFormRow>
      <Form.Item
        name="case_handler"
        label="案件承辦"
        tooltip="從機關承辦清單選擇（來源：承攬案件機關承辦）"
      >
        <Select
          placeholder="選擇案件承辦"
          allowClear
          showSearch
          optionFilterProp="label"
        >
          {agencyContacts.map((contact) => (
            <Option
              key={contact.id}
              value={contact.contact_name}
              label={contact.contact_name}
            >
              {contact.contact_name}
            </Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item
        name="survey_unit"
        label="查估單位"
        tooltip="從協力廠商清單選擇（來源：承攬案件協力廠商）"
      >
        <Select
          placeholder="選擇查估單位"
          allowClear
          showSearch
          optionFilterProp="label"
        >
          {projectVendors.map((vendor: ProjectVendor) => (
            <Option
              key={vendor.vendor_id}
              value={vendor.vendor_name}
              label={vendor.vendor_name}
            >
              {vendor.vendor_name}
            </Option>
          ))}
        </Select>
      </Form.Item>
      <Form.Item name="proposer" label="提案人">
        <Input />
      </Form.Item>
    </ResponsiveFormRow>

    {!isEditing && project && (
      <>
        <Divider />
        <Descriptions size="small" column={3}>
          <Descriptions.Item label="項次">
            {project.sequence_no || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="建立時間">
            {project.created_at ? dayjs(project.created_at).format('YYYY-MM-DD HH:mm') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="更新時間">
            {project.updated_at ? dayjs(project.updated_at).format('YYYY-MM-DD HH:mm') : '-'}
          </Descriptions.Item>
        </Descriptions>
      </>
    )}
  </Form>
);
