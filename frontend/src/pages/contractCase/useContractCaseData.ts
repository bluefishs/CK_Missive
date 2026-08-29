import { useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '../../api/projectsApi';
import { documentsApi } from '../../api/documentsApi';
import { filesApi, type FileAttachment } from '../../api/filesApi';
import { projectStaffApi, type ProjectStaff } from '../../api/projectStaffApi';
import { projectVendorsApi, type ProjectVendor } from '../../api/projectVendorsApi';
import { getProjectAgencyContacts } from '../../api/projectAgencyContacts';
import { logger } from '../../utils/logger';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import type { ProjectAgencyContact } from '../../api/projectAgencyContacts';

import { filterAssignableUsers, userDisplayName } from '../../utils/assignableUsers';
import { useUsersDropdown, useSubcontractorOptions } from '../../hooks/business/useDropdownData';

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

  // 人員清單改用共用的 `useUsersDropdown`（queryKey `users-dropdown`）。
  //
  // ⚠️ 2026-08-27 —— 這裡原本自己開一支 `contract-case-user-options`，
  //    **與 ContractCaseStaffFormPage 用同一個 key，而兩支的 queryFn 回傳形狀不同**：
  //
  //      詳情頁（這裡） → [{ id, name, email }]        ← 已 map 過
  //      新增同仁頁     → response.items = User[]      ← 原始欄位
  //
  //    共用 key ⇒ 誰先載入誰就決定快取內容。使用者的動線正是
  //    「詳情頁 → 新增承辦同仁」，於是 create 頁拿到的是 `{id,name,email}`，
  //    而它會對每一筆做 `full_name || username || '#'+id` ——
  //    那三個欄位在這個形狀裡都不存在 ⇒ **label 全變成 `#3`、`#13`**，
  //    也就是 owner 反覆回報的「只顯示代號無姓名」。
  //
  //    2026-08-20 修的是「兩處資料源不同」（都改打 assignable），源確實對齊了，
  //    **但形狀沒有對齊**，所以症狀原封不動。而它只在那一條動線上出現：
  //    直接開 create 頁的網址是正常的 —— 這就是它被修過還能反覆回報的原因。
  //
  //    `queryKey_drift_audit` 抓不到，因為它的座標系裡只有「資料源」沒有「回傳形狀」。
  //
  //    治法不是再對齊一次形狀（那是第三次對齊同一件事），是**讓它只有一份**：
  //    共用 hook ⇒ 一個 queryFn、一種形狀，結構上不可能再分岔。
  //    另外四個人員下拉（資產保管人／PM 承辦／公文承辦／文件操作）本來就用它。
  const { users: assignableUsers } = useUsersDropdown();
  const userOptions = useMemo(
    // 排除已合併的分身帳號（ADR-0025）—— 見 utils/assignableUsers
    () => filterAssignableUsers(assignableUsers).map((u) => ({
      id: u.id,
      name: userDisplayName(u),
      email: u.email,
    })),
    [assignableUsers],
  );

  // ⚠️ 2026-08-27 —— 與人員清單**完全相同的問題**，只是換成協力廠商。
  //    這裡與 `ContractCaseVendorFormPage` 共用 `contract-case-vendor-options`，
  //    而兩支 queryFn 的回傳形狀不同：
  //
  //      詳情頁（這裡）       → { id, name, code }
  //      新增協力廠商頁       → { value, label }     ← AntD Select 要的形狀
  //
  //    那一頁的註解寫著「廠商清單沿用詳情頁本來就在用的那支與查詢鍵」——
  //    **它以為自己在共用，但形狀不一樣**。動線「詳情頁 → 新增協力廠商」
  //    會讓 Select 拿到 `{id,name,code}`，`value`／`label` 雙雙 undefined。
  //
  //    同樣改用既有的共用 hook（回原始 `Vendor[]`），呈現形狀留在各自的消費端。
  const { subcontractors } = useSubcontractorOptions();
  const vendorOptions = useMemo(
    () => subcontractors.map((v) => ({
      id: v.id,
      name: v.vendor_name,
      code: v.vendor_code || '',
    })),
    [subcontractors],
  );

  const data = coreData?.project ?? null;
  const staffList = coreData?.staffList ?? [];
  const vendorList = coreData?.vendorList ?? [];
  const agencyContacts = coreData?.agencyContacts ?? [];
  const loading = coreLoading;
  // 案件本身的附件（`pm_case_attachments`，以 case_code 關聯）。
  //
  // ⚠️ 2026-08-29：這一段原本不存在，於是分頁徽章寫「附件紀錄 0」
  // 而**面板裡就擺著 1 個檔案** —— 徽章只數了關聯公文的附件。
  // 實測 `/contract-cases/284`：徽章 0、內容「案件附件 (1) 報價單_B115-A007-1.pdf」。
  //
  // queryKey 與 `AttachmentPanel` **刻意相同** ⇒ 共用快取、不多發一次請求，
  // 且面板上傳後 invalidate 這個 key 時徽章會一起更新
  // （queryKey drift 讓 invalidate 靜靜失效是本專案記過的 L39）。
  const { data: caseAttachmentData } = useQuery({
    queryKey: ['pm-case-attachments', data?.case_code],
    queryFn: () => apiClient.post<{ attachments?: unknown[] }>(
      API_ENDPOINTS.PM.ATTACHMENTS_LIST(data!.case_code!),
    ),
    enabled: !!data?.case_code,
  });
  const caseAttachmentCount = caseAttachmentData?.attachments?.length ?? 0;

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
    caseAttachmentCount,
    loading,
    userOptions,
    vendorOptions,
    reloadData,
    queryClient,
  };
}
