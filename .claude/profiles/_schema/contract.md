# stack profile の契約（conformance contract）

共有ハーネス（`.claude/` の SDD ワークフロー・不変条件）が、**どのスタックにも要求する項目**の定義。
各スタックはこの契約を満たす `profiles/<id>/profile.yml` を1枚用意する。**プロジェクトごとではなくスタックごとに1回**書けばよく、同一スタックの別プロジェクトは使い回す。

- 見本（実値入り）: [../python-fastapi/profile.yml](../python-fastapi/profile.yml)
- 空の雛形: [profile.template.yml](profile.template.yml)

---

## コアが固定する前提（マニフェストに書かない）

ここを各プロファイルに埋めさせると再現性が崩れるため、**共有コア側で固定**する。プロファイルはこれらを「所与」として満たす。

- **Clean Architecture の4層と依存方向**（内→外、domain が最内・依存ゼロ、依存性逆転、エンティティ↔永続化の分離）
- **テスト方針**（TDD red→green→refactor / Gherkin が唯一の正本 / 要件→シナリオ→テストのトレーサビリティ / 未テスト=未完了）
- **タグ規約** `@R-x` / `@backend` / `@e2e`
- **`specs/<feature>/` の場所と構造**（discovery / requirements / acceptance / design / tasks）

---

## 契約項目

`R` = 必須（欠けたらそのスタックでは契約不成立）、`O` = 任意（ポリシーとして課すなら必須化）。
「読む主体」= その値を実際に使う共有コア側の要素。

### 0. 識別（トップレベル）

| フィールド | R/O | 意味 | 読む主体 |
|---|---|---|---|
| `id` | R | プロファイル識別名（例: `python-fastapi`） | 進行役・プロジェクト設定 |
| `runtime` | R | 言語・主要バージョン | scaffold / CI |
| `package_manager` | R | 依存・lockfile 管理（再現性） | scaffold / CI |
| `components[]` | R | このスタックのコンポーネント（例: backend, frontend）。各々が下の②③④を持つ | 全体 |

各コンポーネントは `name` と `root`（ルートディレクトリ）を持つ。

### ② Clean Architecture 強制（`components[].architecture`）

| フィールド | R/O | 意味 | 読む主体 |
|---|---|---|---|
| `layers[]` | R | コア固定の各層 → **実ディレクトリ**の対応（外→内の順） | rules / spec-compliance / tasks（ビルド順） |
| `forbidden_imports` | R | 層ごとの**禁止 import**（特に domain / application が外部FWを持ち込まない） | guard hook / arch lint |
| `guard_inner_paths[]` | R | 編集時フックが「内側」として守るパス | guard hook |
| `arch_lint_cmd` | R★ | 依存方向を**機械検証**するコマンド | CI / pre-commit / spec-compliance |
| `persistence` | O | 「書き方」禁止（例: 直接SQL禁止＝ORM必須）。`orm_only` / `forbidden_patterns[]` / `detect_cmd`。DBを持つスタックは実質必須 | guard / pre-commit |
| `composition_root` | R | DI 結線（抽象↔具象の配線）の場所 | rules / spec-compliance |

★ `arch_lint_cmd` は「CA遵守」という不変条件を支える中核。機械検証の道具（import-linter / dependency-cruiser / go-arch-lint 等）が無いスタックは、**代替の強制手段を用意するか、その欠如を明示**する（`null` ＋ NOTE）。埋めないまま黙って通さない。

### ③ テスト強制（`components[].testing`）

| フィールド | R/O | 意味 | 読む主体 |
|---|---|---|---|
| `bdd_runner` | R | `@backend` シナリオを**実行可能テストに束ねる道具**（pytest-bdd / cucumber-js / godog 等） | implement / test-coverage |
| `e2e_runner` | O | `@e2e` を束ねる道具（UIありなら必須。playwright-bdd 等） | implement / test-coverage |
| `step_defs_location` | R | ステップ定義の置き場（Gherkin原本は `specs/` を相対参照・コピー禁止） | implement |
| `gherkin_source` | R | Gherkin 原本への参照パス（コア固定値を明示） | implement |
| `test_cmd` | R | テスト実行コマンド（TDDゲート＆網羅レビュアーが実行） | CI / pre-commit / test-coverage |
| `e2e_cmd` | O | E2E 実行（UIありなら必須） | CI |

### ④ 品質ゲート（`components[].quality_gates`）

| フィールド | R/O | 意味 | 現行例 |
|---|---|---|---|
| `lint_cmd` | R | Lint | ruff check / eslint |
| `format_check_cmd` | R | 整形チェック | ruff format --check / prettier --check |
| `typecheck_cmd` | R | **strict 型**チェック | pyright / tsc --noEmit |
| `complexity_cmd` | O | 複雑度 | xenon |
| `build_cmd` | O | ビルド成立確認（ビルド対象があるコンポーネントは必須） | vite build |

### 横断: `enforcement`

| フィールド | R/O | 意味 |
|---|---|---|
| `test_required` | R | 「未テスト=未完了」ゲートを課すか（原則 true） |
| `run_on[]` | R | 上記コマンド群を回す場所（pre-commit / ci） |

---

## 適合チェック（コアがプロファイルを検証する観点）

新しいプロファイルを受け入れる前に、コアは最低限これを確認する（将来スクリプト化）:

1. `R` 項目がすべて埋まっている（`null` の場合は必ず NOTE で理由と代替が添えられている）。
2. `layers[]` がコア固定の CA 4層すべてを網羅し、`root` 配下の実在パスを指す。
3. `forbidden_imports` に、そのスタックの Web/ORM 相当フレームワークが含まれる（domain / application が汚染されない）。
4. `arch_lint_cmd` / `test_cmd` / 各 `quality_gates` が**実行可能**（コマンドが解決する）。
5. UI コンポーネントがあるなら `e2e_runner` / `e2e_cmd`（または明示的な未配線 NOTE）がある。

> この一覧を満たさないプロファイルは「契約不成立」。散文（skills/agents/rules）はプロファイルの存在と充足を前提に無編集で動くため、穴があると強制が空振りする。
