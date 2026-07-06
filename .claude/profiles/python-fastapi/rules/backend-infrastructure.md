---
paths:
  - "backend/app/infrastructure/**"
---

# infrastructure 層のルール（永続化の具象）

infrastructure は最外層。`adapters` / `application` / `domain` を import してよい（内向き依存はOK）。

## MUST
- **SQLAlchemy 2.0 の ORM モデル**をここに置く（`Mapped` / `mapped_column` の型付きスタイル）。
- application が定義した**リポジトリ抽象の具象実装**をここに置き、`implements` する。
- **ORM モデル ↔ domain エンティティの相互変換**をこの層で行う。リポジトリの戻り値は domain エンティティ（ORM モデルを外へ漏らさない）。
- DB セッション・エンジン・設定（`pydantic-settings`）をここに集約する。
- **競合しうる更新（カウンター・集計等）は原子的に**行う。read→modify→write で上書きせず、式更新（`update(Model).values(x=Model.x + 1)`）か `with_for_update()` を使う。

## MUST NOT
- **直接 SQL を書かない。アクセスは必ず SQLAlchemy ORM 経由**（CLAUDE.md: ORM必須・直接SQL禁止）。
  → import-linter では判定できない（“書き方”の問題）。**層③（pre-commit/Hooks）で `text(...)` / `exec_driver_sql` 等の生SQL口を検出して弾く**ことで決定論化する。それまではレビューで担保。
- ORM モデルを adapters/application/domain にそのまま渡さない。

## 補足
- スキーマ（テーブル・カラム・外部キー・制約）はそのプロジェクトの design.md に従う。
- 将来 PostgreSQL へ載せ替え可能に保つ（特定 DB 固有機能に依存しすぎない）。
