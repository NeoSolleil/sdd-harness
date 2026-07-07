# HARNESS.md — 構成台帳（何が変わらず、何が変わるか）

このハーネスを**他のプロジェクトへ持ち込むとき**に、どこをそのまま使い、どこを差し替え・記入するかの台帳。
各部が「何をする部分か」も併記する。概要は [README.md](README.md)、日々の運用は [USAGE.md](USAGE.md)、規約の正本は [CLAUDE.md](CLAUDE.md)。
エージェント×スキルの呼び出し規約と5段階の実行順序の**図解**は [docs/sdd-call-map.html](docs/sdd-call-map.html)（ブラウザで開く）。

## 4つの区分

| 区分 | 変わる頻度 | 変えるときの意味 |
|---|---|---|
| **① core（共有）** | どのプロジェクトでも同一 | 変える＝テンプレ自体の改善（全プロジェクトに波及させる価値があるときだけ） |
| **② stack profile** | **スタックごとに1回**（プロジェクトごとではない） | 新しい技術構成を初めて使うときだけ書く。同じスタックの別プロジェクトは使い回す |
| **③ domain** | **プロジェクトごとに毎回**記入 | そのプロジェクトが「何を作るか」。AI に埋めさせてよい |
| **④ 生成物** | 触らない | `apply.py` が②から自動配置するコピー。**編集禁止**（次の配置で上書き） |

---

## ① core — 変わらないもの（SDD の方法論と強制機構）

### SDD 段階駆動スキル（`.claude/skills/`）— 進行役の台本（slash 専用・ワーカーは呼ばない）

> **呼び出し規約**: 段階駆動スキル（discover〜implement）は `disable-model-invocation: true` の slash 専用で、**進行役だけ**が `/x` で起動しワーカーを spawn する。ワーカー役エージェントはこれを呼ばず、委譲プロンプトで起動され、craft は参照スキル（下記 `bdd`・`ubiquitous-language`、および ② の stack 参照スキル）を一次情報にする。EARS だけは craft が `specify/ears.md` にあり scenario-author が Read で参照する。

| パス | 何をする部分か |
|---|---|
| `skills/discover/` | 段階0（発見）。Example Mapping で価値・ルール・具体例・疑問を洗い出す手順。3アナリストへの並行委譲指示を含む |
| `skills/specify/`（+ `ears.md`） | 段階1（仕様化）。discovery を EARS 要件＋Gherkin に清書する手順と EARS 記法リファレンス |
| `skills/plan/` | 段階2（設計）。DDD・レイヤ配置・API契約・データモデル・トレーサビリティ・人間ゲート論点の作り方 |
| `skills/tasks/` | 段階3（作業分解）。内側→外側の TDD ビルド順・シナリオ紐付け・網羅確認の作り方 |
| `skills/implement/` | 段階4（実装）。red→green→refactor、選択的バインド、完了後レビューのループ |
| `skills/bdd/` | 参照知識。Gherkin 記法（Rule: 構造・BRIEF・タグ規約 @R-x/@backend/@e2e） |
| `skills/ubiquitous-language/` | 参照知識。用語集の**運用ルール**（→ 用語表そのものは③） |

### core エージェント（`.claude/agents/`）— 独立コンテキストで働く役割
| パス | 何をする部分か |
|---|---|
| `product-analyst` | discover の価値観点（誰の・何を・なぜ／MVP／スコープ） |
| `quality-analyst` | discover の QA 観点（異常・境界・失敗モードの洗い出し） |
| `solution-analyst` | discover の実現性観点＋ plan/tasks の起草（設計・作業分解） |
| `scenario-author` | specify の清書（EARS＋Gherkin。発明禁止・差し戻し判断） |
| `spec-compliance` | 実装後レビュー：仕様適合・スコープ・CA 遵守の独立検証 |
| `test-coverage` | 実装後レビュー：要件→シナリオ→テストの構造網羅と実行確認 |
| `code-reviewer` | 実装後レビュー：バグ・可読性・重複・簡潔さ（品質一般） |

