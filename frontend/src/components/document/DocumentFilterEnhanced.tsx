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
  Space,
  Divider,
  Tooltip,
  Form,
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
import { DocumentFilter as DocumentFilterType } from '../../types';
import { useResponsive } from '../../hooks/useResponsive';
import { API_BASE_URL } from '../../api/client';
const { Option } = Select;
const { Title } = Typography;

interface DocumentFilterProps {
  filters: DocumentFilterType;
  onFiltersChange: (filters: DocumentFilterType) => void;
  onReset: () => void;
}

// 統一的選項介面
interface DropdownOption {
  value: string;
  label: string;
  id?: number;
  year?: number;
  category?: string;
  agency_type?: string;
}

const statusOptions = [
  { value: '', label: '全部狀態' },
  { value: '收文完成', label: '收文完成' },
  { value: '使用者確認', label: '使用者確認' },
  { value: '收文異常', label: '收文異常' },
  { value: '待處理', label: '待處理' },
  { value: '已辦畢', label: '已辦畢' },
];

const docTypeOptions = [
  { value: '', label: '全部類型' },
  { value: '函', label: '函' },
  { value: '開會通知單', label: '開會通知單' },
  { value: '會勘通知單', label: '會勘通知單' },
  { value: '公告', label: '公告' },
  { value: '通知', label: '通知' },
];

