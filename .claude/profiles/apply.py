#!/usr/bin/env python3
"""active な stack profile の内容を .claude/ へ配置する（真の差し替え式）。

Claude Code は .claude/rules・.claude/skills・.claude/agents を固定パスから
自動ロードする。stack 固有の rules/skills/agents は profiles/<id>/ を単一の
真実として持ち、このスクリプトが active プロファイルからそれらを .claude/ へ
コピーする。配置物は .gitignore 済みの生成物（追跡しない）。

使い方:
    python3 .claude/profiles/apply.py            # active を配置
    python3 .claude/profiles/apply.py <id>       # <id> を active にして配置
    python3 .claude/profiles/apply.py --auto     # SessionStart フック用: 静かに配置し、
                                                 # 問題があっても exit 0（fail-open）で
                                                 # 1行の警告だけ出す

active の決定:
    1) 引数 <id> があればそれ（.active も更新）
    2) profiles/.active があればそのid
    3) profile.yml が1つだけならそれ
スタックを切り替えると、前回配置した注入物を掃除してから入れ替える
（.claude/.profile-applied に前回の配置一覧を記録）。stdlib のみ。
"""

import json
import os
import shutil
import sys

PROFILES_DIR = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.dirname(PROFILES_DIR)
MANIFEST = os.path.join(CLAUDE_DIR, ".profile-applied")
ACTIVE_PTR = os.path.join(PROFILES_DIR, ".active")

# profiles/<id>/<sub> を .claude/<sub> へ配置する対象
INJECT = {
    "rules": "rules",       # profiles/<id>/rules/*    → .claude/rules/
    "skills": "skills",     # profiles/<id>/skills/<n>/→ .claude/skills/<n>/
    "agents": "agents",     # profiles/<id>/agents/*   → .claude/agents/
}


def profile_ids() -> list[str]:
    ids = []
    for name in sorted(os.listdir(PROFILES_DIR)):
        d = os.path.join(PROFILES_DIR, name)
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "profile.yml")):
            ids.append(name)
    return ids


def resolve_active(arg: str | None) -> str:
    ids = profile_ids()
    if not ids:
        sys.exit("エラー: profiles/ に profile.yml が見つかりません。")
    if arg:
        if arg not in ids:
            sys.exit(f"エラー: プロファイル '{arg}' が見つかりません。候補: {ids}")
        return arg
    if os.path.isfile(ACTIVE_PTR):
        want = open(ACTIVE_PTR, encoding="utf-8").read().strip()
        if want in ids:
            return want
        sys.exit(f"エラー: .active='{want}' が実在しません。候補: {ids}")
    if len(ids) == 1:
        return ids[0]
    sys.exit(f"エラー: プロファイルが複数あります。id を指定してください: {ids}")


def cleanup_prior() -> None:
    if not os.path.isfile(MANIFEST):
        return
    try:
        prior = json.load(open(MANIFEST, encoding="utf-8"))
    except Exception:
        prior = []
    for rel in prior:
        target = os.path.join(CLAUDE_DIR, rel)
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
        elif os.path.isfile(target):
            os.remove(target)


def inject(active: str) -> list[str]:
    src_root = os.path.join(PROFILES_DIR, active)
    applied: list[str] = []
    for sub in INJECT.values():
        src = os.path.join(src_root, sub)
        if not os.path.isdir(src):
            continue
        dst_dir = os.path.join(CLAUDE_DIR, sub)
        os.makedirs(dst_dir, exist_ok=True)
        for name in sorted(os.listdir(src)):
            s = os.path.join(src, name)
            d = os.path.join(dst_dir, name)
            if os.path.isdir(s):                       # skill ディレクトリ
                if os.path.isdir(d):
                    shutil.rmtree(d, ignore_errors=True)
                shutil.copytree(s, d)
            else:                                      # rule / agent ファイル
                shutil.copy2(s, d)
            applied.append(os.path.relpath(d, CLAUDE_DIR))
    return applied


def _apply(arg: str | None) -> tuple[str, list[str]]:
    active = resolve_active(arg)
    cleanup_prior()
    applied = inject(active)
    with open(ACTIVE_PTR, "w", encoding="utf-8") as f:
        f.write(active + "\n")
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(applied, f, ensure_ascii=False, indent=2)
    return active, applied


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--auto"]
    auto = "--auto" in sys.argv[1:]
    arg = args[0] if args else None

    if auto:
        # SessionStart フック用: 静かに・速く・絶対に失敗で止めない（fail-open）
        try:
            active, applied = _apply(arg)
            print(f"[profiles] applied '{active}' ({len(applied)} items)")
            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "validate", os.path.join(PROFILES_DIR, "validate.py")
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                errors, _ = mod.validate(active)
                if errors:
                    print(f"[profiles] warning: contract errors in '{active}': "
                          + "; ".join(errors[:3]))
            except Exception:
                pass  # 検証自体の不具合では警告も出さない
        except SystemExit:
            print("[profiles] warning: profile 未解決（apply スキップ。手動: apply.py <id>）")
        except Exception as e:  # noqa: BLE001
            print(f"[profiles] warning: apply 失敗（{e}）")
        sys.exit(0)

    active, applied = _apply(arg)
    print(f"applied profile: {active}")
    for rel in applied:
        print(f"  + .claude/{rel}")
    print(f"\n{len(applied)} 件を配置。active='{active}'（.claude/.profile-applied に記録）")


if __name__ == "__main__":
    main()
