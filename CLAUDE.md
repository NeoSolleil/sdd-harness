# CLAUDE.md — <プロジェクト名>

SDD（仕様駆動開発）をフル装備で実践するための監督下プロジェクト。
このファイルはコードベースの索引である。詳細な手順・制約・強制は、各セクションが指すファイルに置かれている。

> **これはテンプレートです。** `<...>` のプレースホルダをプロジェクトの値で埋める（ドメインは下の各節と `ubiquitous-language`／`specs/`、技術スタックは **active プロファイル**が正）。

## このプロジェクトで何を作るか

<誰の・何を・なぜ を1〜3文で。提供価値と、当面のスコープ（含む／含まない）の要点>

詳細な要件は specs/ 配下の各機能フォルダを参照（EARS要件とギャーキンシナリオ）。

## 技術スタック

技術スタックの詳細（言語・FW・DB・テスト・品質ゲート・バージョン）は **active プロファイル**が単一の真実として定義する（`.claude/profiles/<id>/profile.yml`）。**このファイルには具体値を再掲しない**（重複＝drift の元）。

- 要約: `<id>`（例: `python-fastapi` = FastAPI(Python) ＋ React(Vite)、テストは pytest-bdd／playwright-bdd）。
- スタックを変える・詳細を見るときは `profile.yml` を編集／参照する。
- パッケージ管理は lockfile をコミットして再現性を担保（具体ツールはプロファイル）。

## アーキテクチャ

backend は **Clean Architecture** に準拠する（**全プロジェクト共通の不変条件**）。レイヤは外側から infrastructure → adapters → application → domain（domain が最内）。

- **依存は内向きのみ**。`domain` は何にも依存しない（Web／ORM／検証フレームワークを import しない）。`application` は `domain` のみに依存。外側は内側に依存してよいが、逆は禁止。
- **ドメインエンティティと永続化モデルは分離する**（厳密版）。`domain` は永続化に無依存の純粋クラス、永続化モデルとリポジトリ実装は最外層に置き、両者を相互変換する。
- application はリポジトリの**インターフェース（抽象）**を定義し、具象は最外層に置く（依存性逆転）。結線は composition root で行う。

層→実ディレクトリの対応・禁止 import・使用フレームワークは **active プロファイル**（`.claude/profiles/<id>/`）が定義する。依存方向の強制は `.claude/rules/` と guard フック（`profile.yml` の `guard:`）＋ import 検証（`arch_lint_cmd`）が担う。このセクションは不変条件の共有に徹する。

## ディレクトリ構成

```
<project-root>/
├── CLAUDE.md        # このファイル（索引）
├── .claude/         # ハーネス（下記「ハーネス」参照）。profiles/ に stack 差し替え層
└── specs/           # SDD成果物（機能ごとに discovery/requirements/acceptance/design/tasks）
```

実装ディレクトリ（backend／frontend 等）と**レイヤ→フォルダの対応**は active プロファイルが定義する（`.claude/profiles/<id>/profile.yml` の `layers`）。各サブディレクトリ固有の規約は `.claude/rules/`（プロファイルが `apply.py` で配置）に置く（このファイルには書かない）。

## SDDワークフロー

本プロジェクトは spec-first〜spec-anchored で進める。AIが各段階を起草し、人間が各ゲートでレビューする。
段階を駆動するプロンプトは .claude/skills/ のスキルとして定義されている。

| 段階 | スキル | 入力 | 出力 |
|------|--------|------|------|
| 0. discover | /discover | アイデア・要望 | specs/<feature>/discovery.md（Example Map：価値・ルール・具体例・疑問。スリーアミーゴス／発見） |
| 1. specify | /specify | 承認済み discovery.md | specs/<feature>/requirements.md（EARS）＋ acceptance.feature（ギャーキン） |
| 2. plan | /plan | 上記仕様 | specs/<feature>/design.md（DDD設計・API契約・データモデル定義） |
| 3. tasks | /tasks | 設計 | specs/<feature>/tasks.md（作業分解。既存シナリオを参照しグルーピングするのみ） |
| 4. implement | /implement | 設計＋ギャーキン | テストコード（プロファイルの BDDランナーへ変換）→ 最小実装（TDD: red→green→refactor） |

