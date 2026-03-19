import { useQuery, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '../../api/projectsApi';
import { usersApi } from '../../api/usersApi';
import { vendorsApi } from '../../api/vendorsApi';
import { documentsApi } from '../../api/documentsApi';
import { filesApi, type FileAttachment } from '../../api/filesApi';
import { projectStaffApi, type ProjectStaff } from '../../api/projectStaffApi';
import { projectVendorsApi, type ProjectVendor } from '../../api/projectVendorsApi';
import { getProjectAgencyContacts } from '../../api/projectAgencyContacts';
import { logger } from '../../utils/logger';
import type { User, Vendor } from '../../types/api';
import type { PaginatedResponse } from '../../api/types';
import type { ProjectAgencyContact } from '../../api/projectAgencyContacts';

import type {
  ProjectData,
  RelatedDocument,
  Attachment,
  LocalGroupedAttachment,
  VendorAssociation,
  Staff,
} from './tabs';

export function useContractCaseData(projectId: number | undefined) {
  const queryClient = useQueryClient();

  const { data: coreData, isLoading: coreLoading } = useQuery({
    queryKey: ['contract-case-detail', projectId],
    queryFn: async () => {
      const pid = projectId!;
      const [projectResponse, staffResponse, vendorsResponse, agencyContactsResponse] = await Promise.all([
        projectsApi.getProject(pid),
        projectStaffApi.getProjectStaff(pid).catch(() => ({ staff: [], total: 0, project_id: pid, project_name: '' })),
        projectVendorsApi.getProjectVendors(pid).catch(() => ({ associations: [], total: 0, project_id: pid, project_name: '' })),
        getProjectAgencyContacts(pid).catch(() => ({ items: [], total: 0 })),
      ]);

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

      return {
        project: projectResponse as ProjectData,
        staffList: transformedStaff,
        vendorList: transformedVendors,
        agencyContacts: (agencyContactsResponse.items || []) as ProjectAgencyContact[],
      };
    },
    enabled: !!projectId,
  });

  const { data: relatedDocsData } = useQuery({
    queryKey: ['contract-case-docs', projectId],
    queryFn: async () => {
      const docsResponse = await documentsApi.getDocumentsByProject(projectId!);
      return docsResponse.items.map(doc => ({
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
      })) as RelatedDocument[];
    },
    enabled: !!projectId,
  });

  const relatedDocs = relatedDocsData ?? [];

  const { data: attachmentData, isLoading: attachmentsLoading } = useQuery({
    queryKey: ['contract-case-attachments', projectId, relatedDocs.map(d => d.id)],
    queryFn: async () => {
      const docs = relatedDocs;
      if (docs.length === 0) return { attachments: [] as Attachment[], grouped: [] as LocalGroupedAttachment[] };

      const BATCH_SIZE = 5;
      const results: { doc: RelatedDocument; attachments: FileAttachment[] }[] = [];

      for (let i = 0; i < docs.length; i += BATCH_SIZE) {
        const batch = docs.slice(i, i + BATCH_SIZE);
        const batchResults = await Promise.all(
          batch.map(async (doc) => {
            try {
              const atts = await filesApi.getDocumentAttachments(doc.id);
              return { doc, attachments: atts };
            } catch {
              logger.warn(`載入公文 ${doc.doc_number} 的附件失敗`);
              return { doc, attachments: [] as FileAttachment[] };
            }
          })
        );
        results.push(...batchResults);
      }

      const allAttachments: Attachment[] = [];
      const grouped: LocalGroupedAttachment[] = [];

      for (const { doc, attachments: docAttachments } of results) {
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
      }
      return { attachments: allAttachments, grouped };
    },
    enabled: !!projectId && relatedDocs.length > 0,
  });

  const { data: userOptions = [] } = useQuery({
    queryKey: ['contract-case-user-options'],
    queryFn: async () => {
      const response = await usersApi.getUsers({ limit: 100 }) as PaginatedResponse<User>;
      const users = response.items || [];
      return users.map((u) => ({
        id: u.id,
        name: u.full_name || u.username,
        email: u.email,
      }));
    },
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const { data: vendorOptions = [] } = useQuery({
    queryKey: ['contract-case-vendor-options'],
    queryFn: async () => {
      const response = await vendorsApi.getVendors({ limit: 100 }) as PaginatedResponse<Vendor>;
      const vendors = response.items || [];
      return vendors.map((v) => ({
        id: v.id,
        name: v.vendor_name,
        code: v.vendor_code || '',
      }));
    },
    staleTime: 10 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const data = coreData?.project ?? null;
  const staffList = coreData?.staffList ?? [];
  const vendorList = coreData?.vendorList ?? [];
  const agencyContacts = coreData?.agencyContacts ?? [];
  const loading = coreLoading;
  const attachments = attachmentData?.attachments ?? [];
  const groupedAttachments = attachmentData?.grouped ?? [];

  const reloadData = () => {
    queryClient.invalidateQueries({ queryKey: ['contract-case-detail', projectId] });
    queryClient.invalidateQueries({ queryKey: ['contract-case-docs', projectId] });
    queryClient.invalidateQueries({ queryKey: ['contract-case-attachments', projectId] });
  };

  return {
    data,
    staffList,
    vendorList,
    agencyContacts,
    relatedDocs,
    attachments,
    groupedAttachments,
    attachmentsLoading,
    loading,
    userOptions,
    vendorOptions,
    reloadData,
    queryClient,
  };
}
