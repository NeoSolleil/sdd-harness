---
paths:
  - "backend/app/adapters/**"
---

# adapters 層のルール（API コントローラ＋ Pydantic DTO）

adapters は `application` / `domain` に依存してよいが、`infrastructure` に依存してはならない。
→ **import-linter の layers 契約で機械強制**（adapters → infrastructure の import は失敗する）。

## adapters/api（FastAPI ルーター）
- **入力は必ず Pydantic スキーマで受ける**（クエリ・ボディ・パスパラメータ）。検証なしの生入力を扱わない。
- ルーターは薄いコントローラに徹する。ビジネスロジックを書かず、ユースケース（application）に委譲する。
- DB・SQLAlchemy に直接触れない。リポジトリ具象も import しない。依存は FastAPI の DI（`Depends`）で**抽象**を受け取り、具象は composition root で結線する。
- 応答も Pydantic スキーマ（出力 DTO）で返す。domain エンティティをそのまま返さない。

## adapters/schemas（Pydantic v2 DTO）
- 入出力の検証・整形を担う **Pydantic v2** モデルを置く。
- domain エンティティとは**別物**として定義し、境界で相互変換する（domain を Pydantic で汚さない）。
- Pydantic v2 のイディオムを使う（`model_config` / `field_validator` / `Annotated` 型など）。

## 補足
ここは「外の世界（HTTP）」と「中の世界（ユースケース）」の翻訳層。検証・シリアライズはここで完結させる。
