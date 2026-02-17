/**
 * InlineRecordCreator - Tab 內 Inline 新增作業紀錄
 *
 * 收合狀態顯示「+ 新增紀錄」按鈕，展開後顯示精簡表單。
 * 不離開頁面即可快速建立作業歷程紀錄。
 *
 * @version 1.0.0
 * @date 2026-02-15
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Card,
  Form,
  Select,
  DatePicker,
  Button,
  Space,
  Radio,
  Tag,
  Row,
  Col,
  Input,
  App,
  Typography,
} from 'antd';
import { PlusOutlined, CloseOutlined, SaveOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { workflowApi } from '../../../api/taoyuan';
import type {
  WorkRecord,
  WorkRecordCreate,
  DispatchDocumentLink,
} from '../../../types/taoyuan';
import {
  WORK_CATEGORY_GROUPS,
  CHAIN_STATUS_OPTIONS,
  getCategoryLabel,
} from './chainConstants';
import { isOutgoingDocNumber } from './chainUtils';
import { logger } from '../../../services/logger';

const { TextArea } = Input;
const { Text } = Typography;

// =============================================================================
// Types
// =============================================================================

export interface InlineRecordCreatorProps {
  /** 派工單 ID */
  dispatchOrderId: number;
  /** 已有的作業紀錄（用於前序紀錄下拉） */
  existingRecords: WorkRecord[];
  /** 已關聯的公文列表 */
  linkedDocuments?: DispatchDocumentLink[];
  /** 關聯的工程列表（單一工程時自動帶入） */
  linkedProjects?: { project_id: number; project_name?: string }[];
  /** 建立成功後 callback */
  onCreated?: () => void;
}

// =============================================================================
// 元件
// =============================================================================

