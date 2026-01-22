import React, { useState, useEffect } from 'react';
import {
  Input,
  Select,
  Button,
  Row,
  Col,
  Card,
  Typography,
  Tag,
  DatePicker,
  AutoComplete,
  Divider,
  Tooltip,
} from 'antd';
import dayjs from 'dayjs';
const { RangePicker } = DatePicker;
import {
  SearchOutlined,
  FilterOutlined,
  ClearOutlined,
  DownOutlined,
  UpOutlined,
  QuestionCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import { DocumentFilter as DocumentFilterType, OfficialDocument } from '../../types';
import { API_BASE_URL } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import { logger } from '../../utils/logger';
import { useResponsive } from '../../hooks';
const { Option } = Select;
const { Title } = Typography;

// ============================================================================
// API 回應型別定義
// ============================================================================

/** 下拉選單選項 */
interface DropdownOption {
  value: string;
  label: string;
}

/** 機關下拉選項 API 回應 */
interface AgenciesDropdownResponse {
  options: DropdownOption[];
}

/** 承攬案件下拉選項 API 回應 */
interface ContractProjectsDropdownResponse {
  options: DropdownOption[];
}

/** 年度選項 API 回應 */
interface YearsResponse {
  years: (number | string)[];
}

/** 公文列表 API 回應 */
interface DocumentListResponse {
  items?: OfficialDocument[];
  documents?: OfficialDocument[];
  total?: number;
}

interface DocumentFilterProps {
  filters: DocumentFilterType;
  onFiltersChange: (filters: DocumentFilterType) => void;
  onReset: () => void;
}

// 保留用於未來狀態篩選
const _statusOptions = [
  { value: '', label: '全部狀態' },
  { value: '收文完成', label: '收文完成 (40)' },
  { value: '使用者確認', label: '使用者確認 (26)' },
  { value: '收文異常', label: '收文異常 (1)' },
];

const docTypeOptions = [
  { value: '', label: '全部類型' },
  { value: '函', label: '函' },
  { value: '開會通知單', label: '開會通知單' },
  { value: '會勘通知單', label: '會勘通知單' },
];

const deliveryMethodOptions = [
  { value: '', label: '全部形式' },
  { value: '電子交換', label: '電子交換' },
  { value: '紙本郵寄', label: '紙本郵寄' },
];

// 年度選項將從API獲取

const DocumentFilterComponent: React.FC<DocumentFilterProps> = ({
  filters,
  onFiltersChange,
  onReset,
}) => {
  // RWD 響應式
  const { isMobile } = useResponsive();

  // 預設收闔篩選區，公文資訊最大化
  const [expanded, setExpanded] = useState(false);
  const [localFilters, setLocalFilters] = useState<DocumentFilterType>(filters);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  // AutoComplete 狀態
  const [searchOptions, setSearchOptions] = useState<{value: string}[]>([]);
  const [_senderOptions, _setSenderOptions] = useState<{value: string}[]>([]);
  const [_receiverOptions, _setReceiverOptions] = useState<{value: string}[]>([]);
  const [docNumberOptions, setDocNumberOptions] = useState<{value: string}[]>([]);
  const [_contractCaseOptions, _setContractCaseOptions] = useState<{value: string}[]>([]);
  const [contractCaseDropdownOptions, setContractCaseDropdownOptions] = useState<{value: string, label: string}[]>([]);
  const [yearOptions, setYearOptions] = useState<{value: string, label: string}[]>([]);
  const [senderDropdownOptions, setSenderDropdownOptions] = useState<{value: string, label: string}[]>([]);
  const [receiverDropdownOptions, setReceiverDropdownOptions] = useState<{value: string, label: string}[]>([]);

  // 獲取 AutoComplete 建議
  const fetchSearchSuggestions = async (query: string) => {
    if (query.length < 2) {
      setSearchOptions([]);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: query, limit: 50, page: 1 })
      });
      if (response.ok) {
        const data: DocumentListResponse = await response.json();
        const documents = data.items || [];
        const suggestions = documents
          .map((doc) => doc.subject || '')
          .filter((subject, index, arr) =>
            subject && arr.indexOf(subject) === index
          )
          .slice(0, 10)
          .map((subject) => ({ value: subject }));
        setSearchOptions(suggestions);
      }
    } catch (error) {
      logger.error('獲取搜尋建議失敗:', error);
    }
  };

  // 保留用於未來 AutoComplete 功能
  const _fetchSenderSuggestions = async (query: string) => {
    if (query.length < 2) {
      _setSenderOptions([]);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/agencies-dropdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ search: query, limit: 100 })
      });
      if (response.ok) {
        const data: AgenciesDropdownResponse = await response.json();
        const options = data.options || [];
        const senders = options
          .filter((opt) => opt.value?.toString().toLowerCase().includes(query?.toString().toLowerCase()))
          .map((opt) => ({ value: opt.value }));
        _setSenderOptions(senders.slice(0, 10));
      }
    } catch (error) {
      logger.error('獲取發文單位建議失敗:', error);
    }
  };

  // 保留用於未來 AutoComplete 功能
  const _fetchReceiverSuggestions = async (query: string) => {
    if (query.length < 2) {
      _setReceiverOptions([]);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/agencies-dropdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ search: query, limit: 100 })
      });
      if (response.ok) {
        const data: AgenciesDropdownResponse = await response.json();
        const options = data.options || [];
        const receivers = options
          .filter((opt) => opt.value?.toString().toLowerCase().includes(query?.toString().toLowerCase()))
          .map((opt) => ({ value: opt.value }));
        _setReceiverOptions(receivers.slice(0, 10));
      }
    } catch (error) {
      logger.error('獲取受文單位建議失敗:', error);
    }
  };

  const fetchDocNumberSuggestions = async (query: string) => {
    if (query.length < 2) {
      setDocNumberOptions([]);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword: query, limit: 100, page: 1 })
      });
      if (response.ok) {
        const responseData: DocumentListResponse = await response.json();
        const documents = responseData.items || [];

        if (Array.isArray(documents)) {
          const docNumbers = documents
            .map((doc) => doc.doc_number || '')
            .filter((docNumber, index, arr) =>
              docNumber && docNumber?.toString().toLowerCase().includes(query?.toString().toLowerCase()) && arr.indexOf(docNumber) === index
            )
            .map((docNumber) => ({ value: docNumber }));
          setDocNumberOptions(docNumbers.slice(0, 10));
        } else {
          logger.warn('API 回應不包含有效的文件陣列:', responseData);
          setDocNumberOptions([]);
        }
      }
    } catch (error) {
      logger.error('獲取公文字號建議失敗:', error);
      setDocNumberOptions([]);
    }
  };

  // 保留用於未來 AutoComplete 功能
  const _fetchContractCaseSuggestions = async (query: string) => {
    if (query.length < 2) {
      _setContractCaseOptions([]);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/contract-projects-dropdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ search: query, limit: 100 })
      });
      if (response.ok) {
        const data: ContractProjectsDropdownResponse = await response.json();
        const options = data.options || [];
        const contractCases = options
          .filter((opt) => opt.value?.toString().toLowerCase().includes(query?.toString().toLowerCase()))
          .map((opt) => ({ value: opt.value }));
        _setContractCaseOptions(contractCases.slice(0, 10));
      }
    } catch (error) {
      logger.error('獲取承攬案件建議失敗:', error);
    }
  };

  // 獲取年度選項
  const fetchYearOptions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/years`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      if (response.ok) {
        const data: YearsResponse = await response.json();
        const options = (data.years || []).map((year) => ({
          value: String(year),
          label: `${year}年`
        }));
        setYearOptions(options);
      }
    } catch (error) {
      logger.error('獲取年度選項失敗:', error);
    }
  };

  // 獲取承攬案件下拉選項 - 修復：從 contract_projects 表查詢
  const fetchContractCaseDropdownOptions = async () => {
    try {
      // 先嘗試新的增強版 API (使用 POST 方法)
      let response = await fetch(`${API_BASE_URL}/documents-enhanced/contract-projects-dropdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 1000 })
      });

      if (response.ok) {
        const data: ContractProjectsDropdownResponse = await response.json();
        const options = (data.options || []).map((option) => ({
          value: option.value,
          label: option.label
        }));
        setContractCaseDropdownOptions(options);
        logger.debug('✅ 成功從 contract_projects 表載入承攬案件選項:', options.length);
        return;
      }

      // 如果新 API 不可用，降級使用原有方式
      logger.warn('⚠️  增強版 API 不可用，使用原有方式');
      response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.DOCUMENTS.INTEGRATED_SEARCH}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 1000 })
      });
      if (response.ok) {
        const data: DocumentListResponse = await response.json();
        const documents = data.documents || [];
        const contractCases = documents
          .map((doc) => doc.contract_case || '')
          .filter((contractCase, index, arr) =>
            contractCase && arr.indexOf(contractCase) === index
          )
          .sort()
          .map((contractCase) => ({
            value: contractCase,
            label: contractCase
          }));
        setContractCaseDropdownOptions(contractCases);
        logger.debug('📄 從公文表載入承攬案件選項:', contractCases.length);
      }
    } catch (error) {
      logger.error('獲取承攬案件選項失敗:', error);
    }
  };

  // 獲取發文單位下拉選項 - 使用標準化的機關名稱 API (不含統計數據)
  const fetchSenderDropdownOptions = async () => {
    try {
      // 使用新的增強版 API，取得標準化機關名稱 (不含統計數據，使用 POST 方法)
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/agencies-dropdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 500 })
      });
      if (response.ok) {
        const data: AgenciesDropdownResponse = await response.json();
        const agencies = data.options || [];
        const senders = agencies
          .filter((agency) => agency.value !== '相關機關') // 排除佔位符
          .map((agency) => ({
            value: agency.value,
            label: agency.label // 使用標準化名稱，不含統計數據
          }));
        setSenderDropdownOptions(senders);
        logger.debug('✅ 成功載入標準化發文單位選項:', senders.length);
        return;
      }

      // 降級方案：直接從公文表查詢
      logger.warn('⚠️  增強版 API 不可用，使用降級方案');
      const fallbackResponse = await fetch(`${API_BASE_URL}${API_ENDPOINTS.DOCUMENTS.INTEGRATED_SEARCH}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 500 })
      });
      if (fallbackResponse.ok) {
        const data: DocumentListResponse = await fallbackResponse.json();
        const documents = data.documents || [];
        const senders = documents
          .map((doc) => doc.sender || '')
          .filter((sender, index, arr) =>
            sender && sender !== '相關機關' && arr.indexOf(sender) === index
          )
          .sort()
          .map((sender) => ({
            value: sender,
            label: sender
          }));
        setSenderDropdownOptions(senders);
        logger.debug('📄 從公文表載入發文單位選項:', senders.length);
      }
    } catch (error) {
      logger.error('獲取發文單位選項失敗:', error);
    }
  };

  // 獲取受文單位下拉選項 - 使用標準化的機關名稱 API (不含統計數據)
  const fetchReceiverDropdownOptions = async () => {
    try {
      // 使用新的增強版 API，取得標準化機關名稱 (不含統計數據，使用 POST 方法)
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/agencies-dropdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 500 })
      });
      if (response.ok) {
        const data: AgenciesDropdownResponse = await response.json();
        const agencies = data.options || [];
        const receivers = agencies
          .filter((agency) => agency.value !== '相關機關') // 排除佔位符
          .map((agency) => ({
            value: agency.value,
            label: agency.label // 使用標準化名稱，不含統計數據
          }));
        setReceiverDropdownOptions(receivers);
        logger.debug('✅ 成功載入標準化受文單位選項:', receivers.length);
        return;
      }

      // 降級方案：直接從公文表查詢
      logger.warn('⚠️  增強版 API 不可用，使用降級方案');
      const fallbackResponse = await fetch(`${API_BASE_URL}${API_ENDPOINTS.DOCUMENTS.INTEGRATED_SEARCH}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 500 })
      });
      if (fallbackResponse.ok) {
        const data: DocumentListResponse = await fallbackResponse.json();
        const documents = data.documents || [];
        const receivers = documents
          .map((doc) => doc.receiver || '')
          .filter((receiver, index, arr) =>
            receiver && receiver !== '相關機關' && arr.indexOf(receiver) === index
          )
          .sort()
          .map((receiver) => ({
            value: receiver,
            label: receiver
          }));
        setReceiverDropdownOptions(receivers);
        logger.debug('📄 從公文表載入受文單位選項:', receivers.length);
      }
    } catch (error) {
      logger.error('獲取受文單位選項失敗:', error);
    }
  };

  // 組件載入時獲取所有選項
  useEffect(() => {
    fetchYearOptions();
    fetchContractCaseDropdownOptions();
    fetchSenderDropdownOptions();
    fetchReceiverDropdownOptions();
  }, []);

  const handleFilterChange = <K extends keyof DocumentFilterType>(field: K, value: DocumentFilterType[K]) => {
    setLocalFilters(prev => ({ ...prev, [field]: value }));
  };

  // 批次更新多個篩選條件（解決日期範圍連續更新問題）
  const handleMultipleFilterChange = (updates: Partial<DocumentFilterType>) => {
    setLocalFilters(prev => ({ ...prev, ...updates }));
  };

  const handleApplyFilters = () => {
    onFiltersChange(localFilters);
  };

  const handleReset = () => {
    const emptyFilters: DocumentFilterType = {};
    setLocalFilters(emptyFilters);
    setDateRange(null);
    onReset();
  };

  const hasActiveFilters = Object.values(filters).some(value => 
    value !== undefined && value !== ''
  );

  const activeFilterCount = Object.values(filters).filter(value => 
    value !== undefined && value !== ''
  ).length;

  return (
    <Card style={{ marginBottom: isMobile ? 12 : 16 }} size={isMobile ? 'small' : 'default'}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: isMobile ? 12 : 16 }}>
        <SearchOutlined style={{ marginRight: 8 }} />
        <Title level={5} style={{ margin: 0, flexGrow: 1, fontSize: isMobile ? 14 : undefined }}>
          {isMobile ? '篩選' : '搜尋與篩選'}
        </Title>

        {hasActiveFilters && (
          <Tag color="blue" style={{ marginRight: 8, fontSize: isMobile ? 12 : undefined }}>
            <FilterOutlined style={{ marginRight: 4 }} />
            {activeFilterCount}
          </Tag>
        )}

        <Button
          type="text"
          size="small"
          onClick={() => setExpanded(!expanded)}
          icon={expanded ? <UpOutlined /> : <DownOutlined />}
        >
          {isMobile ? '' : (expanded ? '收起' : '展開')}
        </Button>
      </div>

      {/* 主要搜尋條件 */}
      <Row gutter={[isMobile ? 8 : 16, isMobile ? 8 : 16]}>
        {/* 關鍵字搜尋 (文號/主旨/說明/備註) - 加寬欄位 */}
        <Col span={24} md={8}>
          {!isMobile && (
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>關鍵字搜尋</span>
              <Tooltip title="搜尋範圍包含：公文字號、主旨、說明、備註。支援模糊搜尋，輸入2個字元以上開始提供建議。按 Enter 快速套用篩選。">
                <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
              </Tooltip>
            </div>
          )}
          <Input.Search
            placeholder={isMobile ? '搜尋...' : '文號/主旨/說明/備註...'}
            value={localFilters.search || ''}
            onChange={(e) => handleFilterChange('search', e.target.value)}
            onSearch={handleApplyFilters}
            allowClear
            enterButton={false}
            style={{ width: '100%' }}
            size={isMobile ? 'small' : 'middle'}
          />
        </Col>

        {/* 公文類型篩選 */}
        <Col span={12} md={4}>
          {!isMobile && (
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>公文類型</span>
              <Tooltip title="選擇特定的公文類型進行篩選。包含：函、開會通知單、會勘通知單。留空顯示所有類型。">
                <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
              </Tooltip>
            </div>
          )}
          <Select
            placeholder={isMobile ? '類型' : '請選擇公文類型'}
            value={localFilters.doc_type || ''}
            onChange={(value) => handleFilterChange('doc_type', value)}
            style={{ width: '100%' }}
            allowClear
            size={isMobile ? 'small' : 'middle'}
          >
            {docTypeOptions.map((option) => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        </Col>

        {/* 發文形式篩選 */}
        <Col span={12} md={4}>
          {!isMobile && (
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>發文形式</span>
              <Tooltip title="選擇公文發送方式：電子交換或紙本郵寄">
                <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
              </Tooltip>
            </div>
          )}
          <Select
            placeholder={isMobile ? '形式' : '請選擇發文形式'}
            value={localFilters.delivery_method || ''}
            onChange={(value) => handleFilterChange('delivery_method', value)}
            style={{ width: '100%' }}
            allowClear
            size={isMobile ? 'small' : 'middle'}
          >
            {deliveryMethodOptions.map((option) => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        </Col>

        {/* 承攬案件 - 使用 Select 搭配 AutoComplete 功能 */}
        <Col span={24} md={8}>
          {!isMobile && (
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
              <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>承攬案件</span>
              <Tooltip title="選擇相關的承攬案件進行篩選。可輸入關鍵字快速搜尋現有案件。選項基於系統中已登記的承攬案件。">
                <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
              </Tooltip>
            </div>
          )}
          <Select
            placeholder={isMobile ? '案件' : '請選擇或搜尋承攬案件...'}
            value={localFilters.contract_case || ''}
            onChange={(value) => handleFilterChange('contract_case', value)}
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
            {contractCaseDropdownOptions.map((option) => (
              <Option key={option.value} value={option.value} label={option.label}>
                {option.label}
              </Option>
            ))}
          </Select>
        </Col>
      </Row>

      {expanded && (
        <>
          <Divider style={{ margin: '16px 0' }}>進階查詢</Divider>
          
          <Row gutter={[16, 16]}>
            {/* 第一行：公文年度、公文字號、公文日期 */}
            <Col span={24} md={8}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>篩選年度</span>
                <Tooltip title="選擇公文的年度。選項基於系統現有公文的年份。可用於統計特定年度的公文量。">
                  <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
                </Tooltip>
              </div>
              <Select
                placeholder="請選擇年度 (預設：所有年度)"
                value={localFilters.year}
                onChange={(value) => handleFilterChange('year', value ? Number(value) : undefined)}
                style={{ width: '100%' }}
                allowClear
                suffixIcon={
                  <div>
                    <Tooltip title="動態載入現有年份">
                      <InfoCircleOutlined style={{ color: '#ccc', fontSize: '12px' }} />
                    </Tooltip>
                  </div>
                }
              >
                {yearOptions.map((option) => (
                  <Option key={option.value} value={option.value}>
                    {option.value}年 ({yearOptions.length > 0 ? '有資料' : '無資料'})
                  </Option>
                ))}
              </Select>
            </Col>

            <Col span={24} md={8}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>公文字號</span>
                <Tooltip title="輸入完整或部分公文字號。例如：乾坤字第1130001號、府字第、部字第等。輸入2個字以上即可取得智能建議。">
                  <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
                </Tooltip>
              </div>
              <Input
                placeholder="請輸入公文字號 (例：乾坤字第)"
                value={localFilters.doc_number || ''}
                onChange={(e) => handleFilterChange('doc_number', e.target.value)}
                onPressEnter={handleApplyFilters}
                allowClear
                style={{ width: '100%' }}
                suffix={
                  <Tooltip title="按 Enter 套用篩選">
                    <SearchOutlined style={{ color: '#ccc' }} />
                  </Tooltip>
                }
              />
            </Col>

            <Col span={24} md={8}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>公文日期</span>
                <Tooltip title="選擇公文日期範圍。可只選擇開始日期或結束日期。日期格式：YYYY-MM-DD。適用於統計特定時間段的公文。">
                  <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
                </Tooltip>
              </div>
              <RangePicker
                placeholder={['選擇開始日期 (可選)', '選擇結束日期 (可選)']}
                value={dateRange}
                onChange={(dates, dateStrings) => {
                  setDateRange(dates);
                  // 批次更新日期範圍，避免連續更新造成狀態遺失
                  handleMultipleFilterChange({
                    doc_date_from: dateStrings[0] || undefined,
                    doc_date_to: dateStrings[1] || undefined
                  });
                }}
                style={{ width: '100%' }}
                format="YYYY-MM-DD"
                suffixIcon={
                  <Tooltip title="日期格式：YYYY-MM-DD">
                    <InfoCircleOutlined style={{ color: '#ccc', fontSize: '12px' }} />
                  </Tooltip>
                }
              />
            </Col>

            {/* 第二行：受文單位、發文單位 */}
            <Col span={24} md={12}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>受文單位</span>
                <Tooltip title="選擇接收公文的機關單位。可輸入關鍵字快速搜尋現有單位。選項基於系統中已登記的公文資料。">
                  <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
                </Tooltip>
              </div>
              <Select
                placeholder="請選擇或搜尋受文單位..."
                value={localFilters.receiver || ''}
                onChange={(value) => handleFilterChange('receiver', value)}
                style={{ width: '100%' }}
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label as string)?.toLowerCase().indexOf((input as string)?.toLowerCase()) >= 0
                }
                suffixIcon={
                  <div>
                    <SearchOutlined style={{ marginRight: 4 }} />
                    <Tooltip title="可搜尋單位名稱">
                      <InfoCircleOutlined style={{ color: '#ccc', fontSize: '12px' }} />
                    </Tooltip>
                  </div>
                }
              >
                {receiverDropdownOptions.map((option) => (
                  <Option key={option.value} value={option.value} label={option.label}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </Col>

            <Col span={24} md={12}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>發文單位</span>
                <Tooltip title="選擇發送公文的機關單位。可輸入關鍵字快速搜尋現有單位。適用於統計特定機關的公文往來。">
                  <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
                </Tooltip>
              </div>
              <Select
                placeholder="請選擇或搜尋發文單位..."
                value={localFilters.sender || ''}
                onChange={(value) => handleFilterChange('sender', value)}
                style={{ width: '100%' }}
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label as string)?.toLowerCase().indexOf((input as string)?.toLowerCase()) >= 0
                }
                suffixIcon={
                  <div>
                    <SearchOutlined style={{ marginRight: 4 }} />
                    <Tooltip title="可搜尋單位名稱">
                      <InfoCircleOutlined style={{ color: '#ccc', fontSize: '12px' }} />
                    </Tooltip>
                  </div>
                }
              >
                {senderDropdownOptions.map((option) => (
                  <Option key={option.value} value={option.value} label={option.label}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </Col>
          </Row>
        </>
      )}

      {/* 操作按鈕 */}
      <div style={{
        display: 'flex',
        justifyContent: isMobile ? 'flex-end' : 'space-between',
        alignItems: 'center',
        marginTop: isMobile ? 12 : 16,
        flexWrap: 'wrap',
        gap: 8,
      }}>
        {/* 篩選結果提示 - 手機版隱藏 */}
        {!isMobile && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {hasActiveFilters && (
              <>
                <InfoCircleOutlined style={{ color: '#1890ff' }} />
                <span style={{ color: '#666', fontSize: '13px' }}>
                  已套用 {activeFilterCount} 個篩選條件
                </span>
              </>
            )}
          </div>
        )}

        <div style={{ display: 'flex', gap: 8 }}>
          <Tooltip title={isMobile ? '' : '清除所有篩選條件，回復預設狀態'}>
            <Button
              onClick={handleReset}
              icon={<ClearOutlined />}
              disabled={!hasActiveFilters}
              size={isMobile ? 'small' : 'middle'}
              style={{ borderColor: hasActiveFilters ? '#ff4d4f' : '', color: hasActiveFilters ? '#ff4d4f' : '' }}
            >
              {isMobile ? '' : '清除篩選'}
            </Button>
          </Tooltip>

          <Tooltip title={isMobile ? '' : '套用當前篩選條件。快速鍵：在任一輸入框中按 Enter'}>
            <Button
              type="primary"
              onClick={handleApplyFilters}
              icon={<FilterOutlined />}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '篩選' : '套用篩選'}
            </Button>
          </Tooltip>
        </div>
      </div>

    </Card>
  );
};

export { DocumentFilterComponent as DocumentFilter };