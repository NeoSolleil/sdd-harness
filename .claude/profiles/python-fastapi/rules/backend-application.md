---
paths:
  - "backend/app/application/**"
---

# application 層のルール（ユースケース＋リポジトリ抽象）

application は **domain のみに依存**する。永続化や Web の詳細を知らない。

## MUST
- ユースケース（アプリケーションサービス）を実装する。ドメインのエンティティ・値オブジェクトを組み合わせて手続きを表現する。
- リポジトリは**抽象インターフェース**（`abc.ABC` または `typing.Protocol`）として *この層で* 定義する。具象実装は `infrastructure` に置く（依存性逆転）。
- 依存（リポジトリ等）はコンストラクタ等で**抽象として注入**する。結線は composition root（`app/main.py`）が担う。
- ユースケースの入出力 DTO は素の `dataclass` を基本とする。

## MUST NOT
- `app.adapters` / `app.infrastructure` を import しない。
  → **import-linter の layers 契約で機械強制**。
- 具象リポジトリ（DB 実装）を直接 import / new しない。
- `fastapi` / `sqlalchemy` / `pydantic` を import しない（永続化・Web・検証の詳細に踏み込まない）。
  → **import-linter の `forbidden` 契約「application must not depend on web or ORM frameworks」で機械強制**。Pydantic も禁止対象（入出力検証は adapters/schemas に寄せる＝厳密版 CA）。

## 補足
「どう保存するか」は知らず、「何をするか」だけを書く層。例: 記録保存のユースケースは `XxxRepository`（抽象）に保存を委譲し、具象は infrastructure に置く。
