/**
 * 案件資訊 Tab
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import React from 'react';
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Progress,
  Form,
  Input,
  Select,
  DatePicker,
  InputNumber,
  Checkbox,
} from 'antd';
import { EditOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import type { CaseInfoTabProps } from './types';
import {
  CATEGORY_OPTIONS,
  CASE_NATURE_OPTIONS,
  STATUS_OPTIONS,
} from './constants';
import { parseCurrencyInput } from '../../../utils/format';

const { Text } = Typography;
const { Option } = Select;

// 輔助函數
const getStatusTagColor = (status?: string) => {
  const statusOption = STATUS_OPTIONS.find(s => s.value === status);
  return statusOption?.color || 'default';
};

const getStatusTagText = (status?: string) => {
  const statusOption = STATUS_OPTIONS.find(s => s.value === status);
  return statusOption?.label || status || '未設定';
};

const getCategoryTagColor = (category?: string) => {
  const categoryOption = CATEGORY_OPTIONS.find(c => c.value === category);
  return categoryOption?.color || 'default';
};

const getCategoryTagText = (category?: string) => {
  const categoryOption = CATEGORY_OPTIONS.find(c => c.value === category);
  return categoryOption?.label || category || '未分類';
};

const getCaseNatureTagColor = (caseNature?: string) => {
  const option = CASE_NATURE_OPTIONS.find(c => c.value === caseNature);
  return option?.color || 'default';
};

const getCaseNatureTagText = (caseNature?: string) => {
  const option = CASE_NATURE_OPTIONS.find(c => c.value === caseNature);
  return option?.label || caseNature || '未設定';
};

const formatAmount = (amount?: number) => {
  if (!amount) return '-';
  return new Intl.NumberFormat('zh-TW').format(amount);
};

export const CaseInfoTab: React.FC<CaseInfoTabProps> = ({
  data,
  isEditing,
  setIsEditing,
  form,
  onSave,
  calculateProgress,
}) => {
  const progress = calculateProgress();

  const startEdit = () => {
    const dateRange = (data.start_date && data.end_date)
      ? [dayjs(data.start_date), dayjs(data.end_date)]
      : undefined;

    form.setFieldsValue({
      project_name: data.project_name,
      year: data.year,
      client_agency: data.client_agency,
      contract_doc_number: data.contract_doc_number,
      project_code: data.project_code,
      category: data.category,
      case_nature: data.case_nature,
      contract_amount: data.contract_amount,
      winning_amount: data.winning_amount,
      date_range: dateRange,
      status: data.status,
      progress: data.progress,
      project_path: data.project_path,
      notes: data.notes,
      has_dispatch_management: data.has_dispatch_management ?? false,
    });
    setIsEditing(true);
  };

  return (
    <div>
      {/* 進度顯示 */}
      <Card title="執行進度" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={18}>
            <Progress
              percent={data.progress ?? progress}
              status={data.status === '已結案' ? 'success' : (data.status === '未得標' || data.status === '暫停') ? 'exception' : 'active'}
            />
          </Col>
          <Col span={6} style={{ textAlign: 'right' }}>
            <div>完成度: {data.progress ?? progress}%</div>
            <div style={{ color: '#666', fontSize: '12px' }}>
              {data.progress !== undefined ? '手動設定' : '根據契約期程計算'}
            </div>
          </Col>
        </Row>
      </Card>

      {/* 基本資訊 */}
      <Card
        title="基本資訊"
        style={{ marginBottom: 16 }}
        extra={
          isEditing ? (
            <Space>
              <Button size="small" onClick={() => setIsEditing(false)}>取消</Button>
              <Button size="small" type="primary" onClick={() => form.submit()}>儲存</Button>
            </Space>
          ) : (
            <Button size="small" icon={<EditOutlined />} onClick={startEdit}>編輯</Button>
          )
        }
      >
        {isEditing ? (
          <Form form={form} layout="vertical" onFinish={onSave}>
            <Row gutter={16}>
              <Col span={24}>
                <Form.Item name="project_name" label="案件名稱" rules={[{ required: true, message: '請輸入案件名稱' }]}>
                  <Input placeholder="請輸入案件名稱" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="year" label="年度" rules={[{ required: true, message: '請選擇年度' }]}>
                  <InputNumber style={{ width: '100%' }} min={2020} max={2050} placeholder="西元年" />
                </Form.Item>
              </Col>
              <Col span={18}>
                <Form.Item name="client_agency" label="委託單位">
                  <Input placeholder="請輸入委託單位" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="contract_doc_number" label="契約文號">
                  <Input placeholder="請輸入契約文號" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="project_code"
                  label="專案編號"
                  tooltip="格式: CK{年度6碼}_{類別2碼}_{性質2碼}_{流水號3碼}"
                >
                  <Input placeholder="留空自動產生" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="category" label="案件類別">
                  <Select placeholder="請選擇案件類別">
                    {CATEGORY_OPTIONS.map(opt => (
                      <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="case_nature" label="案件性質">
                  <Select placeholder="請選擇案件性質">
                    {CASE_NATURE_OPTIONS.map(opt => (
                      <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="contract_amount" label="契約金額">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="請輸入契約金額"
                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={parseCurrencyInput}
                    prefix="NT$"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="winning_amount" label="得標金額">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="請輸入得標金額"
                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={parseCurrencyInput}
                    prefix="NT$"
                  />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="date_range" label="契約期程">
                  <DatePicker.RangePicker
                    style={{ width: '100%' }}
                    placeholder={['開始日期', '結束日期']}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="status" label="執行狀態">
                  <Select placeholder="請選擇執行狀態">
                    {STATUS_OPTIONS.map(opt => (
                      <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="progress" label="完成進度 (%)" tooltip="當狀態設為「已結案」時，進度自動設為 100%">
                  <InputNumber style={{ width: '100%' }} min={0} max={100} placeholder="0-100" />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="project_path" label="專案路徑">
                  <Input placeholder="請輸入專案資料夾路徑 (可選)" />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="notes" label="備註">
                  <Input.TextArea rows={3} placeholder="請輸入備註說明" />
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="has_dispatch_management" valuePropName="checked">
                  <Checkbox>啟用派工管理功能（勾選後此案件可使用派工安排、工程關聯等功能）</Checkbox>
                </Form.Item>
              </Col>
            </Row>
          </Form>
        ) : (
          <Descriptions column={2} bordered size="small" items={[
            { key: '案件名稱', label: '案件名稱', span: 2, children: (
              <Text strong>{data.project_name}</Text>
            ) },
            { key: '年度', label: '年度', children: `${data.year}年` },
            { key: '委託單位', label: '委託單位', children: data.client_agency || '-' },
            { key: '契約文號', label: '契約文號', children: data.contract_doc_number || '-' },
            { key: '專案編號', label: '專案編號', children: data.project_code ? <Text code>{data.project_code}</Text> : '-' },
            { key: '案件類別', label: '案件類別', children: (
              <Tag color={getCategoryTagColor(data.category)}>
                {getCategoryTagText(data.category)}
              </Tag>
            ) },
            { key: '案件性質', label: '案件性質', children: (
              <Tag color={getCaseNatureTagColor(data.case_nature)}>
                {getCaseNatureTagText(data.case_nature)}
              </Tag>
            ) },
            { key: '契約金額', label: '契約金額', children: data.contract_amount ? `NT$ ${formatAmount(data.contract_amount)}` : '-' },
            { key: '得標金額', label: '得標金額', children: data.winning_amount ? `NT$ ${formatAmount(data.winning_amount)}` : '-' },
            { key: '開始日期', label: '開始日期', children: data.start_date ? dayjs(data.start_date).format('YYYY/MM/DD') : '-' },
            { key: '結束日期', label: '結束日期', children: data.end_date ? dayjs(data.end_date).format('YYYY/MM/DD') : '-' },
            { key: '執行狀態', label: '執行狀態', children: (
              <Tag color={getStatusTagColor(data.status)}>
                {getStatusTagText(data.status)}
              </Tag>
            ) },
            { key: '完成進度', label: '完成進度', children: data.progress !== undefined ? `${data.progress}%` : '-' },
            { key: '專案路徑', label: '專案路徑', span: 2, children: data.project_path ? <Text type="secondary">{data.project_path}</Text> : '-' },
            { key: '備註', label: '備註', span: 2, children: data.notes || '-' },
            { key: '派工管理', label: '派工管理', span: 2, children: (
              <Tag color={data.has_dispatch_management ? 'green' : 'default'}>
                {data.has_dispatch_management ? '已啟用' : '未啟用'}
              </Tag>
            ) },
          ]} />
        )}
      </Card>

      {/* 專案說明 */}
      {!isEditing && data.description && (
        <Card title="專案說明" style={{ marginBottom: 16 }}>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{data.description}</div>
        </Card>
      )}
    </div>
  );
};

export default CaseInfoTab;
