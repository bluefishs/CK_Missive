/**
 * 作業歷程表單頁面（導航模式）
 *
 * 支援新建與編輯模式：
 * - 新建: /taoyuan/dispatch/:dispatchId/workflow/create
 * - 編輯: /taoyuan/dispatch/:dispatchId/workflow/:recordId/edit
 *
 * v3.0.0: 精簡表單 — 僅保留必要欄位
 *
 * @version 3.0.0
 * @date 2026-02-15
 */

import React, { useCallback, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  DatePicker,
  Button,
  Space,
  App,
  Typography,
  Row,
  Col,
  Radio,
  Tag,
  Collapse,
} from 'antd';
import {
  ArrowLeftOutlined,
  SaveOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

import { ResponsiveContent } from '../components/common';
import { workflowApi } from '../api/taoyuan';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import type {
  WorkRecordCreate,
  WorkRecordUpdate,
  WorkRecord,
  DispatchDocumentLink,
} from '../types/taoyuan';
import {
  WORK_CATEGORY_GROUPS,
  CHAIN_STATUS_OPTIONS,
  getCategoryLabel,
} from '../components/taoyuan/workflow/chainConstants';
import { logger } from '../services/logger';

const { TextArea } = Input;
const { Title, Text } = Typography;

const WorkRecordFormPage: React.FC = () => {
  const { dispatchId, recordId } = useParams<{
    dispatchId: string;
    recordId: string;
  }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const isNew = !recordId;
  const dispatchOrderId = parseInt(dispatchId || '0', 10);
  const workRecordId = recordId ? parseInt(recordId, 10) : undefined;

  const returnTo = searchParams.get('returnTo');
  const returnPath = returnTo || `/taoyuan/dispatch/${dispatchId}?tab=correspondence`;

  // URL 參數預填（新格式優先，舊格式自動轉換）
  const urlDocumentId = searchParams.get('document_id')
    || searchParams.get('incoming_doc_id')
    || searchParams.get('outgoing_doc_id');
  const urlParentRecordId = searchParams.get('parent_record_id');
  const urlWorkCategory = searchParams.get('work_category');

  // ===========================================================================
  // 資料查詢
  // ===========================================================================

  const { data: record, isLoading } = useQuery({
    queryKey: ['dispatch-work-record', workRecordId],
    queryFn: () => workflowApi.getDetail(workRecordId!),
    enabled: !isNew && !!workRecordId,
  });

  const { data: linkedDocs } = useQuery({
    queryKey: ['dispatch-documents', dispatchOrderId],
    queryFn: async () => {
      const resp = await apiClient.post<{ items: DispatchDocumentLink[] }>(
        API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_DOCUMENTS(dispatchOrderId),
      );
      return resp.items ?? [];
    },
    enabled: dispatchOrderId > 0,
  });

  const { data: existingRecordsData } = useQuery({
    queryKey: ['dispatch-work-records', dispatchOrderId],
    queryFn: () => workflowApi.listByDispatchOrder(dispatchOrderId),
    enabled: dispatchOrderId > 0,
  });

  const existingRecords = useMemo(
    () => (existingRecordsData?.items ?? []) as WorkRecord[],
    [existingRecordsData?.items],
  );

  // 公文選項
  const docOptions = useMemo(() => {
    if (!linkedDocs) return [];
    return linkedDocs.map((d) => {
      const isOutgoing = d.doc_number?.startsWith('乾坤');
      const tag = isOutgoing ? '發' : '收';
      const color = isOutgoing ? 'green' : 'blue';
      return {
        value: d.document_id,
        label: (
          <span>
            <Tag color={color} style={{ marginRight: 4 }}>{tag}</Tag>
            {d.doc_number || `ID:${d.document_id}`}
            {d.doc_date ? ` (${d.doc_date.substring(0, 10)})` : ''}
          </span>
        ),
        searchText: `${d.doc_number || ''} ${d.subject || ''}`,
      };
    });
  }, [linkedDocs]);

  // 前序紀錄選項
  const parentRecordOptions = useMemo(() => {
    return existingRecords
      .filter((r) => r.id !== workRecordId)
      .map((r) => {
        const catLabel = getCategoryLabel(r);
        const docNum = r.document?.doc_number || r.incoming_doc?.doc_number || r.outgoing_doc?.doc_number || '';
        return {
          value: r.id,
          label: `#${r.id} ${catLabel}${docNum ? ` — ${docNum}` : ''}${r.record_date ? ` (${r.record_date})` : ''}`,
        };
      });
  }, [existingRecords, workRecordId]);

  // ===========================================================================
  // 公文選擇時自動帶入主旨
  // ===========================================================================

  const handleDocumentChange = useCallback(
    (docId: number | undefined) => {
      if (!docId || !linkedDocs) return;
      const doc = linkedDocs.find((d) => d.document_id === docId);
      if (doc?.subject) {
        const currentDesc = form.getFieldValue('description');
        // 僅在描述為空時自動帶入公文主旨
        if (!currentDesc) {
          form.setFieldsValue({ description: doc.subject });
        }
      }
    },
    [linkedDocs, form],
  );

  // ===========================================================================
  // 表單初始化
  // ===========================================================================

  // 編輯模式：填入現有資料
  useEffect(() => {
    if (record) {
      // 編輯模式：description 為空時自動帶入公文主旨
      let desc = record.description;
      if (!desc && record.document?.subject) {
        desc = record.document.subject;
      }
      form.setFieldsValue({
        work_category: record.work_category,
        document_id: record.document_id,
        parent_record_id: record.parent_record_id,
        deadline_date: record.deadline_date ? dayjs(record.deadline_date) : undefined,
        status: record.status,
        description: desc,
        batch_no: record.batch_no,
        batch_label: record.batch_label,
        // 保留舊格式供後端向後相容
        incoming_doc_id: record.incoming_doc_id,
        outgoing_doc_id: record.outgoing_doc_id,
        milestone_type: record.milestone_type,
      });
    }
  }, [record, form]);

  // 新建模式：預設值
  useEffect(() => {
    if (isNew) {
      const defaults: Record<string, unknown> = {
        status: 'in_progress',
      };

      if (urlDocumentId) {
        const parsed = parseInt(urlDocumentId, 10);
        if (!isNaN(parsed)) {
          defaults.document_id = parsed;
          // 自動帶入公文主旨
          const doc = linkedDocs?.find((d) => d.document_id === parsed);
          if (doc?.subject) {
            defaults.description = doc.subject;
          }
        }
      }
      if (urlParentRecordId) {
        const parsed = parseInt(urlParentRecordId, 10);
        if (!isNaN(parsed)) defaults.parent_record_id = parsed;
      }
      if (urlWorkCategory) {
        defaults.work_category = urlWorkCategory;
      }

      // 自動預選最後一筆紀錄為前序
      if (!urlParentRecordId && existingRecords.length > 0) {
        const lastRecord = existingRecords[existingRecords.length - 1];
        if (lastRecord) defaults.parent_record_id = lastRecord.id;
      }

      form.setFieldsValue(defaults);
    }
  }, [isNew, form, urlDocumentId, urlParentRecordId, urlWorkCategory, existingRecords, linkedDocs]);

  // ===========================================================================
  // Mutations
  // ===========================================================================

  const createMutation = useMutation({
    mutationFn: (data: WorkRecordCreate) => workflowApi.create(data),
    onSuccess: () => {
      message.success('作業紀錄建立成功');
      queryClient.invalidateQueries({ queryKey: ['dispatch-work-records', dispatchOrderId] });
      queryClient.invalidateQueries({ queryKey: ['project-work-records'] });
      navigate(returnPath);
    },
    onError: (error: Error) => {
      logger.error('[WorkRecordForm] 建立失敗:', error);
      message.error('建立失敗，請稍後再試');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: WorkRecordUpdate }) =>
      workflowApi.update(id, data),
    onSuccess: () => {
      message.success('作業紀錄更新成功');
      queryClient.invalidateQueries({ queryKey: ['dispatch-work-records', dispatchOrderId] });
      queryClient.invalidateQueries({ queryKey: ['project-work-records'] });
      navigate(returnPath);
    },
    onError: (error: Error) => {
      logger.error('[WorkRecordForm] 更新失敗:', error);
      message.error('更新失敗，請稍後再試');
    },
  });

  // ===========================================================================
  // Handlers
  // ===========================================================================

  const formatDate = (val: unknown): string | undefined => {
    if (!val) return undefined;
    if (typeof val === 'object' && val !== null && 'format' in val) {
      return (val as { format: (f: string) => string }).format('YYYY-MM-DD');
    }
    if (typeof val === 'string') return val;
    return undefined;
  };

  const handleSave = useCallback(async () => {
    try {
      const values = await form.validateFields();

      const payload: Record<string, unknown> = {
        work_category: values.work_category,
        document_id: values.document_id || undefined,
        parent_record_id: values.parent_record_id || undefined,
        deadline_date: formatDate(values.deadline_date),
        status: values.status,
        description: values.description || undefined,
        milestone_type: values.milestone_type || 'other',
        batch_no: values.batch_no ?? undefined,
        batch_label: values.batch_label || undefined,
      };

      if (isNew) {
        payload.dispatch_order_id = dispatchOrderId;
        createMutation.mutate(payload as unknown as WorkRecordCreate);
      } else if (workRecordId) {
        updateMutation.mutate({ id: workRecordId, data: payload as unknown as WorkRecordUpdate });
      }
    } catch {
      // form validation failed
    }
  }, [form, isNew, dispatchOrderId, workRecordId, createMutation, updateMutation]);

  const handleBack = useCallback(() => {
    navigate(returnPath);
  }, [navigate, returnPath]);

  const isSaving = createMutation.isPending || updateMutation.isPending;

  // ===========================================================================
  // Render
  // ===========================================================================

  return (
    <ResponsiveContent>
      <div style={{ maxWidth: 600, margin: '0 auto', padding: '24px 0' }}>
        {/* Header */}
        <div style={{ marginBottom: 16 }}>
          <Button
            type="link"
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
            style={{ padding: 0, marginBottom: 8 }}
          >
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            <HistoryOutlined style={{ marginRight: 8 }} />
            {isNew ? '新增作業紀錄' : '編輯作業紀錄'}
          </Title>
        </div>

        {/* Form */}
        <Card loading={!isNew && isLoading}>
          <Form form={form} layout="vertical" size="middle">
            {/* 1. 關聯公文 — 最重要的欄位 */}
            <Form.Item name="document_id" label="關聯公文">
              <Select
                placeholder="選擇關聯公文（可選，主旨自動帶入）"
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

            {/* 2. 作業類別 + 狀態 — 必填 */}
            <Row gutter={12}>
              <Col span={14}>
                <Form.Item
                  name="work_category"
                  label="作業類別"
                  rules={[{ required: true, message: '請選擇作業類別' }]}
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
                  rules={[{ required: true, message: '請選擇狀態' }]}
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

            {/* 3. 前序紀錄 + 期限 */}
            <Row gutter={12}>
              <Col span={14}>
                <Form.Item name="parent_record_id" label="前序紀錄">
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
                <Form.Item name="deadline_date" label="期限日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>

            {/* 4. 事項描述（選擇公文時自動帶入主旨，可修改） */}
            <Form.Item name="description" label="事項描述">
              <TextArea rows={3} placeholder="選擇公文後自動帶入主旨，可自行修改補充" />
            </Form.Item>

            {/* 5. 進階選項（折疊） */}
            <Collapse
              ghost
              size="small"
              items={[{
                key: 'advanced',
                label: '進階選項',
                children: (
                  <Row gutter={12}>
                    <Col span={8}>
                      <Form.Item name="batch_no" label="結案批次">
                        <InputNumber
                          min={1}
                          max={10}
                          placeholder="批次序號"
                          style={{ width: '100%' }}
                        />
                      </Form.Item>
                    </Col>
                    <Col span={16}>
                      <Form.Item name="batch_label" label="批次標籤">
                        <Input placeholder="例：第1批結案" maxLength={50} />
                      </Form.Item>
                    </Col>
                  </Row>
                ),
              }]}
              style={{ marginBottom: 16 }}
            />

            {/* 隱藏欄位：舊格式向後相容 */}
            <Form.Item name="milestone_type" hidden>
              <Input />
            </Form.Item>
            <Form.Item name="incoming_doc_id" hidden>
              <Input />
            </Form.Item>
            <Form.Item name="outgoing_doc_id" hidden>
              <Input />
            </Form.Item>

            {/* Actions */}
            <div style={{ textAlign: 'right', marginTop: 8 }}>
              <Space>
                <Button onClick={handleBack}>取消</Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  loading={isSaving}
                  onClick={handleSave}
                >
                  {isNew ? '建立' : '儲存'}
                </Button>
              </Space>
            </div>
          </Form>
        </Card>
      </div>
    </ResponsiveContent>
  );
};

export default WorkRecordFormPage;
