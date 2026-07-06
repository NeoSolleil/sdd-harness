#!/usr/bin/env python3
"""stack profile の契約適合を機械検証する（_schema/contract.md のスクリプト化）。

チェック内容（stdlib のみ・行ベースの浅い検証。深い意味検証は人間/AI レビューが担う）:
  E1. profile.yml が存在し、`id:` がディレクトリ名と一致する
  E2. 契約の必須キーが出現する（components / layers / forbidden_imports /
      arch_lint_cmd / bdd_runner / gherkin_source / step_defs_location / test_cmd /
      lint_cmd / format_check_cmd / typecheck_cmd / guard: とその必須サブキー）
  E3. layers の path / step_defs_location / composition_root が実在する
      （null は明示的な未配線として許容 = NOTE 運用）
  W1. guard の raw_scope_paths / forbidden_patterns が無い（DB 無しスタックなら妥当）→ 警告

使い方:
  python3 .claude/profiles/validate.py            # 全プロファイルを検証（エラーで exit 1）
  python3 .claude/profiles/validate.py <id>       # 特定プロファイルのみ
戻り値: エラー 0 件なら exit 0（警告は落とさない）。
"""

import os
import re
import sys

PROFILES_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROFILES_DIR))

REQUIRED_KEYS = [
    "id:",
    "components:",
    "layers:",
    "forbidden_imports:",
    "arch_lint_cmd:",
    "bdd_runner:",
    "gherkin_source:",
    "step_defs_location:",
    "test_cmd:",
    "lint_cmd:",
    "format_check_cmd:",
    "typecheck_cmd:",
    "guard:",
]
GUARD_REQUIRED = ["inner_paths:", "forbidden_imports:"]
GUARD_OPTIONAL = ["raw_scope_paths:", "forbidden_patterns:"]

# 実在チェック対象のパス値を拾う（inline map の path: と、単独キー）
PATH_VALUE = re.compile(
    r"^\s*(?:-\s*\{[^}]*\bpath:\s*|step_defs_location:\s*|composition_root:\s*)"
    r"([^\s,}#]+)"
)


def profile_ids(only: str | None) -> list[str]:
    ids = [
        n
        for n in sorted(os.listdir(PROFILES_DIR))
        if os.path.isdir(os.path.join(PROFILES_DIR, n))
        and os.path.isfile(os.path.join(PROFILES_DIR, n, "profile.yml"))
    ]
    return [i for i in ids if only is None or i == only]


def validate(profile_id: str) -> tuple[list[str], list[str]]:
    """(errors, warnings) を返す。"""
    errors: list[str] = []
    warnings: list[str] = []
    path = os.path.join(PROFILES_DIR, profile_id, "profile.yml")
    text = open(path, encoding="utf-8").read()
    lines = text.splitlines()

    # E1: id 一致
    m = re.search(r"^id:\s*(\S+)", text, re.MULTILINE)
    if not m:
        errors.append("E1: `id:` がありません")
    elif m.group(1) != profile_id:
        errors.append(f"E1: id '{m.group(1)}' がディレクトリ名 '{profile_id}' と不一致")

    # E2: 必須キーの出現（コメント行は除外して判定）
    body = "\n".join(ln for ln in lines if not ln.lstrip().startswith("#"))
    for key in REQUIRED_KEYS:
        if not re.search(rf"^\s*{re.escape(key)}", body, re.MULTILINE):
            errors.append(f"E2: 必須キー `{key}` が見つかりません")

    # guard ブロックのサブキー
    if re.search(r"^guard:", body, re.MULTILINE):
        guard_seg = body.split("\nguard:", 1)[-1]
        for key in GUARD_REQUIRED:
            if key not in guard_seg:
                errors.append(f"E2: guard ブロックに `{key}` がありません")
        for key in GUARD_OPTIONAL:
            if key not in guard_seg:
                warnings.append(
                    f"W1: guard ブロックに `{key}` が無い（DB 無しスタックなら妥当。意図的なら OK）"
                )

    # E3: パスの実在（null は許容 = 明示的未配線）
    for ln in lines:
        if ln.lstrip().startswith("#"):
            continue
        pm = PATH_VALUE.search(ln)
        if not pm:
            continue
        value = pm.group(1).strip("\"'")
        if value in ("null", "~", ""):
            continue
        if not os.path.exists(os.path.join(REPO_ROOT, value)):
            errors.append(f"E3: パス `{value}` が実在しません（{ln.strip()}）")

    return errors, warnings


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    ids = profile_ids(only)
    if not ids:
        print(f"validate: 対象プロファイルがありません（{only or 'profiles/*'}）")
        return 1
    total_errors = 0
    for pid in ids:
        errors, warnings = validate(pid)
        status = "NG" if errors else "OK"
        print(f"[{status}] {pid}: エラー {len(errors)} / 警告 {len(warnings)}")
        for e in errors:
            print(f"    ERROR {e}")
        for w in warnings:
            print(f"    warn  {w}")
        total_errors += len(errors)
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
