#!/usr/bin/env bash
# ORM必須・直接SQL禁止（CLAUDE.md / .claude/rules/backend-infrastructure.md）。
#
# import-linter では「生SQLを書いたか」は判定できないため、ここで決定論的に弾く。
# SQLAlchemy の生SQL口である text(...) と exec_driver_sql(...) の使用を検出する。
# ORM / Core 式の通常利用ではこれらは不要。
set -euo pipefail

# repo ルートを解決（直接実行・pre-commit・CI のいずれからでも動くように）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TARGET="${REPO_ROOT}/backend/app"

# 生SQL口のパターン: 直前が識別子文字でない text( / exec_driver_sql(
pattern='(^|[^A-Za-z0-9_.])(text|exec_driver_sql)[[:space:]]*\('

if grep -rnE "${pattern}" "${TARGET}" --include='*.py'; then
  {
    echo ""
    echo "ERROR: 直接SQL（text(...) / exec_driver_sql(...)）を検出しました。"
    echo "SQLAlchemy 2.0 の ORM 経由でアクセスしてください（ORM必須・直接SQL禁止）。"
    echo "参照: .claude/rules/backend-infrastructure.md"
  } >&2
  exit 1
fi

echo "no raw SQL: OK"
