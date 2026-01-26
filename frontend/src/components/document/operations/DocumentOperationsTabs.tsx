/**
 * DocumentOperations Tab 子元件
 *
 * 將各 Tab 的 UI 渲染邏輯從主元件中提取出來
 *
 * @version 1.0.0
 * @date 2026-01-26
 */
import React from 'react';
import {
  Form,
  Input,
  Select,
  DatePicker,
  Card,
  Row,
  Col,
  Tag,
  Spin,
  Empty,
} from 'antd';
import type { UploadFile } from 'antd/es/upload';
import dayjs from 'dayjs';
import { Document, DocumentAttachment } from '../../../types';
import { ExistingAttachmentsList } from './ExistingAttachmentsList';
import { FileUploadSection } from './FileUploadSection';
import type { FileValidationResult } from './types';

const { TextArea } = Input;
const { Option } = Select;

// ============================================================================
// BasicInfoTab - 基本資料 Tab
// ============================================================================

export interface BasicInfoTabProps {
  document: Document | null;
}

export const BasicInfoTab: React.FC<BasicInfoTabProps> = ({ document }) => (
  <>
    <Row gutter={16}>
      <Col span={12}>
        {document?.category === '發文' ? (
          <Form.Item
            label="發文形式"
            name="delivery_method"
            rules={[{ required: true, message: '請選擇發文形式' }]}
          >
            <Select placeholder="請選擇發文形式">
              <Option value="電子交換">電子交換</Option>
              <Option value="紙本郵寄">紙本郵寄</Option>
            </Select>
          </Form.Item>
        ) : (
          <Form.Item
            label="文件類型"
            name="doc_type"
            rules={[{ required: true, message: '請選擇文件類型' }]}
          >
            <Select placeholder="請選擇文件類型">
              <Option value="函">函</Option>
              <Option value="開會通知單">開會通知單</Option>
              <Option value="會勘通知單">會勘通知單</Option>
            </Select>
          </Form.Item>
        )}
      </Col>
      <Col span={12}>
        <Form.Item
          label="公文字號"
          name="doc_number"
          rules={[{ required: true, message: '請輸入公文字號' }]}
        >
          <Input placeholder="如：乾坤字第1130001號" />
        </Form.Item>
      </Col>
    </Row>

    <Row gutter={16}>
      <Col span={12}>
        <Form.Item
          label="發文機關"
          name="sender"
          rules={[{ required: true, message: '請輸入發文機關' }]}
        >
          <Input placeholder="請輸入發文機關" />
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item label="受文者" name="receiver">
          <Input placeholder="請輸入受文者" />
        </Form.Item>
      </Col>
    </Row>

    <Form.Item
      label="主旨"
      name="subject"
      rules={[{ required: true, message: '請輸入主旨' }]}
    >
      <TextArea rows={2} placeholder="請輸入公文主旨" maxLength={200} showCount />
    </Form.Item>

    <Form.Item label="說明" name="content">
      <TextArea rows={4} placeholder="請輸入公文內容說明" maxLength={1000} showCount />
    </Form.Item>

    <Form.Item label="備註" name="notes">
      <TextArea rows={3} placeholder="請輸入備註" maxLength={500} showCount />
    </Form.Item>

    <Form.Item label="簡要說明(乾坤備註)" name="ck_note">
      <TextArea
        rows={3}
        placeholder="請輸入乾坤內部簡要說明或備註"
        maxLength={1000}
        showCount
      />
    </Form.Item>
  </>
);

// ============================================================================
// DateStatusTab - 日期與狀態 Tab
// ============================================================================

export const DateStatusTab: React.FC = () => (
  <>
    <Row gutter={16}>
      <Col span={8}>
        <Form.Item label="發文日期" name="doc_date">
          <DatePicker style={{ width: '100%' }} placeholder="請選擇發文日期" />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item label="收文日期" name="receive_date">
          <DatePicker style={{ width: '100%' }} placeholder="請選擇收文日期" />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item label="發送日期" name="send_date">
          <DatePicker style={{ width: '100%' }} placeholder="請選擇發送日期" />
        </Form.Item>
      </Col>
    </Row>

    <Row gutter={16}>
      <Col span={12}>
        <Form.Item label="優先等級" name="priority">
          <Select placeholder="請選擇優先等級">
            <Option value={1}><Tag color="blue">1 - 最高</Tag></Option>
            <Option value={2}><Tag color="green">2 - 高</Tag></Option>
            <Option value={3}><Tag color="orange">3 - 普通</Tag></Option>
            <Option value={4}><Tag color="red">4 - 低</Tag></Option>
            <Option value={5}><Tag color="purple">5 - 最低</Tag></Option>
          </Select>
        </Form.Item>
      </Col>
      <Col span={12}>
        <Form.Item label="處理狀態" name="status">
          <Select placeholder="請選擇處理狀態">
            <Option value="收文完成">收文完成</Option>
            <Option value="使用者確認">使用者確認</Option>
            <Option value="收文異常">收文異常</Option>
          </Select>
        </Form.Item>
      </Col>
    </Row>
  </>
);

