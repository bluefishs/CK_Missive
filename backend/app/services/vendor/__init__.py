"""Vendor bounded context (DDD Wave 1 sub-batch B, 2026-04-27).

Houses partner vendor (協力廠商) management.
For client (委託單位), see services/agency/ — both share the legacy `vendor`
DB table but are differentiated by `vendor_type`.

Public API:
    VendorService — partner vendor CRUD + projects + filter
"""
from .core import VendorService  # noqa: F401
