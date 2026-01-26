/**
 * 公文詳情頁面 Tab 元件類型定義
 *
 * @version 1.0.0
 * @date 2026-01-23
 */

import type { FormInstance } from 'antd';
import type { Document } from '../../../types';
import type {
  DocumentDispatchLink,
  DocumentProjectLink,
  DispatchOrder,
  TaoyuanProject,
  Project,
  User,
  ProjectStaff,
  DocumentAttachment,
} from '../../../types/api';
import type { UploadFile } from 'antd/es/upload'
import type { ProjectAgencyContact } from '../../../api/projectAgencyContacts';
import type { ProjectVendor } from '../../../api/projectVendorsApi';

/** 共用 Tab Props */
export interface BaseTabProps {
  form: FormInstance;
  document: Document | null;
  isEditing: boolean;
}

/** 公文資訊 Tab Props */
export interface DocumentInfoTabProps extends BaseTabProps {}

/** 日期狀態 Tab Props */
export interface DocumentDateStatusTabProps extends BaseTabProps {}

/** 承案人資 Tab Props */
export interface DocumentCaseStaffTabProps extends BaseTabProps {
  cases: Project[];
  casesLoading: boolean;
  users: User[];
  usersLoading: boolean;
  projectStaffMap: Record<number, ProjectStaff[]>;
  staffLoading: boolean;
  selectedContractProjectId: number | null;
  currentAssigneeValues: string[];
  onProjectChange: (projectId: number | null | undefined) => Promise<void>;
}

/** 附件紀錄 Tab Props */
export interface DocumentAttachmentsTabProps {
  documentId: number | null;
  isEditing: boolean;
  attachments: DocumentAttachment[];
  attachmentsLoading: boolean;
  fileList: UploadFile[];
  setFileList: (files: UploadFile[]) => void;
  uploading: boolean;
  uploadProgress: number;
  uploadErrors: string[];
  setUploadErrors: (errors: string[]) => void;
  fileSettings: {
    allowedExtensions: string[];
    maxFileSizeMB: number;
  };
  onDownload: (attachmentId: number, filename: string) => Promise<void>;
  onPreview: (attachmentId: number, filename: string) => Promise<void>;
  onDelete: (attachmentId: number) => Promise<void>;
}

/** 派工安排 Tab Props */
export interface DocumentDispatchTabProps {
  documentId: number | null;
  document: Document | null;
  isEditing: boolean;
  dispatchLinks: DocumentDispatchLink[];
  dispatchLinksLoading: boolean;
  dispatchForm: FormInstance;
  agencyContacts: ProjectAgencyContact[];
  projectVendors: ProjectVendor[];
  availableDispatches: DispatchOrder[];
  onCreateDispatch: () => Promise<void>;
  onLinkDispatch: (dispatchId: number) => Promise<void>;
  onUnlinkDispatch: (linkId: number) => Promise<void>;
  onRefresh: () => Promise<void>;
}

/** 工程關聯 Tab Props */
export interface DocumentProjectLinkTabProps {
  documentId: number | null;
  document: Document | null;
  isEditing: boolean;
  projectLinks: DocumentProjectLink[];
  projectLinksLoading: boolean;
  availableProjects: TaoyuanProject[];
  onLinkProject: (projectId: number) => Promise<void>;
  onUnlinkProject: (linkId: number) => Promise<void>;
  onRefresh: () => Promise<void>;
}
