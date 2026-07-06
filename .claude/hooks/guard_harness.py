#!/usr/bin/env python3
"""PreToolUse ガード（Write|Edit|MultiEdit｜Bash）: 人間ゲートとハーネス自己保護。

deny ではなく **ask**（許可確認ダイアログ）を返し、人間の明示判断を要求する:

1. 承認ゲート — specs/ 配下への `Status: Approved` を含む書き込み。
   Draft→Approved は人間の承認行為（CLAUDE.md の SDD ワークフロー）。AI の自己承認を防ぎ、
   人間の指示による正当な更新はダイアログの承認で通す。
2. ハーネス自己保護 — 強制層への書き込み:
   - .claude/hooks/（ガード本体・自己テスト）
   - .claude/settings.json（フック登録）
   - .claude/profiles/<id>/profile.yml（guard: 判定値の単一の真実）
   - .claude/profiles/apply.py・validate.py・_schema/（差し替え機構と契約）
   - .claude/rules/（④生成物。直接編集は常に誤り＝正しくは profiles/<id>/rules/ 側）
   - .github/workflows/・.pre-commit-config.yaml・backend/scripts/（コミット/CI の関門）
   「ゲートを通すためにガードを弱める」変更を人間の目なしに行わせない（HARNESS.md）。
3. 上記パス・specs/ への Bash 書き込み（リダイレクト・tee・sed -i・cp/mv/rm）も同様に ask。

例外時は fail-open（許可）。skills / agents / profiles の rules への書き込みは対象外
（知識の追記は通常運用。プロファイル契約は validate.py と pre-commit が別途検査する）。
"""

import json
import re
import sys

# 強制層のパス（Write|Edit|MultiEdit の file_path 用。\ は / に正規化してから判定）
ENFORCEMENT_PATH = re.compile(
    r"(?:^|/)(?:"
    r"\.claude/hooks/"
    r"|\.claude/rules/"
    r"|\.claude/settings\.json"
    r"|\.claude/profiles/(?:apply\.py|validate\.py|_schema/)"
    r"|\.claude/profiles/[^/]+/profile\.yml"
    r"|\.github/workflows/"
    r"|\.pre-commit-config\.yaml"
    r"|backend/scripts/"  # profile の detect_cmd が指す検査スクリプト（スタック追加時はここも確認）
    r")"
)
SPECS_PATH = re.compile(r"(?:^|/)specs/")
# 行頭の Status: Approved（承認は人間の行為）
STATUS_APPROVED = re.compile(r"^\s*Status:\s*Approved\b", re.MULTILINE | re.IGNORECASE)


def _bash_write_re(target: str) -> "re.Pattern[str]":
    """target（パス断片の正規表現）への書き込みを伴う bash コマンドの検出。

    target は `|` を含む選択式でもよい（必ず (?:...) で括ってから埋め込む。
    括らないと選択肢が外側に漏れ、パスに言及しただけのコマンドまで誤検知する）。
    """
    t = rf"(?:{target})"
    return re.compile(
        r"(?:"
        rf">>?\s*['\"]?[^\s'\"|;&]*{t}"  # > file / >> file
        rf"|\btee\b(?:\s+-\S+)*\s+['\"]?[^\s'\"|;&]*{t}"  # tee [-a] file
        rf"|\b(?:sed|perl)\b[^\n|;&]*\s-i[^\n|;&]*{t}"  # in-place 編集
        rf"|\b(?:cp|mv|rm)\b[^\n|;&]*{t}"  # コピー・移動・削除
        r")"
    )


BASH_WRITE_ENFORCEMENT = _bash_write_re(
    r"\.claude/(?:hooks|rules)/"
    r"|\.claude/settings\.json"
    r"|\.claude/profiles/(?:apply\.py|validate\.py|_schema/)"
    r"|\.claude/profiles/[^\s'\"|;&]*profile\.yml"
    r"|\.github/workflows"
    r"|\.pre-commit-config\.yaml"
    r"|backend/scripts/"
)
BASH_WRITE_SPECS = _bash_write_re(r"specs/")


def ask(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def check_bash(tool_input: dict) -> None:
    command = (tool_input.get("command") or "").replace("\\", "/")
    if not command:
        return
    if BASH_WRITE_ENFORCEMENT.search(command):
        ask(
            "ハーネス強制層（hooks / settings.json / profile.yml / apply・validate・_schema / "
            "rules生成物 / CI / pre-commit / scripts）への Bash 書き込みです。"
            "ガードの変更は人間の明示指示が必要です（HARNESS.md）。"
        )
    if BASH_WRITE_SPECS.search(command):
        ask(
            "specs/（SDD 正本）への Bash 書き込みです。成果物の編集は Write / Edit で行い、"
            "Status 変更は人間承認に基づいてください（specs/README.md）。"
        )


def check_write_edit(tool_input: dict) -> None:
    file_path = (tool_input.get("file_path") or "").replace("\\", "/")
    if not file_path:
        return
    if ENFORCEMENT_PATH.search(file_path):
        ask(
            "ハーネス強制層（hooks / settings.json / profile.yml / apply・validate・_schema / "
            "rules生成物 / CI / pre-commit / scripts）の変更です。"
            "ユーザーの明示指示に基づく変更か確認してください。ガードを弱める変更は禁止です"
            "（HARNESS.md。なお .claude/rules/ は生成物＝修正は profiles/<id>/rules/ 側へ）。"
        )
    if SPECS_PATH.search(file_path):
        pieces = [tool_input.get("content"), tool_input.get("new_string")]
        for edit in tool_input.get("edits") or []:  # MultiEdit
            if isinstance(edit, dict):
                pieces.append(edit.get("new_string"))
        content = "\n".join(p for p in pieces if isinstance(p, str))
        if content and STATUS_APPROVED.search(content):
            ask(
                "specs/ 成果物への『Status: Approved』の書き込み＝人間承認ゲートです。"
                "ユーザーが承認を明示しましたか？（自己承認は禁止。specs/README.md）"
            )


def main() -> None:
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    if (data.get("tool_name") or "") == "Bash":
        check_bash(tool_input)
        return
    check_write_edit(tool_input)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # fail-open: ガードが壊れても作業をブロックしない（後段の関門とレビューが残る）
        sys.exit(0)
