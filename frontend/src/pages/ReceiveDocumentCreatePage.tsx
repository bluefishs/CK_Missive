/**
 * 新增收發文紀錄頁面
 *
 * 採用與 DocumentDetailPage 相同的 TAB 設計：
 * - 公文資訊：發文形式、類別、公文類型、公文字號、發文單位、受文單位、日期、主旨、說明、備註
 * - 承案人資：承攬案件、業務同仁
 * - 附件紀錄：附件上傳與管理
 *
 * 預設值邏輯（根據類別動態調整）：
 * - 發文形式：電子交換
 * - 公文類型：函
 *
 * 收文模式（預設）：
 * - 受文單位：乾坤測繪科技有限公司（本公司）
 * - 收文日期：今天
 *
 * 發文模式：
 * - 發文單位：乾坤測繪科技有限公司（本公司）
 * - 發文日期：今天
 * - 受文單位、收文日期清空（因無法得知對方收文時間）
 *
 * @version 1.2.0
 * @date 2026-01-07
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  App,
  Upload,
  Space,
  Row,
  Col,
  Spin,
  List,
  Alert,
  Progress,
} from 'antd';
import {
  FileTextOutlined,
  PaperClipOutlined,
  TeamOutlined,
  SaveOutlined,
  CloseOutlined,
  InboxOutlined,
  CloudUploadOutlined,
  FileOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  DetailPageLayout,
  createTabItem,
} from '../components/common/DetailPage';
import { documentsApi } from '../api/documentsApi';
import { agenciesApi, AgencyOption } from '../api/agenciesApi';
import { filesApi } from '../api/filesApi';
import { apiClient } from '../api/client';

const { TextArea } = Input;
const { Option } = Select;
const { Dragger } = Upload;

// =============================================================================
// 常數定義
// =============================================================================

/** 發文形式選項（電子交換/紙本郵寄） */
const DELIVERY_METHOD_OPTIONS = [
  { value: '電子交換', label: '電子交換' },
  { value: '紙本郵寄', label: '紙本郵寄' },
];

/** 類別選項（收文/發文） */
const CATEGORY_OPTIONS = [
  { value: '收文', label: '收文' },
  { value: '發文', label: '發文' },
];

/** 公文類型選項 */
const DOC_TYPE_OPTIONS = [
  { value: '函', label: '函' },
  { value: '開會通知單', label: '開會通知單' },
  { value: '會勘通知單', label: '會勘通知單' },
];

/** 預設受文單位（本公司） */
const DEFAULT_RECEIVER = '乾坤測繪科技有限公司';

/** 預設檔案驗證常數 */
const DEFAULT_ALLOWED_EXTENSIONS = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
  '.zip', '.rar', '.7z', '.txt', '.csv', '.xml', '.json',
  '.dwg', '.dxf', '.shp', '.kml', '.kmz',
];
const DEFAULT_MAX_FILE_SIZE_MB = 50;

// =============================================================================
// 主元件
// =============================================================================

