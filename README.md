# SDD Harness — 仕様駆動開発の監督ハーネス（テンプレート）

Claude Code 上で **SDD（仕様駆動開発）をフル装備で回す**ための、再利用可能な監督ハーネス。
「AI が各段階を起草し、人間がゲートでレビューする」流れを、スキル・エージェント・ルール・フック・CI で支える。
方針・構成・規約の正本は [CLAUDE.md](CLAUDE.md)（プロジェクト憲法）。

> このブランチはハーネスの**テンプレート本体**。ドメイン（何を作るか）は空のプレースホルダで、他プロジェクトへ持ち込んで埋めて使う。

> どのファイルが「変わらない core／スタックごとの profile／プロジェクトごとの domain／生成物」かの
> **全ファイル台帳と各部の役割**は [HARNESS.md](HARNESS.md) を参照。

## 3層のかまえ

| 層 | 何が入るか | 依存 |
|---|---|---|
| **core** | SDD ワークフロー（discover→implement）・記法（EARS/Gherkin）・レビュアー/アナリスト・hooks・settings | stack/domain 非依存 |
| **stack profile** | 言語・FW・層→パス・禁止 import・BDDランナー・品質ゲート（`.claude/profiles/<id>/`） | スタック固有（差し替え式） |
| **domain** | プロジェクト名・作るもの・用語集（CLAUDE.md のプレースホルダ・`ubiquitous-language`・`specs/`） | プロジェクトごとに記入 |

## 構成

```
.claude/
├── skills/            # 段階駆動（discover/specify/plan/tasks/implement）＋ core 参照（bdd・ubiquitous-language）
├── agents/            # 役割別サブエージェント（core: アナリスト/レビュアー）
├── rules/             # パススコープ制約（apply.py が profile から配置する生成物）
├── hooks/             # PreToolUse ガード（アーキ違反・直接SQL・--no-verify を決定論ブロック）
├── settings.json      # フック登録
└── profiles/          # ★ スタック差し替え層
    ├── apply.py        #   active プロファイルを .claude/ へ配置
    ├── _schema/        #   契約（contract.md）＋新スタック用の雛形
    └── python-fastapi/ #   現行の例スタック（profile.yml / rules / skills / agents）
CLAUDE.md              # プロジェクト憲法（索引・テンプレート）
specs/                 # SDD 成果物（機能ごとに discovery/requirements/acceptance/design/tasks）
backend/ frontend/     # 実装（現行の例スタック python-fastapi のスキャフォルド）
```

## 別プロジェクトでこのハーネスを使う

> **クローン後のセットアップは [SETUP.md](SETUP.md)（AI 向けの実行手順書）に従う**。
> リポジトリを AI に開かせて「SETUP.md に従ってセットアップして」と指示すれば、健全性確認 →
> スタック決定 → 名前差し替え → domain 記入 → 運用開始まで到達できる。以下はその概要。

1. **持ち込む**: このリポジトリをクローンする（詳細手順・履歴の扱いは SETUP.md）。
2. **スタックを選ぶ**:
   - 同じ構成（FastAPI + React）なら既存の `python-fastapi` プロファイルをそのまま使う。
   - 別スタックなら `.claude/profiles/_schema/` の雛形から新プロファイルを作る（→ [.claude/profiles/README.md](.claude/profiles/README.md)、契約は [contract.md](.claude/profiles/_schema/contract.md)）。
3. **配置する**: 通常は **SessionStart フックが自動配置**する（`apply.py --auto`）。スタック切替時のみ手動で `python3 .claude/profiles/apply.py <id>`（`.claude/rules` 等は生成物で gitignore 済み）。新プロファイルは `python3 .claude/profiles/validate.py` で契約適合を機械チェックできる。
4. **ドメインを埋める**（AI に依頼可）: `CLAUDE.md` の `<...>` プレースホルダと、`.claude/skills/ubiquitous-language/` の用語表を、このプロジェクトの内容で埋める。
5. **SDD を回す**（下記ワークフロー）。

## SDD ワークフロー

各段階を該当スキルで駆動し、**各段階の終わりは人間レビューのゲート**（`Status: Approved` まで次へ進まない）。

> **セットアップ後に実際どう回すか**（各段階で人間が何を言い・何をレビューし・どう承認するか、ガードのダイアログの意味、トラブル対応）は **[USAGE.md](USAGE.md)（運用ガイド）** を参照。

| 段階 | スキル | 出力 |
|---|---|---|
| 0. discover | `/discover` | `specs/<feature>/discovery.md`（Example Map） |
| 1. specify | `/specify` | `requirements.md`（EARS）＋ `acceptance.feature`（Gherkin） |
| 2. plan | `/plan` | `design.md`（DDD 設計・API 契約・データモデル） |
| 3. tasks | `/tasks` | `tasks.md`（作業分解） |
| 4. implement | `/implement` | テスト（BDDランナーへ変換）→ 最小実装（TDD: red→green→refactor） |

