---
name: plan
description: SDD段階2（設計）。承認済みの requirements.md / acceptance.feature を入力に、DDD設計・API契約・テーブル定義を design.md にまとめる。仕様が固まって設計に進むときに使う。
argument-hint: [feature-folder]
disable-model-invocation: true
---

# plan — 設計（SDD 段階2）

承認済みの仕様（requirements.md ＋ acceptance.feature）を、実装可能な**設計**に落とす。出力は `specs/<feature>/design.md` のみ。**コードは書かない。**

> **このスキルは slash 専用の「進行役の台本」。** solution-analyst はこれを呼ばず、下の委譲で spawn される。
>
> **実行（進行役への指示）**: solution-analyst を **Agent ツールで spawn** して委譲する。進行役自身は design.md を書かない。委譲プロンプトには feature フォルダ・入力（承認済み requirements.md / acceptance.feature）・期待出力（design.md、`Status: Draft`）を明記する（サブエージェントはこの会話を引き継がない）。

## 最初に参照する

- `ubiquitous-language` … 用語を設計語彙に揃える。
- **有効な stack profile**（`.claude/profiles/<id>/profile.yml`）と、それが指す stack 設計スキル:
  - backend アーキテクチャ（Clean Architecture・依存性逆転・入出力検証・ORM 方針）。
  - frontend アーキテクチャ（CA＋コンポーネント設計・状態/データ取得）と UI デザイン規約（UI を伴う場合）。

## 前提（着手条件）

- `requirements.md` の `Status:` が **Approved**（specify 完了・人間承認済み）であること。`Draft` なら plan に着手しない。

## 手順

1. requirements.md（R-x）と acceptance.feature を読み直す。
2. **ドメインモデル（DDD）**: 境界づけられたコンテキスト・集約・エンティティ・値オブジェクト・ドメインイベント・不変条件を定義。各 EARS 要件をドメインの振る舞いに対応づける。
3. **レイヤ配置（Clean Architecture）**: 何を domain / application（ユースケース＋リポジトリ抽象）/ adapters（API・入出力 DTO）/ infrastructure（永続化モデル・リポジトリ実装）に置くかを決める（実パスはプロファイルの `layers`）。domain は純粋、永続化モデルとドメインエンティティは分離。
4. **API 契約**: エンドポイント・メソッド・リクエスト/レスポンス DTO（プロファイルの検証ライブラリで検証）・ステータスコード・エラー形式。acceptance シナリオと対応づける。
5. **データモデル**: テーブル・カラム・型・主キー/外部キー・制約・インデックス。ORM マッピング方針（プロファイルの ORM を infrastructure に、domain と相互変換）。将来の DB 移行に備え、特定 DB 固有機能に依存しすぎない。
6. **トレーサビリティ**: 各 R-x → 設計要素（ユースケース / エンドポイント / テーブル）の対応表。
7. 人間レビューに出す（**設計上の論点・リスクを添えて**）。ゲートでの決定を design.md に追記し、承認まで tasks へ進まない。

## design.md の構成

- 先頭に `Status: Draft`（人間承認で `Approved`。tasks はこれが Approved で着手）
- 概要・対象 EARS 要件
- ドメインモデル（集約・エンティティ・値オブジェクト・イベント・不変条件）
- レイヤ配置（各層に置く要素）
- API 契約（エンドポイント・DTO・エラー）
- データモデル（テーブル定義・FK・制約）
- **フロント設計（UI を伴う場合）**: 画面・コンポーネント構成、描画/レンダリング方針、状態とデータ取得、`data-testid` 計画・DOM 外描画があれば E2E の観測手段（テストシーム）の計画
- 要件↔設計のトレーサビリティ表（**全 R-x** → 設計要素）
- **人間ゲート向けの論点**: 設計上の判断が必要な点・リスクを明示する節。**ゲートでの決定は design.md に追記して記録する**（決定を会話に埋もれさせない）

## 制約（ハーネス）

- design.md だけを作る。実装・テストは書かない。
- CA の依存方向を守る設計にする（domain は何にも依存しない）。
- 新しい Gherkin・要件を作らない（仕様は specify で確定済み）。スコープ厳守。

## 完了の定義

design.md が揃い、全 EARS 要件が設計に対応づき、**人間が承認して design.md を `Status: Approved`** にした状態。→ 次は `tasks`。
