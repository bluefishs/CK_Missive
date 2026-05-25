# ck-navigation v1.0

Dynamic navigation menu — backend `secure_site_management` API + frontend `layout` (Header / Sidebar / SidebarContent).

> **Source**: CK_Missive v6.10 — `shared-modules/ck-navigation/`
> **FQID**: `CK_Missive#ck-navigation_v1.0`
> **Portability**: ⭐ **1.000** (0 critical / 0 high / 0 medium / 0 domain_specific)
> **跨 repo 試裝結果**:
>   - CK_lvrland_Webmap: **14/14 (100%) 0 conflicts** ✓
>   - CK_PileMgmt:       **14/14 (100%) 0 conflicts** ✓

---

## Quick Start

```bash
# Install (from CK_Missive)
cd /path/to/your_repo
bash /d/CKProject/CK_Missive/shared-modules/ck-navigation/install.sh .

# Dry-run first (recommended)
bash /d/CKProject/CK_Missive/shared-modules/ck-navigation/install.sh . --dry-run
```

---

## What's Included

```
backend/app/api/endpoints/secure_site_management/
├── __init__.py
├── common.py      Permission helpers + role checks
├── config.py      Site config endpoints
├── navigation.py  Navigation CRUD + tree query
└── security.py    Security policy endpoints

backend/app/services/system/
└── navigation_sync.py     Frontend sync helper

frontend/src/components/layout/
├── Header.tsx
├── Sidebar.tsx
├── SidebarContent.tsx
├── index.ts
└── hooks/
    ├── index.ts
    ├── types.ts
    ├── useMenuItems.tsx
    └── useNavigationData.tsx
```

**14 files total / 100% portability**

---

## Dependencies (recommended pairing)

- **ck-auth v1.0** — Provides `current_user` for role-based menu filtering
- **ck-rbac v1.0+** (planned) — Role-based access control

---

## Post-install

1. **Register router** in `main.py`:
   ```python
   from app.api.endpoints.secure_site_management import navigation_router
   app.include_router(navigation_router, prefix="/api/secure-site-management")
   ```

2. **DB migration**: Create `navigation_items` table (see manifest.yml)

3. **Seed default items** (consumer customizes):
   ```python
   DEFAULT_NAVIGATION_ITEMS = [
       {"name": "Dashboard", "path": "/dashboard", "icon": "home", "role_required": "user"},
       # ... your repo-specific menu
   ]
   ```

4. **Frontend**:
   ```tsx
   import { Sidebar, Header } from 'components/layout';

   <Layout>
     <Header />
     <Sidebar />
     <Content>...</Content>
   </Layout>
   ```

---

## Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-05-18 | Initial extraction. 14 files, portability 1.000, dual-repo dry-run 100%. |
