#!/usr/bin/env python3
"""PreToolUse ガード（Write|Edit|MultiEdit ＋ Bash）: SDD の段階ゲートを決定論化する。

specs/<feature>/ の成果物（discovery.md / requirements.md / acceptance.feature /
design.md / tasks.md）に対して:

1) **順序ゲート**: 前段の文書が `Status: Approved` でない限り、次段の成果物を書けない。
     discovery.md → (requirements.md ＋ acceptance.feature) → design.md → tasks.md
2) **凍結**: `Status: Approved` の文書（discovery/requirements/design）は編集できない。
   例外は Status 行を触る編集（＝Draft への差し戻し）だけ。acceptance.feature は自前の
   Status を持たないため requirements.md の Status に従って凍結する（仕様変更は
   requirements.md を Draft に戻してから specify で行う）。tasks.md は実装中の
   追記・進捗更新がありうるため凍結しない（順序ゲートのみ）。
3) **シェル迂回の遮断**: specs 配下の成果物へのリダイレクト / tee / sed -i / cp / mv を
   拒否し、内容を検査できる Write / Edit 経路に限定する。

このガードが強制するのは「順序」と「凍結」だけ。**誰が承認したか（人間か AI か）は
ツール入力からは判定できない**ため、承認の主体は人間ゲートというプロセス規律に残る。
例外時は fail-open（壊れても作業を止めない）。
"""

import json
import os
import re
import sys

# 段階成果物 → 前提となる前段の文書（Status: Approved が必要）
PREREQ = {
    "discovery.md": None,
    "requirements.md": "discovery.md",
    "acceptance.feature": "discovery.md",
    "design.md": "requirements.md",
    "tasks.md": "design.md",
}
# Approved で凍結する文書（tasks.md は除外・acceptance.feature は requirements 経由）
FROZEN_WHEN_APPROVED = ("discovery.md", "requirements.md", "design.md")

STATUS_RE = re.compile(r"^Status:\s*(\S+)", re.MULTILINE)
ARTIFACT_RE = (
    r"specs/[^/\s\"']+/"
    r"(?:discovery\.md|requirements\.md|acceptance\.feature|design\.md|tasks\.md)"
)


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


def _project_dir() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def resolve(file_path: str):
    """specs/<feature>/<成果物> なら (feature_dir_abs, fname) を返す。それ以外は None。"""
    parts = file_path.split("/")
    if "specs" not in parts:
        return None
    i = len(parts) - 1 - parts[::-1].index("specs")
    if len(parts) - i - 1 != 2:  # specs/<feature>/<file> の深さのみ対象
        return None
    feature, fname = parts[i + 1], parts[i + 2]
    if fname not in PREREQ:
        return None
    root = "/".join(parts[: i + 1])
    if not os.path.isabs(file_path):
        root = os.path.join(_project_dir(), root)
    return os.path.join(root, feature), fname


def status_of(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            m = STATUS_RE.search(f.read())
        return m.group(1) if m else None
    except OSError:
        return None


def touches_status(tool_input: dict) -> bool:
    """この編集が Status 行の変更（差し戻し）を含むか。"""
    content = tool_input.get("content")
    if isinstance(content, str):  # Write: 全文置換。新しい Status が Approved 以外なら差し戻し
        m = STATUS_RE.search(content)
        return bool(m and m.group(1) != "Approved")
    edits = list(tool_input.get("edits") or []) + [tool_input]  # MultiEdit / Edit
    for e in edits:
        if not isinstance(e, dict):
            continue
        old, new = e.get("old_string"), e.get("new_string")
        if (isinstance(old, str) and "Status:" in old) or (
            isinstance(new, str) and "Status:" in new
        ):
            return True
    return False


def check_bash(command: str) -> None:
    """specs 成果物へのシェル書き込み（内容を検査できない経路）を遮断する。"""
    patterns = (
        rf"(?:>>?)\s*[\"']?\S*{ARTIFACT_RE}",                  # > / >> で成果物へ
        rf"\btee\b(?:\s+-\S+)*\s+[\"']?\S*{ARTIFACT_RE}",       # tee で成果物へ
        rf"\bsed\b[^|;&\n]*\s-i\S*\s[^|;&\n]*{ARTIFACT_RE}",    # sed -i で直接編集
    )
    for pat in patterns:
        if re.search(pat, command):
            deny(
                "specs 配下の SDD 成果物をシェル（リダイレクト / tee / sed -i）で"
                "変更することは禁止です。Write / Edit ツールで編集してください"
                "（SDD ゲート（順序・凍結）が内容を検査できるため）。"
            )
    # cp / mv の宛先（末尾トークン）が成果物
    for seg in re.split(r"[|;&]+", command):
        toks = seg.split()
        if len(toks) >= 3 and toks[0] in ("cp", "mv"):
            dest = toks[-1].strip("\"'")
            if re.search(ARTIFACT_RE + r"$", dest):
                deny(
                    "specs 配下の SDD 成果物への cp / mv は禁止です。"
                    "Write / Edit ツールで編集してください（SDD ゲートが検査するため）。"
                )


def main() -> None:
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}

    command = tool_input.get("command")
    if isinstance(command, str) and command.strip():
        check_bash(command)
        return

    file_path = (tool_input.get("file_path") or "").replace("\\", "/")
    if not file_path:
        return
    resolved = resolve(file_path)
    if not resolved:
        return
    feature_dir, fname = resolved

    # 1) 順序ゲート: 前段が Approved でなければ着手不可
    prereq = PREREQ[fname]
    if prereq:
        pre_status = status_of(os.path.join(feature_dir, prereq))
        if pre_status != "Approved":
            deny(
                f"SDD 順序ゲート: {prereq} が Status: Approved になるまで "
                f"{fname} には着手できません（現在: {pre_status or '未作成'}）。"
                "前段を完成させ、人間レビューの承認を得てください。"
            )

    # 2) 凍結: Approved の文書は Status 差し戻し以外の編集不可
    if fname in FROZEN_WHEN_APPROVED:
        if status_of(os.path.join(feature_dir, fname)) == "Approved" and not touches_status(
            tool_input
        ):
            deny(
                f"{fname} は Status: Approved で凍結されています。変更するには"
                " Status を Draft に戻し（Status 行を含む編集は許可されます）、"
                "修正後に人間の再承認を得てください（spec-anchored）。"
            )
    elif fname == "acceptance.feature":
        if status_of(os.path.join(feature_dir, "requirements.md")) == "Approved":
            deny(
                "acceptance.feature は requirements.md=Approved により凍結されています。"
                "仕様変更は requirements.md の Status を Draft に戻してから"
                " specify（scenario-author）で行い、再承認を得てください。"
            )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # fail-open: ガード自身の不具合で作業を止めない
        sys.exit(0)
