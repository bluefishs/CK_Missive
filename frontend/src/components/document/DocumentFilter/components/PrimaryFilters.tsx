/**
 * PrimaryFilters 元件
 *
 * 主要篩選區塊：關鍵字搜尋（含 AI 智慧填充）、公文類型、發文形式、承攬案件
 *
 * @version 1.1.0
 * @date 2026-02-06
 */

import React, { useState, useCallback } from 'react';
import { Input, Select, Row, Col, Tooltip, Button, message } from 'antd';
import { SearchOutlined, InfoCircleOutlined, RobotOutlined } from '@ant-design/icons';
import FilterFieldWrapper from './FilterFieldWrapper';
import { DOC_TYPE_OPTIONS, DELIVERY_METHOD_OPTIONS } from '../constants';
import type { PrimaryFiltersProps } from '../types';
import { aiApi } from '../../../../api/aiApi';

const { Option } = Select;

const PrimaryFilters: React.FC<PrimaryFiltersProps> = ({
  localFilters,
  isMobile,
  contractCaseOptions,
  onFilterChange,
  onMultipleFilterChange,
  onApplyFilters,
}) => {
  const [aiLoading, setAiLoading] = useState(false);

  const handleAIParseIntent = useCallback(async () => {
    const query = localFilters.search?.trim();
    if (!query || query.length < 2) {
      message.warning('請先輸入搜尋關鍵字（至少 2 個字元）');
      return;
    }

    setAiLoading(true);
    try {
      const result = await aiApi.parseSearchIntent(query);
      if (!result.success || result.parsed_intent.confidence < 0.1) {
        message.info('AI 無法解析此查詢，請使用傳統篩選');
        return;
      }

      const intent = result.parsed_intent;
      const updates: Record<string, string | undefined> = {};

      if (intent.keywords?.length) updates.search = intent.keywords.join(' ');
      if (intent.doc_type) updates.doc_type = intent.doc_type;
      if (intent.category) updates.category = intent.category;
      if (intent.sender) updates.sender = intent.sender;
      if (intent.receiver) updates.receiver = intent.receiver;
      if (intent.date_from) updates.date_from = intent.date_from;
      if (intent.date_to) updates.date_to = intent.date_to;
      if (intent.status) updates.status = intent.status;
      if (intent.contract_case) updates.contract_case = intent.contract_case;

      if (onMultipleFilterChange) {
        onMultipleFilterChange(updates);
      }

      const fieldCount = Object.keys(updates).length;
      message.success(`AI 已解析並填充 ${fieldCount} 個篩選條件（信心度 ${Math.round(intent.confidence * 100)}%）`);
    } catch {
      message.error('AI 解析失敗，請稍後再試');
    } finally {
      setAiLoading(false);
    }
  }, [localFilters.search, onMultipleFilterChange]);

  return (
    <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]}>
      {/* 關鍵字搜尋 (文號/主旨/說明/備註) + AI 智慧填充 */}
      <Col span={24} md={8}>
        <FilterFieldWrapper
          label="關鍵字搜尋"
          tooltip="搜尋範圍包含：公文字號、主旨、說明、備註。支援模糊搜尋。點擊 AI 按鈕可智慧解析自然語言並自動填充篩選條件。"
          isMobile={isMobile}
        >
          <Input.Search
            placeholder={isMobile ? '搜尋或輸入自然語言...' : '文號/主旨/說明/備註 或 自然語言查詢...'}
            value={localFilters.search || ''}
            onChange={(e) => onFilterChange('search', e.target.value)}
            onSearch={onApplyFilters}
            allowClear
            enterButton={false}
            style={{ width: '100%' }}
            size={isMobile ? 'small' : 'middle'}
            suffix={
              <Tooltip title="AI 智慧解析：將自然語言查詢自動填充到篩選條件">
                <Button
                  type="text"
                  size="small"
                  icon={<RobotOutlined />}
                  loading={aiLoading}
                  onClick={handleAIParseIntent}
                  style={{
                    color: aiLoading ? '#1890ff' : '#8c8c8c',
                    padding: '0 4px',
                  }}
                />
              </Tooltip>
            }
          />
        </FilterFieldWrapper>
      </Col>

      {/* 公文類型篩選 */}
      <Col span={12} md={4}>
        <FilterFieldWrapper
          label="公文類型"
          tooltip="選擇特定的公文類型進行篩選。包含：函、開會通知單、會勘通知單。留空顯示所有類型。"
          isMobile={isMobile}
        >
          <Select
            placeholder={isMobile ? '類型' : '請選擇公文類型'}
            value={localFilters.doc_type || ''}
            onChange={(value) => onFilterChange('doc_type', value)}
            style={{ width: '100%' }}
            allowClear
            size={isMobile ? 'small' : 'middle'}
          >
            {DOC_TYPE_OPTIONS.map((option) => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        </FilterFieldWrapper>
      </Col>

      {/* 發文形式篩選 */}
      <Col span={12} md={4}>
        <FilterFieldWrapper
          label="發文形式"
          tooltip="選擇公文發送方式：電子交換或紙本郵寄"
          isMobile={isMobile}
        >
          <Select
            placeholder={isMobile ? '形式' : '請選擇發文形式'}
            value={localFilters.delivery_method || ''}
            onChange={(value) => onFilterChange('delivery_method', value)}
            style={{ width: '100%' }}
            allowClear
            size={isMobile ? 'small' : 'middle'}
          >
            {DELIVERY_METHOD_OPTIONS.map((option) => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        </FilterFieldWrapper>
      </Col>

      {/* 承攬案件 */}
      <Col span={24} md={8}>
        <FilterFieldWrapper
          label="承攬案件"
          tooltip="選擇相關的承攬案件進行篩選。可輸入關鍵字快速搜尋現有案件。選項基於系統中已登記的承攬案件。"
          isMobile={isMobile}
        >
          <Select
            placeholder={isMobile ? '案件' : '請選擇或搜尋承攬案件...'}
            value={localFilters.contract_case || ''}
            onChange={(value) => onFilterChange('contract_case', value)}
            style={{ width: '100%' }}
            allowClear
            showSearch
            size={isMobile ? 'small' : 'middle'}
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().indexOf((input as string)?.toLowerCase()) >= 0
            }
            suffixIcon={
              isMobile ? null : (
                <div>
                  <SearchOutlined style={{ marginRight: 4 }} />
                  <Tooltip title="可搜尋案件名稱">
                    <InfoCircleOutlined style={{ color: '#ccc', fontSize: '12px' }} />
                  </Tooltip>
                </div>
              )
            }
          >
            {contractCaseOptions.map((option) => (
              <Option key={option.value} value={option.value} label={option.label}>
                {option.label}
              </Option>
            ))}
          </Select>
        </FilterFieldWrapper>
      </Col>
    </Row>
  );
};

export default PrimaryFilters;
