---
name: specify
description: SDD段階1（仕様化／Formulation）。承認済みの discovery.md（Example Map）を EARS 要件（requirements.md）と Gherkin 受け入れ基準（acceptance.feature）に清書する。Discovery（段階0 /discover）の完了後に使う。
argument-hint: [feature-folder 例: 0001-<機能名>]
disable-model-invocation: true
---

# specify — 仕様化（SDD 段階1）

承認済みの `discovery.md`（Example Map）を、**機械検証可能な仕様**＝ EARS 要件＋Gherkin シナリオに清書（Formulation）する。**白紙から生成しない**：発見は前段の `discover`（段階0）で済ませ、ここはその成果を formal 化する工程。

> **実行（進行役への指示）**: scenario-author を **Agent ツールで spawn** して委譲する。進行役自身は requirements.md / acceptance.feature を書かない。委譲プロンプトには feature フォルダ・入力（承認済み discovery.md のパス）・期待出力（requirements.md ＋ acceptance.feature、`Status: Draft`）を明記する（サブエージェントはこの会話を引き継がない）。

## 出力（これだけを作る）

- `specs/<feature>/requirements.md` … **EARS 形式の要件**（ルールの台帳）
- `specs/<feature>/acceptance.feature` … **Gherkin の受け入れシナリオ**（合格条件）

> **Gherkin の一次著作はこの段階の1回だけ。** tasks/implement は参照・変換のみで、新規に書かない。

## 機能 ＞ 要件 ＞ シナリオ の3段構造

| 段 | もの | 置き場 | 個数 |
| --- | --- | --- | --- |
| 機能 | ユーザーが意味のある1タスクを完了できる縦切り（例: 1つのユーザータスクを完結できる単位） | `specs/NNNN-name/`（フォルダ） | 1 |
| 要件 | 機能を構成する個々のルール（EARS） | requirements.md（1ファイル）内に複数、ID `R-1`… | 数件〜十数件 |
| シナリオ | 各要件の具体例（Gherkin） | acceptance.feature（1ファイル）内に複数、`@R-1` タグで紐付け | 各要件に1本以上（観点の網羅は Rule 単位） |

**機能フォルダの粒度の目安**: そこから EARS 要件が数件〜十数件出るくらい。要件が1件しか出ないなら小さすぎ（それは機能ではなく要件）。無関係な複数ゴールが混ざるなら大きすぎ（分割する）。例:「入力値の検証」は機能ではなく、より大きな機能の中の要件 `R-1`。

## 最初に参照する

- **`discovery.md`（承認済み Example Map）… 主入力。** 🔵Rule→EARS 要件、🟢Example→Gherkin シナリオの素になる。
- `ubiquitous-language`（用語集）… 用語を揃える。新語が出たら用語集への追加を提案する。
- `bdd`（Gherkin の書き方）… Feature / Rule / Example、BRIEF 原則。

## 前提（着手条件）

- `discovery.md` が存在し、先頭の `Status:` が **Approved**（人間承認済み）であること。`Draft` のままなら specify に着手せず、`discover` を完了させる。

## 手順

1. **discovery.md を読む。** 🔵Rule を EARS 要件、🟢Example を Gherkin シナリオへ対応づける。discovery.md に無いルール／スコープが新たに必要になったら、勝手に足さず `discover` に差し戻す。
2. **discover が作成した feature フォルダを使う**（`specs/NNNN-kebab-name/`）。新たに採番・作成しない。
3. **EARS 要件を書く**（requirements.md）。1要件＝1ルール。下記パターンを使い、各要件に ID（`R-1`, `R-2`…）を振る。曖昧語（速い・適切・十分など）を避け、**測定可能**に書く。要件は **Rule（要件グループ。discovery の 🔵 に対応）見出し**でまとめる。
4. **各要件に Gherkin シナリオをぶら下げる**（acceptance.feature）。各要件に最低1本。**正常系・異常系・境界値の網羅は Rule（要件グループ）単位**で揃える——境界・異常が独立の要件（IF-THEN 等）として立っている場合は、そのシナリオ自体が異常系／境界の1本と数える（要件ごとに3観点を機械的に強要しない）。各シナリオに対応要件IDのタグ（`@R-1`）を付け、ファイル内は requirements.md と同じグループの **`Rule:` ブロック**で構造化する。ファイルは1機能1つのまま——肥大化したらファイル分割ではなく**機能の分割**（discover の粒度規則）に立ち返る。
5. **網羅とトレーサビリティを確認する。**
   - discovery.md の **🔵Rule がすべて ≥1 の EARS 要件**に、**🟢Example がすべて ≥1 のシナリオ**になっているか（取りこぼし無し）。
   - 「要件にシナリオが無い」「シナリオに対応要件が無い」を潰す。
   - 不足・新たな穴が見つかったら、勝手に埋めず `discover` に差し戻す。
6. **人間レビューに出す。** 承認されるまで plan へ進まない。

## EARS（記法の詳細は [ears.md](ears.md)）

要件は EARS のいずれかのパターンで書く。核は **the `<システム>` SHALL `<応答>`**：
ユビキタス / イベント駆動 `WHEN` / 状態駆動 `WHILE` / オプション `WHERE` / 望ましくない挙動 `IF-THEN` / 複合。

**テンプレート・例・よくある失敗・提出前チェックリストは [ears.md](ears.md) を必ず参照する。**

## 出力フォーマット

**requirements.md**
- 先頭に `Status: Draft`（人間が承認したら `Approved`。plan はこれが Approved で着手）
- 機能名 / 概要 / スコープ（含む・含まない）
- 要件リスト（ID 付き EARS 文）
- 用語メモ（`ubiquitous-language` への参照。新語があれば追加提案）

**acceptance.feature**
- `Feature:` 機能が生む価値
- 必要に応じ `Rule:`
- `Scenario:` / `Scenario Outline:`（Given-When-Then）。要件IDタグで紐付け。

## 制約（ハーネス）

- specs/ 配下の文書だけを作る。**コード実装はしない**。
- スコープ厳守。要望に無い機能を足さない。
- Gherkin の新規著作はこの段階のみ。
- **specify はルール・スコープ・🔴の答えを発明しない。** discovery.md に無い不足が見つかったら `discover` に差し戻す。

## 完了の定義

requirements.md と acceptance.feature が揃い、全要件にシナリオが対応し、**人間がレビュー承認**して requirements.md を `Status: Approved` にした状態。→ 次は `plan`。

> specify 完了後は **requirements.md ＋ acceptance.feature が正本**。discovery.md は発見の記録であり、以後は同期維持しない（仕様変更は requirements.md／acceptance.feature 側で行う）。