### 強制機構（hooks / settings / 自己テスト）— 散文でなく決定論で守る層
| パス | 何をする部分か |
|---|---|
| `hooks/guard_architecture.py` | CA 違反編集の遮断（domain/application への FW import・直接SQL・シェル迂回）。**コードは共通、判定値は②の `guard:` から読む** |
| `hooks/guard_no_verify.py` | pre-commit 迂回の遮断（--no-verify / -n / SKIP= / hooksPath 差し替え等） |
| `hooks/guard_sdd_gates.py` | SDD ゲートの決定論化（前段 Approved まで着手不可・承認済み文書の凍結・specs へのシェル書き込み遮断） |
| `hooks/guard_harness.py` | 人間ゲートとハーネス自己保護（**ask**=確認ダイアログ）。specs への `Status: Approved` 書き込み（AI の自己承認防止）と、強制層（hooks・settings.json・profile.yml・apply/validate/_schema・rules 生成物・CI・pre-commit・scripts）への書き込みに人間の明示承認を要求 |
| `hooks/test_guards.py` | 上記4ガードの自己テスト（79ケース）。pre-commit / CI が実行 |
| `settings.json` | フック登録（PreToolUse）＋ SessionStart での自動配置（apply --auto） |

### 差し替え機構（`.claude/profiles/` の機構部分）— ②を成立させる仕組み
| パス | 何をする部分か |
|---|---|
| `profiles/apply.py` | active プロファイルを `.claude/` へ配置（④を生成）。`--auto` は SessionStart 用 |
| `profiles/validate.py` | プロファイルが契約を満たすかの機械検証（必須キー・guard・パス実在） |
| `profiles/_schema/contract.md` | 全プロファイルが埋めるべき項目の定義（契約） |
| `profiles/_schema/profile.template.yml` | 新スタック用の空雛形 |

### その他 core
| パス | 何をする部分か |
|---|---|
| `SETUP.md` | **クローン後に AI が読む実行手順書**（健全性確認→スタック決定→名前差し替え→domain 記入→運用開始） |
| `specs/README.md` | specs/ の規約（フォルダ命名・Status フロー・ゲートの仕様） |
| `.gitignore` の生成物指定 | ④を git 管理外に保つ |

---

## ② stack profile — スタックごとに変わるもの（`.claude/profiles/<id>/`）

**単一の真実はここ。** 新しい技術構成のときだけ1式書き、同スタックの別プロジェクトは使い回す。
現行の見本: `python-fastapi/`（FastAPI + React）。

| パス | 何をする部分か |
|---|---|
| `profile.yml` | マニフェスト。層→実パス（`layers`）・禁止 import・BDD/E2E ランナー・テスト/品質ゲートコマンド・`guard:`（編集時フックが読む投影） |
| `rules/` | パススコープ制約（各層を触るときだけ読まれる責務ルール）→ ④へ配置 |
| `skills/` | stack 参照知識（backend/frontend アーキテクチャ・design トークン・e2e 方針）→ ④へ配置 |
| `agents/` | 実装者エージェント（backend-engineer / frontend-engineer）→ ④へ配置 |
| `profiles/.active` | いまどのスタックが有効か（apply.py が更新） |

> 補足: `.pre-commit-config.yaml` と `.github/workflows/ci.yml` は**枠組みは共通**だが、
> 中身のコマンドが現行スタック直書き（既知の制約）。多スタック化するときは
> 「プロファイルが CI/pre-commit 設定も提供する」方式にする（[README](README.md) の既知の制約参照）。

---

## ③ domain — プロジェクトごとに変わるもの（毎回記入。AI に埋めさせてよい）

