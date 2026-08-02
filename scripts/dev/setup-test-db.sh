#!/bin/bash
# ============================================================
# 建立/重建測試資料庫 ck_documents_test
#
# 為什麼需要它（2026-08-03）：
#   測試套件長期「不能安全執行」。查證後真正的路徑是——
#   `client` fixture 跑真的 app，端點經 get_async_db 走模組級全域 engine，
#   連的是**生產庫** ck_documents。（`db_session` 反而因為傳同步 driver 給
#   create_async_engine，engine 根本建不起來，從未真的連上。）
#
#   conftest 現在會解析出獨立測試庫並 override get_async_db，
#   但那個庫要先存在 —— 就是這支腳本負責的事。
#
# 設計取捨：
#   - schema 從生產庫 pg_dump --schema-only（**唯讀**，不對生產做任何 DDL/DML）
#   - **不複製業務資料**（documents / KG / users 全部留空）：
#     測試不該依賴生產資料，而且生產 users 含 PII
#   - 只帶必要參照資料（role_permissions / site_navigation_items）+ 一個 seed user
#     那個 seed user 純粹是為了滿足 role_permissions.updated_by 的 FK
#
# 冪等：可重複執行。--reset 會先 DROP 再重建。
#
# 用法：
#   bash scripts/dev/setup-test-db.sh
#   bash scripts/dev/setup-test-db.sh --reset   # 資料被測試改壞時重來
# ============================================================

set -euo pipefail

CONTAINER="${TEST_DB_CONTAINER:-ck_missive_postgres}"
DB_USER="${TEST_DB_USER:-ck_user}"
PROD_DB="${TEST_DB_SOURCE:-ck_documents}"
TEST_DB="${TEST_DB_NAME:-ck_documents_test}"
SEED_TABLES=(role_permissions site_navigation_items)

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
psql_prod() { docker exec "$CONTAINER" psql -U "$DB_USER" -d "$PROD_DB" -tAc "$1"; }
psql_test() { docker exec "$CONTAINER" psql -U "$DB_USER" -d "$TEST_DB" -tAc "$1"; }

# 這個名字一樣就整支拒絕跑 —— 腳本本身也不該有「不小心打到生產」的路徑
if [[ "$TEST_DB" == "$PROD_DB" ]]; then
    echo -e "${RED}✗ 測試庫與來源庫同名（$PROD_DB），拒絕執行${NC}"; exit 2
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo -e "${RED}✗ 找不到執行中的容器 $CONTAINER${NC}"; exit 2
fi

echo -e "${CYAN}=== 建立測試資料庫 $TEST_DB（來源 schema：$PROD_DB，唯讀）===${NC}"

if [[ "${1:-}" == "--reset" ]]; then
    echo "  --reset：先移除既有測試庫"
    docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -q \
        -c "DROP DATABASE IF EXISTS $TEST_DB;" >/dev/null
fi

exists=$(docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$TEST_DB';")
if [[ -z "$exists" ]]; then
    docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -q \
        -c "CREATE DATABASE $TEST_DB OWNER $DB_USER;" >/dev/null
    echo "  建立資料庫 ✓"
else
    echo "  資料庫已存在（略過建立）"
fi

prod_tables=$(psql_prod "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
test_tables=$(psql_test "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")

if [[ "$test_tables" -lt "$prod_tables" ]]; then
    echo "  匯入 schema（$test_tables → 目標 $prod_tables）..."
    docker exec "$CONTAINER" sh -c \
        "pg_dump -U $DB_USER --schema-only --no-owner --no-privileges $PROD_DB | psql -U $DB_USER -d $TEST_DB -q" \
        2>&1 | grep -viE "^NOTICE|already exists|^SET|^ *$|set_config|^-+$|^\(1 row\)$" || true
    test_tables=$(psql_test "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
fi
echo "  schema：$test_tables / $prod_tables tables"

# seed user 只為滿足 role_permissions.updated_by 的 FK。
# 刻意不複製生產 users —— 那是真人資料。
psql_test "
INSERT INTO users (id, username, email, role, is_active)
VALUES (1, 'test_seed_user', 'test-seed@invalid.local', 'superuser', true)
ON CONFLICT (id) DO NOTHING;" >/dev/null
psql_test "SELECT setval(pg_get_serial_sequence('users','id'), 1000, true);" >/dev/null

for t in "${SEED_TABLES[@]}"; do
    psql_test "TRUNCATE $t CASCADE;" >/dev/null 2>&1 || true
    docker exec "$CONTAINER" sh -c \
        "pg_dump -U $DB_USER --data-only --no-owner -t $t $PROD_DB | psql -U $DB_USER -d $TEST_DB -q" \
        >/dev/null 2>&1
    src=$(psql_prod "SELECT count(*) FROM $t;")
    dst=$(psql_test "SELECT count(*) FROM $t;")
    if [[ "$src" == "$dst" ]]; then
        echo -e "  ${GREEN}✓${NC} $t：$dst 筆"
    else
        echo -e "  ${RED}✗${NC} $t：來源 $src 筆但只匯入 $dst 筆"; exit 1
    fi
done

# 業務資料必須是空的 —— 若不是，代表有人把生產資料倒進來了
biz=$(psql_test "SELECT count(*) FROM documents;")
if [[ "$biz" != "0" ]]; then
    echo -e "  ${RED}✗ documents 表有 $biz 筆資料；測試庫不應含業務資料${NC}"; exit 1
fi

echo -e "${GREEN}✓ 測試庫就緒${NC}（業務資料 0 筆）"
echo "  pytest 會自動使用它；要指定別的庫請設 TEST_DATABASE_URL。"
