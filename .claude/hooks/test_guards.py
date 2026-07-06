#!/usr/bin/env python3
"""ハーネスの guard フック4本の自己テスト（回帰防止）。

対象: guard_no_verify / guard_architecture / guard_sdd_gates / guard_harness
方針: 各フックを実際のイベント JSON（stdin）で subprocess 起動し、
      permissionDecision の DENY / ASK / ALLOW を期待値と突き合わせる。
      「迂回=DENY」「人間ゲート=ASK」と「正当操作=ALLOW（誤検知しない）」の両面を検査する。

実行: python3 .claude/hooks/test_guards.py   （stdlib のみ・数秒で完了）
強制: pre-commit（.claude 変更時）と CI の harness ジョブが実行する。
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
REPO_ROOT = HOOKS_DIR.parents[1]  # .claude/hooks → repo root

results: list[bool] = []


def run(hook: str, desc: str, payload: dict, expect: str, project_dir: str) -> None:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": project_dir}
    p = subprocess.run(
        [sys.executable, str(HOOKS_DIR / hook)],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )
    if '"permissionDecision": "deny"' in p.stdout:
        got = "DENY"
    elif '"permissionDecision": "ask"' in p.stdout:
        got = "ASK"
    else:
        got = "ALLOW"
    ok = got == expect
    results.append(ok)
    print(f"  [{'OK ' if ok else '!!NG'}] {got:5s}(期待{expect:5s}) {desc}")


def bash(cmd: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


def w(fp: str, content: str) -> dict:
    return {"tool_input": {"file_path": fp, "content": content}}


def e(fp: str, old: str, new: str) -> dict:
    return {"tool_input": {"file_path": fp, "old_string": old, "new_string": new}}


# =============================================================================
# guard_no_verify — pre-commit / git フック迂回の遮断
# =============================================================================
def test_no_verify() -> None:
    print("=== guard_no_verify（迂回経路の遮断）===")
    R = str(REPO_ROOT)
    cases = [
        ("git commit --no-verify", bash("git commit --no-verify -m x"), "DENY"),
        ("git commit -n（短形式）", bash("git commit -n -m x"), "DENY"),
        ("git commit -an（束ね短形式）", bash("git commit -an -m x"), "DENY"),
        ("メッセージ内の -n は許可", bash('git commit -m "use -n flag carefully"'), "ALLOW"),
        ("SKIP= 付き commit", bash("SKIP=pytest git commit -m x"), "DENY"),
        ("SKIP= 付き pre-commit run（手動は許可）", bash("SKIP=x pre-commit run --all-files"), "ALLOW"),
        ("git push --no-verify", bash("git push --no-verify"), "DENY"),
        ("git push -n は dry-run（許可）", bash("git push -n origin main"), "ALLOW"),
        ("pre-commit uninstall", bash("pre-commit uninstall"), "DENY"),
        ("core.hooksPath 差し替え", bash("git config core.hooksPath /dev/null"), "DENY"),
        ("git -c core.hooksPath= commit", bash("git -c core.hooksPath=/tmp commit -m x"), "DENY"),
        ("通常の git commit（許可）", bash('git commit -m "feat: 追加"'), "ALLOW"),
        ("git commit --amend（許可）", bash("git commit --amend --no-edit"), "ALLOW"),
    ]
    for desc, payload, expect in cases:
        run("guard_no_verify.py", desc, payload, expect, R)


# =============================================================================
# guard_architecture — CA 違反編集・シェル迂回の遮断（実リポジトリの profile を使用）
# =============================================================================
def test_architecture() -> None:
    print("=== guard_architecture（Write/Edit/MultiEdit ＋ Bash 迂回）===")
    R = str(REPO_ROOT)
    D, A = "backend/app/domain", "backend/app/application"
    cases = [
        ("Write: domain に fastapi", w(f"{D}/g.py", "import fastapi"), "DENY"),
        ("Write: domain に dataclasses（許可）", w(f"{D}/g.py", "from dataclasses import dataclass"), "ALLOW"),
        ("Edit: application に sqlalchemy", e(f"{A}/u.py", "a", "import sqlalchemy"), "DENY"),
        ("Write: adapters に fastapi（許可=内側でない）",
         w("backend/app/adapters/api/r.py", "from fastapi import APIRouter"), "ALLOW"),
        ("Write: infrastructure に直接SQL text(",
         w("backend/app/infrastructure/r.py", 'conn.execute(text("SELECT 1"))'), "DENY"),
        ("MultiEdit: domain に fastapi",
         {"tool_input": {"file_path": f"{D}/g.py",
                         "edits": [{"old_string": "a", "new_string": "from fastapi import APIRouter"}]}},
         "DENY"),
        ("MultiEdit: domain 正常編集（許可）",
         {"tool_input": {"file_path": f"{D}/g.py",
                         "edits": [{"old_string": "a", "new_string": "from enum import Enum"}]}},
         "ALLOW"),
        ("Bash: echo リダイレクトで domain へ", bash(f'echo "import fastapi" > {D}/x.py'), "DENY"),
        ("Bash: >> 追記で application へ", bash(f"echo x >> {A}/uc.py"), "DENY"),
        ("Bash: tee で domain へ", bash(f"echo x | tee {D}/y.py"), "DENY"),
        ("Bash: sed -i で domain 直接編集", bash(f"sed -i 's/a/b/' {D}/x.py"), "DENY"),
        ("Bash: cp で domain へ（宛先）", bash(f"cp /tmp/x.py {D}/y.py"), "DENY"),
        ("Bash: mv で application へ（宛先）", bash(f"mv /tmp/x.py {A}/y.py"), "DENY"),
        ("Bash: cp domain→/tmp（許可=宛先が外）", bash(f"cp {D}/x.py /tmp/out.py"), "ALLOW"),
        ("Bash: domain を読むだけ（許可）", bash(f"grep -n foo {D}/x.py"), "ALLOW"),
        ("Bash: domain から /tmp へ出力（許可）", bash(f"cat {D}/x.py > /tmp/out.txt"), "ALLOW"),
        ("Bash: adapters へのリダイレクト（許可=内側でない）",
         bash("echo x > backend/app/adapters/api/r.py"), "ALLOW"),
    ]
    for desc, payload, expect in cases:
        run("guard_architecture.py", desc, payload, expect, R)


# =============================================================================
# guard_sdd_gates — 順序ゲート・凍結・シェル迂回（一時プロジェクトの specs を使用）
# =============================================================================
def _doc(status: str) -> str:
    return f"# doc\n\nStatus: {status}\n\n本文\n"


def test_sdd_gates() -> None:
    print("=== guard_sdd_gates（順序・凍結・シェル迂回）===")
    tmp = tempfile.mkdtemp(prefix="gates-test-")
    feat = Path(tmp) / "specs" / "0001-t"
    feat.mkdir(parents=True)
    REQ = "specs/0001-t/requirements.md"
    ACC = "specs/0001-t/acceptance.feature"
    DES = "specs/0001-t/design.md"
    TSK = "specs/0001-t/tasks.md"
    DIS = "specs/0001-t/discovery.md"

    def set_file(name: str, status: str | None) -> None:
        p = feat / name
        if status is None:
            if p.exists():
                p.unlink()
        else:
            p.write_text(_doc(status), encoding="utf-8")

    # --- 順序ゲート ---
    set_file("discovery.md", "Draft")
    set_file("requirements.md", None)
    run("guard_sdd_gates.py", "順序: discovery=Draft で requirements 着手", w(REQ, _doc("Draft")), "DENY", tmp)
    set_file("discovery.md", "Approved")
    run("guard_sdd_gates.py", "順序: discovery=Approved で requirements 着手（許可）", w(REQ, _doc("Draft")), "ALLOW", tmp)
    set_file("requirements.md", "Draft")
    run("guard_sdd_gates.py", "順序: requirements=Draft で design 着手", w(DES, _doc("Draft")), "DENY", tmp)
    set_file("requirements.md", "Approved")
    run("guard_sdd_gates.py", "順序: requirements=Approved で design 着手（許可）", w(DES, _doc("Draft")), "ALLOW", tmp)
    set_file("design.md", "Draft")
    run("guard_sdd_gates.py", "順序: design=Draft で tasks 着手", w(TSK, _doc("Draft")), "DENY", tmp)
    set_file("design.md", "Approved")
    run("guard_sdd_gates.py", "順序: design=Approved で tasks 着手（許可）", w(TSK, _doc("Draft")), "ALLOW", tmp)

    # --- 凍結（requirements / acceptance / discovery）---
    set_file("requirements.md", "Approved")
    run("guard_sdd_gates.py", "凍結: Approved requirements の通常 Edit", e(REQ, "本文", "変更"), "DENY", tmp)
    run("guard_sdd_gates.py", "凍結解除: Status 行を触る Edit（差し戻し・許可）",
        e(REQ, "Status: Approved", "Status: Draft"), "ALLOW", tmp)
    run("guard_sdd_gates.py", "凍結解除: Write 全文で Status: Draft（許可）", w(REQ, _doc("Draft")), "ALLOW", tmp)
    run("guard_sdd_gates.py", "凍結: Write 全文が Status: Approved のまま内容変更", w(REQ, _doc("Approved")), "DENY", tmp)
    run("guard_sdd_gates.py", "凍結: requirements=Approved 中の acceptance 編集",
        e(ACC, "a", "b"), "DENY", tmp)
    set_file("requirements.md", "Draft")
    run("guard_sdd_gates.py", "凍結解除: requirements=Draft なら acceptance 編集可",
        e(ACC, "a", "b"), "ALLOW", tmp)
    run("guard_sdd_gates.py", "凍結: Approved discovery の通常 Edit",
        e(DIS, "本文", "変更"), "DENY", tmp)
    # --- tasks.md は凍結しない（実行段階の追記に道を残す）---
    set_file("tasks.md", "Approved")
    set_file("design.md", "Approved")
    run("guard_sdd_gates.py", "例外: Approved tasks.md の編集は許可（進捗追記）",
        e(TSK, "本文", "T-01 done"), "ALLOW", tmp)

    # --- 対象外ファイル・シェル迂回 ---
    run("guard_sdd_gates.py", "対象外: specs 配下の非成果物（許可）",
        w("specs/0001-t/notes.md", "memo"), "ALLOW", tmp)
    run("guard_sdd_gates.py", "対象外: specs 外のファイル（許可）",
        w("backend/app/adapters/api/r.py", "x = 1"), "ALLOW", tmp)
    run("guard_sdd_gates.py", "Bash: リダイレクトで requirements へ",
        bash(f"echo x > {REQ}"), "DENY", tmp)
    run("guard_sdd_gates.py", "Bash: sed -i で design 直接編集",
        bash(f"sed -i 's/a/b/' {DES}"), "DENY", tmp)
    run("guard_sdd_gates.py", "Bash: cp で tasks へ（宛先）",
        bash(f"cp /tmp/x.md {TSK}"), "DENY", tmp)
    run("guard_sdd_gates.py", "Bash: specs を読むだけ（許可）",
        bash(f"grep -n Status {REQ}"), "ALLOW", tmp)
    run("guard_sdd_gates.py", "Bash: specs から /tmp へ出力（許可）",
        bash(f"cat {REQ} > /tmp/out.md"), "ALLOW", tmp)

    shutil.rmtree(tmp, ignore_errors=True)


# =============================================================================
# guard_harness — 人間ゲート（自己承認の ask）とハーネス自己保護（強制層の ask）
# =============================================================================
def test_harness() -> None:
    print("=== guard_harness（承認ゲート・強制層の自己保護）===")
    R = str(REPO_ROOT)
    REQ = "specs/0001-t/requirements.md"
    cases = [
        # --- 強制層への Write/Edit → ASK ---
        ("Write: hooks のガード本体", w(".claude/hooks/guard_architecture.py", "x = 1"), "ASK"),
        ("Edit: settings.json（フック登録）", e(".claude/settings.json", "a", "b"), "ASK"),
        ("Write: profile.yml（guard: 判定値）",
         w(".claude/profiles/python-fastapi/profile.yml", "guard: {}"), "ASK"),
        ("Write: profiles/apply.py（差し替え機構）", w(".claude/profiles/apply.py", "pass"), "ASK"),
        ("Edit: profiles/_schema/（契約）", e(".claude/profiles/_schema/contract.md", "a", "b"), "ASK"),
        ("Write: .claude/rules/（④生成物への直接編集）", w(".claude/rules/backend-domain.md", "x"), "ASK"),
        ("Edit: CI ワークフロー", e(".github/workflows/ci.yml", "a", "b"), "ASK"),
        ("Write: .pre-commit-config.yaml", w(".pre-commit-config.yaml", "repos: []"), "ASK"),
        ("Write: backend/scripts/（検査スクリプト）", w("backend/scripts/check_no_raw_sql.sh", "true"), "ASK"),
        # --- 通常運用は ALLOW（誤検知しない）---
        ("Write: profile の skills（知識の追記・許可）",
         w(".claude/profiles/python-fastapi/skills/backend-architecture/SKILL.md", "x"), "ALLOW"),
        ("Write: profile の rules（②単一の真実・許可）",
         w(".claude/profiles/python-fastapi/rules/backend-domain.md", "x"), "ALLOW"),
        ("Edit: core エージェント（散文・許可）", e(".claude/agents/product-analyst.md", "a", "b"), "ALLOW"),
        ("Write: 実装コード（許可）", w("backend/app/domain/note.py", "x = 1"), "ALLOW"),
        # --- specs への自己承認 → ASK ---
        ("Write: specs に Status: Approved（自己承認）", w(REQ, "# r\n\nStatus: Approved\n"), "ASK"),
        ("Write: specs に Status: Draft（許可）", w(REQ, "# r\n\nStatus: Draft\n"), "ALLOW"),
        ("Edit: new_string に Status: Approved", e(REQ, "Status: Draft", "Status: Approved"), "ASK"),
        ("MultiEdit: edits 内に Status: Approved",
         {"tool_input": {"file_path": REQ,
                         "edits": [{"old_string": "Status: Draft", "new_string": "Status: Approved"}]}},
         "ASK"),
        ("Edit: specs の本文編集（Status 変更なし・許可）", e(REQ, "a", "b"), "ALLOW"),
        # --- Bash 迂回 → ASK ---
        ("Bash: リダイレクトで hooks へ", bash('echo "x" > .claude/hooks/guard_harness.py'), "ASK"),
        ("Bash: tee で settings.json へ", bash("echo x | tee .claude/settings.json"), "ASK"),
        ("Bash: sed -i で pre-commit 設定を編集", bash("sed -i 's/a/b/' .pre-commit-config.yaml"), "ASK"),
        ("Bash: rm で CI ワークフロー削除", bash("rm .github/workflows/ci.yml"), "ASK"),
        ("Bash: cp で profile.yml へ（宛先）",
         bash("cp /tmp/x.yml .claude/profiles/python-fastapi/profile.yml"), "ASK"),
        ("Bash: リダイレクトで specs へ", bash(f"echo x > {REQ}"), "ASK"),
        # --- Bash の正当操作は ALLOW ---
        ("Bash: hooks を読むだけ（許可）", bash("cat .claude/hooks/guard_harness.py"), "ALLOW"),
        ("Bash: apply.py の実行（書き込みでない・許可）",
         bash("python3 .claude/profiles/apply.py --auto"), "ALLOW"),
        ("Bash: test_guards の実行（許可）", bash("python3 .claude/hooks/test_guards.py"), "ALLOW"),
        ("Bash: specs を読むだけ（許可）", bash(f"grep -n Status {REQ}"), "ALLOW"),
    ]
    for desc, payload, expect in cases:
        run("guard_harness.py", desc, payload, expect, R)


def main() -> int:
    test_no_verify()
    print()
    test_architecture()
    print()
    test_sdd_gates()
    print()
    test_harness()
    print()
    n_ok = sum(results)
    print(f"結果: {n_ok}/{len(results)} 件 期待どおり")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
