/**
 * 承攬案件詳情頁面
 *
 * 重構版本：使用模組化 Tab 元件
 * @version 2.0.0
 * @date 2026-01-23
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Tag,
  Button,
  Space,
  Typography,
  Spin,
  Tabs,
  Form,
  App,
} from 'antd';
import {
  ArrowLeftOutlined,
  InfoCircleOutlined,
  BankOutlined,
  TeamOutlined,
  ShopOutlined,
  PaperClipOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { ROUTES } from '../router/types';
import { queryKeys } from '../config/queryConfig';

// 使用統一 API 服務
import { projectsApi } from '../api/projectsApi';
import { usersApi } from '../api/usersApi';
import { vendorsApi } from '../api/vendorsApi';
import { documentsApi } from '../api/documentsApi';
import { filesApi, FileAttachment } from '../api/filesApi';
import { projectStaffApi, type ProjectStaff } from '../api/projectStaffApi';
import { projectVendorsApi, type ProjectVendor } from '../api/projectVendorsApi';
import {
  getProjectAgencyContacts,
  createAgencyContact,
  updateAgencyContact,
  deleteAgencyContact,
} from '../api/projectAgencyContacts';
import { logger } from '../utils/logger';
import type { User, Vendor } from '../types/api';
import type { PaginatedResponse } from '../api/types';

// 匯入模組化 Tab 元件和型別
import {
  CaseInfoTab,
  AgencyContactTab,
  StaffTab,
  VendorsTab,
  AttachmentsTab,
  RelatedDocumentsTab,
  CATEGORY_OPTIONS,
  STATUS_OPTIONS,
} from './contractCase/tabs';

import type {
  ProjectData,
  RelatedDocument,
  Attachment,
  LocalGroupedAttachment,
  VendorAssociation,
  Staff,
  CaseInfoFormValues,
  AgencyContactFormValues,
  StaffFormValues,
  VendorFormValues,
  ApiErrorResponse,
  PydanticValidationError,
} from './contractCase/tabs';

import type { ProjectAgencyContact } from '../api/projectAgencyContacts';

const { Title } = Typography;

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

export const ContractCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  // 主要狀態
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ProjectData | null>(null);
  const [activeTab, setActiveTab] = useState('info');

  // 資料狀態
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [vendorList, setVendorList] = useState<VendorAssociation[]>([]);
  const [relatedDocs, setRelatedDocs] = useState<RelatedDocument[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [groupedAttachments, setGroupedAttachments] = useState<LocalGroupedAttachment[]>([]);
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

  // 表單
  const [staffForm] = Form.useForm<StaffFormValues>();
  const [vendorForm] = Form.useForm<VendorFormValues>();
  const [caseInfoForm] = Form.useForm<CaseInfoFormValues>();
  const [agencyContactForm] = Form.useForm<AgencyContactFormValues>();

  // 選項狀態
  const [userOptions, setUserOptions] = useState<{ id: number; name: string; email: string }[]>([]);
  const [vendorOptions, setVendorOptions] = useState<{ id: number; name: string; code: string }[]>([]);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  // ============================================================================
  // 資料載入函數
  // ============================================================================

  const loadData = async () => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    setLoading(true);
    try {
      const [projectResponse, staffResponse, vendorsResponse, agencyContactsResponse] = await Promise.all([
        projectsApi.getProject(projectId),
        projectStaffApi.getProjectStaff(projectId).catch(() => ({ staff: [], total: 0, project_id: projectId, project_name: '' })),
        projectVendorsApi.getProjectVendors(projectId).catch(() => ({ associations: [], total: 0, project_id: projectId, project_name: '' })),
        getProjectAgencyContacts(projectId).catch(() => ({ items: [], total: 0 })),
      ]);

      setData(projectResponse);

      // 轉換承辦同仁資料
      const transformedStaff: Staff[] = staffResponse.staff.map((s: ProjectStaff) => ({
        id: s.id,
        user_id: s.user_id,
        name: s.user_name || '未指定',
        role: s.role || 'member',
        department: s.department,
        phone: s.phone,
        email: s.user_email,
        join_date: s.start_date,
        status: s.status || 'active',
      }));
      setStaffList(transformedStaff);

      // 轉換協力廠商資料
      const transformedVendors: VendorAssociation[] = vendorsResponse.associations.map((v: ProjectVendor) => ({
        id: v.vendor_id,
        vendor_id: v.vendor_id,
        vendor_name: v.vendor_name || '未知廠商',
        vendor_code: v.vendor?.vendor_code,
        contact_person: v.vendor_contact_person,
        phone: v.vendor_phone,
        role: v.role || '供應商',
        contract_amount: v.contract_amount,
        start_date: v.start_date,
        end_date: v.end_date,
        status: v.status || 'active',
      }));
      setVendorList(transformedVendors);

      setAgencyContacts(agencyContactsResponse.items || []);

      // 載入關聯公文
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
      } catch {
        setRelatedDocs([]);
      }

      // 載入附件
      await loadAttachments(loadedDocs);

    } catch (error) {
      logger.error('載入數據失敗:', error);
      message.error('載入數據失敗');
    } finally {
      setLoading(false);
    }
  };

  const loadAttachments = async (docs: RelatedDocument[]) => {
    setAttachmentsLoading(true);
    try {
      const allAttachments: Attachment[] = [];
      const grouped: LocalGroupedAttachment[] = [];

      for (const doc of docs) {
        try {
          const docAttachments = await filesApi.getDocumentAttachments(doc.id);
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
          logger.warn(`載入公文 ${doc.doc_number} 的附件失敗:`, attError);
        }
      }
      setAttachments(allAttachments);
      setGroupedAttachments(grouped);
    } catch {
      setAttachments([]);
      setGroupedAttachments([]);
    } finally {
      setAttachmentsLoading(false);
    }
  };

  const loadUserOptions = async () => {
    try {
      const response = await usersApi.getUsers({ limit: 100 }) as PaginatedResponse<User>;
      const users = response.items || [];
      setUserOptions(users.map((u) => ({
        id: u.id,
        name: u.full_name || u.username,
        email: u.email,
      })));
    } catch (error) {
      logger.error('載入使用者列表失敗:', error);
    }
  };

  const loadVendorOptions = async () => {
    try {
      const response = await vendorsApi.getVendors({ limit: 100 }) as PaginatedResponse<Vendor>;
      const vendors = response.items || [];
      setVendorOptions(vendors.map((v) => ({
        id: v.id,
        name: v.vendor_name,
        code: v.vendor_code || '',
      })));
    } catch (error) {
      logger.error('載入廠商列表失敗:', error);
    }
  };

  // ============================================================================
  // 事件處理函數
  // ============================================================================

  const handleBack = () => navigate(ROUTES.CONTRACT_CASES);

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

  // 案件資訊保存
  const handleSaveCaseInfo = async (values: CaseInfoFormValues) => {
    if (!data || !id) return;
    const projectId = parseInt(id, 10);

    try {
      const autoProgress = values.status === '已結案' ? 100 : values.progress;
      const startDate = values.date_range?.[0] ? dayjs(values.date_range[0]).format('YYYY-MM-DD') : undefined;
      const endDate = values.date_range?.[1] ? dayjs(values.date_range[1]).format('YYYY-MM-DD') : undefined;

      const updateData = {
        project_name: values.project_name,
        year: values.year,
        client_agency: values.client_agency || undefined,
        contract_doc_number: values.contract_doc_number || undefined,
        project_code: values.project_code || undefined,
        category: values.category || undefined,
        case_nature: values.case_nature || undefined,
        contract_amount: values.contract_amount || undefined,
        winning_amount: values.winning_amount || undefined,
        start_date: startDate,
        end_date: endDate,
        status: values.status || undefined,
        progress: autoProgress ?? undefined,
        project_path: values.project_path || undefined,
        notes: values.notes || undefined,
      };

      await projectsApi.updateProject(projectId, updateData as Parameters<typeof projectsApi.updateProject>[1]);
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });

      setData({ ...data, ...updateData });
      setIsEditingCaseInfo(false);
      message.success('案件資訊已更新');
    } catch (error) {
      logger.error('更新案件資訊失敗:', error);
      const axiosError = error as { response?: { data?: ApiErrorResponse } };
      message.error(axiosError.response?.data?.detail as string || '更新案件資訊失敗');
    }
  };

  // 機關承辦處理
  const handleAgencyContactSubmit = async (values: AgencyContactFormValues) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      if (editingAgencyContactId) {
        await updateAgencyContact(editingAgencyContactId, values);
        message.success('更新成功');
      } else {
        await createAgencyContact({ ...values, project_id: projectId });
        message.success('新增成功');
      }
      setAgencyContactModalVisible(false);
      setEditingAgencyContactId(null);
      agencyContactForm.resetFields();
      loadData();
    } catch {
      message.error('儲存失敗');
    }
  };

  const handleDeleteAgencyContact = async (contactId: number) => {
    try {
      await deleteAgencyContact(contactId);
      message.success('刪除成功');
      loadData();
    } catch {
      message.error('刪除失敗');
    }
  };

  // 同仁處理
  const handleAddStaff = async (values: StaffFormValues) => {
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
    } catch (error) {
      const axiosError = error as { response?: { data?: ApiErrorResponse } };
      const detail = axiosError.response?.data?.detail;
      let errorMsg = '新增承辦同仁失敗';
      if (typeof detail === 'string') {
        errorMsg = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        errorMsg = detail.map((d: PydanticValidationError) => d.msg || d.message || JSON.stringify(d)).join(', ');
      }
      message.error(errorMsg);
    }
  };

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
      setStaffList(staffList.map(s => s.id === staffId ? { ...s, role: newRole } : s));
      setEditingStaffId(null);
      message.success('角色已更新');
    } catch {
      message.error('更新角色失敗');
      setEditingStaffId(null);
    }
  };

  const handleDeleteStaff = async (staffId: number) => {
    if (!id) return;
    const projectId = parseInt(id, 10);
    const staff = staffList.find(s => s.id === staffId);
    if (!staff) return;

    try {
      await projectStaffApi.deleteStaff(projectId, staff.user_id);
      setStaffList(staffList.filter(s => s.id !== staffId));
      message.success('已移除同仁');
    } catch {
      message.error('移除同仁失敗');
    }
  };

  // 廠商處理
  const handleAddVendor = async (values: VendorFormValues) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      const vendorData: {
        project_id: number;
        vendor_id: number;
        role: string;
        status: string;
        contract_amount?: number;
        start_date?: string;
        end_date?: string;
      } = {
        project_id: projectId,
        vendor_id: values.vendor_id,
        role: values.role,
        status: 'active',
      };

      if (values.contract_amount) vendorData.contract_amount = values.contract_amount;
      if (values.start_date) vendorData.start_date = dayjs(values.start_date).format('YYYY-MM-DD');
      if (values.end_date) vendorData.end_date = dayjs(values.end_date).format('YYYY-MM-DD');

      await projectVendorsApi.addVendor(vendorData);

      vendorForm.resetFields();
      setVendorModalVisible(false);
      message.success('新增協力廠商成功');
      loadData();
    } catch {
      message.error('新增協力廠商失敗');
    }
  };

  const handleVendorRoleChange = async (vendorId: number, newRole: string) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      await projectVendorsApi.updateVendor(projectId, vendorId, { role: newRole });
      setVendorList(vendorList.map(v => v.vendor_id === vendorId ? { ...v, role: newRole } : v));
      setEditingVendorId(null);
      message.success('角色已更新');
    } catch {
      message.error('更新角色失敗');
      setEditingVendorId(null);
    }
  };

  const handleDeleteVendor = async (vendorId: number) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      await projectVendorsApi.deleteVendor(projectId, vendorId);
      setVendorList(vendorList.filter(v => v.vendor_id !== vendorId));
      message.success('已移除廠商');
    } catch {
      message.error('移除廠商失敗');
    }
  };

  // 附件處理
  const handleDownloadAttachment = async (attachmentId: number, filename: string) => {
    try {
      await filesApi.downloadAttachment(attachmentId, filename);
    } catch {
      message.error('下載附件失敗');
    }
  };

  const handlePreviewAttachment = async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch {
      message.error(`預覽 ${filename} 失敗`);
    }
  };

  const handleDownloadAllAttachments = async (group: LocalGroupedAttachment) => {
    message.loading({ content: `正在下載 ${group.file_count} 個檔案...`, key: 'download-all' });
    for (const att of group.attachments) {
      try {
        await filesApi.downloadAttachment(att.id, att.filename);
      } catch (error) {
        logger.error(`下載 ${att.filename} 失敗:`, error);
      }
    }
    message.success({ content: '下載完成', key: 'download-all' });
  };

  // ============================================================================
  // 渲染
  // ============================================================================

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

  const tabItems = [
    {
      key: 'info',
      label: <span><InfoCircleOutlined /> 案件資訊</span>,
      children: (
        <CaseInfoTab
          data={data}
          isEditing={isEditingCaseInfo}
          setIsEditing={setIsEditingCaseInfo}
          form={caseInfoForm}
          onSave={handleSaveCaseInfo}
          calculateProgress={calculateProgress}
        />
      ),
    },
    {
      key: 'agency',
      label: <span><BankOutlined /> 機關承辦 <Tag color="blue" style={{ marginLeft: 8 }}>{agencyContacts.length}</Tag></span>,
      children: (
        <AgencyContactTab
          agencyContacts={agencyContacts}
          modalVisible={agencyContactModalVisible}
          setModalVisible={setAgencyContactModalVisible}
          editingId={editingAgencyContactId}
          setEditingId={setEditingAgencyContactId}
          form={agencyContactForm}
          onSubmit={handleAgencyContactSubmit}
          onDelete={handleDeleteAgencyContact}
        />
      ),
    },
    {
      key: 'staff',
      label: <span><TeamOutlined /> 承辦同仁 <Tag color="blue" style={{ marginLeft: 8 }}>{staffList.length}</Tag></span>,
      children: (
        <StaffTab
          staffList={staffList}
          editingStaffId={editingStaffId}
          setEditingStaffId={setEditingStaffId}
          onRoleChange={handleStaffRoleChange}
          onDelete={handleDeleteStaff}
          modalVisible={staffModalVisible}
          setModalVisible={setStaffModalVisible}
          form={staffForm}
          onAddStaff={handleAddStaff}
          userOptions={userOptions}
          loadUserOptions={loadUserOptions}
        />
      ),
    },
    {
      key: 'vendors',
      label: <span><ShopOutlined /> 協力廠商 <Tag color="blue" style={{ marginLeft: 8 }}>{vendorList.length}</Tag></span>,
      children: (
        <VendorsTab
          vendorList={vendorList}
          editingVendorId={editingVendorId}
          setEditingVendorId={setEditingVendorId}
          onRoleChange={handleVendorRoleChange}
          onDelete={handleDeleteVendor}
          modalVisible={vendorModalVisible}
          setModalVisible={setVendorModalVisible}
          form={vendorForm}
          onAddVendor={handleAddVendor}
          vendorOptions={vendorOptions}
          loadVendorOptions={loadVendorOptions}
        />
      ),
    },
    {
      key: 'attachments',
      label: <span><PaperClipOutlined /> 附件紀錄 <Tag color="blue" style={{ marginLeft: 8 }}>{attachments.length}</Tag></span>,
      children: (
        <AttachmentsTab
          attachments={attachments}
          groupedAttachments={groupedAttachments}
          loading={attachmentsLoading}
          onRefresh={loadData}
          onDownload={handleDownloadAttachment}
          onPreview={handlePreviewAttachment}
          onDownloadAll={handleDownloadAllAttachments}
          relatedDocsCount={relatedDocs.length}
        />
      ),
    },
    {
      key: 'documents',
      label: <span><FileTextOutlined /> 關聯公文 <Tag color="blue" style={{ marginLeft: 8 }}>{relatedDocs.length}</Tag></span>,
      children: (
        <RelatedDocumentsTab
          relatedDocs={relatedDocs}
          onRefresh={loadData}
        />
      ),
    },
  ];

  return (
    <div>
      {/* 頁面標題 */}
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
        </div>
      </Card>

      {/* Tab 分頁 */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          size="large"
        />
      </Card>
    </div>
  );
};

export default ContractCaseDetailPage;
