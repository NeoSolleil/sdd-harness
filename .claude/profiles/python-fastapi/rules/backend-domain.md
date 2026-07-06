---
paths:
  - "backend/app/domain/**"
---

# domain 層のルール（最内・依存ゼロ）

domain は Clean Architecture の最内層。**永続化・フレームワークに無依存の純粋な Python** で書く。

## MUST
- エンティティ・値オブジェクトは標準ライブラリ（`dataclasses` / `enum` / `datetime` / `decimal` / `uuid` 等）と他の domain 要素のみで構成する。
- ビジネスルール（不変条件・計算・状態遷移）はこの層に置く。
- 型ヒント必須（pyright strict 対象）。

## MUST NOT
- `app.application` / `app.adapters` / `app.infrastructure` を import しない（外側への依存禁止）。
  → **import-linter の layers 契約で機械強制**。違反は `uv run lint-imports` で失敗する。
- `fastapi` / `pydantic` / `sqlalchemy` を import しない。永続化・HTTP・I/O の概念を持ち込まない。
  → **import-linter の `forbidden` 契約「domain must be framework-free」で機械強制**。`uv run lint-imports` で違反を検出・ブロックする。
- SQLAlchemy の ORM モデルをここに置かない。ORM モデルは `infrastructure` 側に置き、entity ↔ ORM の変換も infrastructure で行う。

## 補足
domain は「テーブル」ではなく「概念」を表す。マスタも記録も、まず永続化に無依存の純粋なエンティティ・値オブジェクトとして表現する（テーブル設計は後の infrastructure の関心）。
