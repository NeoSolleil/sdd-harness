---
name: tasks
description: SDD段階3（作業分解）。design.md を入力に、Clean Architecture／TDD のビルド順で作業を分解した tasks.md を作る。既存の Gherkin シナリオを参照・グルーピングするだけで、新規シナリオや要件は作らない。
argument-hint: [feature-folder]
disable-model-invocation: true
---

# tasks — 作業分解（SDD 段階3）

承認済みの design.md を、順序付きの**作業リスト**に分解する。出力は `specs/<feature>/tasks.md` のみ。

> **実行（進行役への指示）**: solution-analyst を **Agent ツールで spawn** して委譲する。進行役自身は tasks.md を書かない。委譲プロンプトには feature フォルダ・入力（承認済み design.md）・期待出力（tasks.md、`Status: Draft`）を明記する（サブエージェントはこの会話を引き継がない）。

> **既存の acceptance.feature を参照・グルーピングするだけ。新しい Gherkin シナリオも要件も作らない。**

## 最初に参照する

- design.md（設計）・acceptance.feature（シナリオ）・requirements.md（R-x）

## 前提（着手条件）

- `design.md` の `Status:` が **Approved**（plan 完了・人間承認済み）であること。`Draft` なら tasks に着手しない。

## 手順

1. design.md と acceptance.feature を読む。
2. **ビルド順で分解**（Clean Architecture の内側から。層の並びと実パスはプロファイルの `layers`）: domain（エンティティ／値オブジェクト）→ application（ユースケース＋リポジトリ抽象）→ infrastructure（永続化モデル・リポジトリ実装）→ adapters（入出力 DTO・API）→ composition root → frontend。
3. **各タスクに、検証すべき既存シナリオを紐付ける**（**シナリオ名＋`@R-x`** で参照。.feature の行番号は編集でズレるため補助にとどめる）。「このタスクが green にすべきシナリオ」を明記する。基盤整備・セットアップ・CI などの**イネーブリングタスク**は対象シナリオ無しで置いてよい（後続タスクからの依存を明記する）。
4. **TDD を前提に順序付け**: 各実装タスクは「対象シナリオをプロファイルの `bdd_runner` でテスト化して red → 最小実装で green → refactor」を内包する。依存（内側の層）が先。
5. 各タスクは小さく検証可能に。完了条件（どのテスト／チェックが通れば終わりか）を書く。
6. 人間レビューに出す（**順序・依存の論点を添えて**）。ゲートでの決定を tasks.md に追記し、承認まで implement へ進まない。

## tasks.md の構成

- 先頭に `Status: Draft`（人間承認で `Approved`。implement はこれが Approved で着手）
- タスク一覧（ID・内容・依存・対象シナリオ `@R-x`・完了条件）
- 推奨順序（内側の層 → 外側、test-first）
- **網羅確認の節**（全シナリオ → タスクの対応表）と**トレーサビリティ**（`R-x` → タスク）
- **人間ゲート向けの論点**（順序・依存のリスク・実装前に決めるべき点）。**ゲートでの決定は tasks.md に追記して記録する**

## 制約（ハーネス）

- 新規 Gherkin・要件を作らない（参照・グルーピングのみ）。
- 実装・テストコードは書かない（それは implement）。
- 全シナリオがどれかのタスクに紐づく（網羅）。**逆は要求しない**——イネーブリングタスク（基盤・セットアップ・CI）はシナリオ無しでよい。

## 完了の定義

tasks.md が揃い、全シナリオがタスクに割り当てられ、**人間が承認して tasks.md を `Status: Approved`** にした状態。→ 次は `implement`。
