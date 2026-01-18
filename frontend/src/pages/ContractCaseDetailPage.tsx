import React, { useState, useEffect } from 'react';
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  Spin,
  message,
  Row,
  Col,
  Progress,
  Tabs,
  Table,
  Upload,
  Empty,
  Tooltip,
  Popconfirm,
  Avatar,
  Statistic,
  Form,
  Input,
  Select,
  Modal,
  DatePicker,
  InputNumber,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  PaperClipOutlined,
  InfoCircleOutlined,
  UploadOutlined,
  DownloadOutlined,
  EyeOutlined,
  TeamOutlined,
  ShopOutlined,
  PlusOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  BankOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { ROUTES } from '../router/types';
// 使用統一 API 服務
import { projectsApi } from '../api/projectsApi';
import { usersApi } from '../api/usersApi';
import { vendorsApi } from '../api/vendorsApi';
import { documentsApi } from '../api/documentsApi';
import { filesApi, FileAttachment } from '../api/filesApi';
import { projectStaffApi, type ProjectStaff } from '../api/projectStaffApi';
import { projectVendorsApi, type ProjectVendor } from '../api/projectVendorsApi';
// 機關承辦 API
import {
  getProjectAgencyContacts,
  createAgencyContact,
  updateAgencyContact,
  deleteAgencyContact,
  type ProjectAgencyContact,
} from '../api/projectAgencyContacts';

const { Title, Text } = Typography;
const { Option } = Select;

// 案件類別選項
const CATEGORY_OPTIONS = [
  { value: '01', label: '01委辦案件', color: 'blue' },
  { value: '02', label: '02協力計畫', color: 'green' },
  { value: '03', label: '03小額採購', color: 'orange' },
  { value: '04', label: '04其他類別', color: 'default' },
];

// 案件性質選項
const CASE_NATURE_OPTIONS = [
  { value: '01', label: '01測量案', color: 'cyan' },
  { value: '02', label: '02資訊案', color: 'purple' },
  { value: '03', label: '03複合案', color: 'gold' },
];

// 執行狀態選項 (使用中文值對應資料庫)
const STATUS_OPTIONS = [
  { value: '待執行', label: '待執行', color: 'warning' },
  { value: '執行中', label: '執行中', color: 'processing' },
  { value: '已結案', label: '已結案', color: 'success' },
  { value: '暫停', label: '暫停', color: 'error' },
];

// 承辦同仁角色選項 (與 StaffPage ROLE_OPTIONS 一致)
const STAFF_ROLE_OPTIONS = [
  { value: '計畫主持', label: '計畫主持', color: 'red' },
  { value: '計畫協同', label: '計畫協同', color: 'orange' },
  { value: '專案PM', label: '專案PM', color: 'blue' },
  { value: '職安主管', label: '職安主管', color: 'green' },
];

// 協力廠商角色選項
const VENDOR_ROLE_OPTIONS = [
  { value: '測量業務', label: '測量業務', color: 'blue' },
  { value: '系統業務', label: '系統業務', color: 'green' },
  { value: '查估業務', label: '查估業務', color: 'orange' },
  { value: '其他類別', label: '其他類別', color: 'default' },
];

// 專案資料類型 (對應後端 ProjectResponse - 完整欄位)
interface ProjectData {
  id: number;
  project_name: string;           // 案件名稱
  year?: number;                  // 年度 (可選)
  client_agency?: string;         // 委託單位
  category?: string;              // 案件類別 (01-04)
  case_nature?: string;           // 案件性質 (01測量案, 02資訊案)
  contract_doc_number?: string;   // 契約文號
  project_code?: string;          // 專案編號 (CK年度_類別_性質_流水號)
  contract_amount?: number;       // 契約金額
  winning_amount?: number;        // 得標金額
  start_date?: string;            // 開始日期
  end_date?: string;              // 結束日期
  status?: string;                // 執行狀態
  progress?: number;              // 完成進度 (0-100)
  notes?: string;                 // 備註
  project_path?: string;          // 專案路徑
  description?: string;           // 專案描述
  created_at: string;
  updated_at: string;
}

// 承辦同仁類型
interface Staff {
  id: number;
  user_id: number;
  name: string;
  role: string;
  department?: string | undefined;
  phone?: string | undefined;
  email?: string | undefined;
  join_date?: string | undefined;
  status: string;
}

// 協力廠商關聯類型
interface VendorAssociation {
  id: number;
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string | undefined;
  contact_person?: string | undefined;
  phone?: string | undefined;
  role: string;
  contract_amount?: number | undefined;
  start_date?: string | undefined;
  end_date?: string | undefined;
  status: string;
}

// 關聯文件類型（對應 Document 型別）
interface RelatedDocument {
  id: number;
  doc_number: string;
  doc_type: string;
  subject: string;
  doc_date: string;
  sender: string;
  receiver: string;
  category: string;           // 收文/發文
  delivery_method: string;    // 發文形式：電子交換/紙本郵寄/電子+紙本
  has_attachment: boolean;    // 是否含附件
}

// 附件類型（彙整自關聯公文）
interface Attachment {
  id: number;
  filename: string;
  original_filename?: string;
  file_size: number;
  file_type: string;
  content_type?: string;
  uploaded_at: string;
  uploaded_by: string;
  // 所屬公文資訊
  document_id: number;
  document_number: string;
  document_subject: string;
}

// 按公文分組的附件（用於摺疊顯示）
interface GroupedAttachment {
  document_id: number;
  document_number: string;
  document_subject: string;
  file_count: number;
  total_size: number;
  last_updated: string;
  attachments: Attachment[];
}

