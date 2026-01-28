/**
 * AdvancedFilters 元件
 *
 * 進階篩選區塊：年度、公文字號、日期範圍、受文單位、發文單位
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import { Input, Select, Row, Col, Tooltip, DatePicker } from 'antd';
import { SearchOutlined, InfoCircleOutlined } from '@ant-design/icons';
import FilterFieldWrapper from './FilterFieldWrapper';
import type { AdvancedFiltersProps } from '../types';

const { Option } = Select;
const { RangePicker } = DatePicker;

const AdvancedFilters: React.FC<AdvancedFiltersProps> = ({
  localFilters,
  isMobile,
  yearOptions,
  senderOptions,
  receiverOptions,
  dateRange,
  onFilterChange,
  onMultipleFilterChange,
  onDateRangeChange,
  onApplyFilters,
}) => {
  return (
    <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]}>
      {/* 第一行：公文年度、公文字號、公文日期 */}
      <Col xs={12} sm={12} md={8}>
        <FilterFieldWrapper
          label="篩選年度"
          tooltip="選擇公文的年度。選項基於系統現有公文的年份。可用於統計特定年度的公文量。"
          isMobile={isMobile}
        >
          <Select
            placeholder={isMobile ? '年度' : '請選擇年度 (預設：所有年度)'}
            value={localFilters.year}
            onChange={(value) => onFilterChange('year', value ? Number(value) : undefined)}
            style={{ width: '100%' }}
            allowClear
            size={isMobile ? 'small' : 'middle'}
            suffixIcon={isMobile ? null : (
              <div>
                <Tooltip title="動態載入現有年份">
                  <InfoCircleOutlined style={{ color: '#ccc', fontSize: '12px' }} />
                </Tooltip>
              </div>
            )}
          >
            {yearOptions.map((option) => (
              <Option key={option.value} value={option.value}>
                {isMobile ? option.value : `${option.value}年 (${yearOptions.length > 0 ? '有資料' : '無資料'})`}
              </Option>
            ))}
          </Select>
        </FilterFieldWrapper>
      </Col>

      <Col xs={12} sm={12} md={8}>
        <FilterFieldWrapper
          label="公文字號"
          tooltip="輸入完整或部分公文字號。例如：乾坤字第1130001號、府字第、部字第等。輸入2個字以上即可取得智能建議。"
          isMobile={isMobile}
        >
          <Input
            placeholder={isMobile ? '字號' : '請輸入公文字號 (例：乾坤字第)'}
            value={localFilters.doc_number || ''}
            onChange={(e) => onFilterChange('doc_number', e.target.value)}
            onPressEnter={onApplyFilters}
            allowClear
            size={isMobile ? 'small' : 'middle'}
            style={{ width: '100%' }}
            suffix={isMobile ? null : (
              <Tooltip title="按 Enter 套用篩選">
                <SearchOutlined style={{ color: '#ccc' }} />
              </Tooltip>
            )}
          />
        </FilterFieldWrapper>
      </Col>

      <Col span={24} md={8}>
        <FilterFieldWrapper
          label="公文日期"
          tooltip="選擇公文日期範圍。可只選擇開始日期或結束日期。日期格式：YYYY-MM-DD。適用於統計特定時間段的公文。"
          isMobile={isMobile}
        >
          <RangePicker
            placeholder={isMobile ? ['起始', '結束'] : ['選擇開始日期 (可選)', '選擇結束日期 (可選)']}
            value={dateRange}
            onChange={(dates, dateStrings) => {
              onDateRangeChange(dates);
              // 批次更新日期範圍
              onMultipleFilterChange({
                doc_date_from: dateStrings[0] || undefined,
                doc_date_to: dateStrings[1] || undefined
              });
            }}
            style={{ width: '100%' }}
            size={isMobile ? 'small' : 'middle'}
            format="YYYY-MM-DD"
            suffixIcon={isMobile ? null : (
              <Tooltip title="日期格式：YYYY-MM-DD">
                <InfoCircleOutlined style={{ color: '#ccc', fontSize: '12px' }} />
              </Tooltip>
            )}
          />
        </FilterFieldWrapper>
      </Col>

      {/* 第二行：受文單位、發文單位 */}
      <Col span={24} md={12}>
        <FilterFieldWrapper
          label="受文單位"
          tooltip="選擇接收公文的機關單位。可輸入關鍵字快速搜尋現有單位。選項基於系統中已登記的公文資料。"
          isMobile={isMobile}
        >
          <Select
            placeholder={isMobile ? '受文單位' : '請選擇或搜尋受文單位...'}
            value={localFilters.receiver || ''}
            onChange={(value) => onFilterChange('receiver', value)}
            style={{ width: '100%' }}
            allowClear
            showSearch
            size={isMobile ? 'small' : 'middle'}
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().indexOf((input as string)?.toLowerCase()) >= 0
            }
            suffixIcon={isMobile ? null : (
              <div>
                <SearchOutlined style={{ marginRight: 4 }} />
                <Tooltip title="可搜尋單位名稱">
                  <InfoCircleOutlined style={{ color: '#ccc', fontSize: '12px' }} />
                </Tooltip>
              </div>
            )}
          >
            {receiverOptions.map((option) => (
              <Option key={option.value} value={option.value} label={option.label}>
                {option.label}
              </Option>
            ))}
          </Select>
        </FilterFieldWrapper>
      </Col>

      <Col span={24} md={12}>
        <FilterFieldWrapper
          label="發文單位"
          tooltip="選擇發送公文的機關單位。可輸入關鍵字快速搜尋現有單位。適用於統計特定機關的公文往來。"
          isMobile={isMobile}
        >
          <Select
            placeholder={isMobile ? '發文單位' : '請選擇或搜尋發文單位...'}
            value={localFilters.sender || ''}
            onChange={(value) => onFilterChange('sender', value)}
            style={{ width: '100%' }}
            allowClear
            showSearch
            size={isMobile ? 'small' : 'middle'}
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().indexOf((input as string)?.toLowerCase()) >= 0
            }
            suffixIcon={isMobile ? null : (
              <div>
                <SearchOutlined style={{ marginRight: 4 }} />
                <Tooltip title="可搜尋單位名稱">
                  <InfoCircleOutlined style={{ color: '#ccc', fontSize: '12px' }} />
                </Tooltip>
              </div>
            )}
          >
            {senderOptions.map((option) => (
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

export default AdvancedFilters;
