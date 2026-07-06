---
name: bdd
description: ドメイン参照。Gherkin（受け入れシナリオ）の書き方。Feature/Rule/Scenario、BRIEF 原則、Example Map からの変換、タグ規約（@R-x / @backend / @e2e）。specify で清書し implement/e2e で実行する際に参照する。
---

# bdd — Gherkin の書き方

`discover` の 🟢Example を、`specify` で**実行可能な受け入れシナリオ**に清書するための記法。原本は `specs/<feature>/acceptance.feature`。implement（プロファイルの `bdd_runner`）と E2E（`e2e_runner`）が同じ原本を読む。

## キーワードは英語、本文は日本語

`Feature` / `Rule` / `Scenario` / `Scenario Outline` / `Background` / `Given` / `When` / `Then` / `And` は**英語キーワード**を使い、ステップ本文は日本語で書く。
（理由: BDD ランナーの既定は英語キーワードで、EARS も英語構文。ツール整合と一貫性のため `# language: ja` は使わない。）

## 構造

- `Feature:` … 機能が生む価値（1機能=1ファイル）。
- `Rule:` … **要件グループ（discovery の 🔵Rule）ごとに置いて**シナリオを構造化する。requirements.md のグループ見出しと鏡写しに対応させ、1機能=1ファイルのまま見通しを保つ。
- `Scenario:` … 具体例1件（Given-When-Then）。
- `Scenario Outline:` ＋ `Examples:` … 同型で値違い（境界値・データ駆動）に使う。
- `Background:` … 同一 Feature 内の共通 Given。

## BRIEF 原則

- **B**usiness language: 業務・ドメインの言葉（ubiquitous-language）で書く。実装用語を避ける。
- **R**eal data: 具体的な値（数値・日時・件数）を使う。
- **I**ntention revealing: 何を確かめたいかが伝わる名前にする。
- **E**ssential: 本質的な前提・操作・結果だけ。
- **F**ocused: 1シナリオ=1つの振る舞い。
- **B**rief: 短く。

## Given-When-Then の規律

- **Given** = 前提・文脈（状態の用意）。
- **When** = **ただ1つ**のトリガー操作。複数の When を並べない。
- **Then** = 観測可能な結果（記録された／表示された／拒否された）。
- UI 詳細（ボタンの色等）は業務シナリオに書かない（それは e2e の関心）。
- **宣言的に書く（What、not How）**: ❌「送信ボタンをクリックする」→ ⭕「注文を確定する」。UI 操作ではなく業務の意図を書く。

## タグ規約

- `@R-x` … 対応する EARS 要件（requirements.md の ID）。**全シナリオに必須**。要件↔シナリオの**正式な紐付けはこのタグ**。`Rule:` は任意の可読グルーピングで、紐付けの正本ではない。
- `@backend` … プロファイルの `bdd_runner` で**ドメイン／アプリ／API**として検証するシナリオ。
- `@e2e` … プロファイルの `e2e_runner` で**動く UI**として検証するシナリオ。
- 1つの振る舞いを両レベルで確かめたい場合のみ、別シナリオに分けてそれぞれ付与する。

**タグはツールでこう効く**: BDD ランナーはタグを**テスト選択の仕組み**（マーカー／tag 式）に変換できるため、実行時に検証レベルを分離できる。具体の選択方法は active プロファイルのランナー（`bdd_runner` / `e2e_runner`）に従う。

## Example Map → Gherkin の変換

- 🔵Rule → `Rule:`（または `@R-x` でグルーピング）。
- 🟢Example（正常）→ `Scenario:`。
- 🟢Example（境界・異常）→ それぞれ別 `Scenario:`（値違いが多ければ `Scenario Outline`）。

## 例（English keyword ＋ 日本語本文・書式見本／差し替え可）

以下は Given-When-Then とタグ規約の**書式を示す中立例**。自プロジェクトのシナリオへ差し替える。

```gherkin
Feature: 問い合わせフォーム送信

  @R-1 @backend
  Scenario: 必須項目が揃った送信は受理される
    Given 入力フォームが表示されている
    And 氏名とメールが入力されている
    When ユーザーが送信する
    Then システムは問い合わせを保存する
    And 受理メッセージを返す

  @R-2 @backend
  Scenario: 必須項目が空の送信は拒否される
    Given 入力フォームが表示されている
    And メールが未入力である
    When ユーザーが送信する
    Then システムは送信を拒否する
    And エラーメッセージを表示する

  @R-1 @e2e
  Scenario: 送信後に完了画面へ遷移する
    Given フォーム画面を開いている
    When 有効な内容で送信する
    Then 完了画面が表示される
```

## アンチパターン

- 1シナリオに複数 When を詰める。
- Then に観測できない内部状態を書く。
- `@R-x` 無しのシナリオ（要件と紐付かない＝台帳の外）。
- 実装語・UI 語で業務ルールを書く。
