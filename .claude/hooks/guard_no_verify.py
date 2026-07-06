#!/usr/bin/env python3
"""PreToolUse ガード（Bash）: pre-commit / git フックを迂回する操作を禁止する。

遮断する迂回経路:
- git commit / git push の --no-verify（長形式）
- git commit の -n（--no-verify の短形式。git push の -n は --dry-run なので対象外）
- SKIP=... を付けた git commit（pre-commit のフック選択スキップ）
- pre-commit uninstall（フックの取り外し）
- core.hooksPath の変更（フックディレクトリの差し替え）

クォート内は除去してから判定する（コミットメッセージ中の "-n" 等を誤検知しない）。
例外時は fail-open（許可）。最終関門は CI。
"""

import json
import re
import sys

QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
# 単一ダッシュの短形式フラグ束に n を含む（例: -n / -an / -sn）。--long は対象外。
SHORT_N = re.compile(r"(?:^|\s)-[A-Za-z]*n[A-Za-z]*(?=\s|$)")


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def main() -> None:
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    stripped = QUOTED.sub(" ", command)

    # パイプ・連結で区切った1コマンド単位で判定する
    for seg in re.split(r"[|;&]+", stripped):
        is_git = re.search(r"\bgit\b", seg)
        is_commit = is_git and re.search(r"\bgit\b[^\n]*\bcommit\b", seg)
        is_push = is_git and re.search(r"\bgit\b[^\n]*\bpush\b", seg)

        if (is_commit or is_push) and "--no-verify" in seg:
            deny(
                "pre-commit を迂回する --no-verify は禁止です。"
                "フックが失敗したら迂回せず原因を修正してください（層③a）。"
            )
        if is_commit and SHORT_N.search(seg):
            deny(
                "git commit の -n（--no-verify の短形式）は禁止です。"
                "フックが失敗したら迂回せず原因を修正してください（層③a）。"
            )
        if is_commit and re.search(r"(?:^|\s)SKIP=\S+", seg):
            deny(
                "SKIP=... によるコミット時の pre-commit フックのスキップは禁止です。"
                "失敗するフックは迂回せず直してください（層③a）。"
            )
        if re.search(r"\bpre-commit\b\s+uninstall\b", seg):
            deny(
                "pre-commit uninstall（フックの取り外し）は禁止です。"
                "ローカル関門（層③a）を無効化しないでください。"
            )
        if is_git and "core.hooksPath" in seg:
            deny(
                "core.hooksPath の変更（git フックの差し替え）は禁止です。"
                "pre-commit の関門を保ってください（層③a）。"
            )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
