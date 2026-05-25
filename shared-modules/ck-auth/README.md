# ck-auth v1.0

Cross-repo authentication module — Google OAuth / LINE Login / MFA / CSRF / domain whitelist.

> **Source**: CK_Missive v6.10 — `shared-modules/ck-auth/`
> **FQID**: `CK_Missive#ck-auth_v1.0`
> **Portability**: ⭐ 1.000 (verified by `module_portability_audit.py`)
> **License**: Internal use across CK projects

---

## Quick Start

```bash
# 1. Install (from CK_Missive)
cd /path/to/your_repo
bash /d/CKProject/CK_Missive/shared-modules/ck-auth/install.sh .

# 2. Configure env vars
cp .env.ck-auth.template .env  # Edit values

# 3. Run alembic migration (consumer responsibility)
alembic revision --autogenerate -m "add ck-auth tables"
alembic upgrade head

# 4. Register router (backend/main.py)
from app.api.endpoints.auth import auth_router
app.include_router(auth_router, prefix="/api/auth")

# 5. Use frontend
# import LoginPanel from 'components/auth/LoginPanel'
```

---

## What's Included

### Backend (10 endpoints + 5 core modules)

```
backend/app/api/endpoints/auth/
├── oauth.py           Google OAuth 2.0 flow
├── line_login.py      LINE Login flow
├── mfa.py             Multi-Factor Authentication
├── session.py         Session management
├── sessions.py        Sessions admin
├── login_history.py   Login audit log
├── profile.py         User profile
├── email_verify.py    Email verification
├── password_reset.py  Password reset
└── common.py          Shared helpers

backend/app/core/
├── auth_service.py        Core auth logic (755L)
├── csrf.py                CSRF token middleware
├── domain_whitelist.py    Cross-origin whitelist
├── service_auth.py        Service-to-service auth
└── security_headers.py    HSTS / CSP / X-Frame headers
```

### Frontend (6 files)

```
frontend/src/components/auth/
├── LoginPanel.tsx     Reusable login UI (props-driven)
└── withAuth.tsx       HOC for protected routes

frontend/src/services/
└── authService.ts     631-line auth client

frontend/src/api/
└── authApi.ts         API endpoints

frontend/src/hooks/utility/
├── useAuthGuard.ts    Route protection hook
└── useLineLogin.ts    LINE Login hook

frontend/src/types/
└── google-oauth.d.ts  Google OAuth types
```

---

## Required Env Vars

| Variable | Description | Required? |
|---|---|---|
| `CKAUTH_GOOGLE_CLIENT_ID` | Google OAuth Client ID | YES |
| `CKAUTH_GOOGLE_CLIENT_SECRET` | Google OAuth Secret | YES |
| `CKAUTH_JWT_SECRET_KEY` | JWT signing key | YES |
| `CKAUTH_GOOGLE_REDIRECT_URI` | OAuth callback | Recommended |
| `CKAUTH_LINE_CHANNEL_ID` | LINE Login Channel | Optional |
| `CKAUTH_LINE_CHANNEL_SECRET` | LINE Secret | Optional |
| `CKAUTH_LINE_CALLBACK_URL` | LINE callback | Optional |
| `CKAUTH_JWT_ALGORITHM` | default `HS256` | No |
| `CKAUTH_ACCESS_TOKEN_EXPIRE_MINUTES` | default `60` | No |
| `CKAUTH_SESSION_TTL_SECONDS` | default `3600` | No |

### v6.x Backward Compatibility

`auth_service.py` reads namespace-prefixed first, fallback to legacy:

```python
def get_google_client_id() -> str:
    return os.getenv("CKAUTH_GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_CLIENT_ID", "")
```

Deprecation: Legacy variables removed in **v6.11**.

---

## DB Schema Requirements

Consumer must have a `users` table with these columns (see `manifest.yml` for full schema):

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False)
    google_id = Column(String(100))
    line_user_id = Column(String(64), unique=True)
    role = Column(String(20), default='user')
    canonical_user_id = Column(Integer, ForeignKey('users.id'))  # ADR-0025
    # ...
```

A reusable `BaseUser` ORM mixin will ship in v1.1.

---

## Portability Audit

```bash
# Before installing, audit guarantees no business coupling:
PYTHONIOENCODING=utf-8 python scripts/checks/module_portability_audit.py \
    shared-modules/ck-auth/ --strict
```

Expected output:
```
Module Portability Audit — shared-modules/ck-auth
  Files scanned:        16
  Lines scanned:        3998
  Total hits:           12 (all domain_specific, no critical/high/medium)
  Portability score:    1.000
  Verdict:              [OK] PORTABLE
```

`install.sh` runs this audit automatically. **Refuses to install if NOT_PORTABLE.**

---

## Architecture Decisions

This package follows:
- [ADR-0025 Identity Unification](../../docs/adr/0025-identity-unification.md) — canonical_user_id mechanism
- [ADR-0027 Telegram Permanent Ban](../../docs/adr/0027-telegram-permanent-ban.md) — admin_push gate
- [ADR-0028 Error Contract](../../docs/adr/0028-error-contract-silent-failure-policy.md) — silent failure policy
- [ADR-0033 SSO-Only](../../docs/adr/0033-sso-only-no-password.md) — password login disabled

---

## Versioning

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | 2026-05-18 | Initial extraction. 16 files, portability 1.000. |

---

## Consumer Examples

### CK_AaaP (planned v6.11)
```bash
cd /d/CKProject/CK_AaaP
bash /d/CKProject/CK_Missive/shared-modules/ck-auth/install.sh .
```

### CK_lvrland_Webmap (planned v6.11)
```bash
cd /d/CKProject/CK_lvrland_Webmap
bash /d/CKProject/CK_Missive/shared-modules/ck-auth/install.sh .
```

---

## Support

Issues? See `_meta/troubleshooting.md` or check consumers.yml for `last_audit` notes.

Source maintainer: `@bluefishs` (CK_Missive)
