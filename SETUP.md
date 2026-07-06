# SETUP.md — クローン後のセットアップ手順（AI 向け）

**あなた（Claude 等の AI）へ**: このリポジトリは SDD ハーネスのテンプレートで、いまクローンされた直後の状態にある。
この手順書に従って、**新しいプロジェクト用のセットアップを完了**させること。
判断が必要な箇所（🙋）は勝手に決めず、ユーザーに確認する（選択肢があるものは AskUserQuestion）。

> 全体像: 構成は **core（変えない）/ stack profile（スタックごと）/ domain（このプロジェクト用に記入）/ 生成物（触らない）** の4区分。
> 台帳と各部の役割は [HARNESS.md](HARNESS.md)、使い方は [README.md](README.md)、規約の正本は [CLAUDE.md](CLAUDE.md)。
> **このセットアップであなたが触るのは domain（③）と、必要なら stack profile（②）だけ。core は変えない。**

---

## 1. リポジトリの付け替え 🙋

テンプレート由来の履歴をどうするか、ユーザーに確認する:

- **(a) 履歴を捨てて新規開始（通常はこちら）**: `rm -rf .git && git init` → 新プロジェクトの remote を設定
- **(b) テンプレ履歴を保持**: remote だけ付け替え（`git remote set-url origin <新URL>`）

コミット者名・メールもユーザーに確認する（会社用/個人用の使い分けがあるため勝手に推測しない）。

## 2. ハーネスの健全性確認（クローン直後に必ず）

```bash
python .claude/hooks/test_guards.py      # 期待: 「結果: 79/79 件 期待どおり」
python .claude/profiles/validate.py      # 期待: [OK] python-fastapi: エラー 0
python .claude/profiles/apply.py --auto  # 期待: applied 'python-fastapi' (11 items)
```

- コマンド名が `python` で動かない環境は `python3` に読み替える（**Windows の `python3` は Microsoft Store のスタブで実行されないことがある**ため、settings.json のフック登録は `python … || python3 …` の両対応にしてある）。
- 3つとも通れば、ガード（CA 違反・pre-commit 迂回・SDD ゲート・自己保護）と差し替え機構は稼働状態。
- **1つでも失敗したら先へ進まない**（クローン破損か改変。ユーザーに報告する）。
- apply は以後 SessionStart フックが毎セッション自動実行する（手動は不要）。
- 仕上げに**フックの実弾確認**を1回行う: AI に `backend/app/domain/` 配下へ `import fastapi` を書き込ませてみて、**DENY されること**を確認する（DENY されなければフックが実行されていない＝Python の解決を疑う）。

## 3. スタックの決定 🙋

ユーザーに確認: このプロジェクトの技術スタックは **python-fastapi（FastAPI + React）のままか、別か**。

- **そのまま** → 手順4へ。
- **別スタック** → 以下を実施してから手順5へ:
  1. `.claude/profiles/_schema/profile.template.yml` を `profiles/<id>/profile.yml` にコピーして埋める（契約は [`_schema/contract.md`](.claude/profiles/_schema/contract.md)）
  2. `profiles/<id>/{rules,skills,agents}/` をそのスタック用に用意（python-fastapi のものが見本）
  3. `python3 .claude/profiles/validate.py <id>` → `python3 .claude/profiles/apply.py <id>`
  4. `.gitignore` の「stack profile による生成物」節を新スタックの配置物に合わせて更新
  5. `backend/` `frontend/` のスキャフォルドを自スタックのものへ置き換え、`.pre-commit-config.yaml` と `.github/workflows/ci.yml` のコマンドをプロファイルの `*_cmd` と一致させる（[README](README.md) の既知の制約参照）

## 4. プロジェクト名の差し替え（python-fastapi 続用時）🙋

ユーザーに新しいプロジェクト名を確認し、テンプレ由来の名前を置き換える。**lockfile は直接編集しない**（後で再生成）。

| ファイル | 箇所 |
|---|---|
| `backend/pyproject.toml` | `name = "aim-trainer-backend"` と `description` |
| `backend/app/__init__.py` | docstring |
| `backend/app/main.py` | `FastAPI(title="Aim Trainer API")` |
| `backend/app/infrastructure/db.py` | SQLite ファイル名 `aim_trainer.db` |
| `frontend/package.json` | `"name": "aim-trainer-frontend"` |
| `frontend/index.html` | `<title>` |
| `frontend/src/App.tsx` | 表示名 |

置き換え後、依存とコミット時強制を有効化（lockfile はここで再生成される）:

```bash
cd backend && uv sync && uv run pre-commit install
cd ../frontend && npm install
```

## 5. domain の記入 🙋（AI が対話で埋める部分）

1. ユーザーに「**誰の・何を・なぜ**」をヒアリングし、[CLAUDE.md](CLAUDE.md) の `<...>` プレースホルダを埋める
   （タイトル・「このプロジェクトで何を作るか」・技術スタック要約の `<id>`）。
2. [`.claude/skills/ubiquitous-language/SKILL.md`](.claude/skills/ubiquitous-language/SKILL.md) の用語表を埋める
   （スキル内の「このテンプレの埋め方」に従う。`（例）` 行は削除）。概念がまだ薄い場合は
   中心概念だけ書き、残りは最初の `/discover` で育ててよい。

## 6. 動作確認（任意・ハーネスが「効いている」ことの実地確認）

わざとゲート違反を1つ試し、deny されることを確認する（例: `specs/0001-test/requirements.md` を
Write しようとする → discovery.md が無いので**順序ゲートが拒否**すれば正常）。確認後、試した
ファイルが作られていないことを確認する。

## 7. 運用開始

- 最初の機能は **`/discover`** から（以降 specify → plan → tasks → implement）。
- 各段階の終わりは**人間の承認**（`Status: Approved` にするのは人間の決定。AI が自己承認しない）。
- implement 後はレビュアー3体（spec-compliance / test-coverage / code-reviewer）を並行で回す。

---

## 完了の定義（このセットアップの DoD）

- [ ] git remote / 履歴 / コミット者がユーザーの指示どおり
- [ ] test_guards **79/79**・validate **OK**・apply 済み
- [ ] スタック決定済み（別スタックならプロファイル一式＋validate/apply/gitignore/CI 更新済み）
- [ ] テンプレ由来の名前（上の表の8箇所）が新プロジェクト名に置換済み・lockfile 再生成済み
- [ ] `pre-commit install` 済み（コミット時強制が有効）

> セットアップ完了後の**日々の回し方**（機能の作り方・ゲートでの人間の操作・トラブル対応）は [USAGE.md](USAGE.md) へ。
- [ ] CLAUDE.md のプレースホルダ解消・用語表が実用語（または「初回 discover で追記」と合意済み）
- [ ] ユーザーに完了報告と、次の一歩（`/discover <最初の機能アイデア>`）の提案
