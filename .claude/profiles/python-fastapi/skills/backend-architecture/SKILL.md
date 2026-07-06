---
name: backend-architecture
description: ドメイン参照。backend の Clean Architecture（レイヤと依存方向・依存性逆転）、Pydantic v2 と SQLAlchemy 2.0 のイディオム、縦切りのリファレンス実装（reference-impl.md）、負荷テストの考え方。plan/implement で backend を設計・実装する際に参照する。
---

# backend-architecture — backend 設計の知識

backend は Clean Architecture（外側 infrastructure → adapters → application → domain）。**依存は内向きのみ**。詳細な禁止は `.claude/rules/` と import-linter が強制する。

> 縦切りの実装見本（domain→application→infrastructure→adapters→結線→テスト）は同梱の [reference-impl.md](reference-impl.md)。**初回のコード生成前に読み、パターンを踏襲する。**

## 各層の責務

- **domain**（最内・純粋）: エンティティ・値オブジェクト・不変条件・ビジネスルール。標準ライブラリのみ（`dataclasses`/`enum`/`datetime`/`decimal`）。FW・ORM を import しない。
- **application**: ユースケース（アプリケーションサービス）＋**リポジトリの抽象**（`typing.Protocol` か `abc.ABC`）。入出力は素の `dataclass`。domain のみに依存。FastAPI・SQLAlchemy・Pydantic を使わない。
- **adapters/api**: FastAPI ルーター。薄いコントローラ。入力は Pydantic で検証、依存は `Depends` で**抽象**を受け取る。ビジネスロジックを書かない。infrastructure を import しない。
- **adapters/schemas**: Pydantic v2 DTO。domain エンティティとは別物として定義し、境界で相互変換。
- **infrastructure**: SQLAlchemy 2.0 の ORM モデル・**リポジトリ抽象の具象実装**・entity↔ORM 変換・セッション/エンジン・設定（pydantic-settings）。

## 依存性逆転と結線

- application が**インターフェース**を定義 → infrastructure が**実装**する。
- 具象の注入は composition root（`app/main.py`）で行う（main.py はレイヤ契約の外）。
- ルーターは抽象に依存し、`Depends` で具象が注入される。

## Pydantic v2 イディオム（adapters/schemas）

- `model_config = ConfigDict(...)`（旧 `class Config` は使わない）。
- バリデーションは `field_validator` / `model_validator`、制約型は `Annotated[int, Field(ge=0)]`。
- ORM/エンティティからの生成は `model_config = ConfigDict(from_attributes=True)` ＋ `model_validate(obj)`。
- 出力は明示の Response モデルで返す。domain エンティティを直接返さない。

## SQLAlchemy 2.0 イディオム（infrastructure）

- `DeclarativeBase` を継承、`Mapped[...]` ＋ `mapped_column(...)` の型付きスタイル。
- アクセスは ORM／Core 式のみ。**`text(...)` / `exec_driver_sql` の生SQLは禁止**（pre-commit/CI が検出）。
- リポジトリ実装は ORM モデルで読み書きし、**戻り値は domain エンティティに変換**して返す（ORM を外へ漏らさない）。
- **競合しうる更新は原子的に**: カウンター・集計・残数などは read→modify→write で上書きせず、式更新（`update(Model).values(count=Model.count + 1)`）か `with_for_update()` を使う。同時要求・二重実行で欠損しない書き方を既定にする。
- 将来 PostgreSQL へ移せるよう、SQLite 固有機能に依存しすぎない。URL 1行で切替できる構成を保つ。

## 実装の定石（エラー・セッション・テスト）

- **エラー方針**: domain は domain 固有の例外を投げる（純粋）。例外には**安定した内部エラーコード**（domain の enum）を持たせ、adapters/api で捕捉して**写像表**で HTTP ステータス＋一貫したエラー DTO（`{ "code": ..., "message": ... }` 等）に変換する（対応は design.md の API 契約と一致させる）。ビジネス例外を 500 で漏らさない。
- **構造化ログ**: ログは「イベント名＋キー値」で構造化する（標準 `logging` の `extra=` で可）。自然文だけのメッセージにせず、追跡用の識別子（entity id・リクエスト id 等）を含める。domain 層にはロガーを持ち込まない（純粋）。
- **セッション／Unit of Work**: 原則 **1 リクエスト 1 セッション**。FastAPI の依存でセッションを供給し、ユースケース境界で commit／例外時 rollback。ルーターやドメインで散発的に commit しない。
- **テストの継ぎ目**: application は**リポジトリ抽象の in-memory フェイク**を注入して単体テスト（DB 不要・高速）。infrastructure の具象は実 DB（テスト用 SQLite 等）で別途検証。domain は純粋なので素の単体テスト。adapters/api は **`TestClient` ＋ `dependency_overrides` でユースケースをモック**し、HTTP ステータス・エラー写像・入力バリデーションを検証する。単体テストの命名は `test_<振る舞い>_<条件>_<期待>`。
- **アルゴリズム効率**: Hot Path（リクエスト・フレームごとに走る処理）は **O(1) / O(log N)** を選ぶ（包含判定は `set`/`dict`、ソート済み探索は `bisect`）。Hot Path 以外でのオーバーエンジニアリングは避ける。単体テストの命名は `test_<振る舞い>_<条件>_<期待>`（例: `test_save_record_負のスコア_エラー`）。
- **pytest-bdd のバインド**: `scenarios()` の一括ではなく **`@scenario(FEATURE, "シナリオ名")` の明示バインド**で、そのタスクで green にするシナリオだけを束ねる（`@e2e` や未着手タスク分を undefined で収集しない）。Gherkin タグは pytest マーカーに変換されるため、未登録マーカー警告は pyproject で登録・抑止する。

## 強制（参考）

- 依存方向: import-linter の layers 契約。
- domain/application の FW 非依存: import-linter の forbidden 契約。
- 直接SQL: pre-commit/CI の no-raw-sql チェック。
- 型: pyright strict。lint/format: Ruff。複雑度: xenon。

## 負荷テストの考え方（必要になったら）

- 対象は一覧取得・集計・検索など、件数で重くなる API。
- 観点: スループット（req/s）、p95 レイテンシ、DB クエリ数（N+1 回避）。
- 手段は軽量に: `pytest` ベンチ、または locust/k6 を別途。CI 常時実行はしない（必要時に手動）。
- まず設計で N+1 を避ける（適切な join／eager load、インデックス）。計測は推測の後の確認に使う。
- 本格的に計画するとき（想定負荷の見積り・負荷シナリオ・シーディング）は同梱の [performance.md](performance.md) の手法を使う。
