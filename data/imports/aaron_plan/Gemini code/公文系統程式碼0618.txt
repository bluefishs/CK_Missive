<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CK 公文管理系統 V8.0</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
    <style>
        :root {
            --sidebar-width-full: 250px;
            --sidebar-width-collapsed: 80px;
        }
        html, body {
            overflow-x: hidden;
        }
        body {
            font-family: 'Inter', '微軟正黑體', 'Microsoft JhengHei', sans-serif;
            background-color: #f0f2f5;
        }
        /* --- Drawer / Sidebar Styles --- */
        .sidebar {
            width: var(--sidebar-width-full);
            transition: width 0.3s ease-in-out, transform 0.3s ease-in-out;
            flex-shrink: 0;
            position: fixed;
            left: 0;
            top: 0;
            height: 100%;
            z-index: 40;
            overflow-x: hidden;
        }
        .sidebar .nav-text {
            transition: opacity 0.2s;
        }
        .main-content {
            transition: margin-left 0.3s ease-in-out;
            width: 100%;
        }
        .sidebar-backdrop {
            position: fixed;
            inset: 0;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 30;
            transition: opacity 0.3s ease-in-out;
        }

        /* Mobile-first: Drawer is hidden by default */
        .sidebar {
             transform: translateX(calc(-1 * var(--sidebar-width-full)));
        }
        .sidebar-backdrop {
            opacity: 0;
            pointer-events: none;
        }
        
        /* When sidebar is open on mobile */
        #app-container.sidebar-open .sidebar {
            transform: translateX(0);
        }
        #app-container.sidebar-open .sidebar-backdrop {
            opacity: 1;
            pointer-events: auto;
        }

        /* Desktop: Sidebar is visible by default */
        @media (min-width: 1024px) {
            .sidebar {
                transform: translateX(0);
            }
            .sidebar .nav-link {
                justify-content: flex-start;
            }
            .sidebar .nav-text {
                opacity: 1;
            }
            .sidebar .nav-link .lucide {
                width: 1.25em; height: 1.25em;
            }
            .main-content {
                margin-left: var(--sidebar-width-full);
                width: calc(100% - var(--sidebar-width-full));
            }
            .sidebar-backdrop {
                display: none;
            }
            /* When sidebar is collapsed on desktop */
            #app-container.sidebar-collapsed .sidebar {
                width: var(--sidebar-width-collapsed);
            }
            #app-container.sidebar-collapsed .sidebar .nav-text, 
            #app-container.sidebar-collapsed .sidebar .sidebar-brand-text {
                opacity: 0;
                width: 0;
                pointer-events: none;
            }
             #app-container.sidebar-collapsed .sidebar .nav-link {
                justify-content: center;
            }
            #app-container.sidebar-collapsed .sidebar .nav-link .lucide {
                margin-right: 0;
                width: 1.5em; /* Larger icons when collapsed */
                height: 1.5em;
            }
            #app-container.sidebar-collapsed .main-content {
                margin-left: var(--sidebar-width-collapsed);
                width: calc(100% - var(--sidebar-width-collapsed));
            }
        }

        /* --- Other Styles --- */
        .modal { background-color: rgba(0, 0, 0, 0.5); }
        .table-container { max-height: 60vh; overflow-y: auto; }
        .table-container thead th { position: sticky; top: 0; z-index: 10; background-color: #f3f4f6; }
        .lucide { pointer-events: none; }
        .icon-btn { padding: 0.25rem; }
        .tab-btn { padding: 8px 16px; border-bottom: 2px solid transparent; transition: all 0.2s; white-space: nowrap; }
        .tab-btn.active { border-color: #3b82f6; color: #3b82f6; font-weight: 600; }
        .sortable-header { cursor: pointer; user-select: none; }
        .sortable-header:hover { background-color: #e5e7eb; }
        .sort-icon { opacity: 0.5; transition: opacity 0.2s; }
        .sortable-header.sorted .sort-icon { opacity: 1; }
    </style>
</head>
<body class="text-gray-800">

    <div id="app-container">
        <div id="sidebar-backdrop" class="sidebar-backdrop"></div>
        <aside class="sidebar bg-white text-gray-800 shadow-lg flex flex-col">
            <div class="p-4 border-b border-gray-200 flex justify-between items-center h-16">
                <h1 class="text-2xl font-bold text-blue-600 flex items-center overflow-hidden">
                    <i data-lucide="file-archive" class="mr-2 flex-shrink-0"></i> 
                    <span class="sidebar-brand-text whitespace-nowrap">CK公文系統</span>
                </h1>
                <button id="sidebar-close" class="p-1 rounded-md hover:bg-gray-200 lg:hidden">
                    <i data-lucide="x" style="width:1.5em; height:1.5em"></i>
                </button>
            </div>
            <nav class="flex-grow p-4 space-y-2">
                <a href="#documents" class="nav-link flex items-center px-4 py-2 rounded-lg hover:bg-blue-100 transition-colors">
                    <i data-lucide="inbox" class="mr-3"></i> <span class="nav-text">公文總表</span>
                </a>
                <a href="#cases" class="nav-link flex items-center px-4 py-2 rounded-lg hover:bg-blue-100 transition-colors">
                    <i data-lucide="briefcase" class="mr-3"></i> <span class="nav-text">承攬案件</span>
                </a>
                <a href="#doc-number" class="nav-link flex items-center px-4 py-2 rounded-lg hover:bg-blue-100 transition-colors">
                    <i data-lucide="wand-2" class="mr-3"></i> <span class="nav-text">公文取號</span>
                </a>
                <a href="#resources" class="nav-link flex items-center px-4 py-2 rounded-lg hover:bg-blue-100 transition-colors">
                    <i data-lucide="database" class="mr-3"></i> <span class="nav-text">資源管理</span>
                </a>
                <a href="#settings" class="nav-link flex items-center px-4 py-2 rounded-lg hover:bg-blue-100 transition-colors">
                    <i data-lucide="settings" class="mr-3"></i> <span class="nav-text">系統設定</span>
                </a>
            </nav>
            <div class="p-4 border-t border-gray-200">
                <p class="text-sm text-gray-500 nav-text">&copy; 2025 CK Corp. V9.0</p>
            </div>
        </aside>

        <main class="main-content bg-gray-50 min-h-screen">
             <div class="p-4 sm:p-6 lg:p-8">
                <header class="flex items-center mb-6">
                     <button id="sidebar-toggle" class="p-2 rounded-md hover:bg-gray-200 mr-4">
                        <i data-lucide="menu" style="width:1.5em; height:1.5em"></i>
                    </button>
                    <h2 id="page-title" class="text-3xl font-bold">公文總表清單</h2>
                </header>
                <div id="page-content">
                    </div>
            </div>
        </main>
    </div>

    <div id="modal-container"></div>

<script type="module">
    // --- Initial Data (Complete and unchanged from V8) ---
    const initialData = {
        documents: [
            { id: 1, doc_type: '發文', issuer: '乾坤科技有限公司', recipient: '交通部公路局', doc_number: '乾坤測字第1130000001號', doc_date: '2024-03-15', subject: '檢送「埔里工務段、信義工務段優先關注邊坡光達應用暨進階檢測圖資建置計畫(第六期)」工作執行計畫書', case_id: 1, remarks: '', attachments: [{fileName: '2024-03-15_乾坤測字第1130000001號_檢送「埔里工務段.pdf', url: '#'}] },
            { id: 2, doc_type: '發文', issuer: '乾坤科技有限公司', recipient: '交通部公路局', doc_number: '乾坤測字第1130000002號', doc_date: '2024-04-15', subject: '檢送「埔里工務段、信義工務段優先關注邊坡光達應用暨進階檢測圖資建置計畫(第六期)」期中報告', case_id: 1, remarks: '', attachments: [] },
            { id: 3, doc_type: '發文', issuer: '乾坤科技有限公司', recipient: '交通部公路局', doc_number: '乾坤測字第1130000003號', doc_date: '2024-05-15', subject: '檢送「埔里工務段、信義工務段優先關注邊坡光達應用暨進階檢測圖資建置計畫(第六期)」期末報告', case_id: 1, remarks: '', attachments: [] },
            { id: 4, doc_type: '收文', issuer: '桃園市政府', recipient: '乾坤科技有限公司', doc_number: '桃工字第1130000001號', doc_date: '2024-03-20', subject: '有關「112至113年度桃園市轄內興辦公共設施工程用地取得所需土地市價及地上物查估、測量作業暨相關計畫書製作委託專業服務(開口契約)」案，請查照', case_id: 2, remarks: '', attachments: [{fileName: '2024-03-20_桃工字第1130000001號_有關「112至113.zip', url: '#'}] },
            { id: 5, doc_type: '收文', issuer: '桃園市政府', recipient: '乾坤科技有限公司', doc_number: '桃工字第1130000002號', doc_date: '2024-04-20', subject: '有關「114年度桃園市都市計畫內公共設施完竣地區調查及範圍劃定管理系統建置計畫」案，請查照', case_id: 3, remarks: '', attachments: [] },
            { id: 6, doc_type: '發文', issuer: '乾坤科技有限公司', recipient: '桃園市政府', doc_number: '乾坤測字第1140000001號', doc_date: '2025-05-20', subject: '檢送「114年度桃園市都市計畫內公共設施完竣地區調查及範圍劃定管理系統建置計畫」工作執行計畫書', case_id: 3, remarks: '', attachments: [] },
            { id: 7, doc_type: '發文', issuer: '乾坤科技有限公司', recipient: '桃園市政府', doc_number: '乾坤測字第1140000002號', doc_date: '2025-06-20', subject: '檢送「114年度桃園市都市計畫內公共設施完竣地區調查及範圍劃定管理系統建置計畫」期中報告', case_id: 3, remarks: '', attachments: [] },
            { id: 8, doc_type: '收文', issuer: '南投縣政府', recipient: '乾坤科技有限公司', doc_number: '投府字第1140000001號', doc_date: '2025-05-25', subject: '有關「114年度南投縣都市計畫樁位測定及補訂案委託技術服務案(開口契約)」案，請查照', case_id: 4, remarks: '', attachments: [] },
            { id: 9, doc_type: '發文', issuer: '乾坤科技有限公司', recipient: '南投縣政府', doc_number: '乾坤測字第1140000003號', doc_date: '2025-06-25', subject: '檢送「114年度南投縣都市計畫樁位測定及補訂案委託技術服務案(開口契約)」服務建議書', case_id: 4, remarks: '', attachments: [] },
            { id: 10, doc_type: '收文', issuer: '交通部公路局', recipient: '乾坤科技有限公司', doc_number: '路局字第1140000001號', doc_date: '2025-06-30', subject: '有關「台8臨37線3K~22K(含中橫故事館)及台14甲線翠峰至大禹嶺(18K~41K)路段委託監測、巡查及評估服務工作」案，請查照', case_id: 5, remarks: '', attachments: [] },
        ],
        cases: [
            { id: 1, year: 2024, name: '埔里工務段、信義工務段優先關注邊坡光達應用暨進階檢測圖資建置計畫(第六期)', case_nature: '委辦計畫', client: '交通部公路局', period: '2024/01/01-2024/12/31', staff_id: 1, vendor_id: 3 },
            { id: 2, year: 2024, name: '112至113年度桃園市轄內興辦公共設施工程用地取得所需土地市價及地上物查估、測量作業暨相關計畫書製作委託專業服務(開口契約)', case_nature: '委辦擴充', client: '桃園市政府', period: '2023/07/01-2025/06/30', staff_id: 2, vendor_id: 2 },
            { id: 3, year: 2025, name: '114年度桃園市都市計畫內公共設施完竣地區調查及範圍劃定管理系統建置計畫', case_nature: '委辦計畫', client: '桃園市政府', period: '2025/04/01-2026/03/31', staff_id: 1, vendor_id: 1 },
            { id: 4, year: 2025, name: '114年度南投縣都市計畫樁位測定及補訂案委託技術服務案(開口契約)', case_nature: '委辦計畫', client: '南投縣政府', period: '2025/05/01-2026/04/30', staff_id: 3, vendor_id: 1 },
            { id: 5, year: 2025, name: '台8臨37線3K~22K(含中橫故事館)及台14甲線翠峰至大禹嶺(18K~41K)路段委託監測、巡查及評估服務工作', case_nature: '創新專案', client: '交通部公路局', period: '2025/07/01-2026/06/30', staff_id: 2, vendor_id: 3 },
        ],
        resources: [
            { id: 1, type: '機關單位', fullName: '桃園市政府', shortName: '桃市府', code: '380110000G', department: '工務局' },
            { id: 2, type: '機關單位', fullName: '交通部公路局', shortName: '公路局', code: 'A15030200HU', department: '' },
            { id: 3, type: '機關單位', fullName: '南投縣政府', shortName: '投縣府', code: '387140000A', department: '' },
            { id: 4, type: '機關單位', fullName: '乾坤科技有限公司', shortName: 'CK', code: '', department: '' },
            { id: 1, type: '承辦同仁', name: '王駿禮' },
            { id: 2, type: '承辦同仁', name: '陳穎' },
            { id: 3, type: '承辦同仁', name: '林香' },
            { id: 1, type: '協力廠商', name: '政資訊有限公司', email: 'service@gov-info.com', phone: '02-12345678', contact: '王經理' },
            { id: 2, type: '協力廠商', name: '吉不動產估價師事務所', email: 'info@chi-app.com', phone: '04-23456789', contact: '林小姐' },
            { id: 3, type: '協力廠商', name: '上升空間資訊股份有限公司', email: 'contact@up-space.com.tw', phone: '07-34567890', contact: '陳先生' },
        ]
    };
    const state = {
        documents: [], cases: [], resources: [],
        docFilters: { year: '', keyword: '', doc_type: '總彙整' },
        caseFilters: { year: '', keyword: '' },
        resourceFilters: { '機關單位': '', '協力廠商': '', '承辦同仁': ''},
        settings: { nasPath: '/volume1/CK_Documents/' },
        docCurrentPage: 1,
        docRowsPerPage: 10,
        docSort: { key: 'id', order: 'desc' },
        caseSort: { key: 'year', order: 'desc'},
        resourceSort: {key: 'name', order: 'asc'},
        confirmDeleteCallback: null
    };

    const db = {
        init() {
            const storedData = localStorage.getItem('ck_system_data_v8');
            if (storedData) {
                const data = JSON.parse(storedData);
                state.documents = data.documents;
                state.cases = data.cases;
                state.resources = data.resources;
                state.settings = data.settings;
            } else {
                state.documents = initialData.documents;
                state.cases = initialData.cases;
                state.resources = initialData.resources;
                this.saveAll();
            }
        },
        saveAll() {
            localStorage.setItem('ck_system_data_v8', JSON.stringify({
                documents: state.documents,
                cases: state.cases,
                resources: state.resources,
                settings: state.settings,
            }));
        },
        _learnResource(name) {
            if (!name || typeof name !== 'string') return;
            const trimmedName = name.trim();
            if (!trimmedName) return;
            const exists = state.resources.some(r => r.type === '機關單位' && r.fullName === trimmedName);
            if (!exists) {
                this.addResource({ type: '機關單位', fullName: trimmedName, shortName: '', code: '', department: '' });
            }
        },
        addDocument(doc) {
            this._learnResource(doc.issuer);
            this._learnResource(doc.recipient);
            doc.id = state.documents.length > 0 ? Math.max(...state.documents.map(d => d.id)) + 1 : 1;
            state.documents.push(doc);
            this.saveAll();
        },
        updateDocument(updatedDoc) {
            this._learnResource(updatedDoc.issuer);
            this._learnResource(updatedDoc.recipient);
            const index = state.documents.findIndex(d => d.id === updatedDoc.id);
            if (index !== -1) { state.documents[index] = updatedDoc; this.saveAll(); }
        },
        deleteDocument(id) { state.documents = state.documents.filter(d => d.id !== id); this.saveAll(); },
        getDocuments() {
            let filtered = [...state.documents];
            if (state.docFilters.year) { filtered = filtered.filter(d => d.doc_date.startsWith(state.docFilters.year)); }
            if (state.docFilters.keyword) {
                const keyword = state.docFilters.keyword.toLowerCase();
                filtered = filtered.filter(d => 
                    (d.subject?.toLowerCase().includes(keyword)) ||
                    (d.doc_number?.toLowerCase().includes(keyword)) ||
                    (d.issuer?.toLowerCase().includes(keyword)) ||
                    (d.recipient?.toLowerCase().includes(keyword))
                );
            }
            if (state.docFilters.doc_type !== '總彙整') { filtered = filtered.filter(d => d.doc_type === state.docFilters.doc_type); }
            const { key, order } = state.docSort;
            if (key) {
                filtered.sort((a, b) => {
                    let valA = a[key]; let valB = b[key];
                    if (key === 'id') { valA = Number(valA); valB = Number(valB); }
                    if (valA < valB) return order === 'asc' ? -1 : 1;
                    if (valA > valB) return order === 'asc' ? 1 : -1;
                    return 0;
                });
            }
            return filtered;
        },
        getCases(isList = false) {
            let filtered = [...state.cases];
            if (isList) {
                if (state.caseFilters.year) { filtered = filtered.filter(c => c.year.toString() === state.caseFilters.year); }
                if (state.caseFilters.keyword) {
                    const keyword = state.caseFilters.keyword.toLowerCase();
                    filtered = filtered.filter(c => c.name.toLowerCase().includes(keyword) || c.client.toLowerCase().includes(keyword));
                }
                const { key, order } = state.caseSort;
                 if (key) {
                    filtered.sort((a, b) => {
                        let valA = a[key]; let valB = b[key];
                        if (key === 'year' || key === 'id') { valA = Number(valA); valB = Number(valB); }
                        if (valA < valB) return order === 'asc' ? -1 : 1;
                        if (valA > valB) return order === 'asc' ? 1 : -1;
                        return 0;
                    });
                }
            } else { // Kanban view
                if (state.caseFilters.year) { filtered = filtered.filter(c => c.year.toString() === state.caseFilters.year); }
                 return filtered.sort((a,b) => b.year - a.year);
            }
            return filtered;
        },
        addCase(caseItem) { caseItem.id = state.cases.length > 0 ? Math.max(...state.cases.map(c => c.id)) + 1 : 1; state.cases.push(caseItem); this.saveAll(); },
        updateCase(updatedCase) { const index = state.cases.findIndex(c => c.id === updatedCase.id); if (index !== -1) { state.cases[index] = updatedCase; this.saveAll(); } },
        deleteCase(id) { state.cases = state.cases.filter(c => c.id !== id); this.saveAll(); },
        getResources(type) { 
            let filtered = state.resources.filter(r => r.type === type);
            if (state.resourceFilters[type]) {
                const keyword = state.resourceFilters[type].toLowerCase();
                filtered = filtered.filter(r => r.name?.toLowerCase().includes(keyword) || r.fullName?.toLowerCase().includes(keyword) || r.shortName?.toLowerCase().includes(keyword) || r.contact?.toLowerCase().includes(keyword));
            }
            const { key, order } = state.resourceSort;
            const sortKey = (type === '機關單位') ? 'fullName' : 'name';
            filtered.sort((a,b) => {
                const valA = a[sortKey] || '';
                const valB = b[sortKey] || '';
                if(valA < valB) return order === 'asc' ? -1 : 1;
                if(valA > valB) return order === 'asc' ? 1 : -1;
                return 0;
            });
            return filtered;
        },
        addResource(resource) {
            const ofType = state.resources.filter(r => r.type === resource.type);
            resource.id = ofType.length > 0 ? Math.max(...ofType.map(r => r.id)) + 1 : 1;
            state.resources.push(resource);
            this.saveAll();
        },
        updateResource(resource) {
            const index = state.resources.findIndex(r => r.id === resource.id && r.type === resource.type);
            if(index !== -1) {
                const oldName = state.resources[index].fullName || state.resources[index].name;
                state.resources[index] = resource;
                const newName = resource.fullName || resource.name;
                if(resource.type === '機關單位' && oldName !== newName){
                    state.cases.forEach(c => { if(c.client === oldName) c.client = newName; });
                    state.documents.forEach(d => { 
                        if(d.issuer === oldName) d.issuer = newName;
                        if(d.recipient === oldName) d.recipient = newName;
                    });
                }
                this.saveAll();
            }
        },
        deleteResource(type, id) { state.resources = state.resources.filter(r => !(r.type === type && r.id === id)); this.saveAll(); }
    };
    
    const render = {
        page(pageId) {
            const contentEl = document.getElementById('page-content');
            if(!contentEl) return;
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('bg-blue-100', 'text-blue-700'));
            const activeLink = document.querySelector(`.nav-link[href="#${pageId}"]`);
            if (activeLink) {
                activeLink.classList.add('bg-blue-100', 'text-blue-700');
                document.getElementById('page-title').textContent = activeLink.querySelector('.nav-text').textContent;
            }

            switch(pageId) {
                case 'documents': contentEl.innerHTML = this.documentsPage(); this.documentsTable(); break;
                case 'cases': contentEl.innerHTML = this.casesPage(); this.casesView('kanban'); break;
                case 'doc-number': contentEl.innerHTML = this.docNumberPage(); this.docNumberHistoryTable(); modals.populateSelect('dn-recipient', '機關單位'); modals.populateSelect('dn-case-id', 'case'); break;
                case 'resources': contentEl.innerHTML = this.resourcesPage(); this.resourceTabContent('機關單位'); break;
                case 'settings': contentEl.innerHTML = this.settingsPage(); break;
            }
            lucide.createIcons();
        },
        documentsPage() {
            const years = [...new Set(state.documents.map(d => d.doc_date.substring(0, 4)))].sort().reverse();
            return `
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <div class="flex flex-wrap items-center justify-between mb-4 gap-4">
                        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 flex-grow">
                            <div>
                                <label for="doc-filter-keyword" class="text-sm font-medium">關鍵字查詢</label>
                                <input type="text" id="doc-filter-keyword" placeholder="主旨、字號、單位..." class="mt-1 w-full border-gray-300 rounded-md shadow-sm">
                            </div>
                            <div>
                                <label for="doc-filter-year" class="text-sm font-medium">年度</label>
                                <select id="doc-filter-year" class="mt-1 w-full border-gray-300 rounded-md shadow-sm">
                                    <option value="">全部年度</option>
                                    ${years.map(y => `<option value="${y}">${y}</option>`).join('')}
                                </select>
                            </div>
                            <div>
                                <label for="doc-filter-type" class="text-sm font-medium">類型</label>
                                <select id="doc-filter-type" class="mt-1 w-full border-gray-300 rounded-md shadow-sm">
                                    <option value="總彙整">總彙整</option>
                                    <option value="收文">收文</option>
                                    <option value="發文">發文</option>
                                </select>
                            </div>
                        </div>
                        <div class="flex items-center space-x-2 self-end">
                            <button id="batch-import-btn" class="bg-teal-500 text-white px-4 py-2 rounded-md hover:bg-teal-600 flex items-center"><i data-lucide="upload-cloud" class="mr-2"></i> 批次匯入</button>
                            <input type="file" id="batch-import-input" class="hidden" accept=".csv,.xlsx">
                            <button id="export-xlsx" class="bg-green-500 text-white px-4 py-2 rounded-md hover:bg-green-600 flex items-center"><i data-lucide="file-down" class="mr-2"></i> 匯出 XLSX</button>
                            <button id="add-doc-btn" class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 flex items-center"><i data-lucide="plus" class="mr-2"></i> 新增公文</button>
                        </div>
                    </div>
                </div>
                <div class="mt-6 bg-white rounded-lg shadow-md overflow-hidden">
                    <div class="table-container">
                        <table id="documents-table" class="w-full text-sm text-left"></table>
                    </div>
                    <div id="documents-pagination" class="p-4 border-t border-gray-200 flex flex-wrap gap-4 justify-between items-center"></div>
                </div>
            `;
        },
        documentsTable() {
            const tableEl = document.getElementById('documents-table');
            const paginationEl = document.getElementById('documents-pagination');
            if(!tableEl || !paginationEl) return;
            const docs = db.getDocuments();
            
            const totalPages = Math.ceil(docs.length / state.docRowsPerPage);
            state.docCurrentPage = Math.min(state.docCurrentPage, totalPages || 1);
            const paginatedDocs = docs.slice((state.docCurrentPage - 1) * state.docRowsPerPage, state.docCurrentPage * state.docRowsPerPage);
            
            if (docs.length === 0) {
                tableEl.innerHTML = `<tbody><tr><td colspan="9" class="text-center text-gray-500 py-8">無符合條件的公文紀錄。</td></tr></tbody>`;
                paginationEl.innerHTML = '';
                return;
            }
            
            const sortIcon = (key) => {
                if(state.docSort.key === key) {
                    return state.docSort.order === 'asc' ? '<i data-lucide="arrow-up" class="sort-icon h-4 w-4 inline-block ml-1"></i>' : '<i data-lucide="arrow-down" class="sort-icon h-4 w-4 inline-block ml-1"></i>';
                }
                return '<i data-lucide="arrow-down-up" class="sort-icon h-4 w-4 inline-block ml-1"></i>';
            };

            tableEl.innerHTML = `
                <thead class="bg-gray-100 text-gray-600 uppercase">
                    <tr>
                        <th class="p-3 sortable-header ${state.docSort.key === 'id' ? 'sorted' : ''}" data-sort="id"># ${sortIcon('id')}</th>
                        <th class="p-3 sortable-header ${state.docSort.key === 'doc_type' ? 'sorted' : ''}" data-sort="doc_type">類型 ${sortIcon('doc_type')}</th>
                        <th class="p-3">公文字號</th>
                        <th class="p-3 sortable-header ${state.docSort.key === 'doc_date' ? 'sorted' : ''}" data-sort="doc_date">公文日期 ${sortIcon('doc_date')}</th>
                        <th class="p-3 min-w-[300px]">主旨</th>
                        <th class="p-3">發文單位</th>
                        <th class="p-3">關聯案件</th>
                        <th class="p-3">附件</th>
                        <th class="p-3 text-center">操作</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
                    ${paginatedDocs.map((doc) => {
                        const caseName = state.cases.find(c => c.id === doc.case_id)?.name || '未關聯';
                        const attachmentsHTML = (doc.attachments && doc.attachments.length > 0)
                            ? doc.attachments.map(att => `<a href="${att.url}" target="_blank" class="text-blue-600 hover:underline flex items-center"><i data-lucide="paperclip" class="w-4 h-4 mr-1"></i>${att.fileName.substring(0,15)}...</a>`).join('<br>')
                            : '無';
                        return `
                            <tr class="hover:bg-gray-50">
                                <td class="p-3 font-medium">${doc.id}</td>
                                <td class="p-3"><span class="px-2 py-1 text-xs rounded-full ${doc.doc_type === '收文' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">${doc.doc_type}</span></td>
                                <td class="p-3 font-mono">${doc.doc_number}</td>
                                <td class="p-3">${doc.doc_date}</td>
                                <td class="p-3">${doc.subject}</td>
                                <td class="p-3">${doc.issuer}</td>
                                <td class="p-3 text-gray-600">${caseName.substring(0, 20)}${caseName.length > 20 ? '...' : ''}</td>
                                <td class="p-3 text-sm">${attachmentsHTML}</td>
                                <td class="p-3 text-center">
                                    <button class="icon-btn edit-doc-btn text-blue-600 hover:text-blue-800" data-id="${doc.id}"><i data-lucide="edit"></i></button>
                                    <button class="icon-btn delete-doc-btn text-red-600 hover:text-red-800" data-id="${doc.id}"><i data-lucide="trash-2"></i></button>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            `;
            
            paginationEl.innerHTML = `
                <span class="text-sm text-gray-700">共 ${docs.length} 筆紀錄</span>
                <div class="flex items-center space-x-2">
                    <select id="doc-rows-per-page" class="border-gray-300 rounded-md text-sm">
                        ${[10, 20, 50, 100].map(n => `<option value="${n}" ${state.docRowsPerPage === n ? 'selected' : ''}>${n} 筆/頁</option>`).join('')}
                    </select>
                    <button id="prev-page" class="p-2 rounded-md hover:bg-gray-100 disabled:opacity-50" ${state.docCurrentPage === 1 ? 'disabled' : ''}><i data-lucide="chevron-left"></i></button>
                    <span class="text-sm">第 ${state.docCurrentPage} / ${totalPages} 頁</span>
                    <button id="next-page" class="p-2 rounded-md hover:bg-gray-100 disabled:opacity-50" ${state.docCurrentPage >= totalPages ? 'disabled' : ''}><i data-lucide="chevron-right"></i></button>
                </div>
            `;
            lucide.createIcons();
        },
        casesPage() {
            return `
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <div class="flex flex-wrap items-center justify-between mb-4 gap-4">
                        <div class="flex items-center bg-gray-200 p-1 rounded-lg">
                           <button id="kanban-view-btn" class="view-toggle-btn bg-white text-blue-600 px-3 py-1 rounded-md shadow flex items-center"><i data-lucide="layout-grid" class="mr-2"></i> 看板</button>
                           <button id="list-view-btn" class="view-toggle-btn px-3 py-1 rounded-md text-gray-600 flex items-center"><i data-lucide="list" class="mr-2"></i> 列表</button>
                        </div>
                        <div class="flex items-center gap-4">
                            <div id="case-list-filters" class="hidden">
                                <label for="case-filter-keyword" class="text-sm font-medium mr-2">關鍵字</label>
                                <input type="text" id="case-filter-keyword" class="border-gray-300 rounded-md shadow-sm">
                            </div>
                            <div>
                                <label for="case-filter-year" class="text-sm font-medium mr-2">年度</label>
                                <select id="case-filter-year" class="border-gray-300 rounded-md shadow-sm">
                                    <option value="">全部年度</option>
                                    ${[...new Set(state.cases.map(c => c.year))].sort().reverse().map(y => `<option value="${y}">${y}</option>`).join('')}
                                </select>
                            </div>
                            <button id="add-case-btn" class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 flex items-center"><i data-lucide="plus" class="mr-2"></i> 新增案件</button>
                        </div>
                    </div>
                </div>
                <div id="cases-view-container" class="mt-6"></div>
            `;
        },
        casesView(viewType) {
            const container = document.getElementById('cases-view-container');
            const listFilters = document.getElementById('case-list-filters');
            if(!container || !listFilters) return;

            document.querySelectorAll('.view-toggle-btn').forEach(btn => btn.classList.remove('bg-white', 'text-blue-600', 'shadow'));
            document.getElementById(`${viewType}-view-btn`).classList.add('bg-white', 'text-blue-600', 'shadow');
            
            const cases = db.getCases(viewType === 'list');
            if (viewType === 'list') {
                listFilters.style.display = 'block';
            } else {
                listFilters.style.display = 'none';
            }
            
            if (cases.length === 0) {
                container.innerHTML = `<p class="text-center text-gray-500 py-8 bg-white rounded-lg shadow-md">無符合條件的案件紀錄。</p>`;
                return;
            }
            
            if (viewType === 'kanban') {
                const casesByYear = cases.reduce((acc, aCase) => {
                    (acc[aCase.year] = acc[aCase.year] || []).push(aCase);
                    return acc;
                }, {});
                container.innerHTML = `<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-6">
                    ${Object.keys(casesByYear).sort((a,b) => b-a).map(year => `
                        <div>
                            <h3 class="text-xl font-semibold mb-4 p-2 bg-gray-200 rounded-t-lg">${year} 年度</h3>
                            <div class="space-y-4">${casesByYear[year].map(c => this.caseCard(c)).join('')}</div>
                        </div>
                    `).join('')}
                </div>`;
            } else { // list view
                const sortIcon = (key) => state.caseSort.key === key ? (state.caseSort.order === 'asc' ? '↑' : '↓') : '↕';
                container.innerHTML = `<div class="bg-white p-6 rounded-lg shadow-md overflow-x-auto">
                    <table class="w-full text-sm text-left">
                        <thead class="bg-gray-100 text-gray-600 uppercase">
                            <tr>
                                <th class="p-3 sortable-header" data-sort="year">年度 ${sortIcon('year')}</th>
                                <th class="p-3 sortable-header" data-sort="name">案件名稱 ${sortIcon('name')}</th>
                                <th class="p-3 sortable-header" data-sort="case_nature">性質 ${sortIcon('case_nature')}</th>
                                <th class="p-3 sortable-header" data-sort="client">委託單位 ${sortIcon('client')}</th>
                                <th class="p-3">承辦人</th>
                                <th class="p-3">期程</th><th class="p-3 text-center">操作</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200">
                            ${cases.map(c => `
                                <tr class="hover:bg-gray-50">
                                    <td class="p-3">${c.year}</td>
                                    <td class="p-3 font-medium min-w-[300px]">${c.name}</td>
                                    <td class="p-3">${c.case_nature}</td>
                                    <td class="p-3">${c.client || ''}</td>
                                    <td class="p-3">${db.getResources('承辦同仁').find(r => r.id === c.staff_id)?.name || ''}</td>
                                    <td class="p-3">${c.period}</td>
                                    <td class="p-3 text-center">
                                        <button class="icon-btn edit-case-btn text-blue-600 hover:text-blue-800" data-id="${c.id}"><i data-lucide="edit"></i></button>
                                        <button class="icon-btn delete-case-btn text-red-600 hover:text-red-800" data-id="${c.id}"><i data-lucide="trash-2"></i></button>
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>`;
            }
            lucide.createIcons();
        },
        caseCard(c) {
            const client = c.client || 'N/A';
            const staff = db.getResources('承辦同仁').find(r => r.id === c.staff_id)?.name || 'N/A';
            const natureColors = { '創新專案': 'bg-purple-500', '委辦計畫': 'bg-green-500', '協辦計畫': 'bg-yellow-500', '委辦擴充': 'bg-orange-500', '小額採購': 'bg-pink-500' };
            return `
                <div class="bg-white p-4 rounded-lg shadow-md border-l-4 border-blue-500">
                    <div class="flex justify-between items-start">
                         <h4 class="font-bold mb-2 flex-1">${c.name}</h4>
                         <div class="flex-shrink-0 ml-2">
                             <button class="icon-btn edit-case-btn text-blue-600 hover:text-blue-800" data-id="${c.id}"><i data-lucide="edit"></i></button>
                             <button class="icon-btn delete-case-btn text-red-600 hover:text-red-800" data-id="${c.id}"><i data-lucide="trash-2"></i></button>
                         </div>
                    </div>
                    <p class="text-xs text-white px-2 py-0.5 rounded-full inline-block ${natureColors[c.case_nature] || 'bg-gray-500'}">${c.case_nature}</p>
                    <div class="mt-3 text-sm space-y-1 text-gray-600">
                        <p><strong class="font-medium text-gray-800">委託單位:</strong> ${client}</p>
                        <p><strong class="font-medium text-gray-800">承辦同仁:</strong> ${staff}</p>
                        <p><strong class="font-medium text-gray-800">期程:</strong> ${c.period}</p>
                    </div>
                </div>`;
        },
        resourcesPage() {
            return `
                <div class="bg-white rounded-lg shadow-md">
                    <div class="border-b border-gray-200">
                        <nav class="flex space-x-1 sm:space-x-4 px-2 sm:px-4" id="resource-tabs">
                           <button class="tab-btn active" data-tab="機關單位">機關單位</button>
                           <button class="tab-btn" data-tab="協力廠商">協力廠商</button>
                           <button class="tab-btn" data-tab="承辦同仁">承辦同仁</button>
                        </nav>
                    </div>
                    <div id="resource-content" class="p-4 sm:p-6"></div>
                </div>`;
        },
        resourceTabContent(type) {
            const container = document.getElementById('resource-content');
            if(!container) return;
            const resources = db.getResources(type);
            const sortKey = (type === '機關單位') ? 'fullName' : 'name';
            const sortIcon = (key) => state.resourceSort.key === key ? (state.resourceSort.order === 'asc' ? '↑' : '↓') : '↕';
            
            let tableHeaders, tableRows;
            switch(type) {
                case '機關單位':
                    tableHeaders = `<th class="p-3 sortable-header" data-sort="fullName">機關全銜 ${sortIcon('fullName')}</th>
                                    <th class="p-3">機關簡稱</th>
                                    <th class="p-3">機關代碼</th>
                                    <th class="p-3 text-center">操作</th>`;
                    tableRows = resources.map(r => `
                        <tr>
                            <td class="p-3">${r.fullName}</td><td class="p-3">${r.shortName}</td><td class="p-3">${r.code}</td>
                            <td class="p-3 text-center">
                                <button class="icon-btn edit-resource-btn text-blue-600" data-type="${type}" data-id="${r.id}"><i data-lucide="edit"></i></button>
                                <button class="icon-btn delete-resource-btn text-red-600" data-type="${type}" data-id="${r.id}"><i data-lucide="trash-2"></i></button>
                            </td>
                        </tr>`).join('');
                    break;
                case '協力廠商':
                    tableHeaders = `<th class="p-3 sortable-header" data-sort="name">公司名稱 ${sortIcon('name')}</th>
                                    <th class="p-3">聯絡窗口</th><th class="p-3">聯絡電話</th><th class="p-3">聯絡信箱</th>
                                    <th class="p-3 text-center">操作</th>`;
                    tableRows = resources.map(r => `
                        <tr>
                            <td class="p-3">${r.name}</td><td class="p-3">${r.contact}</td><td class="p-3">${r.phone}</td><td class="p-3">${r.email}</td>
                            <td class="p-3 text-center">
                                <button class="icon-btn edit-resource-btn text-blue-600" data-type="${type}" data-id="${r.id}"><i data-lucide="edit"></i></button>
                                <button class="icon-btn delete-resource-btn text-red-600" data-type="${type}" data-id="${r.id}"><i data-lucide="trash-2"></i></button>
                            </td>
                        </tr>`).join('');
                    break;
                default: //承辦同仁
                     tableHeaders = `<th class="p-3 sortable-header" data-sort="name">名稱 ${sortIcon('name')}</th><th class="p-3 text-center">操作</th>`;
                     tableRows = resources.map(r => `
                        <tr>
                            <td class="p-3">${r.name}</td>
                            <td class="p-3 text-center">
                                <button class="icon-btn edit-resource-btn text-blue-600" data-type="${type}" data-id="${r.id}"><i data-lucide="edit"></i></button>
                                <button class="icon-btn delete-resource-btn text-red-600" data-type="${type}" data-id="${r.id}"><i data-lucide="trash-2"></i></button>
                            </td>
                        </tr>`).join('');
            }

            container.innerHTML = `
                <div class="flex flex-wrap gap-4 mb-4">
                    <div class="flex-grow">
                        <label for="resource-filter-keyword" class="text-sm font-medium">關鍵字查詢</label>
                        <input type="text" id="resource-filter-keyword" placeholder="篩選 ${type}..." class="mt-1 w-full border-gray-300 rounded-md shadow-sm" data-type="${type}">
                    </div>
                    <div class="self-end">
                       <button class="add-resource-btn bg-blue-500 text-white p-2 rounded-md hover:bg-blue-600 flex items-center" data-type="${type}"><i data-lucide="plus" class="mr-1"></i> 新增 ${type}</button>
                    </div>
                </div>
                <div class="table-container border rounded-lg">
                    <table class="w-full text-sm">
                        <thead class="bg-gray-100"><tr class="text-left">${tableHeaders}</tr></thead>
                        <tbody class="divide-y divide-gray-200">${tableRows || `<tr><td colspan="5" class="text-center p-4 text-gray-500">尚無資料</td></tr>`}</tbody>
                    </table>
                </div>`;
            lucide.createIcons();
        },
        docNumberPage() {
            const outgoingDocs = state.documents.filter(d => d.doc_type === '發文' && d.doc_number.startsWith('乾坤測字第')).sort((a, b) => {
                const numA = parseInt(a.doc_number.split('第')[1]?.replace('號', '')) || 0;
                const numB = parseInt(b.doc_number.split('第')[1]?.replace('號', '')) || 0;
                return numB - numA;
            });

            let newDocNumber = '乾坤測字第1130000001號';
            if (outgoingDocs.length > 0) {
                const lastNum = parseInt(outgoingDocs[0].doc_number.split('第')[1]?.replace('號', '')) || 0;
                if(isFinite(lastNum)){
                    const newNum = lastNum + 1;
                    newDocNumber = `乾坤測字第${newNum}號`;
                }
            }
            
            return `
                 <div class="bg-white p-6 rounded-lg shadow-md max-w-4xl mx-auto">
                    <h2 class="text-3xl font-bold mb-4">公文取號服務</h2>
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <div>
                           <p class="text-gray-600 mb-6">系統會自動偵測已發文的最後一筆字號，並產生新的字號供您使用。</p>
                            <div class="text-center bg-gray-50 p-8 rounded-lg border border-dashed">
                                <p class="text-lg text-gray-500 mb-2">下一個可用公文字號</p>
                                <p id="new-doc-number" class="text-4xl font-bold text-blue-600 font-mono">${newDocNumber}</p>
                            </div>
                            <div class="mt-8">
                                <h3 class="text-xl font-semibold mb-4">取號填報</h3>
                                <form id="doc-number-form" class="space-y-4">
                                    <div>
                                        <label for="dn-case-id" class="block text-sm font-medium text-gray-700 mb-1">承攬案件名稱</label>
                                        <select id="dn-case-id" class="w-full border-gray-300 rounded-md shadow-sm" required></select>
                                    </div>
                                     <div>
                                        <label for="dn-recipient" class="block text-sm font-medium text-gray-700 mb-1">受文單位</label>
                                        <select id="dn-recipient" class="w-full border-gray-300 rounded-md shadow-sm" required></select>
                                    </div>
                                    <div>
                                        <label for="dn-subject" class="block text-sm font-medium text-gray-700 mb-1">公文主旨</label>
                                        <textarea id="dn-subject" rows="3" class="w-full border-gray-300 rounded-md shadow-sm" required></textarea>
                                    </div>
                                    <div class="flex justify-end">
                                        <button type="submit" class="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 flex items-center"><i data-lucide="check-circle" class="mr-2"></i>確認取號並建立草稿</button>
                                    </div>
                                </form>
                            </div>
                        </div>
                        <div>
                            <h3 class="text-xl font-semibold mb-4">近期取號紀錄</h3>
                            <div id="doc-number-history" class="table-container border rounded-lg"></div>
                        </div>
                    </div>
                </div>`;
        },
        docNumberHistoryTable() {
            const container = document.getElementById('doc-number-history');
            if(!container) return;
            const numberedDocs = state.documents
                .filter(d => d.remarks === '由取號服務建立之草稿' || d.doc_number.startsWith('乾坤測字第'))
                .sort((a,b) => b.id - a.id)
                .slice(0, 20); // show last 20
            
            if(numberedDocs.length === 0) {
                container.innerHTML = `<p class="text-center text-gray-500 p-4">尚無取號紀錄</p>`;
                return;
            }
            container.innerHTML = `
                <table class="w-full text-sm">
                    <thead class="bg-gray-100"><tr><th class="p-2 text-left">取號日期</th><th class="p-2 text-left">字號</th><th class="p-2 text-left">主旨</th></tr></thead>
                    <tbody class="divide-y divide-gray-200">
                    ${numberedDocs.map(d => `
                        <tr>
                            <td class="p-2 text-xs">${d.doc_date}</td>
                            <td class="p-2 font-mono text-xs">${d.doc_number}</td>
                            <td class="p-2 text-xs">${d.subject.substring(0,20)}...</td>
                        </tr>
                    `).join('')}
                    </tbody>
                </table>
            `;
        },
        settingsPage() {
            return `<div class="bg-white p-6 rounded-lg shadow-md max-w-2xl mx-auto">
                <h2 class="text-3xl font-bold mb-6">系統設定</h2>
                <form id="settings-form">
                    <div class="space-y-4">
                        <div>
                            <label for="nas-path" class="block text-sm font-medium text-gray-700 mb-1">公文檔案儲存路徑 (NAS)</label>
                            <input type="text" id="nas-path" value="${state.settings.nasPath}" class="w-full border-gray-300 rounded-md shadow-sm font-mono">
                            <p class="text-xs text-gray-500 mt-1">此路徑為系統存放公文PDF與ZIP檔的根目錄。</p>
                        </div>
                    </div>
                    <div class="mt-8 flex justify-end">
                        <button type="submit" class="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700">儲存設定</button>
                    </div>
                </form>
            </div>`;
        },
        allModals() {
            const modalContainer = document.getElementById('modal-container');
            if(!modalContainer) return;
            modalContainer.innerHTML = ``;
        }
    };

    const modals = {
        open(modalId, ...args) { 
            const container = document.getElementById('modal-container');
            if (!container) return;
            
            const modalHTML = this.getModalHTML(modalId, ...args);
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = modalHTML;
            const modalEl = tempDiv.firstElementChild;
            
            container.appendChild(modalEl);
            setTimeout(() => modalEl.classList.replace('hidden', 'flex'), 10);
            lucide.createIcons();
            this.postOpen(modalId, ...args);
        },
        close(modalId) {
            const modalEl = document.getElementById(modalId);
            if(modalEl) modalEl.remove();
        },
        getModalHTML(modalId) {
             switch (modalId) {
                case 'doc-modal':
                    return `<div id="doc-modal" class="modal fixed inset-0 z-50 items-center justify-center hidden p-4">
                        <div class="bg-white rounded-lg shadow-2xl w-full max-w-2xl max-h-full overflow-y-auto">
                            <form id="doc-form" class="p-6">
                                <h2 id="doc-modal-title" class="text-2xl font-bold mb-6"></h2>
                                <input type="hidden" id="doc-id">
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div><label for="doc_type" class="block text-sm font-medium text-gray-700 mb-1">收發文類別</label><select id="doc_type" class="w-full border-gray-300 rounded-md shadow-sm" required><option value="收文">收文</option><option value="發文">發文</option></select></div>
                                    <div><label for="doc_number" class="block text-sm font-medium text-gray-700 mb-1">公文字號</label><input type="text" id="doc_number" class="w-full border-gray-300 rounded-md shadow-sm" required></div>
                                    <div><label for="doc_date" class="block text-sm font-medium text-gray-700 mb-1">公文日期</label><input type="date" id="doc_date" class="w-full border-gray-300 rounded-md shadow-sm" required></div>
                                    <div><label for="doc_case_id" class="block text-sm font-medium text-gray-700 mb-1">關聯案件</label><select id="doc_case_id" class="w-full border-gray-300 rounded-md shadow-sm"></select></div>
                                    <div class="md:col-span-2"><label for="issuer" class="block text-sm font-medium text-gray-700 mb-1">發文單位</label><div class="flex items-center space-x-2"><select id="issuer" class="w-full border-gray-300 rounded-md shadow-sm" required></select><button type="button" class="add-quick-resource bg-blue-100 text-blue-700 p-2 rounded-md hover:bg-blue-200" data-type="機關單位" data-target-select="issuer"><i data-lucide="plus"></i></button></div></div>
                                    <div class="md:col-span-2"><label for="recipient" class="block text-sm font-medium text-gray-700 mb-1">受文單位</label><div class="flex items-center space-x-2"><select id="recipient" class="w-full border-gray-300 rounded-md shadow-sm" required></select><button type="button" class="add-quick-resource bg-blue-100 text-blue-700 p-2 rounded-md hover:bg-blue-200" data-type="機關單位" data-target-select="recipient"><i data-lucide="plus"></i></button></div></div>
                                    <div class="md:col-span-2"><label for="subject" class="block text-sm font-medium text-gray-700 mb-1">主旨</label><textarea id="subject" rows="3" class="w-full border-gray-300 rounded-md shadow-sm" required></textarea></div>
                                    <div class="md:col-span-2"><label for="remarks" class="block text-sm font-medium text-gray-700 mb-1">備註</label><textarea id="remarks" rows="2" class="w-full border-gray-300 rounded-md shadow-sm"></textarea></div>
                                    <div class="md:col-span-2"><label for="doc-files" class="block text-sm font-medium text-gray-700 mb-1">上傳附件</label><input type="file" id="doc-files" multiple class="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"/><p class="text-xs text-gray-500 mt-1">模擬上傳，檔案將依規則命名。</p><div id="file-naming-preview" class="mt-2 text-sm text-green-700 font-mono"></div></div>
                                </div>
                                <div class="mt-8 flex justify-end space-x-3"><button type="button" class="modal-close-btn bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300">取消</button><button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">儲存</button></div>
                            </form>
                        </div>
                    </div>`;
                case 'case-modal':
                    return `<div id="case-modal" class="modal fixed inset-0 z-50 items-center justify-center hidden p-4">
                        <div class="bg-white rounded-lg shadow-2xl w-full max-w-2xl max-h-full overflow-y-auto">
                           <form id="case-form" class="p-6">
                           <h2 id="case-modal-title" class="text-2xl font-bold mb-6"></h2><input type="hidden" id="case-id">
                           <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                               <div><label for="case_year" class="block text-sm font-medium text-gray-700 mb-1">年度</label><input type="number" id="case_year" class="w-full border-gray-300 rounded-md shadow-sm" required></div>
                               <div><label for="case_nature" class="block text-sm font-medium text-gray-700 mb-1">案件性質</label><select id="case_nature" class="w-full border-gray-300 rounded-md shadow-sm" required><option>創新專案</option><option>委辦計畫</option><option>協辦計畫</option><option>委辦擴充</option><option>小額採購</option></select></div>
                               <div class="md:col-span-2"><label for="case_name" class="block text-sm font-medium text-gray-700 mb-1">專案名稱</label><input type="text" id="case_name" class="w-full border-gray-300 rounded-md shadow-sm" required></div>
                               <div><label for="case_client" class="block text-sm font-medium text-gray-700 mb-1">委託單位</label><select id="case_client" class="w-full border-gray-300 rounded-md shadow-sm" required></select></div>
                               <div><label for="case_staff_id" class="block text-sm font-medium text-gray-700 mb-1">承辦同仁</label><select id="case_staff_id" class="w-full border-gray-300 rounded-md shadow-sm" required></select></div>
                               <div><label for="case_vendor_id" class="block text-sm font-medium text-gray-700 mb-1">協力廠商</label><select id="case_vendor_id" class="w-full border-gray-300 rounded-md shadow-sm"></select></div>
                               <div><label for="case_period" class="block text-sm font-medium text-gray-700 mb-1">契約期程</label><input type="text" id="case_period" placeholder="例如: 2025/01/01-2025/12/31" class="w-full border-gray-300 rounded-md shadow-sm"></div>
                           </div>
                           <div class="mt-8 flex justify-end space-x-3"><button type="button" class="modal-close-btn bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300">取消</button><button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">儲存</button></div>
                           </form>
                        </div>
                    </div>`;
                case 'resource-modal':
                    return `<div id="resource-modal" class="modal fixed inset-0 z-50 items-center justify-center hidden p-4">
                        <div class="bg-white rounded-lg shadow-2xl w-full max-w-lg">
                           <form id="resource-form" class="p-6">
                           <h2 id="resource-modal-title" class="text-2xl font-bold mb-6"></h2>
                           <input type="hidden" id="resource-id"><input type="hidden" id="resource-type">
                           <div id="resource-form-fields" class="space-y-4"></div>
                           <div class="mt-8 flex justify-end space-x-3"><button type="button" class="modal-close-btn bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300">取消</button><button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">儲存</button></div>
                           </form>
                        </div>
                    </div>`;
                case 'confirm-delete-modal':
                    return `<div id="confirm-delete-modal" class="modal fixed inset-0 z-50 items-center justify-center hidden p-4">
                        <div class="bg-white rounded-lg shadow-2xl w-full max-w-sm"><div class="p-6 text-center"><div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100"><i data-lucide="alert-triangle" class="h-6 w-6 text-red-600"></i></div><h3 class="mt-5 text-lg font-medium text-gray-900">確認刪除</h3><div class="mt-2 text-sm text-gray-500"><p>您確定要刪除這筆紀錄嗎？此操作無法復原。</p></div><div class="mt-6 flex justify-center space-x-3"><button type="button" class="modal-close-btn bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300">取消</button><button type="button" id="confirm-delete" class="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700">確認刪除</button></div></div></div>
                    </div>`;
                default: return '';
             }
        },
        postOpen(modalId, ...args) {
             switch (modalId) {
                case 'doc-modal': this.showDocModal(...args); break;
                case 'case-modal': this.showCaseModal(...args); break;
                case 'resource-modal': this.showResourceModal(...args); break;
                case 'confirm-delete-modal': this.confirmDelete(...args); break;
            }
        },
        populateSelect(elementId, type, selectedValue = '') {
            const select = document.getElementById(elementId);
            if (!select) return;
            let options;
            let optionHTML;

            switch(type) {
                case 'case':
                    options = state.cases.sort((a,b) => b.year - a.year || a.name.localeCompare(b.name, 'zh-Hant'));
                    optionHTML = `<option value="">無</option>` + options.map(o => `<option value="${o.id}">${o.year} - ${o.name}</option>`).join('');
                    break;
                case '承辦同仁':
                case '協力廠商':
                    options = db.getResources(type);
                    optionHTML = `<option value="">請選擇...</option>` + options.map(o => `<option value="${o.id}">${o.name}</option>`).join('');
                    break;
                case '機關單位':
                     options = db.getResources(type);
                    optionHTML = `<option value="">請選擇...</option>` + options.map(o => `<option value="${o.fullName}">${o.fullName}</option>`).join('');
                    break;
            }
            
            select.innerHTML = optionHTML;
            select.value = selectedValue;
        },
        showDocModal(docId = null) {
            const form = document.getElementById('doc-form');
            if(!form) return;
            form.reset();
            document.getElementById('file-naming-preview').textContent = '';
            
            if (docId) {
                const doc = state.documents.find(d => d.id === docId);
                document.getElementById('doc-modal-title').textContent = '編輯公文紀錄';
                document.getElementById('doc-id').value = doc.id;
                document.getElementById('doc_type').value = doc.doc_type;
                document.getElementById('doc_number').value = doc.doc_number;
                document.getElementById('doc_date').value = doc.doc_date;
                document.getElementById('subject').value = doc.subject;
                document.getElementById('remarks').value = doc.remarks || '';
                this.populateSelect('doc_case_id', 'case', doc.case_id);
                this.populateSelect('issuer', '機關單位', doc.issuer);
                this.populateSelect('recipient', '機關單位', doc.recipient);
            } else {
                document.getElementById('doc-modal-title').textContent = '新增公文紀錄';
                document.getElementById('doc-id').value = '';
                this.populateSelect('doc_case_id','case');
                this.populateSelect('issuer', '機關單位');
                this.populateSelect('recipient', '機關單位');
            }
        },
        showCaseModal(caseId = null) {
             const form = document.getElementById('case-form');
            if(!form) return;
            form.reset();
            
            if (caseId) {
                 const caseItem = state.cases.find(c => c.id === caseId);
                 document.getElementById('case-modal-title').textContent = '編輯承攬案件';
                 document.getElementById('case-id').value = caseItem.id;
                 document.getElementById('case_year').value = caseItem.year;
                 document.getElementById('case_nature').value = caseItem.case_nature;
                 document.getElementById('case_name').value = caseItem.name;
                 document.getElementById('case_period').value = caseItem.period || '';
                 this.populateSelect('case_client', '機關單位', caseItem.client);
                 this.populateSelect('case_staff_id', '承辦同仁', caseItem.staff_id);
                 this.populateSelect('case_vendor_id', '協力廠商', caseItem.vendor_id);
            } else {
                 document.getElementById('case-modal-title').textContent = '新增承攬案件';
                 document.getElementById('case-id').value = '';
                 document.getElementById('case_year').value = new Date().getFullYear();
                 this.populateSelect('case_client', '機關單位');
                 this.populateSelect('case_staff_id', '承辦同仁');
                 this.populateSelect('case_vendor_id', '協力廠商');
            }
        },
        showResourceModal(type, id = null) {
            const title = (id ? '編輯' : '新增') + ` ${type}`;
            document.getElementById('resource-modal-title').textContent = title;
            document.getElementById('resource-id').value = id || '';
            document.getElementById('resource-type').value = type;

            const fieldsContainer = document.getElementById('resource-form-fields');
            let item = id ? state.resources.find(r => r.id === id && r.type === type) : {};
            
            switch (type) {
                case '機關單位':
                    fieldsContainer.innerHTML = `
                        <div><label class="block text-sm font-medium">機關全銜</label><input type="text" id="resource-fullName" class="mt-1 w-full border-gray-300 rounded-md" value="${item.fullName || ''}" required></div>
                        <div><label class="block text-sm font-medium">機關簡稱</label><input type="text" id="resource-shortName" class="mt-1 w-full border-gray-300 rounded-md" value="${item.shortName || ''}"></div>
                        <div><label class="block text-sm font-medium">機關代碼</label><input type="text" id="resource-code" class="mt-1 w-full border-gray-300 rounded-md" value="${item.code || ''}"></div>
                        <div><label class="block text-sm font-medium">部門名稱</label><input type="text" id="resource-department" class="mt-1 w-full border-gray-300 rounded-md" value="${item.department || ''}"></div>
                    `;
                    break;
                case '協力廠商':
                     fieldsContainer.innerHTML = `
                        <div><label class="block text-sm font-medium">公司名稱</label><input type="text" id="resource-name" class="mt-1 w-full border-gray-300 rounded-md" value="${item.name || ''}" required></div>
                        <div><label class="block text-sm font-medium">聯絡窗口</label><input type="text" id="resource-contact" class="mt-1 w-full border-gray-300 rounded-md" value="${item.contact || ''}"></div>
                        <div><label class="block text-sm font-medium">聯絡電話</label><input type="text" id="resource-phone" class="mt-1 w-full border-gray-300 rounded-md" value="${item.phone || ''}"></div>
                        <div><label class="block text-sm font-medium">聯絡信箱</label><input type="email" id="resource-email" class="mt-1 w-full border-gray-300 rounded-md" value="${item.email || ''}"></div>
                    `;
                    break;
                case '承辦同仁':
                    fieldsContainer.innerHTML = `<div><label class="block text-sm font-medium">姓名</label><input type="text" id="resource-name" class="mt-1 w-full border-gray-300 rounded-md" value="${item.name || ''}" required></div>`;
                    break;
            }
        },
        confirmDelete(callback) {
            state.confirmDeleteCallback = callback;
        }
    };

    function setupEventListeners() {
        document.body.addEventListener('click', (e) => {
            const target = e.target.closest('button, a, .sortable-header, #sidebar-backdrop');
            if (!target) return;

            const navLink = target.closest('.nav-link');
            if (navLink) {
                e.preventDefault();
                const pageId = navLink.getAttribute('href').substring(1);
                render.page(pageId);
                 if (window.innerWidth < 1024) {
                    document.getElementById('app-container').classList.remove('sidebar-open');
                } else {
                    document.getElementById('app-container').classList.add('sidebar-collapsed');
                }
                return;
            }

            if (target.matches('.sortable-header')) {
                const key = target.dataset.sort;
                const parentTable = target.closest('table');
                let sortState, renderFunc;
                
                if(parentTable.closest('#documents-table')) { sortState = state.docSort; renderFunc = render.documentsTable; }
                else if(parentTable.closest('#cases-view-container')) { sortState = state.caseSort; renderFunc = () => render.casesView('list'); }
                else { sortState = state.resourceSort; renderFunc = () => { const activeTab = document.querySelector('.tab-btn.active'); if(activeTab) render.resourceTabContent(activeTab.dataset.tab); } }
                
                if (sortState.key === key) {
                    sortState.order = sortState.order === 'asc' ? 'desc' : 'asc';
                } else {
                    sortState.key = key;
                    sortState.order = 'asc';
                }
                renderFunc();
            }

            switch(target.id) {
                case 'sidebar-toggle':
                    if (window.innerWidth < 1024) { document.getElementById('app-container').classList.add('sidebar-open'); } 
                    else { document.getElementById('app-container').classList.toggle('sidebar-collapsed'); }
                    break;
                case 'sidebar-close':
                case 'sidebar-backdrop':
                    document.getElementById('app-container').classList.remove('sidebar-open');
                    break;
                case 'batch-import-btn': document.getElementById('batch-import-input').click(); break;
                case 'add-doc-btn': modals.open('doc-modal'); break;
                case 'export-xlsx': exportToXLSX(); break;
                case 'prev-page': state.docCurrentPage--; render.documentsTable(); break;
                case 'next-page': state.docCurrentPage++; render.documentsTable(); break;
                case 'add-case-btn': modals.open('case-modal'); break;
                case 'kanban-view-btn': render.casesView('kanban'); break;
                case 'list-view-btn': render.casesView('list'); break;
                case 'confirm-delete':
                    if (state.confirmDeleteCallback) state.confirmDeleteCallback();
                    modals.close('confirm-delete-modal');
                    state.confirmDeleteCallback = null;
                    break;
            }

            if (target.matches('.modal-close-btn')) { const modal = target.closest('.modal'); if (modal) modals.close(modal.id); }
            if (target.matches('.edit-doc-btn')) modals.open('doc-modal', Number(target.dataset.id));
            if (target.matches('.delete-doc-btn')) modals.open('confirm-delete-modal', () => { db.deleteDocument(Number(target.dataset.id)); render.documentsTable(); });
            if (target.matches('.edit-case-btn')) modals.open('case-modal', Number(target.dataset.id));
            if (target.matches('.delete-case-btn')) modals.open('confirm-delete-modal', () => { 
                db.deleteCase(Number(target.dataset.id)); 
                const currentView = document.querySelector('#kanban-view-btn.active') ? 'kanban' : 'list';
                render.casesView(currentView || 'kanban');
            });

            const tabBtn = target.closest('.tab-btn');
            if (tabBtn) {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                tabBtn.classList.add('active');
                render.resourceTabContent(tabBtn.dataset.tab);
            }
            const editBtn = target.closest('.edit-resource-btn');
            if (editBtn) {
                 const { type, id} = editBtn.dataset;
                 modals.open('resource-modal', type, Number(id));
            }
            const addResBtn = target.closest('.add-resource-btn');
            if(addResBtn) {
                 modals.open('resource-modal', addResBtn.dataset.type);
            }
            const deleteResBtn = target.closest('.delete-resource-btn');
            if (deleteResBtn) {
                 const { type, id } = deleteResBtn.dataset;
                 modals.open('confirm-delete-modal', () => { db.deleteResource(type, Number(id)); render.resourceTabContent(type); });
            }

            const quickAddBtn = target.closest('.add-quick-resource');
            if(quickAddBtn) {
                const type = quickAddBtn.dataset.type;
                const newName = prompt(`請輸入要新增的 ${type}:`);
                if (newName && newName.trim()) {
                    db.addResource({type: '機關單位', fullName: newName.trim()});
                    const targetSelectId = quickAddBtn.dataset.targetSelect;
                    const otherSelectId = targetSelectId === 'issuer' ? 'recipient' : 'issuer';
                    const otherSelect = document.getElementById(otherSelectId);
                    
                    modals.populateSelect(targetSelectId, type, newName.trim());
                    modals.populateSelect(otherSelectId, type, otherSelect.value);
                }
            }
        });

        document.body.addEventListener('input', (e) => {
            const target = e.target;
            const targetId = target.id;
            if (['doc-filter-keyword', 'doc-filter-year', 'doc-filter-type'].includes(targetId)) {
                state.docFilters.keyword = document.getElementById('doc-filter-keyword').value;
                state.docFilters.year = document.getElementById('doc-filter-year').value;
                state.docFilters.doc_type = document.getElementById('doc-filter-type').value;
                state.docCurrentPage = 1;
                render.documentsTable();
            }
            if (targetId === 'case-filter-year' || targetId === 'case-filter-keyword') {
                state.caseFilters.year = document.getElementById('case-filter-year').value;
                state.caseFilters.keyword = document.getElementById('case-filter-keyword').value;
                const currentView = document.querySelector('#kanban-view-btn.active') ? 'kanban' : 'list';
                render.casesView(currentView || 'kanban');
            }
            if (targetId === 'resource-filter-keyword') {
                state.resourceFilters[target.dataset.type] = target.value;
                render.resourceTabContent(target.dataset.type);
            }
             if(['doc_date', 'doc_number', 'subject', 'doc-files'].includes(targetId)) {
                updateFileNamePreview();
            }
        });
        
        document.body.addEventListener('change', (e) => {
            if (e.target.id === 'batch-import-input') {
                handleBatchImport(e);
            }
            if(e.target.id === 'doc-rows-per-page') {
                state.docRowsPerPage = Number(e.target.value);
                state.docCurrentPage = 1;
                render.documentsTable();
            }
        });
        
        document.body.addEventListener('submit', (e) => {
             e.preventDefault();
             handleFormSubmit(e.target);
        });
    }
    
    function handleFormSubmit(form) {
        if(!form) return;
        const formId = form.id;
        
        switch(formId) {
            case 'doc-form': {
                const id = Number(document.getElementById('doc-id').value);
                const attachments = Array.from(document.getElementById('doc-files').files).map(file => ({
                    fileName: updateFileNamePreview(true),
                    url: '#'
                }));
                const doc = {
                    id: id || null, doc_type: document.getElementById('doc_type').value, doc_number: document.getElementById('doc_number').value,
                    doc_date: document.getElementById('doc_date').value, issuer: document.getElementById('issuer').value,
                    recipient: document.getElementById('recipient').value, subject: document.getElementById('subject').value,
                    case_id: Number(document.getElementById('doc_case_id').value) || null, remarks: document.getElementById('remarks')?.value || '',
                    attachments: id ? (state.documents.find(d=>d.id === id).attachments || []).concat(attachments) : attachments,
                };
                if (id) db.updateDocument(doc); else db.addDocument(doc);
                modals.close('doc-modal');
                render.documentsTable();
                break;
            }
            case 'case-form': {
                const id = Number(document.getElementById('case-id').value);
                const caseItem = {
                    id: id || null, year: Number(document.getElementById('case_year').value), name: document.getElementById('case_name').value,
                    case_nature: document.getElementById('case_nature').value, client: document.getElementById('case_client').value,
                    period: document.getElementById('case_period').value, staff_id: Number(document.getElementById('case_staff_id').value) || null,
                    vendor_id: Number(document.getElementById('case_vendor_id').value) || null,
                };
                if (id) db.updateCase(caseItem); else db.addCase(caseItem);
                modals.close('case-modal');
                const currentView = document.querySelector('#kanban-view-btn.active') ? 'kanban' : 'list';
                render.casesView(currentView || 'kanban');
                break;
            }
            case 'resource-form': {
                const id = Number(document.getElementById('resource-id').value);
                const type = document.getElementById('resource-type').value;
                let resource;
                if(type === '機關單位') {
                    resource = { id: id || null, type, fullName: document.getElementById('resource-fullName').value, shortName: document.getElementById('resource-shortName').value, code: document.getElementById('resource-code').value, department: document.getElementById('resource-department').value };
                } else if (type === '協力廠商') {
                    resource = { id: id || null, type, name: document.getElementById('resource-name').value, contact: document.getElementById('resource-contact').value, phone: document.getElementById('resource-phone').value, email: document.getElementById('resource-email').value };
                } else { // 承辦同仁
                    resource = { id: id || null, type, name: document.getElementById('resource-name').value };
                }

                if (id) db.updateResource(resource); else db.addResource(resource);
                modals.close('resource-modal');
                render.resourceTabContent(type);
                break;
            }
            case 'doc-number-form': {
                const newDoc = {
                     doc_type: '發文', doc_number: document.getElementById('new-doc-number').textContent,
                     doc_date: new Date().toISOString().split('T')[0], issuer: '乾坤科技有限公司', recipient: document.getElementById('dn-recipient').value,
                     subject: document.getElementById('dn-subject').value, case_id: Number(document.getElementById('dn-case-id').value) || null,
                     remarks: '由取號服務建立之草稿', attachments: []
                 };
                 db.addDocument(newDoc);
                 alert(`公文草稿已建立！\n字號: ${newDoc.doc_number}\n請至「公文總表」查看與編輯。`);
                 render.page('doc-number');
                 break;
            }
            case 'settings-form': {
                state.settings.nasPath = document.getElementById('nas-path').value;
                db.saveAll();
                alert('設定已儲存！');
                break;
            }
        }
    }
    
    function updateFileNamePreview(returnName = false) {
        const dateEl = document.getElementById('doc_date');
        const numberInput = document.getElementById('doc_number');
        const subjectInput = document.getElementById('subject');
        
        if(!dateEl || !numberInput || !subjectInput) return;

        const date = dateEl.value;
        const number = numberInput.value.replace(/[\/\\?%*:|"<>]/g, '-');
        const subject = subjectInput.value.substring(0, 20).replace(/[\/\\?%*:|"<>]/g, '-');
        const files = document.getElementById('doc-files').files;

        if (!date || !number || !subject) {
             const previewEl = document.getElementById('file-naming-preview');
             if (previewEl) previewEl.textContent = '';
             return '';
        }
        
        const extension = files.length > 1 ? '.zip' : (files.length === 1 ? '.' + files[0].name.split('.').pop() : '.pdf');
        
        const filename = `${date}_${number}_${subject}${extension}`;

        if(returnName) return filename;

        const previewEl = document.getElementById('file-naming-preview');
        if(previewEl) {
             previewEl.innerHTML = `
               <p class="text-xs">預計存檔名稱:</p>
               <p>${filename}</p>
            `;
        }
        return filename;
    }

    function handleBatchImport(event) {
        const file = event.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = new Uint8Array(e.target.result);
                const workbook = XLSX.read(data, {type: 'array', cellDates: true});
                const sheetName = workbook.SheetNames[0];
                const worksheet = workbook.Sheets[sheetName];
                const json = XLSX.utils.sheet_to_json(worksheet);
                let importedCount = 0;
                json.forEach(row => {
                    const doc = {
                        doc_type: row['收發文類別'], issuer: row['發文單位'], recipient: row['受文單位'], doc_number: row['公文字號'],
                        doc_date: formatImportedDate(row['公文日期']), subject: row['主旨'], case_id: null, remarks: '批次匯入', attachments: []
                    };
                    if (doc.doc_type && doc.doc_number && doc.doc_date && doc.subject) {
                        db.addDocument(doc);
                        importedCount++;
                    }
                });
                alert(`成功匯入 ${importedCount} 筆公文紀錄！`);
                render.page('documents');
            } catch (error) {
                console.error("批次匯入失敗:", error);
                alert("檔案處理失敗，請確認檔案格式是否正確。");
            }
        };
        reader.readAsArrayBuffer(file);
    }
    
    function formatImportedDate(dateInput) {
        if (!dateInput) return new Date().toISOString().split('T')[0];
        if (dateInput instanceof Date) {
            return dateInput.toISOString().split('T')[0];
        }
        if (typeof dateInput === 'string' && dateInput.includes('/')) {
            const parts = dateInput.split('/');
            if (parts.length === 3) {
                const rocYear = parseInt(parts[0]);
                if (!isNaN(rocYear) && rocYear < 200) {
                    return `${rocYear + 1911}-${String(parts[1]).padStart(2, '0')}-${String(parts[2]).padStart(2, '0')}`;
                }
            }
        }
        const parsedDate = new Date(dateInput);
        return !isNaN(parsedDate) ? parsedDate.toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
    }

    function exportToXLSX() {
        const today = new Date().toISOString().split('T')[0];
        const docsToExport = [...state.documents].sort((a,b) => a.id - b.id).map(doc => {
            const docNumberParts = doc.doc_number.split('字第');
            const zi = docNumberParts[0] ? docNumberParts[0] + '字' : '';
            const wenhao = docNumberParts[1] ? docNumberParts[1].replace('號', '') : '';

            return {
                '流水號': doc.id, '文件類型': doc.doc_type, '公文字號': doc.doc_number,
                '日期': doc.doc_date,
                '公文日期': `中華民國 ${new Date(doc.doc_date).getFullYear() - 1911} 年 ${new Date(doc.doc_date).getMonth() + 1} 月 ${new Date(doc.doc_date).getDate()} 日`,
                '類別': '', '字': zi, '文號': wenhao, '主旨': doc.subject,
                '發文單位': doc.issuer, '受文單位': doc.recipient,
                '收發狀態': '', '收文日期': doc.doc_type === '收文' ? doc.doc_date : '',
                '發文形式': '', '備註': doc.remarks || '',
                '承攬案件': state.cases.find(c => c.id === doc.case_id)?.name || '',
                '系統輸出日期': today,
            }
        });
        const worksheet = XLSX.utils.json_to_sheet(docsToExport);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "公文總表");
        XLSX.writeFile(workbook, "CK公文總表_匯出.xlsx");
    }

    function initApp() {
        db.init();
        render.allModals();
        setupEventListeners();
        render.page('documents');
    }

    initApp();

</script>
</body>
</html>
