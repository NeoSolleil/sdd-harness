# profiles/ — stack profile（スタック差し替え層）

共有ハーネス（`.claude/` の SDD ワークフロー・不変条件）は**スタック非依存**に保つ。
スタック固有のもの（マニフェスト・rules・アーキ/E2E スキル・engineer エージェント）は、
この `profiles/<id>/` を**単一の真実**として隔離する。

- 散文（core の skills / agents）は特定スタックの固有名詞を書かず、プロファイルの項目を**間接参照**する。
- 具体値・stack 固有ファイルはプロファイルにだけ存在する（core 側は無編集で固定）。
- プロファイルは**スタックごとに1回**用意すればよい。同一スタックの別プロジェクトは使い回す（新スタックのときだけ用意）。

## 構成

```
profiles/
├── apply.py                 # active プロファイルを .claude/ へ配置する（差し替え式）
│                            #   --auto: SessionStart フック用（静か・fail-open・契約警告つき）
├── validate.py              # 契約適合の機械検証（必須キー・guard・パス実在）。CI/pre-commit でも実行
├── .active                  # 現在の active プロファイル id（apply.py が更新）
├── _schema/
│   ├── contract.md          # 全プロファイルが必ず埋める項目の定義（契約）
│   └── profile.template.yml # 新スタック追加用の空雛形
└── python-fastapi/          # スタック1つ = このディレクトリ1つ
    ├── profile.yml          # マニフェスト（実値の見本）。`guard:` は編集時フックが読む
    ├── rules/               # → .claude/rules/ に配置（パススコープ制約）
    ├── skills/              # → .claude/skills/ に配置（アーキ/design/e2e 参照スキル）
    └── agents/              # → .claude/agents/ に配置（backend/frontend-engineer）
```

## 配置の仕組み（真の差し替え式）

Claude Code は `.claude/rules`・`.claude/skills`・`.claude/agents` を**固定パス**から自動ロードする。
そこで `apply.py` が active プロファイルの `rules/ skills/ agents/` を `.claude/` へコピーする。

- `.claude/` 側の配置物は **`.gitignore` 済みの生成物**（追跡しない）。真の真実は `profiles/<id>/`。
- 配置一覧は `.claude/.profile-applied` に記録され、**スタック切替時に前回分を掃除**してから入れ替える。

```bash
python3 .claude/profiles/apply.py                 # active（.active か単一）を配置
python3 .claude/profiles/apply.py python-fastapi  # id を指定して切替＋配置
```

> 配置は **SessionStart フックが毎セッション自動実行**する（`apply.py --auto`。fail-open で、
> 問題時は1行警告のみ）。スタック切替時のみ手動で `apply.py <id>` を実行する。
> guard フックは profile.yml を直接読むため、配置と独立に動く。

## 新しいスタックを足すとき

1. `profiles/<id>/` を作り、`_schema/profile.template.yml` を `profile.yml` にコピーして実値で埋める
   （`R` 項目は必須。埋められない機械検証は `null` ＋ NOTE。`guard:` 投影も埋める）。
2. `rules/`・`skills/`・`agents/` にそのスタック用の stack 固有ファイルを置く。
3. `python3 .claude/profiles/validate.py <id>` で契約適合を機械チェックする（`_schema/contract.md` が定義の正）。
4. `python3 .claude/profiles/apply.py <id>` で配置し、`.gitignore` に新スタックの配置先を追記する。

> 補足: この配置は暫定。共有コアを別リポジトリ化する/テンプレートリポジトリにする等、
> リポジトリ構成が決まれば profiles/ の置き場は移動しうる。
