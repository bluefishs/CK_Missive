import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { MessageInstance } from 'antd/es/message/interface';
import type { NavigateFunction } from 'react-router-dom';
import type { FormInstance } from 'antd';
import type { UploadFile } from 'antd/es/upload';
import type {
  DispatchOrder,
  DispatchOrderUpdate,
  ContractPayment,
  ContractPaymentCreate,
} from '../../types/api';
import {
  dispatchOrdersApi,
  taoyuanProjectsApi,
  projectLinksApi,
  dispatchAttachmentsApi,
  contractPaymentsApi,
} from '../../api/taoyuanDispatchApi';
import { queryKeys } from '../../config/queryConfig';
import { TAOYUAN_CONTRACT } from '../../constants/taoyuanOptions';
import { logger } from '../../services/logger';

interface LinkedProjectItem {
  link_id: number;
  project_id: number;
  id?: number;
}

interface UseDispatchMutationsParams {
  id: string | undefined;
  form: FormInstance;
  message: MessageInstance;
  navigate: NavigateFunction;
  dispatch: DispatchOrder | undefined;
  paymentData: ContractPayment | null | undefined;
  refetch: () => void;
  refetchPayment: () => void;
  refetchAttachments: () => void;
  setIsEditing: (editing: boolean) => void;
  fileList: UploadFile[];
  setFileList: (files: UploadFile[]) => void;
  setUploading: (uploading: boolean) => void;
  setUploadProgress: (progress: number) => void;
  setUploadErrors: (errors: string[]) => void;
  setSelectedProjectId: (id: number | undefined) => void;
}

export function useDispatchMutations({
  id,
  form,
  message,
  navigate,
  dispatch,
  paymentData,
  refetch,
  refetchPayment,
  refetchAttachments,
  setIsEditing,
  fileList,
  setFileList,
  setUploading,
  setUploadProgress,
  setUploadErrors,
  setSelectedProjectId,
}: UseDispatchMutationsParams) {
  const queryClient = useQueryClient();
  const dispatchId = parseInt(id || '0', 10);

  const paymentMutation = useMutation({
    mutationFn: async (values: ContractPaymentCreate) => {
      const existingId = paymentData?.id;
      if (existingId) {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { dispatch_order_id: _dispatch_order_id, ...updateData } = values;
        return contractPaymentsApi.update(existingId, updateData);
      } else {
        return contractPaymentsApi.create(values);
      }
    },
    onSuccess: () => {
      message.success('契金紀錄儲存成功');
      refetchPayment();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanPayments.all });
    },
    onError: (error: Error) => {
      logger.error('[paymentMutation] 契金儲存失敗:', error);
      message.error('契金儲存失敗，請重新編輯');
      refetchPayment();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: DispatchOrderUpdate) =>
      dispatchOrdersApi.update(dispatchId, data),
    onSuccess: () => {
      message.success('派工單更新成功');
      refetch();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      setIsEditing(false);
    },
    onError: () => message.error('更新失敗'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => dispatchOrdersApi.delete(dispatchId),
    onSuccess: () => {
      message.success('派工單刪除成功');
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      navigate('/taoyuan/dispatch');
    },
    onError: () => message.error('刪除失敗'),
  });

  const linkProjectMutation = useMutation({
    mutationFn: (projectId: number) =>
      projectLinksApi.linkDispatch(projectId, dispatchId),
    onSuccess: (data) => {
      message.success('工程關聯成功');
      if (data.auto_sync && data.auto_sync.auto_linked_count > 0) {
        message.info(`已自動同步 ${data.auto_sync.auto_linked_count} 個公文的工程關聯`);
      }
      setSelectedProjectId(undefined);
      refetch();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanProjects.all });
      queryClient.invalidateQueries({ queryKey: ['document-project-links'] });
    },
    onError: () => message.error('關聯失敗'),
  });

  const createProjectMutation = useMutation({
    mutationFn: (projectName: string) =>
      taoyuanProjectsApi.create({
        project_name: projectName,
        contract_project_id: dispatch?.contract_project_id || TAOYUAN_CONTRACT.PROJECT_ID,
      }),
    onSuccess: (newProject) => {
      message.success(`工程「${newProject.project_name}」建立成功`);
      queryClient.invalidateQueries({ queryKey: ['taoyuan-projects-for-dispatch-link'] });
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanProjects.all });
      form.setFieldsValue({ project_name: newProject.project_name });
      linkProjectMutation.mutate(newProject.id);
    },
    onError: (error: Error) => {
      message.error(`建立工程失敗: ${error.message}`);
    },
  });

  const unlinkProjectMutation = useMutation({
    mutationFn: (linkId: number) => {
      if (linkId === undefined || linkId === null) {
        logger.error('[unlinkProjectMutation] linkId 無效:', linkId);
        return Promise.reject(new Error('關聯 ID 無效'));
      }

      const linkedProjects: LinkedProjectItem[] = (dispatch?.linked_projects || []) as LinkedProjectItem[];
      const targetProject = linkedProjects.find((p) => p.link_id === linkId);
      if (!targetProject) {
        logger.error('[unlinkProjectMutation] 找不到 link_id:', linkId);
        return Promise.reject(new Error('找不到關聯工程，請重新整理頁面'));
      }

      const projectId = targetProject.project_id ?? targetProject.id;
      if (!projectId) {
        logger.error('[unlinkProjectMutation] project_id 無效:', targetProject);
        return Promise.reject(new Error('工程 ID 無效，請重新整理頁面'));
      }

      return projectLinksApi.unlinkDispatch(projectId, linkId);
    },
    onSuccess: () => {
      message.success('已移除工程關聯');
      refetch();
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanDispatch.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.taoyuanProjects.all });
    },
    onError: (error: Error) => {
      message.error(`移除關聯失敗: ${error.message}`);
      refetch();
    },
  });

  const uploadAttachmentsMutation = useMutation({
    mutationFn: async () => {
      if (fileList.length === 0) return;
      const files = fileList
        .map((f) => f.originFileObj as File | undefined)
        .filter((f): f is File => f !== undefined);
      if (files.length === 0) return;
      setUploading(true);
      setUploadProgress(0);
      return dispatchAttachmentsApi.uploadFiles(
        dispatchId,
        files,
        (percent) => setUploadProgress(percent)
      );
    },
    onSuccess: (result) => {
      setUploading(false);
      setFileList([]);
      setUploadProgress(0);
      if (result) {
        const successCount = result.files?.length ?? 0;
        const errorCount = result.errors?.length ?? 0;
        if (errorCount > 0) {
          setUploadErrors(result.errors || []);
          message.warning(`上傳完成：${successCount} 成功，${errorCount} 失敗`);
        } else {
          message.success(`成功上傳 ${successCount} 個檔案`);
        }
      }
      refetchAttachments();
    },
    onError: (error: Error) => {
      setUploading(false);
      setUploadProgress(0);
      message.error(`上傳失敗: ${error.message}`);
    },
  });

  const deleteAttachmentMutation = useMutation({
    mutationFn: (attachmentId: number) =>
      dispatchAttachmentsApi.deleteAttachment(attachmentId),
    onSuccess: () => {
      message.success('附件刪除成功');
      refetchAttachments();
    },
    onError: () => message.error('刪除失敗'),
  });

  return {
    paymentMutation,
    updateMutation,
    deleteMutation,
    linkProjectMutation,
    createProjectMutation,
    unlinkProjectMutation,
    uploadAttachmentsMutation,
    deleteAttachmentMutation,
  };
}