// ============================================================================
// ProjectStaffTab - 案件與人員 Tab
// ============================================================================

export interface ProjectStaffTabProps {
  cases: { id: number; project_name?: string }[];
  users: { id: number; full_name?: string; username: string }[];
  casesLoading: boolean;
  usersLoading: boolean;
  selectedProjectId: number | null;
  projectStaffMap: Record<number, { user_id?: number; id?: number; user_name?: string; role?: string }[]>;
  staffLoading: boolean;
  onProjectChange: (projectId: number | null | undefined) => void;
}

export const ProjectStaffTab: React.FC<ProjectStaffTabProps> = ({
  cases,
  users,
  casesLoading,
  usersLoading,
  selectedProjectId,
  projectStaffMap,
  staffLoading,
  onProjectChange,
}) => (
  <Row gutter={16}>
    <Col span={12}>
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
          options={Array.isArray(cases) ? cases.map(case_ => ({
            value: case_.id,
            label: case_.project_name || '未命名案件',
            key: case_.id,
          })) : []}
        />
      </Form.Item>
    </Col>
    <Col span={12}>
      <Form.Item label="業務同仁" name="assignee">
        <Select
          mode="multiple"
          placeholder="請選擇業務同仁（可複選）"
          loading={usersLoading || staffLoading}
          allowClear
          showSearch
          filterOption={(input, option) =>
            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
          }
          options={
            selectedProjectId && (projectStaffMap[selectedProjectId]?.length ?? 0) > 0
              ? (projectStaffMap[selectedProjectId] ?? []).map(staff => ({
                  value: staff.user_name,
                  label: staff.role ? `${staff.user_name}(${staff.role})` : staff.user_name,
                  key: staff.user_id || staff.id,
                }))
              : Array.isArray(users) ? users.map(user => ({
                  value: user.full_name || user.username,
                  label: user.full_name || user.username,
                  key: user.id,
                })) : []
          }
        />
      </Form.Item>
    </Col>
  </Row>
);

// ============================================================================
// AttachmentTab - 附件上傳 Tab
// ============================================================================

export interface AttachmentTabProps {
  existingAttachments: DocumentAttachment[];
  attachmentsLoading: boolean;
  fileList: UploadFile[];
  uploading: boolean;
  uploadProgress: number;
  uploadErrors: string[];
  fileSettings: { maxFileSizeMB: number; allowedExtensions: string[] };
  isReadOnly: boolean;
  onDownload: (id: number, filename: string) => Promise<void>;
  onPreview: (id: number, filename: string) => void;
  onDelete: (id: number) => Promise<void>;
  onFileListChange: (fileList: UploadFile[]) => void;
  onRemove: (file: UploadFile) => void;
  onClearErrors: () => void;
  validateFile: (file: File) => FileValidationResult;
  onCheckDuplicate: (file: File) => boolean;
}

export const AttachmentTab: React.FC<AttachmentTabProps> = ({
  existingAttachments,
  attachmentsLoading,
  fileList,
  uploading,
  uploadProgress,
  uploadErrors,
  fileSettings,
  isReadOnly,
  onDownload,
  onPreview,
  onDelete,
  onFileListChange,
  onRemove,
  onClearErrors,
  validateFile,
  onCheckDuplicate,
}) => (
  <Spin spinning={attachmentsLoading}>
    <ExistingAttachmentsList
      attachments={existingAttachments}
      loading={false}
      readOnly={isReadOnly}
      onDownload={onDownload}
      onPreview={onPreview}
      onDelete={onDelete}
    />

    {!isReadOnly ? (
      <FileUploadSection
        fileList={fileList}
        uploading={uploading}
        uploadProgress={uploadProgress}
        uploadErrors={uploadErrors}
        maxFileSizeMB={fileSettings.maxFileSizeMB}
        allowedExtensions={fileSettings.allowedExtensions}
        readOnly={isReadOnly}
        onFileListChange={onFileListChange}
        onRemove={onRemove}
        onClearErrors={onClearErrors}
        validateFile={validateFile}
        onCheckDuplicate={onCheckDuplicate}
      />
    ) : (
      existingAttachments.length === 0 && (
        <Empty description="此公文尚無附件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )
    )}
  </Spin>
);

// ============================================================================
// SystemInfoTab - 系統資訊 Tab
// ============================================================================

export interface SystemInfoTabProps {
  document: Document;
}

export const SystemInfoTab: React.FC<SystemInfoTabProps> = ({ document }) => (
  <Card size="small" title="系統資訊" type="inner">
    <Row gutter={16}>
      <Col span={8}>
        <strong>建立時間:</strong>
        <br />
        {document.created_at ? dayjs(document.created_at).format('YYYY-MM-DD HH:mm') : '未知'}
      </Col>
      <Col span={8}>
        <strong>修改時間:</strong>
        <br />
        {document.updated_at ? dayjs(document.updated_at).format('YYYY-MM-DD HH:mm') : '未知'}
      </Col>
      <Col span={8}>
        <strong>建立者:</strong>
        <br />
        {document.creator || '系統'}
      </Col>
    </Row>
  </Card>
);