各段階は、進行役が該当する**ワーカー役エージェント**（.claude/agents/）に委譲して実施する：discover=product/quality/solution-analyst（3観点を進行役が統合）、specify=scenario-author、plan・tasks=solution-analyst、implement=engineer（active プロファイル提供の backend／frontend-engineer）。implement 完了後は**レビュー役**（spec-compliance / test-coverage / code-reviewer）を回し、指摘はワーカーが修正して再確認する。各段階の終わりは人間レビューのゲートで、承認（Status: Approved）まで次段階に進まない。

この委譲は文章上の約束ではなく、**進行役が Agent ツールで実際にサブエージェントを起動**して行う（進行役は段階成果物を自分で書かない。例外は discover の統合のみ）。委譲プロンプトには feature フォルダ・入力・期待出力を明記する（サブエージェントは会話履歴を引き継がない）。独立した複数の委譲は1メッセージで並行に spawn する。

スキルは2系統を**併用**する。**呼び出し規約: 段階駆動スキルは進行役だけが起動し、ワーカーは参照スキルを呼ぶ（逆はしない）。**

- **段階駆動スキル**（上表・core, `disable-model-invocation: true` の slash 専用）: discover / specify / plan / tasks / implement。**進行役の台本**で、ゲート確認 → ワーカー役エージェントの spawn → 事後処理（レビュー等）を駆動する。**ワーカーはこれを呼ばない**（slash 専用なので呼べない）。discover（発見）→ specify（清書）の順で、生成を急がず前段で詰める。
- **ドメイン参照スキル**（model-invocable）: **ワーカーが craft の一次情報として呼ぶ**知識役。
  - **core（stack 非依存）**: `ubiquitous-language`（用語集・全タスクで最初に参照）／`bdd`（Gherkin の書き方）。
  - **active プロファイル提供（stack 固有・`.claude/profiles/<id>/skills/`）**: backend／frontend アーキテクチャ・design（デザイントークン）・e2e-testing 等。

## 記法ルール

- 要件は EARS形式で書く（例: WHEN <トリガー>, the <システム> SHALL <応答>）。EARSは「ルールの台帳」。
- 受け入れ基準は ギャーキン（Given-When-Then）で書く。EARS要件1件に対しシナリオが複数ぶら下がる（正常系・異常系・境界値）。
- ギャーキンの一次著作は specify段階の1回のみ。下流（tasks/implement）はこれを参照・変換するだけで、新規作成しない。
- ギャーキン原本は specs/<feature>/acceptance.feature。BDDランナー（active プロファイル）の実行時はそこを参照する（コピーしない）。
- 設計段階では DDDの語彙（境界づけられたコンテキスト・集約・ドメインイベント）を用いてモデリングする。

詳細な記法ガイドは .claude/skills/specify/ を参照。

## ハーネス（監督の仕組み）

「設計通りに実装させる」ための層。詳細は各ファイル。**構成台帳（何が core/profile/domain/生成物か・各部の役割）は [HARNESS.md](HARNESS.md)**。

- このファイル（CLAUDE.md）… 構成・規約の事実を共有する。
- .claude/rules/ … パススコープの制約（例: 入力検証必須、永続化は抽象経由）。該当ファイルを触るときだけ読まれる。**active プロファイルが `apply.py` で配置する**。
- .claude/agents/ … 役割別サブエージェント。**ワーカー役**（product-analyst・quality-analyst・solution-analyst・scenario-author、および active プロファイル提供の backend／frontend-engineer）が各段階で**参照スキル**を呼んで実作業し（段階駆動スキルは進行役が起動する台本で、ワーカーは呼ばない）、**レビュー役**（spec-compliance・test-coverage・code-reviewer）が独立コンテキストで検証する。
- .claude/settings.json … Claude Code のフック登録。**PreToolUse**: アーキ違反（domain/application への FW import）・直接SQL・pre-commit 迂回（--no-verify 等）・**SDD ゲート違反（前段未承認での着手・承認済み文書の変更）**を編集／実行時に決定論的にブロックする。さらに **人間ゲート（ask=確認ダイアログ）**として、specs への `Status: Approved` 書き込み（AI の自己承認防止）とハーネス強制層（hooks・settings・profile.yml・CI 等）への変更に人間の明示承認を要求する（guard_harness）。**SessionStart**: active プロファイルを自動配置（apply --auto）。テスト実行や lint の強制はコミット時の pre-commit と CI が担い、**ガード自体の回帰テスト**（`.claude/hooks/test_guards.py`）と**プロファイル契約検証**（`profiles/validate.py`）も pre-commit / CI で強制する。
- .claude/profiles/ … **スタック差し替え層**。core（SDDワークフロー・不変条件）はスタック非依存に保ち、スタック固有物（マニフェスト `profile.yml`・rules・アーキ/E2E スキル・engineer エージェント）は `profiles/<id>/` を単一の真実として隔離する。`apply.py` が active プロファイルを `.claude/` へ配置し、guard フックは `profile.yml` の `guard:` を直接読む。詳細は `.claude/profiles/README.md`。