| 場所 | 何を記入するか |
|---|---|
| `CLAUDE.md` の `<...>` | プロジェクト名・「何を作るか」（誰の・何を・なぜ）・スタック要約の `<id>` |
| `skills/ubiquitous-language/` の用語表 | このプロジェクトのドメイン用語（日本語・英語識別子・定義）。運用ルール部分は①なので変えない |
| `specs/NNNN-*/` | SDD 成果物そのもの（discovery→tasks）。ワークフローの産出物 |
| `backend/` `frontend/` 等の実装 | プロダクトコード（②のスキャフォルドに沿って実装される） |

---

## ④ 生成物 — 触らないもの（git 管理外・自動再生成）

`apply.py` が②から `.claude/` の固定パス（Claude Code が実際に読む場所）へ配置するコピー。
**直接編集しても次の配置で上書きされる。修正は必ず②側で行う。**

| パス | 由来 |
|---|---|
| `.claude/rules/*` | ← `profiles/<id>/rules/` |
| `.claude/skills/backend-architecture・frontend-architecture・design・e2e-testing` | ← `profiles/<id>/skills/` |
| `.claude/agents/backend-engineer.md・frontend-engineer.md` | ← `profiles/<id>/agents/` |
| `.claude/.profile-applied` | 配置台帳（スタック切替時の掃除に使う） |

---

## 修正の適用パス（何が要るか・いつ効くか・何が守るか）

前提ツールは **Python 3 系のみ**（ハーネス機構は stdlib で動く。コマンド名は `python` / `python3` のどちらでもよく、フック登録は `python … || python3 …` の両対応——**Windows の `python3` は Store スタブで実行されないことがある**）。スタックの品質ゲートは②のツール（例: uv / npm）、コミット時強制には `pre-commit install` 済みであることが必要。

### まず全体感：適用タイミングは4パターン

| タイミング | 対象 | なぜそう効くか |
|---|---|---|
| **即時** | ガード本体（`hooks/guard_*.py`）・②`profile.yml` の `guard:` 値 | ツール呼び出しごとにサブプロセスで実行され、毎回ファイルを読み直すため |
| **apply で即時（放置でも次セッション）** | ②の rules・stack スキル・engineer | `apply.py` が④へ配置して初めて Claude Code に読まれる。**SessionStart が自動実行するので何もしなくても次セッションには効く** |
| **次の呼び出しから** | core スキル・エージェント本文 | 呼ばれた時に読まれる（一覧に出る説明文だけは次セッション） |
| **次セッションから** | `settings.json` のフック**登録**・CLAUDE.md | 起動時にスナップショットされるため |

| 直す対象 | 編集する場所 | 適用のされ方（いつ効くか） | 自動検証（何が守るか） |
|---|---|---|---|
| SDD の手順（core スキル） | `.claude/skills/<名前>/SKILL.md` | **次にそのスキルが呼ばれた時**から（説明文の変更は次セッション） | 人間レビュー（機械検証なし） |
| core エージェントの役割 | `.claude/agents/<名前>.md` | **次にそのエージェントを spawn した時**から（一覧の説明は次セッション） | 同上 |
| ガードの判定ロジック | `.claude/hooks/guard_*.py` | **即時**（ツール呼び出しごとにサブプロセス実行される） | `test_guards.py` を同時に更新。**pre-commit が .claude 変更時に79ケースを強制実行**（通らないとコミット不可） |
| フックの**登録**（どのツールに効かせるか） | `.claude/settings.json` | **次セッション**から（登録は起動時にスナップショットされる） | JSON 構文エラーは起動時に判明 |
| ガードの**判定値**（禁止 import・対象パス等） | ②の `profile.yml` の `guard:` | **即時**（フックが毎回 profile.yml を直接読む） | `validate.py`（pre-commit / CI） |
| rules・stack スキル・engineer | ②の `profiles/<id>/{rules,skills,agents}/` | `python3 .claude/profiles/apply.py` で**即時配置**。放置しても**次の SessionStart で自動反映** | `validate.py` ＋ ④との diff は apply が常に上書きで解消 |
| テスト/品質ゲートのコマンド | ②の `profile.yml`（`*_cmd`） | **次にエージェント/レビュアーがそのコマンドを読んだ時**から（※ pre-commit / CI のコマンドは別途直書き＝既知の制約） | `validate.py` |
| CLAUDE.md・用語表（③） | `CLAUDE.md`／`skills/ubiquitous-language/` | CLAUDE.md は**次セッション**、用語表は**次に参照された時**から | 人間レビュー |
| **Approved 済みの仕様（③）** | `specs/<feature>/…` | **そのままでは編集不可（ゲートが deny）**。下の差し戻しフローで適用 | `guard_sdd_gates` が順序・凍結を強制 |
| pre-commit / CI の設定 | `.pre-commit-config.yaml`／`.github/workflows/ci.yml` | pre-commit は**次のコミット**、CI は**次の push/PR** から | pre-commit 自身が構文検査 |

