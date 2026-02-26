/**
 * 公文建立 - 公文資訊 Tab
 *
 * 共用於收文和發文建立頁面，根據 mode 顯示不同欄位
 *
 * @version 1.0.0
 * @date 2026-01-28
 */

import React from 'react';
import { Form, Input, Select, DatePicker, Row, Col, Card, Space, Skeleton } from 'antd';
import type { FormInstance } from 'antd';
import type { NextSendNumberResponse } from '../../../api/documentsApi';
import type { DocumentCreateMode } from '../../../hooks/business/useDocumentCreateForm';
import { AIClassifyPanel } from '../../ai/AIClassifyPanel';
import { AgencyMatchInput } from '../../common/AgencyMatchInput';
import type { AgencyCandidate } from '../../../types/ai';

import {
  DELIVERY_METHOD_OPTIONS,
  DOC_DIRECTION_OPTIONS,
  DOC_TYPE_OPTIONS,
} from '../../../constants';

const { TextArea } = Input;
const { Option } = Select;

/** 發文專用公文類型選項 */
const SEND_DOC_TYPE_OPTIONS = [
  { value: '函', label: '函' },
  { value: '書函', label: '書函' },
  { value: '開會通知單', label: '開會通知單' },
  { value: '會勘通知單', label: '會勘通知單' },
  { value: '公告', label: '公告' },
  { value: '令', label: '令' },
  { value: '通知', label: '通知' },
];

export interface DocumentCreateInfoTabProps {
  mode: DocumentCreateMode;
  form: FormInstance;
  agenciesLoading: boolean;
  buildAgencyOptions: (includeCompany?: boolean) => Array<{ value: string; label: string }>;
  handleCategoryChange?: (value: string) => void;
  // 發文模式專用
  nextNumber?: NextSendNumberResponse | null;
  nextNumberLoading?: boolean;
  /** AI 機關匹配候選列表 (從 agencies 列表轉換) */
  agencyCandidates?: AgencyCandidate[];
}

export const DocumentCreateInfoTab: React.FC<DocumentCreateInfoTabProps> = ({
  mode,
  form,
  agenciesLoading,
  buildAgencyOptions,
  handleCategoryChange,
  nextNumber,
  nextNumberLoading,
  agencyCandidates,
}) => {
  if (mode === 'receive') {
    return <ReceiveInfoTab
      form={form}
      agenciesLoading={agenciesLoading}
      buildAgencyOptions={buildAgencyOptions}
      handleCategoryChange={handleCategoryChange}
      agencyCandidates={agencyCandidates}
    />;
  }

  return <SendInfoTab
    form={form}
    agenciesLoading={agenciesLoading}
    buildAgencyOptions={buildAgencyOptions}
    nextNumber={nextNumber}
    nextNumberLoading={nextNumberLoading}
    agencyCandidates={agencyCandidates}
  />;
};

// =============================================================================
// 收文資訊 Tab
// =============================================================================

interface ReceiveInfoTabProps {
  form: FormInstance;
  agenciesLoading: boolean;
  buildAgencyOptions: (includeCompany?: boolean) => Array<{ value: string; label: string }>;
  handleCategoryChange?: (value: string) => void;
  agencyCandidates?: AgencyCandidate[];
}

