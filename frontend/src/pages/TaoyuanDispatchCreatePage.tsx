/**
 * 桃園派工單新增頁面
 *
 * 導航式新增頁面，提供完整表單讓使用者建立新派工單
 * 使用共用 DispatchFormFields 元件
 *
 * @version 2.0.0 - 重構使用共用表單元件
 * @date 2026-01-29
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ResponsiveContent } from '../components/common';
import {
  Form,
  Button,
  App,
  Card,
  Typography,
  Space,
} from 'antd';
import {
  SendOutlined,
  SaveOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { DispatchFormFields } from '../components/taoyuan/DispatchFormFields';
import { dispatchOrdersApi, taoyuanProjectsApi, contractPaymentsApi } from '../api/taoyuanDispatchApi';
import { documentsApi } from '../api/documentsApi';
import { getProjectAgencyContacts } from '../api/projectAgencyContacts';
import { projectVendorsApi } from '../api/projectVendorsApi';
import type { DispatchOrderCreate, ContractPaymentCreate } from '../types/api';
import { TAOYUAN_CONTRACT } from '../constants/taoyuanOptions';
import { logger } from '../services/logger';

const { Title } = Typography;

export const TaoyuanDispatchCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 公文搜尋狀態
  const [agencyDocSearch, setAgencyDocSearch] = useState('');
  const [companyDocSearch, setCompanyDocSearch] = useState('');

  // =============================================================================
  // 資料查詢
  // =============================================================================

  // 查詢可關聯的工程
  const { data: projectsData } = useQuery({
    queryKey: ['taoyuan-projects-for-dispatch', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () =>
      taoyuanProjectsApi.getList({
        contract_project_id: TAOYUAN_CONTRACT.PROJECT_ID,
        limit: 500,
      }),
  });
  const projects = projectsData?.items ?? [];

  // 查詢機關承辦清單
  const { data: agencyContactsData } = useQuery({
    queryKey: ['agency-contacts', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => getProjectAgencyContacts(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const agencyContacts = agencyContactsData?.items ?? [];

  // 查詢協力廠商清單
  const { data: vendorsData } = useQuery({
    queryKey: ['project-vendors', TAOYUAN_CONTRACT.PROJECT_ID],
    queryFn: () => projectVendorsApi.getProjectVendors(TAOYUAN_CONTRACT.PROJECT_ID),
  });
  const projectVendors = vendorsData?.associations ?? [];

  // 查詢機關函文（收文）
  const { data: agencyDocsData } = useQuery({
    queryKey: ['agency-docs-for-dispatch-create', agencyDocSearch, TAOYUAN_CONTRACT.CODE],
    queryFn: () =>
      documentsApi.getDocuments({
        contract_case: TAOYUAN_CONTRACT.CODE,
        category: 'receive',
        search: agencyDocSearch || undefined,
        limit: 50,
      }),
  });

  // 查詢乾坤函文（發文）
  const { data: companyDocsData } = useQuery({
    queryKey: ['company-docs-for-dispatch-create', companyDocSearch, TAOYUAN_CONTRACT.CODE],
    queryFn: () =>
      documentsApi.getDocuments({
        contract_case: TAOYUAN_CONTRACT.CODE,
        category: 'send',
        search: companyDocSearch || undefined,
        limit: 50,
      }),
  });

  // =============================================================================
  // 選項轉換
  // =============================================================================

  const agencyDocOptions = (agencyDocsData?.items ?? []).map((doc) => ({
    value: doc.id,
    label: `${doc.doc_number || '(無字號)'} - ${doc.subject?.substring(0, 20) || '(無主旨)'}...`,
  }));

  const companyDocOptions = (companyDocsData?.items ?? []).map((doc) => ({
    value: doc.id,
    label: `${doc.doc_number || '(無字號)'} - ${doc.subject?.substring(0, 20) || '(無主旨)'}...`,
  }));

  const projectLinkOptions = projects.map((p) => ({
    value: p.id,
    label: `${p.project_name}${p.district ? ` (${p.district})` : ''}`,
  }));

  // =============================================================================
  // Mutations
  // =============================================================================

  const createMutation = useMutation({
    mutationFn: async (data: DispatchOrderCreate & { paymentData?: Partial<ContractPaymentCreate> }) => {
      const { paymentData, ...dispatchData } = data;
      const result = await dispatchOrdersApi.create(dispatchData);

      // 如果有契金資料，一併建立契金記錄
      if (paymentData && Object.values(paymentData).some((v) => v !== undefined && v !== 0)) {
        const currentAmount =
          (paymentData.work_01_amount || 0) +
          (paymentData.work_02_amount || 0) +
          (paymentData.work_03_amount || 0) +
          (paymentData.work_04_amount || 0) +
          (paymentData.work_05_amount || 0) +
          (paymentData.work_06_amount || 0) +
          (paymentData.work_07_amount || 0);

        if (currentAmount > 0) {
          await contractPaymentsApi.create({
            dispatch_order_id: result.id,
            ...paymentData,
            current_amount: currentAmount,
          } as ContractPaymentCreate);
        }
      }

      return result;
    },
    onSuccess: (result) => {
      message.success('派工單新增成功');
      queryClient.invalidateQueries({ queryKey: ['taoyuan-dispatch-orders'] });
      navigate(`/taoyuan/dispatch/${result.id}`);
    },
    onError: (error: Error) => {
      message.error(error?.message || '新增失敗');
    },
  });

  // =============================================================================
  // Effects
  // =============================================================================

  // 頁面載入時自動獲取下一個派工單號
  useEffect(() => {
    const loadNextDispatchNo = async () => {
      try {
        const result = await dispatchOrdersApi.getNextDispatchNo();
        if (result.success && result.next_dispatch_no) {
          form.setFieldsValue({
            dispatch_no: result.next_dispatch_no,
          });
        }
      } catch (error) {
        logger.error('載入派工單號失敗:', error);
      }
    };
    loadNextDispatchNo();
  }, [form]);

  // =============================================================================
  // Handlers
  // =============================================================================

  // 選擇工程時自動加入關聯
  const handleProjectSelect = (projectId: number) => {
    const currentLinked = form.getFieldValue('linked_project_ids') || [];
    if (!currentLinked.includes(projectId)) {
      form.setFieldsValue({
        linked_project_ids: [...currentLinked, projectId],
      });
      message.info('已自動加入工程關聯');
    }
  };

  // 儲存
  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      // 收集契金資料
      const paymentData: Partial<ContractPaymentCreate> = {
        work_01_amount: values.work_01_amount || undefined,
        work_02_amount: values.work_02_amount || undefined,
        work_03_amount: values.work_03_amount || undefined,
        work_04_amount: values.work_04_amount || undefined,
        work_05_amount: values.work_05_amount || undefined,
        work_06_amount: values.work_06_amount || undefined,
        work_07_amount: values.work_07_amount || undefined,
      };

      // work_type 轉換：陣列轉逗號分隔字串
      const workTypeString = Array.isArray(values.work_type)
        ? values.work_type.join(', ')
        : values.work_type || '';

      const data = {
        dispatch_no: values.dispatch_no,
        contract_project_id: TAOYUAN_CONTRACT.PROJECT_ID,
        project_name: values.project_name,
        work_type: workTypeString,
        sub_case_name: values.sub_case_name,
        deadline: values.deadline,
        case_handler: values.case_handler,
        survey_unit: values.survey_unit,
        cloud_folder: values.cloud_folder,
        project_folder: values.project_folder,
        contact_note: values.contact_note,
        agency_doc_id: values.agency_doc_id || undefined,
        company_doc_id: values.company_doc_id || undefined,
        linked_project_ids: values.linked_project_ids || [],
        paymentData,
      };
      createMutation.mutate(data);
    } catch {
      message.error('請檢查表單欄位');
    }
  };

  const handleCancel = () => {
    navigate('/taoyuan/dispatch');
  };

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      {/* Header */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={handleCancel}>
              返回
            </Button>
            <Title level={4} style={{ margin: 0 }}>
              <SendOutlined /> 新增派工單
            </Title>
          </Space>
          <Space>
            <Button onClick={handleCancel}>取消</Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={createMutation.isPending}
              disabled={createMutation.isPending}
              onClick={handleSave}
            >
              儲存
            </Button>
          </Space>
        </div>
      </Card>

      {/* 表單內容 - 使用共用元件 */}
      <Card>
        <Form form={form} layout="vertical">
          <DispatchFormFields
            form={form}
            mode="create"
            availableProjects={projects}
            agencyContacts={agencyContacts}
            projectVendors={projectVendors}
            onProjectSelect={handleProjectSelect}
            showPaymentFields={true}
            showDocLinkFields={true}
            agencyDocOptions={agencyDocOptions}
            companyDocOptions={companyDocOptions}
            onAgencyDocSearch={setAgencyDocSearch}
            onCompanyDocSearch={setCompanyDocSearch}
            showProjectLinkFields={true}
            projectLinkOptions={projectLinkOptions}
          />
        </Form>
      </Card>
    </ResponsiveContent>
  );
};

export default TaoyuanDispatchCreatePage;
