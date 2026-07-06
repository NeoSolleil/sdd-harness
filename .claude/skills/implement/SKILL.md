---
name: implement
description: SDD段階4（実装）。design.md・acceptance.feature・tasks.md を入力に、TDD（red→green→refactor）で実装する。Gherkin を有効な stack profile の BDD ランナーでテストへ変換して先に作り、最小実装で通す。
argument-hint: [feature-folder]
disable-model-invocation: true
---

# implement — 実装（SDD 段階4・TDD）

tasks.md の順に、**テストを先に書いて**実装する。Gherkin 原本は参照・変換するだけ（新規作成しない）。

> **実行（進行役への指示）**: 対象タスクに応じて backend-engineer / frontend-engineer を **Agent ツールで spawn** して委譲する（互いに独立なタスクなら並行可）。進行役自身は実装・テストを書かない。委譲プロンプトには feature フォルダ・担当タスク（tasks.md の ID）・対象シナリオ（`@R-x`）を明記する（サブエージェントはこの会話を引き継がない）。完了後にレビュアーを回す（末尾「完了後のレビュー」）。

## 最初に参照する

- **有効な stack profile**（`.claude/profiles/<id>/profile.yml`）… 使う道具の単一の真実。`bdd_runner` / `e2e_runner` / `step_defs_location` / `layers` / `arch_lint_cmd` / `quality_gates` を参照する。
- `bdd`（Gherkin をシナリオに書く/変換する作法）と、プロファイルが指す stack スキル（アーキテクチャ・E2E 等）。
- 該当レイヤの `.claude/rules/`（domain 純粋・入力は境界で検証・永続化は抽象経由 等）

## 前提（着手条件）

- `tasks.md` の `Status:` が **Approved**（tasks 完了・人間承認済み）であること。`Draft` なら implement に着手しない。

## 手順（tasks.md の各タスクを依存順に）

1. **Red**: そのタスクが対象とする acceptance.feature のシナリオを、プロファイルの `bdd_runner` で `step_defs_location` にテスト化し、`specs/<feature>/acceptance.feature` を参照してバインドする。バインドは**選択的**に——現在のタスクと検証レベルに対応するシナリオだけを束ね、`@e2e` を backend ランナーで収集したり、未着手タスクのシナリオを undefined で落とさない（バインドの最終網羅は test-coverage が検証する）。実行して**失敗**を確認。
2. **Green**: 正しい CA レイヤ（プロファイルの `layers`）に**最小限**のコードを書いて通す。依存方向（domain は何も import しない 等）を守る（プロファイルの `arch_lint_cmd`／編集時フックが強制）。
3. **Refactor**: green を保ったまま整理。プロファイルの `quality_gates`（lint／format／typecheck／complexity／build）を全て緑にする。
4. **frontend（UI がある場合）**: プロファイルが指す frontend アーキ・E2E スキルに従って実装。E2E は `e2e_runner` で acceptance を再利用し、`data-testid` を必須にする。
5. 仕様／シナリオに無い機能を足さない。**テストの無い実装をコミットしない**（pre-commit／CI が強制）。

## BDD バインド（テスト↔Gherkin）

- ステップ定義はプロファイルの `step_defs_location` に置くが、**Gherkin 原本は `specs/<feature>/acceptance.feature`**。そこから相対参照する（コピーを作らない）。
- シナリオの `@R-x` タグで、どの要件を検証しているか追える状態を保つ。`@backend`／`@e2e` で検証レベルを分け、プロファイルの `bdd_runner`／`e2e_runner` にそれぞれ束ねる。

## 制約（ハーネス）

- Gherkin・要件の新規作成禁止（参照・変換のみ）。
- TDD 順（red → green → refactor）。最小実装に徹する。
- 全品質ゲートが緑になるまで「完了」としない。

## 完了後のレビュー（ループ）

実装が緑になったら、独立レビュアー3体を **Agent ツールで並行に spawn**（1メッセージで3呼び出し）する：

- **spec-compliance**（仕様適合・スコープ・CA）／**test-coverage**（要件→シナリオ→テストの網羅）／**code-reviewer**（バグ・可読性・重複・簡潔さ）。委譲プロンプトには feature フォルダと対象変更の範囲を明記する。
- 指摘は該当 engineer に**再委譲**して修正させ、修正後にレビュアーを再実行する。**3体すべて PASS ＋人間承認**まで反復する。

## 完了の定義

対象シナリオが全て pass、品質ゲートが全て緑、レビュアー3体の指摘なし、人間レビュー承認。→ その機能は完成（必要なら次の機能へ）。
