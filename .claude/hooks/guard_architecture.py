#!/usr/bin/env python3
"""PreToolUse ガード（Write|Edit|MultiEdit ＋ Bash）: アーキテクチャ違反の編集をブロックする。

- Write / Edit / MultiEdit: 書き込まれる本文（content / new_string / edits[].new_string）を検査。
- Bash: 内側パス（domain/application）への **シェル経由の書き込み**（リダイレクト・tee・sed -i）
  を遮断する。内容を検査できない書き込み経路を塞ぎ、Write/Edit（検査可能）へ誘導する。

設定は **stack profile** から読む（ハードコードしない）:
  .claude/profiles/<id>/profile.yml の `guard:` ブロック
    - inner_paths        … FW import を禁止する内側パス（domain/application）
    - forbidden_imports  … 内側が import してはならない外部フレームワーク
    - raw_scope_paths    … 直接SQL を禁止するパス
    - forbidden_patterns … 生SQL口（例: text( / exec_driver_sql(）

どのプロファイルが有効かは:
  1) .claude/profiles/.active（プロファイルidを1行）があればそれ
  2) 無ければ profiles/*/profile.yml が1つだけなら、それ
  3) 特定できなければ何もしない（fail-open）

実行環境に PyYAML が無い前提で、`guard:` ブロックだけを stdlib で読む極小パーサを内蔵する。
違反時は permissionDecision=deny で編集を止める。ガード自身が壊れても作業を止めない
よう、例外時は fail-open（許可）。最終的な関門は import-linter / pre-commit / CI。
"""

import glob
import json
import os
import re
import sys


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


def find_active_profile() -> str | None:
    prof_dir = os.path.join(_project_dir(), ".claude", "profiles")
    candidates = sorted(glob.glob(os.path.join(prof_dir, "*", "profile.yml")))
    if not candidates:
        return None
    ptr = os.path.join(prof_dir, ".active")
    if os.path.isfile(ptr):
        active = open(ptr, encoding="utf-8").read().strip()
        for p in candidates:
            if os.path.basename(os.path.dirname(p)) == active:
                return p
    return candidates[0] if len(candidates) == 1 else None


def _unquote(v: str) -> str:
    """スカラーからクォートを外し、クォート外の行末コメントを落とす。"""
    v = v.strip()
    if v and v[0] in "\"'":
        q = v[0]
        end = v.find(q, 1)
        if end != -1:
            return v[1:end]
    if " #" in v:
        v = v.split(" #", 1)[0].strip()
    return v