export const InlineRecordCreator: React.FC<InlineRecordCreatorProps> = ({
  dispatchOrderId,
  existingRecords,
  linkedDocuments = [],
  linkedProjects = [],
  onCreated,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // =========================================================================
  // 公文選項
  // =========================================================================

  const docOptions = useMemo(() => {
    return linkedDocuments.map((d) => {
      const isOutgoing = isOutgoingDocNumber(d.doc_number);
      const tag = isOutgoing ? '發' : '收';
      const color = isOutgoing ? 'green' : 'blue';
      return {
        value: d.document_id,
        label: (
          <span>
            <Tag color={color} style={{ marginRight: 4 }}>{tag}</Tag>
            {d.doc_number || `ID:${d.document_id}`}
          </span>
        ),
        searchText: `${d.doc_number || ''} ${d.subject || ''}`,
      };
    });
  }, [linkedDocuments]);

  // =========================================================================
  // 前序紀錄選項
  // =========================================================================

  const parentRecordOptions = useMemo(() => {
    return existingRecords.map((r) => {
      const catLabel = getCategoryLabel(r);
      const docNum =
        r.document?.doc_number ||
        r.incoming_doc?.doc_number ||
        r.outgoing_doc?.doc_number ||
        '';
      return {
        value: r.id,
        label: `#${r.id} ${catLabel}${docNum ? ` — ${docNum}` : ''}${r.record_date ? ` (${r.record_date})` : ''}`,
      };
    });
  }, [existingRecords]);

  // =========================================================================
  // 展開時設定預設值
  // =========================================================================

  useEffect(() => {
    if (expanded) {
      const defaults: Record<string, unknown> = {
        status: 'in_progress',
      };
      // 自動預選最後一筆紀錄為前序
      if (existingRecords.length > 0) {
        const lastRecord = existingRecords[existingRecords.length - 1];
        if (lastRecord) defaults.parent_record_id = lastRecord.id;
      }
      form.setFieldsValue(defaults);
    }
  }, [expanded, existingRecords, form]);

  // =========================================================================
  // 公文選擇時自動帶入主旨
  // =========================================================================

  const handleDocumentChange = useCallback(
    (docId: number | undefined) => {
      if (!docId) return;
      const doc = linkedDocuments.find((d) => d.document_id === docId);
      if (doc?.subject) {
        const currentDesc = form.getFieldValue('description');
        if (!currentDesc) {
          form.setFieldsValue({ description: doc.subject });
        }
      }
    },
    [linkedDocuments, form],
  );

  // =========================================================================
  // Mutation
  // =========================================================================

  const createMutation = useMutation({
    mutationFn: (data: WorkRecordCreate) => workflowApi.create(data),
    onSuccess: () => {
      message.success('作業紀錄建立成功');
      form.resetFields();
      setExpanded(false);
      queryClient.invalidateQueries({
        queryKey: ['dispatch-work-records', dispatchOrderId],
      });
      queryClient.invalidateQueries({ queryKey: ['project-work-records'] });
      onCreated?.();
    },
    onError: (error: Error) => {
      logger.error('[InlineRecordCreator] 建立失敗:', error);
      message.error('建立失敗，請稍後再試');
    },
  });

  // =========================================================================
  // Handlers
  // =========================================================================

  const handleSave = useCallback(async () => {
    try {
      const values = await form.validateFields();

      // 工程 ID：單一工程自動帶入，多工程由使用者選
      const projectId =
        values.taoyuan_project_id ||
        (linkedProjects.length === 1 ? linkedProjects[0]!.project_id : undefined);

      const payload: WorkRecordCreate = {
        dispatch_order_id: dispatchOrderId,
        taoyuan_project_id: projectId,
        work_category: values.work_category,
        document_id: values.document_id || undefined,
        parent_record_id: values.parent_record_id || undefined,
        status: values.status,
        description: values.description || undefined,
        milestone_type: 'other',
      };

      // 處理 deadline_date（dayjs → string）
      if (values.deadline_date) {
        payload.deadline_date = values.deadline_date.format('YYYY-MM-DD');
      }

      createMutation.mutate(payload);
    } catch {
      // form validation failed
    }
  }, [form, dispatchOrderId, createMutation]);

  const handleCancel = useCallback(() => {
    form.resetFields();
    setExpanded(false);
  }, [form]);

  // =========================================================================
  // Render
  // =========================================================================

  if (!expanded) {
    return (
      <div style={{ marginTop: 12 }}>
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={() => setExpanded(true)}
          block
        >
          新增作業紀錄
        </Button>
      </div>
    );
  }

  return (
    <Card
      size="small"
      style={{ marginTop: 12 }}
      styles={{
        header: { minHeight: 36, padding: '0 12px' },
        body: { padding: '12px' },
      }}
      title={
        <Space size={4}>
          <PlusOutlined />
          <Text style={{ fontSize: 13 }}>新增作業紀錄</Text>
        </Space>
      }
      extra={
        <Button
          type="text"
          size="small"
          icon={<CloseOutlined />}
          onClick={handleCancel}
        />
      }
    >
      <Form form={form} layout="vertical" size="small">
        {/* Row 1: 關聯公文 */}
        <Form.Item name="document_id" label="關聯公文" style={{ marginBottom: 8 }}>
          <Select
            placeholder="選擇公文（可選，主旨自動帶入）"
            options={docOptions}
            allowClear
            showSearch
            optionFilterProp="searchText"
            onChange={handleDocumentChange}
            notFoundContent={
              <Text type="secondary">此派工單尚無關聯公文</Text>
            }
          />
        </Form.Item>

        {/* Row 2: 作業類別 + 狀態 */}
        <Row gutter={8}>
          <Col span={14}>
            <Form.Item
              name="work_category"
              label="作業類別"
              rules={[{ required: true, message: '請選擇' }]}
              style={{ marginBottom: 8 }}
            >
              <Select placeholder="請選擇">
                {WORK_CATEGORY_GROUPS.map((group) => (
                  <Select.OptGroup key={group.group} label={group.group}>
                    {group.items.map((item) => (
                      <Select.Option key={item.value} value={item.value}>
                        {item.label}
                      </Select.Option>
                    ))}
                  </Select.OptGroup>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col span={10}>
            <Form.Item
              name="status"
              label="狀態"
              rules={[{ required: true, message: '請選擇' }]}
              style={{ marginBottom: 8 }}
            >
              <Radio.Group>
                {CHAIN_STATUS_OPTIONS.map((opt) => (
                  <Radio.Button key={opt.value} value={opt.value}>
                    {opt.label}
                  </Radio.Button>
                ))}
              </Radio.Group>
            </Form.Item>
          </Col>
        </Row>

        {/* Row 2.5: 關聯工程（多工程時顯示選擇器） */}
        {linkedProjects.length > 1 && (
          <Form.Item
            name="taoyuan_project_id"
            label="關聯工程"
            style={{ marginBottom: 8 }}
          >
            <Select
              placeholder="選擇關聯工程"
              allowClear
              options={linkedProjects.map((p) => ({
                value: p.project_id,
                label: p.project_name || `工程 #${p.project_id}`,
              }))}
            />
          </Form.Item>
        )}

        {/* Row 3: 前序紀錄 + 期限 */}
        <Row gutter={8}>
          <Col span={14}>
            <Form.Item name="parent_record_id" label="前序紀錄" style={{ marginBottom: 8 }}>
              <Select
                placeholder="自動預選最後一筆"
                options={parentRecordOptions}
                allowClear
                showSearch
                optionFilterProp="label"
                notFoundContent="尚無其他紀錄"
              />
            </Form.Item>
          </Col>
          <Col span={10}>
            <Form.Item name="deadline_date" label="期限日期" style={{ marginBottom: 8 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>

        {/* Row 4: 描述 */}
        <Form.Item name="description" label="事項描述" style={{ marginBottom: 12 }}>
          <TextArea rows={2} placeholder="選擇公文後自動帶入主旨" />
        </Form.Item>

        {/* Actions */}
        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button size="small" onClick={handleCancel}>
              取消
            </Button>
            <Button
              type="primary"
              size="small"
              icon={<SaveOutlined />}
              loading={createMutation.isPending}
              onClick={handleSave}
            >
              建立紀錄
            </Button>
          </Space>
        </div>
      </Form>
    </Card>
  );
};

export default InlineRecordCreator;