const ReceiveInfoTab: React.FC<ReceiveInfoTabProps> = ({
  form,
  agenciesLoading,
  buildAgencyOptions,
  handleCategoryChange,
  agencyCandidates,
}) => {
  const watchedSubject = Form.useWatch('subject', form) as string | undefined;
  return (
    <Form form={form} layout="vertical">
      <Row gutter={16}>
        <Col span={6}>
          <Form.Item
            label="發文形式"
            name="delivery_method"
            rules={[{ required: true, message: '請選擇發文形式' }]}
          >
            <Select placeholder="請選擇發文形式">
              {DELIVERY_METHOD_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item
            label="類別"
            name="category"
            rules={[{ required: true, message: '請選擇類別' }]}
          >
            <Select placeholder="請選擇類別" onChange={handleCategoryChange}>
              {DOC_DIRECTION_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item
            label="公文類型"
            name="doc_type"
            rules={[{ required: true, message: '請選擇公文類型' }]}
          >
            <Select placeholder="請選擇公文類型">
              {DOC_TYPE_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={6}>
          <Form.Item
            label="公文字號"
            name="doc_number"
            rules={[{ required: true, message: '請輸入公文字號' }]}
          >
            <Input placeholder="如：桃工用字第1140024090號" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="發文單位"
            name="sender"
            rules={[{ required: true, message: '請選擇發文單位' }]}
          >
            <AgencyMatchInput
              placeholder="請選擇或輸入發文單位"
              loading={agenciesLoading}
              options={buildAgencyOptions(true)}
              candidates={agencyCandidates}
            />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="受文單位"
            name="receiver"
            rules={[{ required: true, message: '請選擇受文單位' }]}
            extra="收文時預設為本公司"
          >
            <Select
              placeholder="請選擇受文單位"
              loading={agenciesLoading}
              showSearch
              allowClear
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={buildAgencyOptions(true)}
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item label="公文日期" name="doc_date">
            <DatePicker style={{ width: '100%' }} placeholder="請選擇公文日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="收文日期" name="receive_date">
            <DatePicker style={{ width: '100%' }} placeholder="請選擇收文日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item label="發文日期" name="send_date">
            <DatePicker style={{ width: '100%' }} placeholder="請選擇發文日期" />
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

      {/* AI 分類建議 — 主旨填寫後可觸發 */}
      {watchedSubject && watchedSubject.length >= 5 && (
        <AIClassifyPanel
          subject={watchedSubject}
          showCard={false}
          onSelect={(docType, category) => {
            form.setFieldsValue({ doc_type: docType, category });
          }}
          style={{ marginBottom: 16 }}
        />
      )}

      <Form.Item label="說明" name="content">
        <TextArea rows={4} placeholder="請輸入公文內容說明" maxLength={1000} showCount />
      </Form.Item>

      <Form.Item label="備註" name="notes">
        <TextArea rows={3} placeholder="請輸入備註" maxLength={500} showCount />
      </Form.Item>
    </Form>
  );
};

// =============================================================================
// 發文資訊 Tab
// =============================================================================

interface SendInfoTabProps {
  form: FormInstance;
  agenciesLoading: boolean;
  buildAgencyOptions: (includeCompany?: boolean) => Array<{ value: string; label: string }>;
  nextNumber?: NextSendNumberResponse | null;
  nextNumberLoading?: boolean;
  agencyCandidates?: AgencyCandidate[];
}

const SendInfoTab: React.FC<SendInfoTabProps> = ({
  form,
  agenciesLoading,
  buildAgencyOptions,
  nextNumber,
  nextNumberLoading,
  agencyCandidates,
}) => {
  const watchedSubject = Form.useWatch('subject', form) as string | undefined;
  return (
    <Form form={form} layout="vertical">
      {/* 公文字號區塊 */}
      <Card
        size="small"
        title="公文字號（自動產生）"
        style={{ marginBottom: 16, background: '#f6ffed', borderColor: '#b7eb8f' }}
      >
        {nextNumberLoading ? (
          <Skeleton.Input active style={{ width: 300 }} />
        ) : (
          <Space direction="vertical" size={0}>
            <span style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
              {nextNumber?.full_number || '載入中...'}
            </span>
            {nextNumber && (
              <span style={{ color: '#666' }}>
                {nextNumber.year}年 (民國{nextNumber.roc_year}年) • 流水號{' '}
                {nextNumber.sequence_number.toString().padStart(6, '0')}
              </span>
            )}
          </Space>
        )}
        <Form.Item name="doc_number" hidden>
          <Input />
        </Form.Item>
      </Card>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="公文類型"
            name="doc_type"
            rules={[{ required: true, message: '請選擇公文類型' }]}
          >
            <Select placeholder="請選擇公文類型">
              {SEND_DOC_TYPE_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="發文形式"
            name="delivery_method"
            rules={[{ required: true, message: '請選擇發文形式' }]}
          >
            <Select placeholder="請選擇發文形式">
              {DELIVERY_METHOD_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="發文日期"
            name="doc_date"
            rules={[{ required: true, message: '請選擇發文日期' }]}
          >
            <DatePicker style={{ width: '100%' }} placeholder="請選擇發文日期" />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Form.Item
            label="發文機關"
            name="sender"
            rules={[{ required: true, message: '請輸入發文機關' }]}
            extra="預設為本公司，如需修改請直接編輯"
          >
            <Input placeholder="請輸入發文機關" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item
            label="受文單位"
            name="receiver"
            rules={[{ required: true, message: '請選擇受文單位' }]}
          >
            <AgencyMatchInput
              placeholder="請選擇或輸入受文單位"
              loading={agenciesLoading}
              options={buildAgencyOptions(false)}
              candidates={agencyCandidates}
            />
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

      {/* AI 分類建議 — 主旨填寫後可觸發 */}
      {watchedSubject && watchedSubject.length >= 5 && (
        <AIClassifyPanel
          subject={watchedSubject}
          showCard={false}
          onSelect={(docType) => {
            form.setFieldsValue({ doc_type: docType });
          }}
          style={{ marginBottom: 16 }}
        />
      )}

      <Form.Item label="說明" name="content">
        <TextArea rows={4} placeholder="請輸入公文內容說明" maxLength={1000} showCount />
      </Form.Item>

      <Form.Item label="備註" name="notes">
        <TextArea rows={3} placeholder="請輸入備註" maxLength={500} showCount />
      </Form.Item>
    </Form>
  );
};

export default DocumentCreateInfoTab;