def parse_guard_block(path: str) -> dict[str, list[str]]:
    """profile.yml の top-level `guard:` ブロックだけを読む極小パーサ。

    想定する構造（2スペースインデント・block スタイルのスカラーリストのみ）:
        guard:
          key:
            - item
            - "item("
    """
    cfg: dict[str, list[str]] = {}
    lines = open(path, encoding="utf-8").read().splitlines()

    def indent(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    i, n = 0, len(lines)
    while i < n and not re.match(r"^guard:\s*(#.*)?$", lines[i]):
        i += 1
    if i >= n:
        return cfg
    i += 1  # guard: の次行から

    cur: str | None = None
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            i += 1
            continue
        if indent(line) == 0:  # 次の top-level キー → guard ブロック終端
            break
        if indent(line) == 2 and stripped.endswith(":"):
            cur = stripped[:-1].strip()
            cfg[cur] = []
        elif indent(line) >= 4 and stripped.startswith("- ") and cur is not None:
            cfg[cur].append(_unquote(stripped[2:]))
        i += 1
    return cfg


def _path_hits(file_path: str, prefixes: list[str]) -> bool:
    """絶対/相対どちらのパスでも、与えたプレフィックス配下かを判定。"""
    for p in prefixes:
        p = p.strip("/")
        if not p:
            continue
        if file_path.startswith(p + "/") or ("/" + p + "/") in file_path:
            return True
    return False


def check_bash(command: str) -> None:
    """シェル経由の内側パス書き込み（内容を検査できない経路）を遮断する。"""
    profile = find_active_profile()
    if not profile:
        return
    inner = parse_guard_block(profile).get("inner_paths", [])
    if not inner:
        return
    alt = "|".join(re.escape(p.strip("/")) + "/" for p in inner)
    patterns = (
        rf"(?:>>?)\s*[\"']?\S*(?:{alt})",                      # > / >> で内側へ
        rf"\btee\b(?:\s+-\S+)*\s+[\"']?\S*(?:{alt})",           # tee で内側へ
        rf"\bsed\b[^|;&\n]*\s-i\S*\s[^|;&\n]*(?:{alt})",        # sed -i で内側を直接編集
    )
    for pat in patterns:
        if re.search(pat, command):
            deny(
                "domain/application 配下の変更をシェル（リダイレクト / tee / sed -i）で"
                "行うことは禁止です。Write / Edit ツールで編集してください"
                "（ガードが書き込み内容を検査できるため）。"
                "（.claude/rules/ 参照。最終関門は import-linter / CI）"
            )
    # cp / mv の宛先（末尾トークン）が内側パス
    for seg in re.split(r"[|;&]+", command):
        toks = seg.split()
        if len(toks) >= 3 and toks[0] in ("cp", "mv"):
            dest = toks[-1].strip("\"'")
            if _path_hits(dest, inner) or any(
                dest.startswith(p.strip("/") + "/") or dest.rstrip("/") == p.strip("/")
                for p in inner
            ):
                deny(
                    "domain/application 配下への cp / mv は禁止です。"
                    "Write / Edit ツールで編集してください（内容を検査できるため）。"
                )


def main() -> None:
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}

    # Bash: コマンド文字列を検査（file_path は無い）
    command = tool_input.get("command")
    if isinstance(command, str) and command.strip():
        check_bash(command)
        return

    file_path = (tool_input.get("file_path") or "").replace("\\", "/")
    if not file_path:
        return
    # Write は content、Edit は new_string、MultiEdit は edits[].new_string。結合して検査する。
    pieces = [tool_input.get("content"), tool_input.get("new_string")]
    for e in tool_input.get("edits") or []:
        if isinstance(e, dict):
            pieces.append(e.get("new_string"))
    content = "\n".join(p for p in pieces if isinstance(p, str))
    if not content:
        return

    profile = find_active_profile()
    if not profile:
        return  # プロファイル特定不可 → fail-open（CA強制は import-linter/CI が担保）
    cfg = parse_guard_block(profile)

    inner_paths = cfg.get("inner_paths", [])
    forbidden_imports = cfg.get("forbidden_imports", [])
    raw_scope = cfg.get("raw_scope_paths", [])
    forbidden_patterns = cfg.get("forbidden_patterns", [])

    # 内側パスへの FW import を弾く
    if inner_paths and forbidden_imports and _path_hits(file_path, inner_paths):
        alt = "|".join(re.escape(m) for m in forbidden_imports)
        rx = re.compile(rf"^\s*(?:import|from)\s+({alt})\b", re.MULTILINE)
        m = rx.search(content)
        if m:
            deny(
                "Clean Architecture 違反: domain/application は web/ORM フレームワーク"
                f"（{m.group(1)}）を import できません。"
                "入出力検証は adapters/schemas、永続化は infrastructure に置いてください。"
                "（.claude/rules/ 参照。import-linter でも強制）"
            )

    # 対象パスでの直接SQLを弾く（末尾 "(" は前方一致トークンとして扱う）
    if raw_scope and forbidden_patterns and _path_hits(file_path, raw_scope):
        tokens = "|".join(re.escape(p.rstrip("(").strip()) for p in forbidden_patterns)
        rx = re.compile(rf"(?:^|[^A-Za-z0-9_.])({tokens})\s*\(", re.MULTILINE)
        if rx.search(content):
            deny(
                "ORM必須・直接SQL禁止: text(...) / exec_driver_sql(...) は使用できません。"
                "SQLAlchemy 2.0 の ORM でアクセスしてください。"
                "（.claude/rules/backend-infrastructure.md 参照）"
            )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # fail-open: ガードが壊れても編集をブロックしない（後段の関門が残る）
        sys.exit(0)
