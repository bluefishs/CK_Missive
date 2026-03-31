"""
派工-公文關聯 API (已拆分, 2026-03-30)

此檔案已拆分為三個模組：
- dispatch_doc_link_crud.py — 派工→公文關聯 CRUD (search/link/unlink/documents)
- document_dispatch_links.py — 公文→派工關聯反向查詢 (dispatch-links/link-dispatch/unlink-dispatch/batch)
- dispatch_correspondence.py — 收發文對照確認與重建 (confirm/rebuild)

路由已由 __init__.py 分別 include，此檔案保留供參考。
"""