> プロファイル配置は **SessionStart フックが自動実行**する（`.claude/rules` 等は生成物で gitignore 済み）。スタック切替時のみ手動で `python3 .claude/profiles/apply.py <id>`。

注意: 「絶対に起きてはならないこと」はこのファイルの文章では強制できない。本物のガードレールは Hooks と権限設定に置く。

## コーディング規約

- コミットメッセージはセマンティック形式（feat/fix/test/refactor(scope): 説明）。
- 型は strict に運用する（具体の型チェッカ・検証ライブラリは active プロファイル）。入出力は境界で検証する。
- テストファースト（TDD）で進め、テストの無い実装を「完了」と見なさない。pre-commit／CI がテスト実行を強制し（失敗は完了不可）、テストの有無は implement の red→green 手順とレビューで担保する（カバレッジ計測は行わない方針）。
- specに無い機能を追加しない（スコープ厳守）。

## 作業規律（リソース管理と泥沼回避）

トークン・時間は有限の資源。次の規律で無駄撃ちを防ぐ。

- **書く前に見取り図をつくる**: コードより先に、思考（thinking）または応答の冒頭で次の3点を書き出してから編集を始める。
  1. **完了条件** — 何ができれば「済み」と言えるか（期待される振る舞い・成果物）。
  2. **変更箇所** — 触るファイルはどれで、Clean Architecture のどの層に当たるか。既存への波及はあるか。
  3. **手順と検証** — 最短の実装順序と、正しさを何で確かめるか（テスト・ゲート）。
- **ファイルの新規作成は配置計画から**: 既存のディレクトリ構成を確認（`ls`／`tree`）し、置き場所を active プロファイルの `layers` と `.claude/rules/` に従って決めてから作る。
- **3回失敗したら止まる**: 同じエラーへの修正が3回連続で失敗したら、自律修正を中断して状況を要約し、ユーザーに方針を確認する。同一ファイルへの当てずっぽうな再修正を繰り返さない。
- **1ファイルの目安は200行**: 超えそうなら責務を見直して分割を提案する（複雑度ゲートとも整合）。
- **ゲートを緑に保って進める**: 実装中は active プロファイルの品質ゲート（`quality_gates` の lint／型チェック等）と `test_cmd` を適宜実行する。自動修正（フォーマッタ・lint の fix）を先に試し、残りは原因から直す。

## 禁止事項（環境と品質ゲートの保護）

**ホスト環境を汚さない:**

- OS のパッケージマネージャ（apt / dnf / yum / pacman / snap 等）と `sudo` を使わない。`/usr/local` や `/etc` などシステム領域へ書き込まない。
- 依存の追加は、**各コンポーネントの root で active プロファイルの `package_manager` を使う場合のみ**（例: backend/ で `uv add`、frontend/ で `npm install`）。グローバル導入（`-g` 等）は禁止。
- それ以外の道具が必要になったら、インストールせず代替手段を検討するか、実行前にユーザーの許可を求める。

**品質ゲートを黙らせない:**

- lint・型・複雑度などの設定ファイル（`pyproject.toml`・ESLint／TypeScript 設定等）を、**検査が緩む方向に変更しない**。
- 抑止コメントで静的解析を回避しない（Python の `# noqa`／`# type: ignore`、TS/JS の `// eslint-disable`／`// @ts-ignore` 等）。エラーは原因を直す。
- どうしても例外が必要なときは、理由を添えてユーザーの承認を得てから最小範囲で使う。