### Approved 済み仕様の修正フロー（ゲートが強制する唯一の道）

```
1. 対象文書の Status: Approved → Draft に戻す   ← Status 行を触る編集だけはゲートが許可する
2. 内容を修正する（Draft なので編集可能）        ← acceptance.feature は requirements=Draft で解凍
3. 人間レビュー → 承認者が Status: Approved に    ← 下流（design/tasks）に影響するなら同様に差し戻して伝播
```

### 新スタック追加のフロー（②を1式作る）

```
1. profiles/_schema/profile.template.yml を profiles/<id>/profile.yml にコピーして埋める
2. rules/ skills/ agents/ をそのスタック用に用意する
3. python3 .claude/profiles/validate.py <id>     ← 契約適合を機械チェック
4. python3 .claude/profiles/apply.py <id>        ← 配置＋ .active 切替（以後は SessionStart が自動）
5. .gitignore に新スタックの配置物（④）のパスを追記する
```

### 修正そのものを守る仕組み（「修正の適用」もハーネスの検証下にある）

修正はフリーハンドではない。**何を直したかに応じて、対応する検証が自動で走り、通らない修正はコミットできない**。

- **ガード（`hooks/guard_*.py`）を直したら** → 挙動が変わるなら **`test_guards.py` の期待値も同時に更新する**。pre-commit が `.claude/{hooks,profiles}` 変更時に **79ケースの自己テストを強制実行**し、テストと不整合なガード修正はコミット不可。CI（harness ジョブ）でも再実行される。なお強制層への編集自体も `guard_harness` が **ask**（人間の確認）を要求する
- **プロファイル（②）を直したら** → pre-commit / CI が **`validate.py`（契約適合）を強制実行**。必須キー欠落・実在しないパスはコミット不可
- **specs（③）を直したら** → `guard_sdd_gates` が順序・凍結を編集時に強制（上の差し戻しフロー以外の道がない）
- **実装（③）を直したら** → 編集時ガード（CA・直接SQL）＋ pre-commit / CI の品質ゲート（lint・型・アーキ検証・テスト）
- **フックの検証をすり抜けようとしたら** → `guard_no_verify` が `--no-verify` / `-n` / `SKIP=` / `core.hooksPath` 差し替え等の迂回自体を遮断

つまり検証の連鎖は「実装 ← ガード ← ガードのテスト」まで遡って閉じており、**どの層の修正にも“それを検査する層”が存在する**。唯一の例外は core スキル・エージェント本文（散文）で、これは人間レビューが最後の砦。

## 迷ったらこの表（どこを直すべきか）

| やりたいこと | 直す場所 |
|---|---|
| SDD の進め方・レビューの型を変えたい | ①（core skills / agents）——全プロジェクトに波及 |
| 技術の定石・禁止事項・コマンドを変えたい | ②（`profiles/<id>/`）——同スタック全体に波及 |
| このプロジェクトの用語・要件・仕様を書きたい | ③（CLAUDE.md プレースホルダ・用語表・specs/） |
| `.claude/rules/` 等の内容を直したい | **②で直す**（④は生成物。直接編集は無効） |
| 新しいスタックを使いたい | ②を1式作る（`_schema/` の雛形→ `validate.py` で契約チェック→ `apply.py <id>`） |
