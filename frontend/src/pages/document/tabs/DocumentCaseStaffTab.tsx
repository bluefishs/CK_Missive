/**
 * 承案人資 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import {
  Form,
  Select,
} from 'antd';
import { ResponsiveFormRow } from '../../../components/common/ResponsiveFormRow';
import { logger } from '../../../utils/logger';
import type { DocumentCaseStaffTabProps } from './types';

export const DocumentCaseStaffTab: React.FC<DocumentCaseStaffTabProps> = ({
  form,
  isEditing,
  cases,
  casesLoading,
  users,
  usersLoading,
  projectStaffMap,
  staffLoading,
  selectedContractProjectId,
  currentAssigneeValues,
  onProjectChange,
}) => {
  // 使用 Form.useWatch 監聽 assignee 欄位變化（響應式更新）
  const watchedAssignee = Form.useWatch('assignee', form);

  // 取得目前表單的 assignee 值，用於確保已選取的值顯示在選項中
  // 優先使用 watchedAssignee，若為空則使用狀態變數
  const currentAssignees: string[] = Array.isArray(watchedAssignee) && watchedAssignee.length > 0
    ? watchedAssignee
    : currentAssigneeValues;

  // 建立業務同仁選項
  const buildAssigneeOptions = () => {
    // 專案業務同仁選項
    const staffList = selectedContractProjectId ? projectStaffMap[selectedContractProjectId] : undefined;
    const projectStaffOptions =
      staffList && staffList.length > 0
        ? staffList.map((staff) => ({
            value: staff.user_name,
            label: staff.role ? `${staff.user_name}(${staff.role})` : staff.user_name,
            key: `staff-${staff.user_id || staff.id}`,
          }))
        : [];

    // 使用者選項（作為備用）
    const userOptions = Array.isArray(users)
      ? users.map((user) => ({
          value: user.full_name || user.username,
          label: user.full_name || user.username,
          key: `user-${user.id}`,
        }))
      : [];

    // 優先使用專案同仁，若無則使用全部使用者
    const baseOptions = projectStaffOptions.length > 0 ? projectStaffOptions : userOptions;

    // 確保目前已選取的值也在選項中（避免值存在但選項沒載入的情況）
    const existingValues = new Set(baseOptions.map((o) => o.value));
    const missingOptions = currentAssignees
      .filter((v) => v && !existingValues.has(v))
      .map((v) => ({ value: v, label: v, key: `current-${v}` }));

    const finalOptions = [...baseOptions, ...missingOptions];
    logger.debug('[buildAssigneeOptions] currentAssignees:', currentAssignees, 'options count:', finalOptions.length);
    return finalOptions;
  };

  return (
    <Form form={form} layout="vertical" disabled={!isEditing}>
      <ResponsiveFormRow>
        <Form.Item label="承攬案件" name="contract_project_id">
          <Select
            placeholder="請選擇承攬案件"
            loading={casesLoading || staffLoading}
            allowClear
            showSearch
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            onChange={onProjectChange}
            options={cases.map((case_) => ({
              value: case_.id,
              label: case_.project_name || '未命名案件',
              key: case_.id,
            }))}
          />
        </Form.Item>
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
      </ResponsiveFormRow>
    </Form>
  );
};

export default DocumentCaseStaffTab;