const DocumentFilterEnhanced: React.FC<DocumentFilterProps> = ({
  filters,
  onFiltersChange,
  onReset,
}) => {
  const { isMobile, responsiveValue } = useResponsive();
  const [expanded, setExpanded] = useState(false);
  const [localFilters, setLocalFilters] = useState<DocumentFilterType>(filters);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);

  // 統一的 AutoComplete 選項狀態
  const [searchOptions, setSearchOptions] = useState<{value: string}[]>([]);
  const [contractCaseOptions, setContractCaseOptions] = useState<DropdownOption[]>([]);
  const [senderOptions, setSenderOptions] = useState<DropdownOption[]>([]);
  const [receiverOptions, setReceiverOptions] = useState<DropdownOption[]>([]);
  const [docNumberOptions, setDocNumberOptions] = useState<{value: string}[]>([]);
  const [yearOptions, setYearOptions] = useState<DropdownOption[]>([]);

  // 載入狀態
  const [loading, setLoading] = useState({
    contractCase: false,
    sender: false,
    receiver: false,
    years: false,
    docNumbers: false,
  });

  // 統一的 API 呼叫函數
  const fetchWithLoading = async (
    url: string,
    loadingKey: keyof typeof loading,
    onSuccess: (data: any) => void,
    onError?: (error: any) => void
  ) => {
    setLoading(prev => ({ ...prev, [loadingKey]: true }));
    try {
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        onSuccess(data);
      } else {
        throw new Error(`HTTP ${response.status}`);
      }
    } catch (error) {
      console.error(`API 呼叫失敗 (${url}):`, error);
      if (onError) onError(error);
    } finally {
      setLoading(prev => ({ ...prev, [loadingKey]: false }));
    }
  };

  // 承攬案件 AutoComplete - 改為從 contract_projects 表查詢
  const fetchContractCaseOptions = async (search?: string) => {
    const url = search
      ? `${API_BASE_URL}/documents-enhanced/contract-projects-dropdown?search=${encodeURIComponent(search)}&limit=50`
      : `${API_BASE_URL}/documents-enhanced/contract-projects-dropdown?limit=100`;

    await fetchWithLoading(url, 'contractCase', (data) => {
      setContractCaseOptions(data.options || []);
    });
  };

  // 發文單位 AutoComplete - 改為從 government_agencies 表查詢
  const fetchSenderOptions = async (search?: string) => {
    const url = search
      ? `${API_BASE_URL}/documents-enhanced/agencies-dropdown?search=${encodeURIComponent(search)}&limit=50`
      : `${API_BASE_URL}/documents-enhanced/agencies-dropdown?limit=100`;

    await fetchWithLoading(url, 'sender', (data) => {
      setSenderOptions(data.options || []);
    });
  };

  // 受文單位 AutoComplete - 改為從 government_agencies 表查詢
  const fetchReceiverOptions = async (search?: string) => {
    const url = search
      ? `${API_BASE_URL}/documents-enhanced/agencies-dropdown?search=${encodeURIComponent(search)}&limit=50`
      : `${API_BASE_URL}/documents-enhanced/agencies-dropdown?limit=100`;

    await fetchWithLoading(url, 'receiver', (data) => {
      setReceiverOptions(data.options || []);
    });
  };

  // 公文字號 AutoComplete
  const fetchDocNumberOptions = async (search: string) => {
    if (search.length < 2) {
      setDocNumberOptions([]);
      return;
    }

    await fetchWithLoading(
      `${API_BASE_URL}/documents/search-suggestions?q=${encodeURIComponent(search)}&limit=20`,
      'docNumbers',
      (data) => {
        const documents = data.documents || [];
        const docNumbers = documents
          .map((doc: any) => ({ value: doc.doc_number || '' }))
          .filter((item: any, index: number, arr: any[]) =>
            item.value && arr.findIndex(a => a.value === item.value) === index
          );
        setDocNumberOptions(docNumbers);
      }
    );
  };

  // 關鍵字 AutoComplete
  const fetchSearchOptions = async (search: string) => {
    if (search.length < 2) {
      setSearchOptions([]);
      return;
    }

    await fetchWithLoading(
      `${API_BASE_URL}/documents/search-suggestions?q=${encodeURIComponent(search)}&limit=20`,
      'docNumbers',
      (data) => {
        const documents = data.documents || [];
        const subjects = documents
          .map((doc: any) => ({ value: doc.subject || '' }))
          .filter((item: any, index: number, arr: any[]) =>
            item.value && arr.findIndex(a => a.value === item.value) === index
          );
        setSearchOptions(subjects);
      }
    );
  };

  // 年度選項
  const fetchYearOptions = async () => {
    // 使用共用的 API 基礎 URL
    await fetchWithLoading(`${API_BASE_URL}/documents/documents-years`, 'years', (data) => {
      const options = (data.years || []).map((year: string) => ({
        value: year,
        label: `${year}年`
      }));
      setYearOptions(options);
    });
  };

  // 元件載入時獲取選項
  useEffect(() => {
    fetchYearOptions();
    fetchContractCaseOptions();
    fetchSenderOptions();
    fetchReceiverOptions();
  }, []);

  const handleFilterChange = (field: keyof DocumentFilterType, value: any) => {
    const newFilters = { ...localFilters, [field]: value };
    setLocalFilters(newFilters);
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
    <Card size={isMobile ? 'small' : 'default'} style={{ marginBottom: isMobile ? 12 : 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: isMobile ? 12 : 16, flexWrap: 'wrap', gap: 8 }}>
        <SearchOutlined style={{ marginRight: 8 }} />
        <Title level={isMobile ? 5 : 5} style={{ margin: 0, flexGrow: 1 }}>
          {isMobile ? '搜尋' : '智能搜尋與篩選'}
        </Title>

        {hasActiveFilters && (
          <Tag color="blue" style={{ marginRight: isMobile ? 0 : 8 }}>
            <FilterOutlined style={{ marginRight: 4 }} />
            {activeFilterCount} {isMobile ? '' : '個篩選條件'}
          </Tag>
        )}

        <Button
          type="text"
          size="small"
          onClick={() => setExpanded(!expanded)}
          icon={expanded ? <UpOutlined /> : <DownOutlined />}
        >
          {expanded ? '收起' : '展開'}
        </Button>
      </div>

      {/* 主要搜尋條件 */}
      <Row gutter={[16, 16]}>
        {/* 關鍵字搜尋 - AutoComplete */}
        <Col span={24} md={8}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>關鍵字搜尋</span>
            <Tooltip title="智能搜尋公文主旨、文號等內容，支援模糊搜尋。輸入2個字元以上開始提供建議。">
              <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
            </Tooltip>
          </div>
          <AutoComplete
            options={searchOptions}
            onSearch={fetchSearchOptions}
            onSelect={(value) => handleFilterChange('search', value)}
            onChange={(value) => handleFilterChange('search', value)}
            value={localFilters.search || ''}
            placeholder="請輸入關鍵字..."
            style={{ width: '100%' }}
          >
            <Input
              prefix={<SearchOutlined />}
              onPressEnter={handleApplyFilters}
              suffix={
                <Tooltip title="按 Enter 快速搜尋">
                  <span style={{ color: '#ccc', fontSize: '12px' }}>Enter</span>
                </Tooltip>
              }
            />
          </AutoComplete>
        </Col>

        {/* 公文類型 */}
        <Col span={24} md={8}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>公文類型</span>
            <Tooltip title="選擇特定的公文類型進行篩選">
              <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
            </Tooltip>
          </div>
          <Select
            placeholder="請選擇公文類型"
            value={localFilters.doc_type || ''}
            onChange={(value) => handleFilterChange('doc_type', value)}
            style={{ width: '100%' }}
            allowClear
          >
            {docTypeOptions.map((option) => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        </Col>

        {/* 承攬案件 - AutoComplete with Select */}
        <Col span={24} md={8}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>承攬案件</span>
            <Tooltip title="選擇相關的承攬案件。資料來源：專案管理系統，支援智能搜尋。">
              <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
            </Tooltip>
          </div>
          <Select
            placeholder="請選擇或搜尋承攬案件..."
            value={localFilters.contract_case || ''}
            onChange={(value) => handleFilterChange('contract_case', value)}
            style={{ width: '100%' }}
            allowClear
            showSearch
            loading={loading.contractCase}
            onSearch={fetchContractCaseOptions}
            filterOption={false}
            suffixIcon={
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <SearchOutlined style={{ marginRight: 4 }} />
                <Tooltip title="來源：專案系統">
                  <InfoCircleOutlined style={{ color: '#52c41a', fontSize: '12px' }} />
                </Tooltip>
              </div>
            }
          >
            {contractCaseOptions.map((option) => (
              <Option key={option.value} value={option.value}>
                <div>
                  <div>{option.label}</div>
                  {option.category && (
                    <div style={{ fontSize: '12px', color: '#999' }}>
                      分類：{option.category}
                    </div>
                  )}
                </div>
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
                <Tooltip title="選擇公文年度，動態載入系統現有年份">
                  <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
                </Tooltip>
              </div>
              <Select
                placeholder="請選擇年度"
                value={localFilters.year || ''}
                onChange={(value) => handleFilterChange('year', value)}
                style={{ width: '100%' }}
                allowClear
                loading={loading.years}
              >
                {yearOptions.map((option) => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </Col>

            <Col span={24} md={8}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>公文字號</span>
                <Tooltip title="輸入完整或部分公文字號，支援智能建議">
                  <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
                </Tooltip>
              </div>
              <AutoComplete
                options={docNumberOptions}
                onSearch={fetchDocNumberOptions}
                onSelect={(value) => handleFilterChange('doc_number', value)}
                onChange={(value) => handleFilterChange('doc_number', value)}
                value={localFilters.doc_number || ''}
                placeholder="請輸入公文字號"
                style={{ width: '100%' }}
              >
                <Input
                  suffix={
                    <Tooltip title="支援智能建議">
                      <SearchOutlined style={{ color: '#ccc' }} />
                    </Tooltip>
                  }
                />
              </AutoComplete>
            </Col>

            <Col span={24} md={8}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>公文日期</span>
                <Tooltip title="選擇公文日期範圍">
                  <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
                </Tooltip>
              </div>
              <RangePicker
                placeholder={['開始日期', '結束日期']}
                value={dateRange}
                onChange={(dates, dateStrings) => {
                  setDateRange(dates);
                  handleFilterChange('doc_date_from', dateStrings[0]);
                  handleFilterChange('doc_date_to', dateStrings[1]);
                }}
                style={{ width: '100%' }}
                format="YYYY-MM-DD"
              />
            </Col>

            {/* 第二行：發文單位、受文單位 */}
            <Col span={24} md={12}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>發文單位</span>
                <Tooltip title="選擇發文機關。資料來源：政府機關資料庫，支援智能搜尋。">
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
                loading={loading.sender}
                onSearch={fetchSenderOptions}
                filterOption={false}
                suffixIcon={
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <SearchOutlined style={{ marginRight: 4 }} />
                    <Tooltip title="來源：機關資料庫">
                      <InfoCircleOutlined style={{ color: '#1890ff', fontSize: '12px' }} />
                    </Tooltip>
                  </div>
                }
              >
                {senderOptions.map((option) => (
                  <Option key={option.value} value={option.value}>
                    <div>
                      <div>{option.value}</div>
                      {option.agency_type && (
                        <div style={{ fontSize: '12px', color: '#999' }}>
                          類型：{option.agency_type}
                        </div>
                      )}
                    </div>
                  </Option>
                ))}
              </Select>
            </Col>

            <Col span={24} md={12}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>受文單位</span>
                <Tooltip title="選擇受文機關。資料來源：政府機關資料庫，支援智能搜尋。">
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
                loading={loading.receiver}
                onSearch={fetchReceiverOptions}
                filterOption={false}
                suffixIcon={
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <SearchOutlined style={{ marginRight: 4 }} />
                    <Tooltip title="來源：機關資料庫">
                      <InfoCircleOutlined style={{ color: '#1890ff', fontSize: '12px' }} />
                    </Tooltip>
                  </div>
                }
              >
                {receiverOptions.map((option) => (
                  <Option key={option.value} value={option.value}>
                    <div>
                      <div>{option.value}</div>
                      {option.agency_type && (
                        <div style={{ fontSize: '12px', color: '#999' }}>
                          類型：{option.agency_type}
                        </div>
                      )}
                    </div>
                  </Option>
                ))}
              </Select>
            </Col>
          </Row>
        </>
      )}

      {/* 操作按鈕 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: isMobile ? 12 : 16, flexWrap: 'wrap', gap: 8 }}>
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

        <div style={{ display: 'flex', gap: 8, width: isMobile ? '100%' : 'auto', justifyContent: isMobile ? 'flex-end' : 'flex-start' }}>
          <Tooltip title="清除所有篩選條件">
            <Button
              onClick={handleReset}
              icon={<ClearOutlined />}
              disabled={!hasActiveFilters}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '清除篩選'}
            </Button>
          </Tooltip>

          <Tooltip title="套用當前篩選條件 (快速鍵：Enter)">
            <Button
              type="primary"
              onClick={handleApplyFilters}
              icon={<FilterOutlined />}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '搜尋' : '套用篩選'}
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* 資料來源提示 - 僅桌面版顯示 */}
      {!hasActiveFilters && !isMobile && (
        <div style={{
          textAlign: 'center',
          padding: '12px 16px',
          backgroundColor: '#f0f9ff',
          border: '1px solid #bae7ff',
          borderRadius: '6px',
          marginTop: 12
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, marginBottom: 6 }}>
            <InfoCircleOutlined style={{ color: '#1890ff', fontSize: '14px' }} />
            <span style={{ color: '#1890ff', fontSize: '14px', fontWeight: 500 }}>
              智能搜尋功能
            </span>
          </div>
          <div style={{ color: '#666', fontSize: '12px' }}>
            • 承攬案件：來源專案管理系統，資料更精確<br/>
            • 政府機關：整合機關資料庫，支援類型分類<br/>
            • 所有欄位均支援 AutoComplete 智能建議
          </div>
        </div>
      )}
    </Card>
  );
};

export { DocumentFilterEnhanced };