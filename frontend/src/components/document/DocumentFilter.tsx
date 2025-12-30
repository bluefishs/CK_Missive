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
const { Option } = Select;
const { Title } = Typography;

interface DocumentFilterProps {
  filters: DocumentFilterType;
  onFiltersChange: (filters: DocumentFilterType) => void;
  onReset: () => void;
}

const statusOptions = [
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

// 年度選項將從API獲取

const DocumentFilterComponent: React.FC<DocumentFilterProps> = ({
  filters,
  onFiltersChange,
  onReset,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [localFilters, setLocalFilters] = useState<DocumentFilterType>(filters);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null);
  
  // AutoComplete 狀態
  const [searchOptions, setSearchOptions] = useState<{value: string}[]>([]);
  const [senderOptions, setSenderOptions] = useState<{value: string}[]>([]);
  const [receiverOptions, setReceiverOptions] = useState<{value: string}[]>([]);
  const [docNumberOptions, setDocNumberOptions] = useState<{value: string}[]>([]);
  const [contractCaseOptions, setContractCaseOptions] = useState<{value: string}[]>([]);
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
      const response = await fetch(`/api/documents-enhanced/integrated-search?limit=50&search=${encodeURIComponent(query)}`);
      if (response.ok) {
        const data = await response.json();
        const documents = data.documents || [];
        const suggestions = documents
          .map((doc: any) => doc.subject || '')
          .filter((subject: string, index: number, arr: string[]) =>
            subject && arr.indexOf(subject) === index
          )
          .slice(0, 10)
          .map((subject: string) => ({ value: subject }));
        setSearchOptions(suggestions);
      }
    } catch (error) {
      console.error('獲取搜尋建議失敗:', error);
    }
  };

  const fetchSenderSuggestions = async (query: string) => {
    if (query.length < 2) {
      setSenderOptions([]);
      return;
    }
    
    try {
      const response = await fetch(`/api/documents-enhanced/integrated-search?limit=100`);
      if (response.ok) {
        const documents = await response.json();
        const senders = documents
          .map((doc: any) => doc.sender || '')
          .filter((sender: string, index: number, arr: string[]) => 
            sender && sender?.toString().toLowerCase().includes(query?.toString().toLowerCase()) && arr.indexOf(sender) === index
          )
          .map((sender: string) => ({ value: sender }));
        setSenderOptions(senders.slice(0, 10));
      }
    } catch (error) {
      console.error('獲取發文單位建議失敗:', error);
    }
  };

  const fetchReceiverSuggestions = async (query: string) => {
    if (query.length < 2) {
      setReceiverOptions([]);
      return;
    }
    
    try {
      const response = await fetch(`/api/documents-enhanced/integrated-search?limit=100`);
      if (response.ok) {
        const documents = await response.json();
        const receivers = documents
          .map((doc: any) => doc.receiver || '')
          .filter((receiver: string, index: number, arr: string[]) => 
            receiver && receiver?.toString().toLowerCase().includes(query?.toString().toLowerCase()) && arr.indexOf(receiver) === index
          )
          .map((receiver: string) => ({ value: receiver }));
        setReceiverOptions(receivers.slice(0, 10));
      }
    } catch (error) {
      console.error('獲取受文單位建議失敗:', error);
    }
  };

  const fetchDocNumberSuggestions = async (query: string) => {
    if (query.length < 2) {
      setDocNumberOptions([]);
      return;
    }
    
    try {
      const response = await fetch(`/api/documents-enhanced/integrated-search?limit=100`);
      if (response.ok) {
        const responseData = await response.json();
        // 修復：從 API 回應中正確取得文件陣列
        const documents = responseData.documents || responseData || [];

        // 確保 documents 是陣列
        if (Array.isArray(documents)) {
          const docNumbers = documents
            .map((doc: any) => doc.doc_number || '')
            .filter((docNumber: string, index: number, arr: string[]) =>
              docNumber && docNumber?.toString().toLowerCase().includes(query?.toString().toLowerCase()) && arr.indexOf(docNumber) === index
            )
            .map((docNumber: string) => ({ value: docNumber }));
          setDocNumberOptions(docNumbers.slice(0, 10));
        } else {
          console.warn('API 回應不包含有效的文件陣列:', responseData);
          setDocNumberOptions([]);
        }
      }
    } catch (error) {
      console.error('獲取公文字號建議失敗:', error);
      setDocNumberOptions([]);
    }
  };

  const fetchContractCaseSuggestions = async (query: string) => {
    if (query.length < 2) {
      setContractCaseOptions([]);
      return;
    }
    
    try {
      const response = await fetch(`/api/documents-enhanced/integrated-search?limit=100`);
      if (response.ok) {
        const documents = await response.json();
        const contractCases = documents
          .map((doc: any) => doc.contract_case || '')
          .filter((contractCase: string, index: number, arr: string[]) => 
            contractCase && contractCase?.toString().toLowerCase().includes(query?.toString().toLowerCase()) && arr.indexOf(contractCase) === index
          )
          .map((contractCase: string) => ({ value: contractCase }));
        setContractCaseOptions(contractCases.slice(0, 10));
      }
    } catch (error) {
      console.error('獲取承攬案件建議失敗:', error);
    }
  };

  // 獲取年度選項
  const fetchYearOptions = async () => {
    try {
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
      const response = await fetch(`${API_BASE_URL}/api/documents-enhanced/document-years`);
      if (response.ok) {
        const data = await response.json();
        const options = data.years.map((year: string) => ({
          value: year,
          label: `${year}年`
        }));
        setYearOptions(options);
      }
    } catch (error) {
      console.error('獲取年度選項失敗:', error);
    }
  };

  // 獲取承攬案件下拉選項 - 修復：從 contract_projects 表查詢
  const fetchContractCaseDropdownOptions = async () => {
    try {
      // 先嘗試新的增強版 API
      let response = await fetch('/api/documents-enhanced/contract-projects-dropdown?limit=1000');

      if (response.ok) {
        const data = await response.json();
        const options = (data.options || []).map((option: any) => ({
          value: option.value,
          label: option.label
        }));
        setContractCaseDropdownOptions(options);
        console.log('✅ 成功從 contract_projects 表載入承攬案件選項:', options.length);
        return;
      }

      // 如果新 API 不可用，降級使用原有方式
      console.warn('⚠️  增強版 API 不可用，使用原有方式');
      response = await fetch('/api/documents-enhanced/integrated-search?limit=1000');
      if (response.ok) {
        const data = await response.json();
        const documents = data.documents || [];
        const contractCases = documents
          .map((doc: any) => doc.contract_case || '')
          .filter((contractCase: string, index: number, arr: string[]) =>
            contractCase && arr.indexOf(contractCase) === index
          )
          .sort()
          .map((contractCase: string) => ({
            value: contractCase,
            label: contractCase
          }));
        setContractCaseDropdownOptions(contractCases);
        console.log('📄 從公文表載入承攬案件選項:', contractCases.length);
      }
    } catch (error) {
      console.error('獲取承攬案件選項失敗:', error);
    }
  };

  // 獲取發文單位下拉選項 - 使用標準化的機關名稱 API (不含統計數據)
  const fetchSenderDropdownOptions = async () => {
    try {
      // 使用新的增強版 API，取得標準化機關名稱 (不含統計數據)
      const response = await fetch('/api/documents-enhanced/agencies-dropdown?limit=500');
      if (response.ok) {
        const data = await response.json();
        const agencies = data.options || [];
        const senders = agencies
          .filter((agency: any) => agency.value !== '相關機關') // 排除佔位符
          .map((agency: any) => ({
            value: agency.value,
            label: agency.label // 使用標準化名稱，不含統計數據
          }));
        setSenderDropdownOptions(senders);
        console.log('✅ 成功載入標準化發文單位選項:', senders.length);
        return;
      }

      // 降級方案：直接從公文表查詢
      console.warn('⚠️  增強版 API 不可用，使用降級方案');
      const fallbackResponse = await fetch('/api/documents-enhanced/integrated-search?limit=500');
      if (fallbackResponse.ok) {
        const data = await fallbackResponse.json();
        const documents = data.documents || [];
        const senders = documents
          .map((doc: any) => doc.sender || '')
          .filter((sender: string, index: number, arr: string[]) =>
            sender && sender !== '相關機關' && arr.indexOf(sender) === index
          )
          .sort()
          .map((sender: string) => ({
            value: sender,
            label: sender
          }));
        setSenderDropdownOptions(senders);
        console.log('📄 從公文表載入發文單位選項:', senders.length);
      }
    } catch (error) {
      console.error('獲取發文單位選項失敗:', error);
    }
  };

  // 獲取受文單位下拉選項 - 使用標準化的機關名稱 API (不含統計數據)
  const fetchReceiverDropdownOptions = async () => {
    try {
      // 使用新的增強版 API，取得標準化機關名稱 (不含統計數據)
      const response = await fetch('/api/documents-enhanced/agencies-dropdown?limit=500');
      if (response.ok) {
        const data = await response.json();
        const agencies = data.options || [];
        const receivers = agencies
          .filter((agency: any) => agency.value !== '相關機關') // 排除佔位符
          .map((agency: any) => ({
            value: agency.value,
            label: agency.label // 使用標準化名稱，不含統計數據
          }));
        setReceiverDropdownOptions(receivers);
        console.log('✅ 成功載入標準化受文單位選項:', receivers.length);
        return;
      }

      // 降級方案：直接從公文表查詢
      console.warn('⚠️  增強版 API 不可用，使用降級方案');
      const fallbackResponse = await fetch('/api/documents-enhanced/integrated-search?limit=500');
      if (fallbackResponse.ok) {
        const data = await fallbackResponse.json();
        const documents = data.documents || [];
        const receivers = documents
          .map((doc: any) => doc.receiver || '')
          .filter((receiver: string, index: number, arr: string[]) =>
            receiver && receiver !== '相關機關' && arr.indexOf(receiver) === index
          )
          .sort()
          .map((receiver: string) => ({
            value: receiver,
            label: receiver
          }));
        setReceiverDropdownOptions(receivers);
        console.log('📄 從公文表載入受文單位選項:', receivers.length);
      }
    } catch (error) {
      console.error('獲取受文單位選項失敗:', error);
    }
  };

  // 組件載入時獲取所有選項
  useEffect(() => {
    fetchYearOptions();
    fetchContractCaseDropdownOptions();
    fetchSenderDropdownOptions();
    fetchReceiverDropdownOptions();
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
    <Card style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
        <SearchOutlined style={{ marginRight: 8 }} />
        <Title level={5} style={{ margin: 0, flexGrow: 1 }}>
          搜尋與篩選
        </Title>
        
        {hasActiveFilters && (
          <Tag color="blue" style={{ marginRight: 8 }}>
            <FilterOutlined style={{ marginRight: 4 }} />
            {activeFilterCount} 個篩選條件
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
        {/* 關鍵字搜尋 (公文主旨檢索) - 使用 AutoComplete */}
        <Col span={24} md={8}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>關鍵字搜尋</span>
            <Tooltip title="輸入關鍵字搜尋公文主旨，系統會自動提供相關建議。支援模糊搜尋，輸入2個字元以上開始提供建議。按 Enter 快速套用篩選。">
              <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
            </Tooltip>
          </div>
          <AutoComplete
            options={searchOptions}
            onSearch={fetchSearchSuggestions}
            onSelect={(value) => handleFilterChange('search', value)}
            onChange={(value) => handleFilterChange('search', value)}
            value={localFilters.search || ''}
            placeholder="請輸入公文主旨關鍵字..."
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

        {/* 公文類型篩選 */}
        <Col span={24} md={8}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>公文類型</span>
            <Tooltip title="選擇特定的公文類型進行篩選。包含：函、開會通知單、會勘通知單。留空顯示所有類型。">
              <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
            </Tooltip>
          </div>
          <Select
            placeholder="請選擇公文類型 (預設：全部類型)"
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

        {/* 承攬案件 - 使用 Select 搭配 AutoComplete 功能 */}
        <Col span={24} md={8}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ marginRight: 4, fontSize: '14px', color: '#666' }}>承攬案件</span>
            <Tooltip title="選擇相關的承攬案件進行篩選。可輸入關鍵字快速搜尋現有案件。選項基於系統中已登記的承攬案件。">
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
            filterOption={(input, option) =>
              (option?.label as string)?.toLowerCase().indexOf((input as string)?.toLowerCase()) >= 0
            }
            suffixIcon={
              <div>
                <SearchOutlined style={{ marginRight: 4 }} />
                <Tooltip title="可搜尋案件名稱">
                  <InfoCircleOutlined style={{ color: '#ccc', fontSize: '12px' }} />
                </Tooltip>
              </div>
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
                value={localFilters.year || ''}
                onChange={(value) => handleFilterChange('year', value)}
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
              <AutoComplete
                options={docNumberOptions}
                onSearch={fetchDocNumberSuggestions}
                onSelect={(value) => handleFilterChange('doc_number', value)}
                onChange={(value) => handleFilterChange('doc_number', value)}
                value={localFilters.doc_number || ''}
                placeholder="請輸入公文字號 (例：乾坤字第)"
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
                <Tooltip title="選擇公文日期範圍。可只選擇開始日期或結束日期。日期格式：YYYY-MM-DD。適用於統計特定時間段的公文。">
                  <QuestionCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
                </Tooltip>
              </div>
              <RangePicker
                placeholder={['選擇開始日期 (可選)', '選擇結束日期 (可選)']}
                value={dateRange}
                onChange={(dates, dateStrings) => {
                  setDateRange(dates);
                  // 將日期範圍儲存到 filters 中
                  handleFilterChange('doc_date_from', dateStrings[0]);
                  handleFilterChange('doc_date_to', dateStrings[1]);
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16 }}>
        {/* 篩選結果提示 */}
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

        <div style={{ display: 'flex', gap: 8 }}>
          <Tooltip title="清除所有篩選條件，回復預設狀態">
            <Button
              onClick={handleReset}
              icon={<ClearOutlined />}
              disabled={!hasActiveFilters}
              style={{ borderColor: hasActiveFilters ? '#ff4d4f' : '', color: hasActiveFilters ? '#ff4d4f' : '' }}
            >
              清除篩選
            </Button>
          </Tooltip>

          <Tooltip title={`套用當前篩選條件。快速鍵：在任一輸入框中按 Enter`}>
            <Button
              type="primary"
              onClick={handleApplyFilters}
              icon={<FilterOutlined />}
              style={{ position: 'relative' }}
            >
              套用篩選
              <span style={{
                position: 'absolute',
                right: 8,
                top: -2,
                fontSize: '10px',
                color: '#87d068',
                fontWeight: 'normal'
              }}>
                Enter
              </span>
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* 使用提示 */}
      {!hasActiveFilters && (
        <div style={{
          textAlign: 'center',
          padding: '8px 16px',
          backgroundColor: '#f6f8fc',
          border: '1px solid #e6ebf7',
          borderRadius: '6px',
          marginTop: 12
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <InfoCircleOutlined style={{ color: '#8c8c8c', fontSize: '12px' }} />
            <span style={{ color: '#8c8c8c', fontSize: '12px' }}>
              提示：選擇上方篩選條件後點擊「套用篩選」，或在輸入框中按 Enter 即可快速搜尋
            </span>
          </div>
        </div>
      )}
    </Card>
  );
};

export { DocumentFilterComponent as DocumentFilter };