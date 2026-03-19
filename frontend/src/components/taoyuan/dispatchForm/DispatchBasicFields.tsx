import React, { useMemo, useState } from 'react';
import {
  Form,
  Input,
  Select,
  AutoComplete,
  Typography,
} from 'antd';
import { ResponsiveFormRow } from '../../common/ResponsiveFormRow';
import type { FormInstance } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

import type { TaoyuanProject } from '../../../types/api';
import { TAOYUAN_WORK_TYPES } from '../../../types/api';
import type { ProjectAgencyContact } from '../../../api/projectAgencyContacts';
import type { ProjectVendor } from '../../../api/projectVendorsApi';

const { Option } = Select;
const { Text } = Typography;

interface DispatchBasicFieldsProps {
  form: FormInstance;
  availableProjects: TaoyuanProject[];
  agencyContacts: ProjectAgencyContact[];
  projectVendors: ProjectVendor[];
  onProjectSelect?: (projectId: number, projectName: string) => void;
  onCreateProject?: (projectName: string) => void;
}

const CREATE_PREFIX = '__CREATE__';

export const DispatchBasicFields: React.FC<DispatchBasicFieldsProps> = ({
  form,
  availableProjects,
  agencyContacts,
  projectVendors,
  onProjectSelect,
  onCreateProject,
}) => {
  const [projectInputText, setProjectInputText] = useState('');

  const isNewProjectName = useMemo(() => {
    if (!projectInputText.trim()) return false;
    return !availableProjects.some(
      (p) => p.project_name.toLowerCase() === projectInputText.trim().toLowerCase()
    );
  }, [projectInputText, availableProjects]);

  const projectOptions = useMemo(() => {
    const opts = availableProjects.map((proj) => ({
      value: proj.project_name,
      label: (
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span>{proj.project_name}</span>
          <span style={{ color: '#999', fontSize: '12px' }}>
            {[proj.district, proj.sequence_no ? `#${proj.sequence_no}` : null]
              .filter(Boolean)
              .join(' ')}
          </span>
        </div>
      ),
      projectId: proj.id,
    }));

    if (onCreateProject && isNewProjectName) {
      opts.push({
        value: `${CREATE_PREFIX}${projectInputText.trim()}`,
        label: (
          <div style={{ color: '#1890ff', fontWeight: 500 }}>
            <PlusOutlined style={{ marginRight: 4 }} />
            新增工程「{projectInputText.trim()}」
          </div>
        ),
        projectId: 0,
      });
    }

    return opts;
  }, [availableProjects, onCreateProject, isNewProjectName, projectInputText]);

  const handleProjectSelect = (value: string, option: { projectId?: number }) => {
    if (value.startsWith(CREATE_PREFIX) && onCreateProject) {
      const projectName = value.slice(CREATE_PREFIX.length);
      form.setFieldsValue({ project_name: projectName });
      setProjectInputText(projectName);
      onCreateProject(projectName);
      return;
    }
    if (option.projectId && onProjectSelect) {
      onProjectSelect(option.projectId, value);
    }
  };

  return (
    <>
      {/* 第一行：派工單號 + 工程名稱/派工事項 */}
      <ResponsiveFormRow>
        <Form.Item
          name="dispatch_no"
          label="派工單號"
          rules={[{ required: true, message: '請輸入派工單號' }]}
        >
          <Input placeholder="例: TY-2026-001" />
        </Form.Item>
        <Form.Item
          name="project_name"
          label="工程名稱/派工事項"
          tooltip="可從工程列表選擇或直接輸入（如：教育訓練）"
        >
          <AutoComplete
            options={projectOptions}
            onSelect={handleProjectSelect}
            onSearch={setProjectInputText}
            onChange={(value) => {
              if (!value) setProjectInputText('');
            }}
            placeholder="輸入或選擇工程名稱/派工事項"
            allowClear
            filterOption={(inputValue, option) => {
              if (option?.value?.startsWith(CREATE_PREFIX)) return true;
              return option?.value?.toLowerCase().includes(inputValue.toLowerCase()) ?? false;
            }}
          />
        </Form.Item>
      </ResponsiveFormRow>

      {/* 第二行：作業類別 + 分案名稱 + 履約期限 */}
      <ResponsiveFormRow>
        <Form.Item name="work_type" label="作業類別">
          <Select
            mode="multiple"
            allowClear
            placeholder="選擇作業類別（可多選）"
            maxTagCount={2}
          >
            {TAOYUAN_WORK_TYPES.map((type) => (
              <Option key={type} value={type}>
                {type}
              </Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item name="sub_case_name" label="分案名稱/派工備註">
          <Input.TextArea
            rows={2}
            placeholder="輸入分案名稱或備註"
            style={{ resize: 'vertical' }}
          />
        </Form.Item>
        <Form.Item name="deadline" label="履約期限">
          <Input.TextArea
            rows={2}
            placeholder="例: 114/12/31"
            style={{ resize: 'vertical' }}
          />
        </Form.Item>
      </ResponsiveFormRow>

      {/* 第三行：案件承辦 + 查估單位 + 聯絡備註 */}
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
                <div style={{ lineHeight: 1.4 }}>
                  <div>{contact.contact_name}</div>
                  {(contact.position || contact.department) && (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {[contact.position, contact.department].filter(Boolean).join(' / ')}
                    </Text>
                  )}
                </div>
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
            {projectVendors.map((vendor) => (
              <Option
                key={vendor.vendor_id}
                value={vendor.vendor_name}
                label={vendor.vendor_name}
              >
                <div style={{ lineHeight: 1.4 }}>
                  <div>{vendor.vendor_name}</div>
                  {(vendor.role || vendor.vendor_business_type) && (
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      {[vendor.role, vendor.vendor_business_type].filter(Boolean).join(' / ')}
                    </Text>
                  )}
                </div>
              </Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item name="contact_note" label="聯絡備註">
          <Input.TextArea
            rows={2}
            placeholder="輸入聯絡備註"
            style={{ resize: 'vertical' }}
          />
        </Form.Item>
      </ResponsiveFormRow>

      {/* 第四行：雲端資料夾 + 專案資料夾 */}
      <ResponsiveFormRow>
        <Form.Item name="cloud_folder" label="雲端資料夾">
          <Input.TextArea
            rows={2}
            placeholder="Google Drive 連結"
            style={{ resize: 'vertical' }}
          />
        </Form.Item>
        <Form.Item name="project_folder" label="專案資料夾">
          <Input.TextArea
            rows={2}
            placeholder="本地路徑"
            style={{ resize: 'vertical' }}
          />
        </Form.Item>
      </ResponsiveFormRow>

      {/* 第五行：結案批次 */}
      <ResponsiveFormRow>
        <Form.Item name="batch_no" label="結案批次">
          <Select
            placeholder="選擇結案批次"
            allowClear
            options={[
              { value: 1, label: '第1批結案' },
              { value: 2, label: '第2批結案' },
              { value: 3, label: '第3批結案' },
              { value: 4, label: '第4批結案' },
              { value: 5, label: '第5批結案' },
            ]}
          />
        </Form.Item>
        <div />
      </ResponsiveFormRow>
    </>
  );
};
