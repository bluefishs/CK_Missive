/**
 * 派工表單共用欄位元件
 *
 * 統一管理派工表單欄位，避免重複維護。
 * 支援三種模式：
 * - create: 完整新增模式（獨立新增頁面）
 * - edit: 編輯模式（派工詳情頁面）
 * - quick: 快速新增模式（公文內新增派工）
 *
 * v1.4.0 - 拆分 DispatchBasicFields / DispatchPaymentFields / DispatchDocLinkFields
 * @version 1.4.0
 * @date 2026-03-18
 */

import React from 'react';
import {
  Form,
  Select,
  Divider,
} from 'antd';
import type { FormInstance } from 'antd';

import type { TaoyuanProject, OfficialDocument } from '../../types/api';
import type { ProjectAgencyContact } from '../../api/projectAgencyContacts';
import type { ProjectVendor } from '../../api/projectVendorsApi';
import { DispatchBasicFields } from './dispatchForm/DispatchBasicFields';
import { DispatchPaymentFields } from './dispatchForm/DispatchPaymentFields';
import { DispatchDocLinkFields } from './dispatchForm/DispatchDocLinkFields';

// =============================================================================
// Props 介面定義
// =============================================================================

export interface DispatchFormFieldsProps {
  form: FormInstance;
  mode: 'create' | 'edit' | 'quick';
  availableProjects?: TaoyuanProject[];
  agencyContacts?: ProjectAgencyContact[];
  projectVendors?: ProjectVendor[];
  onProjectSelect?: (projectId: number, projectName: string) => void;
  onCreateProject?: (projectName: string) => void;
  showPaymentFields?: boolean;
  watchedWorkTypes?: string[];
  showDocLinkFields?: boolean;
  document?: OfficialDocument | null;
  isReceiveDoc?: boolean;
  agencyDocOptions?: Array<{ value: number; label: string }>;
  companyDocOptions?: Array<{ value: number; label: string }>;
  onAgencyDocSearch?: (keyword: string) => void;
  onCompanyDocSearch?: (keyword: string) => void;
  showProjectLinkFields?: boolean;
  projectLinkOptions?: Array<{ value: number; label: string }>;
}

// =============================================================================
// 主元件
// =============================================================================

export const DispatchFormFields: React.FC<DispatchFormFieldsProps> = ({
  form,
  mode,
  availableProjects = [],
  agencyContacts = [],
  projectVendors = [],
  onProjectSelect,
  onCreateProject,
  showPaymentFields,
  watchedWorkTypes = [],
  showDocLinkFields,
  document,
  isReceiveDoc,
  agencyDocOptions = [],
  companyDocOptions = [],
  onAgencyDocSearch,
  onCompanyDocSearch,
  showProjectLinkFields,
  projectLinkOptions = [],
}) => {
  const shouldShowPayment = showPaymentFields ?? (mode !== 'quick');
  const shouldShowDocLink = showDocLinkFields ?? (mode === 'create' || mode === 'quick');
  const shouldShowProjectLink = showProjectLinkFields ?? (mode === 'create');

  return (
    <>
      <DispatchBasicFields
        form={form}
        availableProjects={availableProjects}
        agencyContacts={agencyContacts}
        projectVendors={projectVendors}
        onProjectSelect={onProjectSelect}
        onCreateProject={onCreateProject}
      />

      {shouldShowDocLink && (
        <DispatchDocLinkFields
          mode={mode}
          document={document}
          isReceiveDoc={isReceiveDoc}
          agencyDocOptions={agencyDocOptions}
          companyDocOptions={companyDocOptions}
          onAgencyDocSearch={onAgencyDocSearch}
          onCompanyDocSearch={onCompanyDocSearch}
        />
      )}

      {shouldShowPayment && (
        <DispatchPaymentFields
          mode={mode}
          watchedWorkTypes={watchedWorkTypes}
        />
      )}

      {shouldShowProjectLink && (
        <>
          <Divider titlePlacement="left">工程關聯</Divider>
          <Form.Item
            name="linked_project_ids"
            label="關聯工程"
            tooltip="可選擇多個相關工程進行關聯"
          >
            <Select
              mode="multiple"
              allowClear
              showSearch
              placeholder="搜尋並選擇要關聯的工程"
              filterOption={(input, option) =>
                String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={projectLinkOptions}
            />
          </Form.Item>
        </>
      )}
    </>
  );
};

export default DispatchFormFields;
