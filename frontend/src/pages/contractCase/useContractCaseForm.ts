/**
 * Contract Case Form Hook
 *
 * Manages form state, data loading, and submission for contract case create/edit.
 */

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Form, App } from 'antd';
import dayjs from 'dayjs';
import { logger } from '../../utils/logger';
import { ROUTES } from '../../router/types';
import { useResponsive } from '../../hooks';
import { queryKeys } from '../../config/queryConfig';
import { projectsApi } from '../../api/projectsApi';
import { agenciesApi } from '../../api/agenciesApi';
import { vendorsApi } from '../../api/vendorsApi';
import { usersApi } from '../../api/usersApi';

export interface ContractCaseFormValues {
  project_name: string;
  year?: number;
  client_agency?: string;
  client_type?: 'agency' | 'vendor' | 'other';
  category?: string;
  case_nature?: string;
  status?: 'pending' | 'in_progress' | 'completed' | 'suspended';
  contract_doc_number?: string;
  contract_amount?: number;
  winning_amount?: number;
  contract_period?: [{ format: (fmt: string) => string }, { format: (fmt: string) => string }];
  progress?: number;
  project_path?: string;
  notes?: string;
  description?: string;
  has_dispatch_management?: boolean;
}

export const CLIENT_TYPE_OPTIONS = [
  { value: 'agency', label: '機關' },
  { value: 'vendor', label: '廠商' },
  { value: 'other', label: '其他' },
];

export function useContractCaseForm() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [addAgencyModalVisible, setAddAgencyModalVisible] = useState(false);
  const [addAgencySubmitting, setAddAgencySubmitting] = useState(false);
  const { isMobile } = useResponsive();

  const isEdit = Boolean(id);
  const title = isEdit ? '編輯承攬案件' : '新增承攬案件';

  const { data: optionsData, isLoading: optionsLoading } = useQuery({
    queryKey: ['contract-case-form-options'],
    queryFn: async () => {
      const [agencies, vendors, users] = await Promise.all([
        agenciesApi.getAgencyOptions(),
        vendorsApi.getVendorOptions(),
        usersApi.getUserOptions(true),
      ]);
      return { agencies, vendors, users };
    },
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const agencyOptions = optionsData?.agencies ?? [];
  const vendorOptions = optionsData?.vendors ?? [];
  const _userOptions = optionsData?.users ?? [];
  void _userOptions;

  const { isLoading: loading } = useQuery({
    queryKey: ['contract-case-form-data', id],
    queryFn: async () => {
      const data = await projectsApi.getProject(parseInt(id!, 10));
      form.setFieldsValue({
        project_name: data.project_name,
        year: data.year,
        client_agency: data.client_agency,
        client_type: data.client_type ?? 'agency',
        category: data.category,
        case_nature: data.case_nature,
        status: data.status,
        contract_doc_number: data.contract_doc_number,
        contract_amount: data.contract_amount,
        winning_amount: data.winning_amount,
        contract_period: (data.start_date && data.end_date)
          ? [dayjs(data.start_date), dayjs(data.end_date)]
          : undefined,
        progress: data.progress,
        project_path: data.project_path,
        notes: data.notes,
        description: data.description,
        has_dispatch_management: data.has_dispatch_management ?? false,
      });
      return data;
    },
    enabled: isEdit && !!id,
    refetchOnWindowFocus: false,
  });

  const handleSubmit = async (values: ContractCaseFormValues) => {
    setSubmitting(true);
    try {
      const contractPeriod = values.contract_period;
      const startDate = contractPeriod?.[0];
      const endDate = contractPeriod?.[1];
      const submitData = {
        project_name: values.project_name,
        year: values.year,
        client_agency: values.client_agency,
        client_type: values.client_type,
        category: values.category,
        case_nature: values.case_nature,
        status: values.status,
        contract_doc_number: values.contract_doc_number,
        contract_amount: values.contract_amount,
        winning_amount: values.winning_amount,
        start_date: startDate ? startDate.format('YYYY-MM-DD') : undefined,
        end_date: endDate ? endDate.format('YYYY-MM-DD') : undefined,
        progress: values.progress,
        project_path: values.project_path,
        notes: values.notes,
        description: values.description,
        has_dispatch_management: values.has_dispatch_management,
      };

      logger.debug('Submitting data:', submitData);

      if (isEdit && id) {
        await projectsApi.updateProject(parseInt(id, 10), submitData);
        queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        queryClient.invalidateQueries({ queryKey: ['taoyuan-dispatch-orders', 'contract-projects'] });
        message.success('更新成功');
      } else {
        const result = await projectsApi.createProject(submitData);
        queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        queryClient.invalidateQueries({ queryKey: ['taoyuan-dispatch-orders', 'contract-projects'] });
        message.success('新增成功');
        navigate(`${ROUTES.CONTRACT_CASES}/${result.id}`);
        return;
      }
      navigate(ROUTES.CONTRACT_CASES);
    } catch (error: unknown) {
      logger.error('提交失敗:', error);
      const errorMsg = error instanceof Error ? error.message : '操作失敗';
      message.error(isEdit ? `更新失敗: ${errorMsg}` : `新增失敗: ${errorMsg}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleBack = () => {
    navigate(ROUTES.CONTRACT_CASES);
  };

  const generateYearOptions = () => {
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let i = currentYear - 2; i <= currentYear + 2; i++) {
      years.push(i.toString());
    }
    return years;
  };

  const handleAddAgencySubmit = async (values: { agency_name: string; agency_short_name?: string; agency_type?: string }) => {
    const exactMatch = agencyOptions.find(
      (a) => a.agency_name.toLowerCase() === values.agency_name.toLowerCase()
    );
    if (exactMatch) {
      message.error(`機關「${exactMatch.agency_name}」已存在，請直接選擇`);
      return;
    }

    setAddAgencySubmitting(true);
    try {
      const newAgency = await agenciesApi.createAgency({
        agency_name: values.agency_name,
        agency_short_name: values.agency_short_name || undefined,
        agency_type: values.agency_type || '政府機關',
      });

      message.success(`機關「${newAgency.agency_name}」建立成功`);
      queryClient.invalidateQueries({ queryKey: queryKeys.agencies.all });
      queryClient.invalidateQueries({ queryKey: ['contract-case-form-options'] });
      form.setFieldValue('client_agency', newAgency.agency_name);
      setAddAgencyModalVisible(false);
    } catch (error: unknown) {
      logger.error('新增機關失敗:', error);
      const errorMsg = error instanceof Error ? error.message : '新增失敗';
      message.error(`新增機關失敗: ${errorMsg}`);
    } finally {
      setAddAgencySubmitting(false);
    }
  };

  return {
    form,
    isEdit,
    title,
    isMobile,
    loading,
    optionsLoading,
    submitting,
    agencyOptions,
    vendorOptions,
    addAgencyModalVisible,
    setAddAgencyModalVisible,
    addAgencySubmitting,
    handleSubmit,
    handleBack,
    generateYearOptions,
    handleAddAgencySubmit,
  };
}
