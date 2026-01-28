/**
 * PrimaryFilters 元件
 *
 * 主要篩選區塊：關鍵字搜尋、公文類型、發文形式、承攬案件
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import { Input, Select, Row, Col, Tooltip } from 'antd';
import { SearchOutlined, InfoCircleOutlined } from '@ant-design/icons';
import FilterFieldWrapper from './FilterFieldWrapper';
import { DOC_TYPE_OPTIONS, DELIVERY_METHOD_OPTIONS } from '../constants';
import type { PrimaryFiltersProps } from '../types';

const { Option } = Select;

const PrimaryFilters: React.FC<PrimaryFiltersProps> = ({
  localFilters,
  isMobile,
  contractCaseOptions,
  onFilterChange,
  onApplyFilters,
}) => {
  return (
    <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]}>
      {/* 關鍵字搜尋 (文號/主旨/說明/備註) */}
      <Col span={24} md={8}>
        <FilterFieldWrapper
          label="關鍵字搜尋"
          tooltip="搜尋範圍包含：公文字號、主旨、說明、備註。支援模糊搜尋，輸入2個字元以上開始提供建議。按 Enter 快速套用篩選。"
          isMobile={isMobile}
        >
          <Input.Search
            placeholder={isMobile ? '搜尋...' : '文號/主旨/說明/備註...'}
            value={localFilters.search || ''}
            onChange={(e) => onFilterChange('search', e.target.value)}
            onSearch={onApplyFilters}
            allowClear
            enterButton={false}
            style={{ width: '100%' }}
            size={isMobile ? 'small' : 'middle'}
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