export const ContractCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ProjectData | null>(null);
  const [activeTab, setActiveTab] = useState('info');
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [vendorList, setVendorList] = useState<VendorAssociation[]>([]);
  const [relatedDocs, setRelatedDocs] = useState<RelatedDocument[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [groupedAttachments, setGroupedAttachments] = useState<GroupedAttachment[]>([]);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);
  const [agencyContacts, setAgencyContacts] = useState<ProjectAgencyContact[]>([]);

  // 編輯模式狀態
  const [isEditingCaseInfo, setIsEditingCaseInfo] = useState(false);
  const [editingStaffId, setEditingStaffId] = useState<number | null>(null);
  const [editingVendorId, setEditingVendorId] = useState<number | null>(null);

  // Modal 狀態
  const [staffModalVisible, setStaffModalVisible] = useState(false);
  const [vendorModalVisible, setVendorModalVisible] = useState(false);
  const [agencyContactModalVisible, setAgencyContactModalVisible] = useState(false);
  const [editingAgencyContactId, setEditingAgencyContactId] = useState<number | null>(null);
  const [staffForm] = Form.useForm();
  const [vendorForm] = Form.useForm();
  const [caseInfoForm] = Form.useForm();
  const [agencyContactForm] = Form.useForm();

  // 使用者和廠商選項 (用於新增時選擇)
  const [userOptions, setUserOptions] = useState<{ id: number; name: string; email: string }[]>([]);
  const [vendorOptions, setVendorOptions] = useState<{ id: number; name: string; code: string }[]>([]);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    setLoading(true);
    try {
      // 同時載入專案資料、承辦同仁、協力廠商、機關承辦
      const [projectResponse, staffResponse, vendorsResponse, agencyContactsResponse] = await Promise.all([
        projectsApi.getProject(projectId),
        projectStaffApi.getProjectStaff(projectId).catch(() => ({ staff: [], total: 0, project_id: projectId, project_name: '' })),
        projectVendorsApi.getProjectVendors(projectId).catch(() => ({ associations: [], total: 0, project_id: projectId, project_name: '' })),
        getProjectAgencyContacts(projectId).catch(() => ({ items: [], total: 0 })),
      ]);

      // 設定專案資料
      setData(projectResponse);

      // 轉換承辦同仁資料格式
      const transformedStaff: Staff[] = staffResponse.staff.map((s: ProjectStaff) => ({
        id: s.id,
        user_id: s.user_id,
        name: s.user_name || '未指定',  // 提供預設值避免 undefined
        role: s.role || 'member',
        department: s.department,
        phone: s.phone,
        email: s.user_email,
        join_date: s.start_date,
        status: s.status || 'active',
      }));
      setStaffList(transformedStaff);

      // 轉換協力廠商資料格式
      const transformedVendors: VendorAssociation[] = vendorsResponse.associations.map((v: ProjectVendor) => ({
        id: v.vendor_id,
        vendor_id: v.vendor_id,
        vendor_name: v.vendor_name || '未知廠商',  // 提供預設值避免 undefined
        vendor_code: (v as any).vendor_code,  // 使用 any 繞過缺少的屬性
        contact_person: v.vendor_contact_person,
        phone: v.vendor_phone,
        role: v.role || '供應商',
        contract_amount: v.contract_amount,
        start_date: v.start_date,
        end_date: v.end_date,
        status: v.status || 'active',
      }));
      setVendorList(transformedVendors);

      // 設定機關承辦資料
      setAgencyContacts(agencyContactsResponse.items || []);

      // 載入關聯公文 (使用新 API)
      let loadedDocs: RelatedDocument[] = [];
      try {
        const docsResponse = await documentsApi.getDocumentsByProject(projectId);
        loadedDocs = docsResponse.items.map(doc => ({
          id: doc.id,
          doc_number: doc.doc_number,
          doc_type: doc.doc_type || '函',
          subject: doc.subject,
          doc_date: doc.doc_date || '',
          sender: doc.sender || '',
          receiver: doc.receiver || '',
          category: doc.category || '收文',
          delivery_method: doc.delivery_method || '電子交換',
          has_attachment: doc.has_attachment || false,
        }));
        setRelatedDocs(loadedDocs);
      } catch (error) {
        console.error('載入關聯公文失敗:', error);
        setRelatedDocs([]);
      }

      // 載入所有關聯公文的附件（彙整檢視 + 分組檢視）
      setAttachmentsLoading(true);
      try {
        const allAttachments: Attachment[] = [];
        const grouped: GroupedAttachment[] = [];

        // 遍歷每個關聯公文，取得其附件
        for (const doc of loadedDocs) {
          try {
            const docAttachments = await filesApi.getDocumentAttachments(doc.id);
            // 將附件加上所屬公文資訊
            const mappedAttachments = docAttachments.map((att: FileAttachment) => ({
              id: att.id,
              filename: att.original_filename || att.filename,
              original_filename: att.original_filename,
              file_size: att.file_size,
              file_type: att.content_type || '',
              content_type: att.content_type,
              uploaded_at: att.created_at || '',
              uploaded_by: att.uploaded_by?.toString() || '系統',
              document_id: doc.id,
              document_number: doc.doc_number,
              document_subject: doc.subject,
            }));
            allAttachments.push(...mappedAttachments);

            // 建立分組資料（只有有附件的公文才加入）
            if (mappedAttachments.length > 0) {
              const totalSize = mappedAttachments.reduce((sum, att) => sum + att.file_size, 0);
              const lastUpdated = mappedAttachments
                .map(att => att.uploaded_at)
                .filter(Boolean)
                .sort()
                .pop() || '';

              grouped.push({
                document_id: doc.id,
                document_number: doc.doc_number,
                document_subject: doc.subject,
                file_count: mappedAttachments.length,
                total_size: totalSize,
                last_updated: lastUpdated,
                attachments: mappedAttachments,
              });
            }
          } catch (attError) {
            console.warn(`載入公文 ${doc.doc_number} 的附件失敗:`, attError);
          }
        }
        setAttachments(allAttachments);
        setGroupedAttachments(grouped);
      } catch (attError) {
        console.error('載入附件失敗:', attError);
        setAttachments([]);
        setGroupedAttachments([]);
      } finally {
        setAttachmentsLoading(false);
      }

      console.log('載入專案資料成功:', { projectResponse, staffResponse, vendorsResponse, agencyContactsResponse });
    } catch (error) {
      console.error('載入數據失敗:', error);
      message.error('載入數據失敗');
    } finally {
      setLoading(false);
    }
  };

  // 載入使用者選項 (用於新增同仁)
  const loadUserOptions = async () => {
    try {
      const response = await usersApi.getUsers({ limit: 100 });
      // API 回傳 items 欄位
      const users = (response as any).items || (response as any).users || response || [];
      setUserOptions(Array.isArray(users) ? users.map((u: any) => ({
        id: u.id,
        name: u.full_name || u.username,
        email: u.email,
      })) : []);
    } catch (error) {
      console.error('載入使用者列表失敗:', error);
    }
  };

  // 載入廠商選項 (用於新增廠商)
  const loadVendorOptions = async () => {
    try {
      const response = await vendorsApi.getVendors({ limit: 100 });
      // 統一 API 回傳 items 欄位
      const vendors = (response as any).items || (response as any).vendors || response || [];
      setVendorOptions(Array.isArray(vendors) ? vendors.map((v: any) => ({
        id: v.id,
        name: v.vendor_name,
        code: v.vendor_code,
      })) : []);
    } catch (error) {
      console.error('載入廠商列表失敗:', error);
    }
  };

  const handleEdit = () => {
    navigate(ROUTES.CONTRACT_CASE_EDIT.replace(':id', id!));
  };

  const handleDelete = () => {
    message.success('刪除成功');
    navigate(ROUTES.CONTRACT_CASES);
  };

  const handleBack = () => {
    navigate(ROUTES.CONTRACT_CASES);
  };

  // 計算項目進度
  const calculateProgress = () => {
    if (!data || !data.start_date || !data.end_date) return 0;
    const startDate = new Date(data.start_date);
    const endDate = new Date(data.end_date);
    const currentDate = new Date();
    if (currentDate < startDate) return 0;
    if (currentDate > endDate) return 100;
    const totalDays = endDate.getTime() - startDate.getTime();
    const passedDays = currentDate.getTime() - startDate.getTime();
    return Math.round((passedDays / totalDays) * 100);
  };

  // 格式化檔案大小
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  // 獲取狀態標籤顏色
  const getStatusTagColor = (status?: string) => {
    const statusOption = STATUS_OPTIONS.find(s => s.value === status);
    return statusOption?.color || 'default';
  };

  // 獲取狀態標籤文字
  const getStatusTagText = (status?: string) => {
    const statusOption = STATUS_OPTIONS.find(s => s.value === status);
    return statusOption?.label || status || '未設定';
  };

  // 獲取類別標籤顏色
  const getCategoryTagColor = (category?: string) => {
    const categoryOption = CATEGORY_OPTIONS.find(c => c.value === category);
    return categoryOption?.color || 'default';
  };

  // 獲取類別標籤文字
  const getCategoryTagText = (category?: string) => {
    const categoryOption = CATEGORY_OPTIONS.find(c => c.value === category);
    return categoryOption?.label || category || '未分類';
  };

  // 獲取案件性質標籤顏色
  const getCaseNatureTagColor = (caseNature?: string) => {
    const option = CASE_NATURE_OPTIONS.find(c => c.value === caseNature);
    return option?.color || 'default';
  };

  // 獲取案件性質標籤文字
  const getCaseNatureTagText = (caseNature?: string) => {
    const option = CASE_NATURE_OPTIONS.find(c => c.value === caseNature);
    return option?.label || caseNature || '未設定';
  };

  // 格式化金額
  const formatAmount = (amount?: number) => {
    if (!amount) return '-';
    return new Intl.NumberFormat('zh-TW').format(amount);
  };

  // 角色顏色 (承辦同仁)
  const getStaffRoleColor = (role: string) => {
    const option = STAFF_ROLE_OPTIONS.find(opt => opt.value === role);
    return option?.color || 'default';
  };

  // 角色顏色 (廠商)
  const getVendorRoleColor = (role: string) => {
    const option = VENDOR_ROLE_OPTIONS.find(opt => opt.value === role);
    return option?.color || 'default';
  };

  // 狀態顏色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'processing';
      case 'completed': return 'success';
      case 'inactive': return 'warning';
      default: return 'default';
    }
  };

  // 處理新增同仁表單提交
  const handleAddStaff = async (values: any) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      await projectStaffApi.addStaff({
        project_id: projectId,
        user_id: values.user_id,
        role: values.role,
        is_primary: values.role === '計畫主持',
        start_date: dayjs().format('YYYY-MM-DD'),
        status: 'active',
      });

      staffForm.resetFields();
      setStaffModalVisible(false);
      message.success('新增承辦同仁成功');
      loadData();
    } catch (error: any) {
      console.error('新增承辦同仁失敗:', error);
      // 處理 Pydantic 驗證錯誤格式
      const detail = error.response?.data?.detail;
      let errorMsg = '新增承辦同仁失敗';
      if (typeof detail === 'string') {
        errorMsg = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        errorMsg = detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', ');
      }
      message.error(errorMsg);
    }
  };

  // 處理新增廠商表單提交
  const handleAddVendor = async (values: any) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      const vendorData: {
        project_id: number;
        vendor_id: number;
        role?: string;
        contract_amount?: number;
        start_date?: string;
        end_date?: string;
        status?: string;
      } = {
        project_id: projectId,
        vendor_id: values.vendor_id,
        role: values.role,
        status: 'active',
      };

      if (values.contract_amount) {
        vendorData.contract_amount = values.contract_amount;
      }
      if (values.start_date) {
        vendorData.start_date = dayjs(values.start_date).format('YYYY-MM-DD');
      }
      if (values.end_date) {
        vendorData.end_date = dayjs(values.end_date).format('YYYY-MM-DD');
      }

      await projectVendorsApi.addVendor(vendorData);

      vendorForm.resetFields();
      setVendorModalVisible(false);
      message.success('新增協力廠商成功');
      loadData();
    } catch (error: any) {
      console.error('新增協力廠商失敗:', error);
      message.error(error.response?.data?.detail || '新增協力廠商失敗');
    }
  };

  // 處理案件資訊編輯 - 支援所有欄位
  const handleSaveCaseInfo = async (values: any) => {
    if (!data || !id) return;
    const projectId = parseInt(id, 10);

    try {
      // 自動設定進度：當狀態設為「已結案」時，進度自動設為 100%
      const autoProgress = values.status === '已結案' ? 100 : (values.progress ?? null);

      // 從 date_range 提取開始和結束日期
      const startDate = values.date_range?.[0] ? dayjs(values.date_range[0]).format('YYYY-MM-DD') : null;
      const endDate = values.date_range?.[1] ? dayjs(values.date_range[1]).format('YYYY-MM-DD') : null;

      // 格式化日期欄位，建立更新物件
      const updateData: Record<string, any> = {
        project_name: values.project_name,
        year: values.year,
        client_agency: values.client_agency || null,
        contract_doc_number: values.contract_doc_number || null,
        project_code: values.project_code || null,
        category: values.category || null,
        case_nature: values.case_nature || null,
        contract_amount: values.contract_amount || null,
        winning_amount: values.winning_amount || null,
        start_date: startDate,
        end_date: endDate,
        status: values.status || null,
        progress: autoProgress,
        project_path: values.project_path || null,
        notes: values.notes || null,
      };

      await projectsApi.updateProject(projectId, updateData);

      // 更新本地資料
      setData({
        ...data,
        project_name: updateData['project_name'],
        year: updateData['year'],
        client_agency: updateData['client_agency'],
        contract_doc_number: updateData['contract_doc_number'],
        project_code: updateData['project_code'],
        category: updateData['category'],
        case_nature: updateData['case_nature'],
        contract_amount: updateData['contract_amount'],
        winning_amount: updateData['winning_amount'],
        start_date: updateData['start_date'],
        end_date: updateData['end_date'],
        status: updateData['status'],
        progress: updateData['progress'],
        project_path: updateData['project_path'],
        notes: updateData['notes'],
      });
      setIsEditingCaseInfo(false);
      message.success('案件資訊已更新');
    } catch (error: any) {
      console.error('更新案件資訊失敗:', error);
      message.error(error.response?.data?.detail || '更新案件資訊失敗');
    }
  };

  // 開始編輯案件資訊 - 載入所有欄位到表單
  const startEditCaseInfo = () => {
    if (data) {
      // 處理日期範圍
      const dateRange = (data.start_date && data.end_date)
        ? [dayjs(data.start_date), dayjs(data.end_date)]
        : undefined;

      caseInfoForm.setFieldsValue({
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
      });
      setIsEditingCaseInfo(true);
    }
  };

  // 處理同仁角色更新
  const handleStaffRoleChange = async (staffId: number, newRole: string) => {
    if (!id) return;
    const projectId = parseInt(id, 10);
    const staff = staffList.find(s => s.id === staffId);
    if (!staff) return;

    try {
      await projectStaffApi.updateStaff(projectId, staff.user_id, {
        role: newRole,
        is_primary: newRole === '計畫主持',
      });

      setStaffList(staffList.map(s =>
        s.id === staffId ? { ...s, role: newRole } : s
      ));
      setEditingStaffId(null);
      message.success('角色已更新');
    } catch (error: any) {
      console.error('更新角色失敗:', error);
      message.error(error.response?.data?.detail || '更新角色失敗');
      setEditingStaffId(null);
    }
  };

  // 處理廠商角色更新
  const handleVendorRoleChange = async (vendorId: number, newRole: string) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      await projectVendorsApi.updateVendor(projectId, vendorId, {
        role: newRole,
      });

      setVendorList(vendorList.map(v =>
        v.vendor_id === vendorId ? { ...v, role: newRole } : v
      ));
      setEditingVendorId(null);
      message.success('角色已更新');
    } catch (error: any) {
      console.error('更新角色失敗:', error);
      message.error(error.response?.data?.detail || '更新角色失敗');
      setEditingVendorId(null);
    }
  };

  // 刪除同仁
  const handleDeleteStaff = async (staffId: number) => {
    if (!id) return;
    const projectId = parseInt(id, 10);
    const staff = staffList.find(s => s.id === staffId);
    if (!staff) return;

    try {
      await projectStaffApi.deleteStaff(projectId, staff.user_id);
      setStaffList(staffList.filter(s => s.id !== staffId));
      message.success('已移除同仁');
    } catch (error: any) {
      console.error('移除同仁失敗:', error);
      message.error(error.response?.data?.detail || '移除同仁失敗');
    }
  };

  // 刪除廠商
  const handleDeleteVendor = async (vendorId: number) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      await projectVendorsApi.deleteVendor(projectId, vendorId);
      setVendorList(vendorList.filter(v => v.vendor_id !== vendorId));
      message.success('已移除廠商');
    } catch (error: any) {
      console.error('移除廠商失敗:', error);
      message.error(error.response?.data?.detail || '移除廠商失敗');
    }
  };

  // 承辦同仁表格欄位
  const staffColumns: ColumnsType<Staff> = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: getStaffRoleColor(record.role) === 'red' ? '#f5222d' : '#1890ff' }} />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: '角色/職責',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      render: (role, record) =>
        editingStaffId === record.id ? (
          <Select
            size="small"
            defaultValue={role}
            style={{ width: 130 }}
            onChange={(value) => handleStaffRoleChange(record.id, value)}
            autoFocus
            open={true}
            onOpenChange={(open) => {
              if (!open) setEditingStaffId(null);
            }}
          >
            {STAFF_ROLE_OPTIONS.map(opt => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
        ) : (
          <Tag
            color={getStaffRoleColor(role)}
            style={{ cursor: 'pointer' }}
            onClick={() => setEditingStaffId(record.id)}
          >
            {role} <EditOutlined style={{ fontSize: 10, marginLeft: 4 }} />
          </Tag>
        ),
    },
    {
      title: '部門',
      dataIndex: 'department',
      key: 'department',
    },
    {
      title: '聯絡方式',
      key: 'contact',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
          {record.email && <span><MailOutlined /> {record.email}</span>}
        </Space>
      ),
    },
    {
      title: '加入日期',
      dataIndex: 'join_date',
      key: 'join_date',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status === 'active' ? '在職' : '離職'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Popconfirm
          title="確定要移除此同仁？"
          okText="確定"
          cancelText="取消"
          onConfirm={() => handleDeleteStaff(record.id)}
        >
          <Tooltip title="移除">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Tooltip>
        </Popconfirm>
      ),
    },
  ];

  // 協力廠商表格欄位
  const vendorColumns: ColumnsType<VendorAssociation> = [
    {
      title: '廠商資訊',
      key: 'vendor_info',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Text strong>{record.vendor_name}</Text>
          {record.vendor_code && <Text type="secondary">統編: {record.vendor_code}</Text>}
        </Space>
      ),
    },
    {
      title: '業務類別',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      render: (role, record) =>
        editingVendorId === record.vendor_id ? (
          <Select
            size="small"
            defaultValue={role}
            style={{ width: 120 }}
            onChange={(value) => handleVendorRoleChange(record.vendor_id, value)}
            autoFocus
            open={true}
            onOpenChange={(open) => {
              if (!open) setEditingVendorId(null);
            }}
          >
            {VENDOR_ROLE_OPTIONS.map(opt => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
        ) : (
          <Tag
            color={getVendorRoleColor(role)}
            style={{ cursor: 'pointer' }}
            onClick={() => setEditingVendorId(record.vendor_id)}
          >
            {role} <EditOutlined style={{ fontSize: 10, marginLeft: 4 }} />
          </Tag>
        ),
    },
    {
      title: '聯絡人',
      key: 'contact',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.contact_person && <span><UserOutlined /> {record.contact_person}</span>}
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
        </Space>
      ),
    },
    {
      title: '合約金額',
      dataIndex: 'contract_amount',
      key: 'contract_amount',
      render: (amount) => <Text>NT$ {formatAmount(amount)}</Text>,
    },
    {
      title: '合作期間',
      key: 'period',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <span>{record.start_date} ~</span>
          <span>{record.end_date}</span>
        </Space>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {status === 'active' ? '合作中' : status === 'completed' ? '已完成' : '暫停'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Popconfirm
          title="確定要移除此廠商？"
          okText="確定"
          cancelText="取消"
          onConfirm={() => handleDeleteVendor(record.vendor_id)}
        >
          <Tooltip title="移除">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Tooltip>
        </Popconfirm>
      ),
    },
  ];

  // 解析機關名稱：提取括號內的名稱
  const extractAgencyName = (value: string | undefined): string => {
    if (!value) return '-';
    const agencies = value.split(' | ').map(agency => {
      const match = agency.match(/\(([^)]+)\)/);
      return match ? match[1] : agency;
    });
    return agencies.join('、');
  };

  // 關聯公文表格欄位（欄位順序對應 /documents 頁面）
  const documentColumns: ColumnsType<RelatedDocument> = [
    {
      title: '公文字號',
      dataIndex: 'doc_number',
      key: 'doc_number',
      width: 180,
      ellipsis: true,
      render: (text, record) => (
        <Button
          type="link"
          style={{ padding: 0, fontWeight: 500 }}
          onClick={() => navigate(`/documents/${record.id}`)}
        >
          {text}
        </Button>
      ),
    },
    {
      title: '發文形式',
      dataIndex: 'delivery_method',
      key: 'delivery_method',
      width: 95,
      align: 'center',
      render: (method: string) => {
        const colorMap: Record<string, string> = {
          '電子交換': 'green',
          '紙本郵寄': 'orange',
          '電子+紙本': 'blue',
        };
        return <Tag color={colorMap[method] || 'default'}>{method || '電子交換'}</Tag>;
      },
    },
    {
      title: '收發單位',
      key: 'correspondent',
      width: 160,
      ellipsis: true,
      render: (_: any, record: RelatedDocument) => {
        // 收文顯示 sender (來文機關)，發文顯示 receiver (受文機關)
        const rawValue = record.category === '收文' ? record.sender : record.receiver;
        const labelPrefix = record.category === '收文' ? '來文：' : '發至：';
        const labelColor = record.category === '收文' ? '#52c41a' : '#1890ff';
        const displayValue = extractAgencyName(rawValue);

        return (
          <Tooltip title={displayValue}>
            <Text ellipsis>
              <span style={{ color: labelColor, fontWeight: 500, fontSize: '11px' }}>
                {labelPrefix}
              </span>
              {displayValue}
            </Text>
          </Tooltip>
        );
      },
    },
    {
      title: '公文日期',
      dataIndex: 'doc_date',
      key: 'doc_date',
      width: 100,
      align: 'center',
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '主旨',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
    },
  ];

  // 下載附件
  const handleDownloadAttachment = async (attachmentId: number, filename: string) => {
    try {
      await filesApi.downloadAttachment(attachmentId, filename);
    } catch (error) {
      console.error('下載附件失敗:', error);
      message.error('下載附件失敗');
    }
  };

  // 預覽附件
  const handlePreviewAttachment = async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      console.error('預覽附件失敗:', error);
      message.error(`預覽 ${filename} 失敗`);
    }
  };

  // 判斷是否可預覽
  const isPreviewable = (contentType?: string, filename?: string): boolean => {
    if (contentType) {
      if (contentType.startsWith('image/') ||
          contentType === 'application/pdf' ||
          contentType.startsWith('text/')) {
        return true;
      }
    }
    if (filename) {
      const ext = filename.toLowerCase().split('.').pop();
      return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'txt', 'csv'].includes(ext || '');
    }
    return false;
  };

  // 批次下載某公文的所有附件
  const handleDownloadAllAttachments = async (group: GroupedAttachment) => {
    message.loading({ content: `正在下載 ${group.file_count} 個檔案...`, key: 'download-all' });
    for (const att of group.attachments) {
      try {
        await filesApi.downloadAttachment(att.id, att.filename);
      } catch (error) {
        console.error(`下載 ${att.filename} 失敗:`, error);
      }
    }
    message.success({ content: '下載完成', key: 'download-all' });
  };

  // 分組附件表格欄位（父層：公文）
  const groupedAttachmentColumns: ColumnsType<GroupedAttachment> = [
    {
      title: '公文字號',
      dataIndex: 'document_number',
      key: 'document_number',
      width: 200,
      render: (text: string, record) => (
        <Tooltip title={record.document_subject}>
          <Button
            type="link"
            style={{ padding: 0, fontWeight: 500 }}
            onClick={() => navigate(`/documents/${record.document_id}`)}
          >
            {text}
          </Button>
        </Tooltip>
      ),
    },
    {
      title: '檔案數',
      dataIndex: 'file_count',
      key: 'file_count',
      width: 100,
      align: 'center',
      render: (count: number) => <Tag color="blue">{count} 個</Tag>,
    },
    {
      title: '總大小',
      dataIndex: 'total_size',
      key: 'total_size',
      width: 100,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: '最後更新',
      dataIndex: 'last_updated',
      key: 'last_updated',
      width: 110,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Tooltip title="全部下載">
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              handleDownloadAllAttachments(record);
            }}
          >
            全部下載
          </Button>
        </Tooltip>
      ),
    },
  ];

  // 展開列：單一附件明細
  const expandedAttachmentColumns: ColumnsType<Attachment> = [
    {
      title: '檔案名稱',
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
      render: (text) => (
        <Space>
          <PaperClipOutlined style={{ color: '#1890ff' }} />
          <Text ellipsis={{ tooltip: text }}>{text}</Text>
        </Space>
      ),
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (size) => formatFileSize(size),
    },
    {
      title: '上傳時間',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
      width: 110,
      render: (date: string) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="下載">
            <Button
              size="small"
              icon={<DownloadOutlined />}
              onClick={() => handleDownloadAttachment(record.id, record.filename)}
            />
          </Tooltip>
          {isPreviewable(record.content_type, record.filename) && (
            <Tooltip title="預覽">
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => handlePreviewAttachment(record.id, record.filename)}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Title level={4}>案件不存在</Title>
          <Button type="primary" onClick={handleBack}>返回列表</Button>
        </div>
      </Card>
    );
  }

  const progress = calculateProgress();

  // TAB 1: 案件資訊
  const renderCaseInfo = () => (
    <div>
      {/* 進度顯示 - 顯示完成進度 */}
      <Card title="執行進度" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={18}>
            <Progress
              percent={data.progress ?? progress}
              status={data.status === '已結案' ? 'success' : data.status === '暫停' ? 'exception' : 'active'}
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

      {/* 基本資訊 - 支援直接編輯 (完整欄位) */}
      <Card
        title="基本資訊"
        style={{ marginBottom: 16 }}
        extra={
          isEditingCaseInfo ? (
            <Space>
              <Button size="small" onClick={() => setIsEditingCaseInfo(false)}>取消</Button>
              <Button size="small" type="primary" onClick={() => caseInfoForm.submit()}>儲存</Button>
            </Space>
          ) : (
            <Button size="small" icon={<EditOutlined />} onClick={startEditCaseInfo}>編輯</Button>
          )
        }
      >
        {isEditingCaseInfo ? (
          <Form form={caseInfoForm} layout="vertical" onFinish={handleSaveCaseInfo}>
            <Row gutter={16}>
              {/* 第一行: 案件名稱 */}
              <Col span={24}>
                <Form.Item name="project_name" label="案件名稱" rules={[{ required: true, message: '請輸入案件名稱' }]}>
                  <Input placeholder="請輸入案件名稱" />
                </Form.Item>
              </Col>
              {/* 第二行: 年度、委託單位 */}
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
              {/* 第三行: 契約文號、專案編號 */}
              <Col span={12}>
                <Form.Item name="contract_doc_number" label="契約文號">
                  <Input placeholder="請輸入契約文號" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="project_code"
                  label="專案編號"
                  tooltip="格式: CK{年度6碼}_{類別2碼}_{性質2碼}_{流水號3碼}，留空自動產生 (如 CK202501_01_01_001)"
                >
                  <Input placeholder="留空自動產生 (如 CK202501_01_01_001)" />
                </Form.Item>
              </Col>
              {/* 第四行: 案件類別、案件性質 */}
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
              {/* 第五行: 契約金額、得標金額 */}
              <Col span={12}>
                <Form.Item name="contract_amount" label="契約金額">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="請輸入契約金額"
                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={value => value?.replace(/\$\s?|(,*)/g, '') as any}
                    addonBefore="NT$"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="winning_amount" label="得標金額">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="請輸入得標金額"
                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={value => value?.replace(/\$\s?|(,*)/g, '') as any}
                    addonBefore="NT$"
                  />
                </Form.Item>
              </Col>
              {/* 第六行: 契約期程 (合併日期) */}
              <Col span={24}>
                <Form.Item name="date_range" label="契約期程">
                  <DatePicker.RangePicker
                    style={{ width: '100%' }}
                    placeholder={['開始日期', '結束日期']}
                  />
                </Form.Item>
              </Col>
              {/* 第七行: 執行狀態、完成進度 */}
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
              {/* 第七行: 專案路徑 */}
              <Col span={24}>
                <Form.Item name="project_path" label="專案路徑">
                  <Input placeholder="請輸入專案資料夾路徑 (可選)" />
                </Form.Item>
              </Col>
              {/* 第八行: 備註 */}
              <Col span={24}>
                <Form.Item name="notes" label="備註">
                  <Input.TextArea rows={3} placeholder="請輸入備註說明" />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        ) : (
          <Descriptions column={2} bordered size="small">
            {/* 1. 案件名稱 */}
            <Descriptions.Item label="案件名稱" span={2}>
              <Text strong>{data.project_name}</Text>
            </Descriptions.Item>
            {/* 2. 年度、3. 委託單位 */}
            <Descriptions.Item label="年度">{data.year}年</Descriptions.Item>
            <Descriptions.Item label="委託單位">{data.client_agency || '-'}</Descriptions.Item>
            {/* 4. 契約文號、5. 專案編號 */}
            <Descriptions.Item label="契約文號">{data.contract_doc_number || '-'}</Descriptions.Item>
            <Descriptions.Item label="專案編號">
              {data.project_code ? <Text code>{data.project_code}</Text> : '-'}
            </Descriptions.Item>
            {/* 6. 案件類別、7. 案件性質 */}
            <Descriptions.Item label="案件類別">
              <Tag color={getCategoryTagColor(data.category)}>
                {getCategoryTagText(data.category)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="案件性質">
              <Tag color={getCaseNatureTagColor(data.case_nature)}>
                {getCaseNatureTagText(data.case_nature)}
              </Tag>
            </Descriptions.Item>
            {/* 8. 契約金額、9. 得標金額 */}
            <Descriptions.Item label="契約金額">
              {data.contract_amount ? `NT$ ${formatAmount(data.contract_amount)}` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="得標金額">
              {data.winning_amount ? `NT$ ${formatAmount(data.winning_amount)}` : '-'}
            </Descriptions.Item>
            {/* 10. 開始日期、11. 結束日期 */}
            <Descriptions.Item label="開始日期">
              {data.start_date ? dayjs(data.start_date).format('YYYY/MM/DD') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="結束日期">
              {data.end_date ? dayjs(data.end_date).format('YYYY/MM/DD') : '-'}
            </Descriptions.Item>
            {/* 12. 執行狀態、13. 完成進度 */}
            <Descriptions.Item label="執行狀態">
              <Tag color={getStatusTagColor(data.status)}>
                {getStatusTagText(data.status)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="完成進度">
              {data.progress !== undefined ? `${data.progress}%` : '-'}
            </Descriptions.Item>
            {/* 14. 專案路徑 */}
            <Descriptions.Item label="專案路徑" span={2}>
              {data.project_path ? <Text type="secondary">{data.project_path}</Text> : '-'}
            </Descriptions.Item>
            {/* 備註 */}
            <Descriptions.Item label="備註" span={2}>
              {data.notes || '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      {/* 專案說明 - 非編輯模式時顯示 */}
      {!isEditingCaseInfo && data.description && (
        <Card title="專案說明" style={{ marginBottom: 16 }}>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{data.description}</div>
        </Card>
      )}
    </div>
  );

  // TAB 2: 承辦同仁
  const renderStaff = () => (
    <Card
      title={
        <Space>
          <TeamOutlined />
          <span>承辦同仁</span>
          <Tag color="blue">{staffList.length} 人</Tag>
        </Space>
      }
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setStaffModalVisible(true)}>
          新增同仁
        </Button>
      }
    >
      {/* [已移除] 統計概覽 - 4種專案角色 (2026-01-07: 承辦同仁 tab 不需要儀表板統計) */}

      {staffList.length > 0 ? (
        <Table
          columns={staffColumns}
          dataSource={staffList}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      ) : (
        <Empty description="尚無承辦同仁" />
      )}
    </Card>
  );

  // TAB 3: 協力廠商
  const renderVendors = () => (
    <Card
      title={
        <Space>
          <ShopOutlined />
          <span>協力廠商</span>
          <Tag color="blue">{vendorList.length} 家</Tag>
        </Space>
      }
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setVendorModalVisible(true)}>
          新增廠商
        </Button>
      }
    >
      {/* 統計概覽 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <Statistic
              title="合約總金額"
              value={vendorList.reduce((sum, v) => sum + (v.contract_amount || 0), 0)}
              formatter={value => `NT$ ${formatAmount(Number(value))}`}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <Statistic
              title="合作中廠商"
              value={vendorList.filter(v => v.status === 'active').length}
              suffix={`/ ${vendorList.length}`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {vendorList.length > 0 ? (
        <Table
          columns={vendorColumns}
          dataSource={vendorList}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      ) : (
        <Empty description="尚無協力廠商" />
      )}
    </Card>
  );

  // TAB 4: 關聯公文（自動關聯機制 - 依 project_id 查詢）
  const renderRelatedDocuments = () => (
    <Card
      title={
        <Space>
          <FileTextOutlined />
          <span>關聯公文</span>
          <Tag color="blue">{relatedDocs.length} 件</Tag>
        </Space>
      }
      extra={
        <Space>
          <Text type="secondary">自動關聯本專案所有公文</Text>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={loadData}
          >
            重新整理
          </Button>
        </Space>
      }
    >
      {relatedDocs.length > 0 ? (
        <Table
          columns={documentColumns}
          dataSource={relatedDocs}
          rowKey="id"
          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (t) => `共 ${t} 筆公文` }}
          size="middle"
        />
      ) : (
        <Empty
          description={
            <span>
              尚無關聯公文<br />
              <Text type="secondary">請在公文管理頁面新增公文時，選擇本專案作為「承攬案件」</Text>
            </span>
          }
        />
      )}
    </Card>
  );

  // TAB 5: 附件紀錄（以公文分組的摺疊式設計）
  const renderAttachments = () => (
    <Card
      title={
        <Space>
          <PaperClipOutlined />
          <span>附件紀錄</span>
          <Tag color="blue">{attachments.length} 個檔案</Tag>
          {groupedAttachments.length > 0 && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              (來自 {groupedAttachments.length} 筆公文)
            </Text>
          )}
        </Space>
      }
      extra={
        <Button
          icon={<ReloadOutlined />}
          onClick={loadData}
          loading={attachmentsLoading}
        >
          重新整理
        </Button>
      }
      loading={attachmentsLoading}
    >
      {groupedAttachments.length > 0 ? (
        <Table
          columns={groupedAttachmentColumns}
          dataSource={groupedAttachments}
          rowKey="document_id"
          pagination={false}
          size="middle"
          expandable={{
            expandedRowRender: (record) => (
              <Table
                columns={expandedAttachmentColumns}
                dataSource={record.attachments}
                rowKey="id"
                pagination={false}
                size="small"
                showHeader={false}
                style={{ margin: 0 }}
              />
            ),
            rowExpandable: (record) => record.attachments.length > 0,
          }}
        />
      ) : (
        <Empty
          description={
            relatedDocs.length === 0 ? (
              <span>
                尚無關聯公文<br />
                <Text type="secondary">
                  請先在「關聯公文」頁籤中關聯公文，附件將自動彙整於此。
                </Text>
              </span>
            ) : (
              <span>
                關聯公文中尚無附件<br />
                <Text type="secondary">
                  可至「關聯公文」頁籤點擊公文字號進入公文詳情頁上傳附件。
                </Text>
              </span>
            )
          }
        />
      )}
    </Card>
  );

  // 處理新增/編輯機關承辦表單提交
  const handleAgencyContactSubmit = async (values: any) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      if (editingAgencyContactId) {
        // 更新
        await updateAgencyContact(editingAgencyContactId, values);
        message.success('更新成功');
      } else {
        // 新增
        await createAgencyContact({ ...values, project_id: projectId });
        message.success('新增成功');
      }
      setAgencyContactModalVisible(false);
      setEditingAgencyContactId(null);
      agencyContactForm.resetFields();
      loadData();
    } catch (error) {
      console.error('儲存機關承辦失敗:', error);
      message.error('儲存失敗');
    }
  };

  // 處理刪除機關承辦
  const handleDeleteAgencyContact = async (contactId: number) => {
    try {
      await deleteAgencyContact(contactId);
      message.success('刪除成功');
      loadData();
    } catch (error) {
      console.error('刪除機關承辦失敗:', error);
      message.error('刪除失敗');
    }
  };

  // 開啟編輯機關承辦 Modal
  const openEditAgencyContactModal = (contact: ProjectAgencyContact) => {
    setEditingAgencyContactId(contact.id);
    agencyContactForm.setFieldsValue(contact);
    setAgencyContactModalVisible(true);
  };

  // 機關承辦表格欄位定義
  const agencyContactColumns: ColumnsType<ProjectAgencyContact> = [
    {
      title: '姓名',
      dataIndex: 'contact_name',
      key: 'contact_name',
      render: (name: string, record: ProjectAgencyContact) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: record.is_primary ? '#1890ff' : '#87d068' }} />
          <span>{name}</span>
          {record.is_primary && <Tag color="blue">主要</Tag>}
        </Space>
      ),
    },
    {
      title: '職稱',
      dataIndex: 'position',
      key: 'position',
      render: (text: string) => text || '-',
    },
    {
      title: '單位/科室',
      dataIndex: 'department',
      key: 'department',
      render: (text: string) => text || '-',
    },
    {
      title: '聯絡電話',
      key: 'phones',
      render: (_: any, record: ProjectAgencyContact) => (
        <Space direction="vertical" size={0}>
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
          {record.mobile && <span><PhoneOutlined /> {record.mobile}</span>}
          {!record.phone && !record.mobile && '-'}
        </Space>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (email: string) => email ? <a href={`mailto:${email}`}><MailOutlined /> {email}</a> : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: ProjectAgencyContact) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEditAgencyContactModal(record)}>
            編輯
          </Button>
          <Popconfirm
            title="確定要刪除此承辦人嗎？"
            onConfirm={() => handleDeleteAgencyContact(record.id)}
            okText="確定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>刪除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // TAB: 機關承辦 (委託單位聯絡窗口)
  const renderAgencyContact = () => (
    <Card
      title={
        <Space>
          <BankOutlined />
          <span>機關承辦</span>
          <Tag color="blue">{agencyContacts.length} 人</Tag>
        </Space>
      }
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditingAgencyContactId(null);
            agencyContactForm.resetFields();
            setAgencyContactModalVisible(true);
          }}
        >
          新增承辦人
        </Button>
      }
    >
      {agencyContacts.length > 0 ? (
        <Table
          columns={agencyContactColumns}
          dataSource={agencyContacts}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      ) : (
        <Empty description="尚無機關承辦資料" />
      )}

      {/* 機關承辦 Modal */}
      <Modal
        title={editingAgencyContactId ? '編輯機關承辦' : '新增機關承辦'}
        open={agencyContactModalVisible}
        onCancel={() => {
          setAgencyContactModalVisible(false);
          setEditingAgencyContactId(null);
          agencyContactForm.resetFields();
        }}
        onOk={() => agencyContactForm.submit()}
        width={600}
      >
        <Form form={agencyContactForm} layout="vertical" onFinish={handleAgencyContactSubmit}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="contact_name" label="姓名" rules={[{ required: true, message: '請輸入姓名' }]}>
                <Input placeholder="請輸入承辦人姓名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="position" label="職稱">
                <Input placeholder="請輸入職稱" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="department" label="單位/科室">
            <Input placeholder="請輸入單位或科室名稱" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="phone" label="電話">
                <Input placeholder="請輸入電話" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="mobile" label="手機">
                <Input placeholder="請輸入手機" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="email" label="電子郵件">
            <Input placeholder="請輸入電子郵件" />
          </Form.Item>
          <Form.Item name="is_primary" valuePropName="checked">
            <Select placeholder="是否為主要承辦人" allowClear>
              <Option value={true}>是 (主要承辦人)</Option>
              <Option value={false}>否</Option>
            </Select>
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} placeholder="請輸入備註" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );

  // Tab 項目定義 - 6 個 TAB (依照用戶需求排序，相關文件拆分為關聯公文+附件管理)
  const tabItems = [
    {
      key: 'info',
      label: (
        <span>
          <InfoCircleOutlined />
          案件資訊
        </span>
      ),
      children: renderCaseInfo(),
    },
    {
      key: 'agency',
      label: (
        <span>
          <BankOutlined />
          機關承辦
          <Tag color="blue" style={{ marginLeft: 8 }}>{agencyContacts.length}</Tag>
        </span>
      ),
      children: renderAgencyContact(),
    },
    {
      key: 'staff',
      label: (
        <span>
          <TeamOutlined />
          承辦同仁
          <Tag color="blue" style={{ marginLeft: 8 }}>{staffList.length}</Tag>
        </span>
      ),
      children: renderStaff(),
    },
    {
      key: 'vendors',
      label: (
        <span>
          <ShopOutlined />
          協力廠商
          <Tag color="blue" style={{ marginLeft: 8 }}>{vendorList.length}</Tag>
        </span>
      ),
      children: renderVendors(),
    },
    {
      key: 'attachments',
      label: (
        <span>
          <PaperClipOutlined />
          附件紀錄
          <Tag color="blue" style={{ marginLeft: 8 }}>{attachments.length}</Tag>
        </span>
      ),
      children: renderAttachments(),
    },
    {
      key: 'documents',
      label: (
        <span>
          <FileTextOutlined />
          關聯公文
          <Tag color="blue" style={{ marginLeft: 8 }}>{relatedDocs.length}</Tag>
        </span>
      ),
      children: renderRelatedDocuments(),
    },
  ];

  return (
    <div>
      {/* 頁面標題和操作 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button type="text" icon={<ArrowLeftOutlined />} onClick={handleBack}>
              返回
            </Button>
            <div>
              <Title level={3} style={{ margin: 0 }}>{data.project_name}</Title>
              <div style={{ marginTop: 8 }}>
                <Tag color={getCategoryTagColor(data.category)}>
                  {data.category || '未分類'}
                </Tag>
                <Tag color={getStatusTagColor(data.status)}>
                  {getStatusTagText(data.status)}
                </Tag>
              </div>
            </div>
          </div>
          {/* 編輯/刪除按鈕已移除，避免誤刪案件。如需編輯案件資訊，請使用「案件資訊」TAB 內的編輯功能 */}
        </div>
      </Card>

      {/* 4個TAB分頁 */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          size="large"
        />
      </Card>

      {/* 新增同仁 Modal */}
      <Modal
        title="新增承辦同仁"
        open={staffModalVisible}
        onCancel={() => setStaffModalVisible(false)}
        footer={null}
        width={500}
        destroyOnHidden
        afterOpenChange={(open) => {
          if (open) loadUserOptions();
        }}
      >
        <Form form={staffForm} layout="vertical" onFinish={handleAddStaff}>
          <Form.Item name="user_id" label="選擇同仁" rules={[{ required: true, message: '請選擇同仁' }]}>
            <Select
              placeholder="請選擇同仁"
              showSearch
              optionFilterProp="label"
              options={userOptions.map(u => ({
                value: u.id,
                label: `${u.name} (${u.email})`,
              }))}
            />
          </Form.Item>
          <Form.Item name="role" label="角色/職責" rules={[{ required: true, message: '請選擇角色/職責' }]}>
            <Select placeholder="請選擇角色/職責">
              {STAFF_ROLE_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setStaffModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">新增</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 新增廠商 Modal */}
      <Modal
        title="新增協力廠商"
        open={vendorModalVisible}
        onCancel={() => setVendorModalVisible(false)}
        footer={null}
        width={600}
        destroyOnHidden
        afterOpenChange={(open) => {
          if (open) loadVendorOptions();
        }}
      >
        <Form form={vendorForm} layout="vertical" onFinish={handleAddVendor}>
          <Form.Item name="vendor_id" label="選擇廠商" rules={[{ required: true, message: '請選擇廠商' }]}>
            <Select
              placeholder="請選擇廠商"
              showSearch
              optionFilterProp="label"
              options={vendorOptions.map(v => ({
                value: v.id,
                label: `${v.name}${v.code ? ` (${v.code})` : ''}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="role" label="業務類別" rules={[{ required: true, message: '請選擇業務類別' }]}>
            <Select placeholder="請選擇業務類別">
              {VENDOR_ROLE_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="contract_amount" label="合約金額">
            <InputNumber
              style={{ width: '100%' }}
              placeholder="請輸入合約金額"
              formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value?.replace(/\$\s?|(,*)/g, '') as any}
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="start_date" label="合作開始日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="end_date" label="合作結束日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setVendorModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">新增</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ContractCaseDetailPage;