進行役がワーカー役エージェントへ **Agent ツールで実際に委譲**し（進行役は成果物を自分で書かない）、implement 後にレビュー役（spec-compliance / test-coverage / code-reviewer）を並行に回す。詳細は [CLAUDE.md](CLAUDE.md)。

## 強制（ガードレール）

- **編集時**: `.claude/hooks/` の PreToolUse ガード3本が**決定論的にブロック**——
  - `guard_architecture` … CA 違反（domain/application への FW import）・直接 SQL・シェル経由の内側書き込み（対象・禁止パターンは active プロファイルの `guard:` から読む）
  - `guard_no_verify` … pre-commit 迂回（`--no-verify` / `-n` / `SKIP=` / `core.hooksPath` 差し替え等）
  - `guard_sdd_gates` … **SDD ゲート**（前段が `Status: Approved` になるまで次段に着手不可・承認済み文書の凍結。差し戻しは Status 行の編集で）
  - `guard_harness` … **人間ゲート（ask=確認ダイアログ）**（specs への `Status: Approved` 書き込み＝AI の自己承認と、ハーネス強制層〈hooks・settings・profile.yml・CI 等〉への変更に、人間の明示承認を要求）
- **セッション開始時**: SessionStart フックが active プロファイルを自動配置（`apply.py --auto`）。
- **コミット時／CI**: pre-commit と GitHub Actions が lint・型・アーキ検証（`arch_lint_cmd`）・テストに加え、**ガード自体の回帰テスト**（`test_guards.py`・79ケース）と**プロファイル契約検証**（`validate.py`）を実行——ハーネスの強制層そのものもテストされる。
- 文章では強制できない。本物のガードレールは Hooks と権限設定にある（CLAUDE.md の方針）。

## 現行の例スタック（python-fastapi）で動かす

現行プロファイルは FastAPI(Python) + React(Vite)。実際のコマンド定義は [profile.yml](.claude/profiles/python-fastapi/profile.yml) が単一の真実。

```bash
# 前提: uv（Python）と Node.js LTS（npm）

# backend
cd backend
uv sync
uv run uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run dev
```

品質チェック（内容は profile.yml の `quality_gates` / `arch_lint_cmd` / `test_cmd`）:

```bash
# backend
cd backend
uv run ruff check . && uv run ruff format --check . && uv run pyright
uv run lint-imports          # Clean Architecture の依存方向（import-linter）
uv run xenon --max-absolute B --max-modules B --max-average A app
uv run pytest

# frontend
cd frontend
npm run lint && npm run format:check && npm run typecheck && npm run test && npm run build
```

## 既知の制約・設計判断（CI / pre-commit）

`.pre-commit-config.yaml` と `.github/workflows/ci.yml` は**リポジトリ直下にあり、現行スタック（uv/pytest 等）のコマンドを直書き**している。これは `profile.yml` の `*_cmd`（`test_cmd` / `arch_lint_cmd` / `quality_gates`）と一部重複する。

- **意図的に「マニフェストから CI/pre-commit を生成する連動」は行わない。** `*_cmd` の主目的（AI エージェントが `test_cmd`・`arch_lint_cmd` を実行する）はすでに満たされており、codegen＋整合チェックの機構は、守るべき重複の小ささに対して過剰なため。コマンドは滅多に変わらず drift リスクも低い。
- **別スタックを実際に足すときの打ち手**は、codegen ではなく「**CI/pre-commit 設定もプロファイルが提供する**」（`profiles/<id>/` に置き `apply.py` が配置）。それまでは単一スタック前提で直下の設定を使う。
- 重複が気になった場合は、生成ではなく**軽量な整合チェック**（`profile.yml` のコマンドと CI/pre-commit の記述の一致を検査する小さな pre-commit フック）で足りる。

**CI はさらに GitHub Actions 前提**（`.github/workflows/ci.yml`）。ただし強制の本体である**編集時 Hooks（`.claude/hooks/`）と pre-commit はホスト非依存**で、CI が無くても同じ lint/型/アーキ/テストは pre-commit が走らせる（CI は冗長な最終関門）。別ホスト（GitLab 等）へは `ci.yml` を各 CI の設定に置き換えるだけ（コマンドは同じ）。

> **修正が必要になったら**: CI 設定は「**スタック軸（どのコマンドか）＋ホスト軸（GitHub Actions / GitLab / …）**」の2軸で変わる。どちらの対応も、core（直下 `ci.yml`・`.pre-commit-config.yaml`）にベタ書きするのをやめ、**プロジェクト／プロファイル側が CI/pre-commit 設定を提供する**形に寄せる（`apply.py` が配置する rules/skills と同じ考え方）。単一スタック・GitHub 運用の間は現状で問題なし。
