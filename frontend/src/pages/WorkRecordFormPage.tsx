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

import React, { useCallback, useEffect, useMemo, useState } from 'react';
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
  Empty,
  Tooltip,
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
import { dispatchOrdersApi } from '../api/taoyuanDispatchApi';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { isReceiveDocument } from '../types/api';
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

  // 公文搜尋狀態
  const [docSearchKeyword, setDocSearchKeyword] = useState('');

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

  // 搜尋可關聯的公文（伺服器端搜尋）
  const { data: searchedDocsResult, isLoading: searchingDocs } = useQuery({
    queryKey: ['documents-for-work-record', docSearchKeyword],
    queryFn: async () => {
      if (!docSearchKeyword.trim()) return { items: [] };
      return dispatchOrdersApi.searchLinkableDocuments(
        docSearchKeyword,
        20,
      );
    },
    enabled: !!docSearchKeyword.trim(),
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

  // 公文選項：合併已關聯公文 + 搜尋結果
  const docOptions = useMemo(() => {
    const seenIds = new Set<number>();
    const options: Array<{
      value: number;
      label: React.ReactNode;
      searchText: string;
    }> = [];

    // 已關聯公文（優先顯示）
    if (linkedDocs) {
      for (const d of linkedDocs) {
        if (seenIds.has(d.document_id)) continue;
        seenIds.add(d.document_id);
        const isOutgoing = d.doc_number?.startsWith('乾坤');
        const tag = isOutgoing ? '發' : '收';
        const color = isOutgoing ? 'green' : 'blue';
        const docNumber = d.doc_number || `ID:${d.document_id}`;
        const subject = d.subject || '';
        options.push({
          value: d.document_id,
          label: (
            <Tooltip
              title={subject}
              placement="right"
              mouseEnterDelay={0.5}
            >
              <span>
                <Tag color={color} style={{ marginRight: 4 }}>{tag}</Tag>
                {docNumber}
                {d.doc_date ? ` (${d.doc_date.substring(0, 10)})` : ''}
              </span>
            </Tooltip>
          ),
          searchText: `${d.doc_number || ''} ${subject}`,
        });
      }
    }

    // 搜尋結果
    const searchedDocs = searchedDocsResult?.items ?? [];
    for (const d of searchedDocs) {
      if (seenIds.has(d.id)) continue;
      seenIds.add(d.id);
      const docIsReceive = isReceiveDocument(d.category);
      const tag = docIsReceive ? '收' : '發';
      const color = docIsReceive ? 'blue' : 'green';
      const docNumber = d.doc_number || `#${d.id}`;
      const subject = d.subject || '(無主旨)';
      options.push({
        value: d.id,
        label: (
          <Tooltip
            title={<div><div>{docNumber}</div><div>{subject}</div></div>}
            placement="right"
            mouseEnterDelay={0.5}
          >
            <span>
              <Tag color={color} style={{ marginRight: 4 }}>{tag}</Tag>
              {docNumber}
              {d.doc_date ? ` (${d.doc_date.substring(0, 10)})` : ''}
              <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>
                {subject.length > 20 ? subject.substring(0, 20) + '...' : subject}
              </span>
            </span>
          </Tooltip>
        ),
        searchText: `${d.doc_number || ''} ${subject}`,
      });
    }

    return options;
  }, [linkedDocs, searchedDocsResult?.items]);

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
      if (!docId) return;
      // 先從已關聯公文找
      const linkedDoc = linkedDocs?.find((d) => d.document_id === docId);
      const searchedDoc = searchedDocsResult?.items?.find((d) => d.id === docId);
      const subject = linkedDoc?.subject || searchedDoc?.subject;
      if (subject) {
        const currentDesc = form.getFieldValue('description');
        // 僅在描述為空時自動帶入公文主旨
        if (!currentDesc) {
          form.setFieldsValue({ description: subject });
        }
      }
    },
    [linkedDocs, searchedDocsResult?.items, form],
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
        document_id: values.document_id ?? null,
        parent_record_id: values.parent_record_id ?? null,
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
                placeholder="輸入公文字號或主旨搜尋..."
                options={docOptions}
                allowClear
                showSearch
                filterOption={false}
                onSearch={setDocSearchKeyword}
                onChange={handleDocumentChange}
                loading={searchingDocs}
                notFoundContent={
                  docSearchKeyword ? (
                    <Empty description="無符合的公文" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : (
                    <Text type="secondary">輸入關鍵字搜尋公文</Text>
                  )
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