export const ReceiveDocumentCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();

  // 狀態
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('info');

  // 機關選項
  const [agencies, setAgencies] = useState<AgencyOption[]>([]);
  const [agenciesLoading, setAgenciesLoading] = useState(false);

  // 承攬案件選項
  const [cases, setCases] = useState<any[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);

  // 使用者選項（業務同仁）
  const [users, setUsers] = useState<any[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);

  // 專案業務同仁
  const [projectStaffMap, setProjectStaffMap] = useState<Record<number, any[]>>({});
  const [staffLoading, setStaffLoading] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const projectStaffCacheRef = React.useRef<Record<number, any[]>>({});

  // 附件相關狀態
  const [fileList, setFileList] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);

  // 檔案設定
  const [fileSettings, setFileSettings] = useState({
    allowedExtensions: DEFAULT_ALLOWED_EXTENSIONS,
    maxFileSizeMB: DEFAULT_MAX_FILE_SIZE_MB,
  });

  // =============================================================================
  // 資料載入
  // =============================================================================

  /** 載入機關選項 */
  const loadAgencies = useCallback(async () => {
    setAgenciesLoading(true);
    try {
      const options = await agenciesApi.getAgencyOptions();
      setAgencies(options);
    } catch (error) {
      console.error('載入機關選項失敗:', error);
      setAgencies([]);
    } finally {
      setAgenciesLoading(false);
    }
  }, []);

  /** 載入承攬案件選項 */
  const loadCases = useCallback(async () => {
    setCasesLoading(true);
    try {
      const data = await apiClient.post<{ projects?: any[]; items?: any[] }>(
        '/projects/list',
        { page: 1, limit: 100 }
      );
      const projectsData = data.projects || data.items || [];
      setCases(Array.isArray(projectsData) ? projectsData : []);
    } catch (error) {
      console.error('載入承攬案件失敗:', error);
      setCases([]);
    } finally {
      setCasesLoading(false);
    }
  }, []);

  /** 載入使用者列表（業務同仁） */
  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const data = await apiClient.post<{ users?: any[]; items?: any[] }>(
        '/users/list',
        { page: 1, limit: 100 }
      );
      const usersData = data.users || data.items || [];
      setUsers(Array.isArray(usersData) ? usersData : []);
    } catch (error) {
      console.error('載入使用者失敗:', error);
      setUsers([]);
    } finally {
      setUsersLoading(false);
    }
  }, []);

  /** 載入專案業務同仁 */
  const fetchProjectStaff = async (projectId: number): Promise<any[]> => {
    if (projectStaffCacheRef.current[projectId]) {
      const cachedData = projectStaffCacheRef.current[projectId];
      setProjectStaffMap(prev => ({ ...prev, [projectId]: cachedData }));
      return cachedData;
    }

    setStaffLoading(true);
    try {
      const data = await apiClient.post<{ staff?: any[] }>(
        `/project-staff/project/${projectId}/list`,
        {}
      );
      const staffData = data.staff || [];
      projectStaffCacheRef.current[projectId] = staffData;
      setProjectStaffMap(prev => ({ ...prev, [projectId]: staffData }));
      return staffData;
    } catch (error) {
      console.error('載入專案業務同仁失敗:', error);
      return [];
    } finally {
      setStaffLoading(false);
    }
  };

  /** 載入檔案設定 */
  const loadFileSettings = useCallback(async () => {
    try {
      const info = await filesApi.getStorageInfo();
      setFileSettings({
        allowedExtensions: info.allowed_extensions,
        maxFileSizeMB: info.max_file_size_mb,
      });
    } catch (error) {
      console.warn('載入檔案設定失敗，使用預設值:', error);
    }
  }, []);

  // 初始載入
  useEffect(() => {
    const initialize = async () => {
      setLoading(true);
      await Promise.all([
        loadAgencies(),
        loadCases(),
        loadUsers(),
        loadFileSettings(),
      ]);
      // 設定表單初始值（預設為收文）
      form.setFieldsValue({
        delivery_method: '電子交換',  // 預設發文形式
        category: '收文',             // 預設類別
        doc_type: '函',               // 預設公文類型
        receiver: DEFAULT_RECEIVER,   // 收文時受文單位為本公司
        receive_date: dayjs(),        // 收文時收文日期為今天
      });
      setLoading(false);
    };
    initialize();
  }, [loadAgencies, loadCases, loadUsers, loadFileSettings, form]);

  // =============================================================================
  // 事件處理
  // =============================================================================

  /** 類別切換處理 - 動態調整預設值 */
  const handleCategoryChange = (value: string) => {
    if (value === '收文') {
      // 收文：受文單位 = 本公司，收文日期 = 今天，清空發文單位和發文日期
      form.setFieldsValue({
        receiver: DEFAULT_RECEIVER,
        receive_date: dayjs(),
        sender: undefined,
        send_date: undefined,
      });
    } else if (value === '發文') {
      // 發文：發文單位 = 本公司，發文日期 = 今天，清空受文單位和收文日期
      form.setFieldsValue({
        sender: DEFAULT_RECEIVER,
        send_date: dayjs(),
        receiver: undefined,
        receive_date: undefined,
      });
    }
  };

  /** 選擇專案後處理 */
  const handleProjectChange = async (projectId: number | null | undefined) => {
    const effectiveProjectId = projectId ?? null;
    form.setFieldsValue({ contract_project_id: effectiveProjectId });

    if (!effectiveProjectId) {
      setSelectedProjectId(null);
      form.setFieldsValue({ assignee: [] });
      return;
    }

    const staffList = await fetchProjectStaff(effectiveProjectId);
    if (!staffList || staffList.length === 0) {
      setSelectedProjectId(effectiveProjectId);
      message.info('此專案尚無指派業務同仁');
      return;
    }

    setSelectedProjectId(effectiveProjectId);

    // 自動填入業務同仁
    setTimeout(() => {
      const currentStaff = projectStaffCacheRef.current[effectiveProjectId];
      if (currentStaff && currentStaff.length > 0) {
        const names = currentStaff.map((s: any) => s.user_name);
        form.setFieldsValue({ assignee: names });
        message.success(`已自動填入 ${names.length} 位業務同仁`);
      }
    }, 150);
  };

  /** 儲存收文 */
  const handleSave = async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();

      // 處理 assignee：陣列轉逗號分隔字串
      let assigneeStr = '';
      if (Array.isArray(values.assignee)) {
        assigneeStr = values.assignee.join(', ');
      } else if (values.assignee) {
        assigneeStr = values.assignee;
      }

      // 準備資料
      const documentData = {
        ...values,
        status: 'active',
        doc_date: values.doc_date?.format('YYYY-MM-DD'),
        receive_date: values.receive_date?.format('YYYY-MM-DD'),
        send_date: values.send_date?.format('YYYY-MM-DD'),
        assignee: assigneeStr,
      };

      // 建立公文
      const newDoc = await documentsApi.createDocument(documentData);

      // 上傳附件（如有）
      if (fileList.length > 0) {
        await uploadFiles(newDoc.id, fileList);
      }

      message.success('收發文紀錄建立成功！');
      navigate('/documents');
    } catch (error) {
      console.error('儲存失敗:', error);
      message.error('儲存失敗，請檢查輸入資料');
    } finally {
      setSaving(false);
    }
  };

  /** 取消 */
  const handleCancel = () => {
    navigate('/documents');
  };

  // =============================================================================
  // 附件處理
  // =============================================================================

  /** 上傳檔案 */
  const uploadFiles = async (documentId: number, files: any[]): Promise<any> => {
    if (files.length === 0) return { success: true, files: [], errors: [] };

    const fileObjects: File[] = files
      .map(f => f.originFileObj)
      .filter((f): f is File => f !== undefined);

    if (fileObjects.length === 0) return { success: true, files: [], errors: [] };

    setUploading(true);
    setUploadProgress(0);
    setUploadErrors([]);

    try {
      const result = await filesApi.uploadFiles(documentId, fileObjects, {
        onProgress: (percent) => setUploadProgress(percent),
      });

      if (result.errors && result.errors.length > 0) {
        setUploadErrors(result.errors);
      }

      const successCount = result.files?.length || 0;
      const errorCount = result.errors?.length || 0;

      if (successCount > 0 && errorCount === 0) {
        message.success(`附件上傳成功（共 ${successCount} 個檔案）`);
      } else if (successCount > 0 && errorCount > 0) {
        message.warning(`部分附件上傳成功（成功 ${successCount} 個，失敗 ${errorCount} 個）`);
      }

      return result;
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '上傳失敗';
      message.error(`附件上傳失敗: ${errorMsg}`);
      throw error;
    } finally {
      setUploading(false);
    }
  };

  /** 檔案驗證 */
  const validateFile = (file: File): { valid: boolean; error?: string } => {
    const { allowedExtensions, maxFileSizeMB } = fileSettings;
    const fileName = file.name.toLowerCase();
    const ext = '.' + (fileName.split('.').pop() || '');

    if (!allowedExtensions.includes(ext)) {
      return {
        valid: false,
        error: `不支援 ${ext} 檔案格式`,
      };
    }

    const maxSizeBytes = maxFileSizeMB * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
      return {
        valid: false,
        error: `檔案大小 ${sizeMB}MB 超過限制 (最大 ${maxFileSizeMB}MB)`,
      };
    }

    return { valid: true };
  };

  /** Upload 元件屬性 */
  const uploadProps = {
    multiple: true,
    fileList,
    showUploadList: false,
    beforeUpload: (file: File) => {
      const validation = validateFile(file);
      if (!validation.valid) {
        message.error(validation.error);
        return Upload.LIST_IGNORE;
      }
      return false;
    },
    onChange: ({ fileList: newFileList }: any) => {
      setFileList(newFileList);
    },
    onRemove: (file: any) => {
      const newFileList = fileList.filter(item => item.uid !== file.uid);
      setFileList(newFileList);
    },
  };

  // =============================================================================
  // Tab 內容渲染
  // =============================================================================

  /** Tab 1: 公文資訊 */
  const renderInfoTab = () => (
    <Form form={form} layout="vertical">
      <Row gutter={16}>
        <Col span={6}>
          <Form.Item
            label="發文形式"
            name="delivery_method"
            rules={[{ required: true, message: '請選擇發文形式' }]}
            initialValue="電子交換"
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
            initialValue="收文"
          >
            <Select placeholder="請選擇類別" onChange={handleCategoryChange}>
              {CATEGORY_OPTIONS.map(opt => (
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
            initialValue="函"
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
            <Select
              placeholder="請選擇發文單位"
              loading={agenciesLoading}
              showSearch
              allowClear
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={[
                // 本公司選項置頂（發文時預設為本公司）
                { value: DEFAULT_RECEIVER, label: `${DEFAULT_RECEIVER} (本公司)` },
                // API 機關選項
                ...agencies
                  .filter(agency => agency.agency_name !== DEFAULT_RECEIVER)
                  .map(agency => ({
                    value: agency.agency_name,
                    label: agency.agency_code
                      ? `${agency.agency_name} (${agency.agency_code})`
                      : agency.agency_name,
                  })),
              ]}
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
              options={[
                // 本公司選項置頂（收文時預設為本公司）
                { value: DEFAULT_RECEIVER, label: `${DEFAULT_RECEIVER} (本公司)` },
                // API 機關選項
                ...agencies
                  .filter(agency => agency.agency_name !== DEFAULT_RECEIVER)
                  .map(agency => ({
                    value: agency.agency_name,
                    label: agency.agency_code
                      ? `${agency.agency_name} (${agency.agency_code})`
                      : agency.agency_name,
                  })),
              ]}
            />
          </Form.Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Form.Item
            label="公文日期"
            name="doc_date"
          >
            <DatePicker style={{ width: '100%' }} placeholder="請選擇公文日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="收文日期"
            name="receive_date"
          >
            <DatePicker style={{ width: '100%' }} placeholder="請選擇收文日期" />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            label="發文日期"
            name="send_date"
          >
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

      <Form.Item label="說明" name="content">
        <TextArea rows={4} placeholder="請輸入公文內容說明" maxLength={1000} showCount />
      </Form.Item>

      <Form.Item label="備註" name="notes">
        <TextArea rows={3} placeholder="請輸入備註" maxLength={500} showCount />
      </Form.Item>
    </Form>
  );

  /** Tab 2: 承案人資 */
  const renderCaseStaffTab = () => {
    // 建立業務同仁選項
    const buildAssigneeOptions = () => {
      const staffList = selectedProjectId ? projectStaffMap[selectedProjectId] : undefined;
      const projectStaffOptions =
        staffList && staffList.length > 0
          ? staffList.map((staff) => ({
              value: staff.user_name,
              label: staff.role ? `${staff.user_name}(${staff.role})` : staff.user_name,
              key: `staff-${staff.user_id || staff.id}`,
            }))
          : [];

      const userOptions = Array.isArray(users)
        ? users.map((user) => ({
            value: user.full_name || user.username,
            label: user.full_name || user.username,
            key: `user-${user.id}`,
          }))
        : [];

      return projectStaffOptions.length > 0 ? projectStaffOptions : userOptions;
    };

    return (
      <Form form={form} layout="vertical">
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item label="承攬案件" name="contract_project_id">
              <Select
                placeholder="請選擇承攬案件（選填）"
                loading={casesLoading || staffLoading}
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                onChange={handleProjectChange}
                options={cases.map((case_) => ({
                  value: case_.id,
                  label: case_.project_name || case_.case_name || '未命名案件',
                }))}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label="業務同仁" name="assignee">
              <Select
                mode="multiple"
                placeholder="請選擇業務同仁（可複選）"
                loading={staffLoading || usersLoading}
                allowClear
                showSearch
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={buildAssigneeOptions()}
              />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    );
  };

  /** Tab 3: 附件紀錄 */
  const renderAttachmentsTab = () => (
    <Spin spinning={uploading}>
      <Dragger {...uploadProps} disabled={uploading}>
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">點擊或拖拽文件到此區域上傳</p>
        <p className="ant-upload-hint">
          支援 PDF、DOC、DOCX、XLS、XLSX、JPG、PNG 等格式，單檔最大 {fileSettings.maxFileSizeMB}MB
        </p>
      </Dragger>

      {/* 待上傳檔案預覽 */}
      {fileList.length > 0 && !uploading && (
        <Card
          size="small"
          style={{ marginTop: 16, background: '#f6ffed', border: '1px solid #b7eb8f' }}
          title={
            <span style={{ color: '#52c41a' }}>
              <CloudUploadOutlined style={{ marginRight: 8 }} />
              待上傳檔案（{fileList.length} 個）
            </span>
          }
        >
          <List
            size="small"
            dataSource={fileList}
            renderItem={(file: any) => (
              <List.Item
                actions={[
                  <Button
                    key="remove"
                    type="link"
                    size="small"
                    danger
                    onClick={() => {
                      const newList = fileList.filter(f => f.uid !== file.uid);
                      setFileList(newList);
                    }}
                  >
                    移除
                  </Button>
                ]}
              >
                <List.Item.Meta
                  avatar={<FileOutlined style={{ color: '#1890ff' }} />}
                  title={file.name}
                  description={`${(file.size / 1024).toFixed(1)} KB`}
                />
              </List.Item>
            )}
          />
          <p style={{ color: '#999', fontSize: 12, marginTop: 8, marginBottom: 0 }}>
            點擊上方「儲存」按鈕後開始上傳
          </p>
        </Card>
      )}

      {/* 上傳進度條 */}
      {uploading && (
        <Card
          size="small"
          style={{ marginTop: 16, background: '#e6f7ff', border: '1px solid #91d5ff' }}
          title={
            <span style={{ color: '#1890ff' }}>
              <LoadingOutlined style={{ marginRight: 8 }} />
              正在上傳檔案...
            </span>
          }
        >
          <Progress
            percent={uploadProgress}
            status="active"
            strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
            strokeWidth={12}
          />
        </Card>
      )}

      {/* 上傳錯誤訊息 */}
      {uploadErrors.length > 0 && (
        <Alert
          type="warning"
          showIcon
          closable
          onClose={() => setUploadErrors([])}
          style={{ marginTop: 16 }}
          message="部分檔案上傳失敗"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {uploadErrors.map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
            </ul>
          }
        />
      )}
    </Spin>
  );

  // =============================================================================
  // Tab 配置
  // =============================================================================

  const tabs = [
    createTabItem(
      'info',
      { icon: <FileTextOutlined />, text: '公文資訊' },
      renderInfoTab()
    ),
    createTabItem(
      'case-staff',
      { icon: <TeamOutlined />, text: '承案人資' },
      renderCaseStaffTab()
    ),
    createTabItem(
      'attachments',
      { icon: <PaperClipOutlined />, text: '附件紀錄', count: fileList.length },
      renderAttachmentsTab()
    ),
  ];

  // =============================================================================
  // Header 配置
  // =============================================================================

  const headerConfig = {
    title: '新增收發文紀錄',
    icon: <FileTextOutlined />,
    backText: '返回公文管理',
    backPath: '/documents',
    tags: [
      { text: '收發文', color: 'green' },
      { text: '新增中', color: 'processing' },
    ],
    extra: (
      <Space>
        <Button icon={<CloseOutlined />} onClick={handleCancel}>
          取消
        </Button>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          loading={saving}
          onClick={handleSave}
        >
          儲存
        </Button>
      </Space>
    ),
  };

  // =============================================================================
  // 渲染
  // =============================================================================

  return (
    <DetailPageLayout
      header={headerConfig}
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      loading={loading}
      hasData={true}
    />
  );
};

export default ReceiveDocumentCreatePage;
