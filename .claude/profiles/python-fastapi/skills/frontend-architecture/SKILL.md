---
name: frontend-architecture
description: ドメイン参照。frontend の Clean Architecture ＋ Atomic Design、Smart/Dumb 分離、SWR でのデータ取得、描画ロジックの分離、TypeScript strict、E2E のための data-testid、縦切りのリファレンス実装（reference-impl.md）。frontend を設計・実装する際に参照する。
---

# frontend-architecture — frontend 設計の知識

React + TypeScript strict（Vite 前提）。関心を分離し、テスト・E2E しやすく保つ。**原則は汎用**。DOM 外の命令的描画を伴う UI（Canvas/WebGL 等）も対象に含む。

> 縦切りの実装見本（api→lib→Dumb/Smart→テスト）は同梱の [reference-impl.md](reference-impl.md)。**初回のコード生成前に読み、パターンを踏襲する。**

## ディレクトリと責務

- `api/` … backend 呼び出しを集約（fetch 直書き禁止）。**SWR** で取得・キャッシュ。
- `components/` … UI（**Atomic Design**: atoms → molecules → organisms → templates → pages）。
- `lib/` … フレームワーク非依存の純粋ロジック（計算・変換）。単体テストしやすく置く。
- 重い／特殊な描画は専用ディレクトリへ分離（例: Canvas 描画なら `canvas/`）。

## Smart / Dumb（Container / Presentational）

- **Smart**: データ取得・状態・副作用（SWR 呼び出し、イベント処理）。
- **Dumb**: props だけで描画する純粋表示。
- Dumb を多く、Smart を薄く。テストは Dumb と `lib/` を中心に。

## データ取得（SWR）

- サーバ状態は SWR。キーは API パスに対応。書き込みは `useSWRMutation`（または `mutate`）で行い、成功時にキャッシュを再検証する。
- fetch のボイラープレート（ヘッダ・HTTP/ネットワークエラーの変換）は `api/` の**共通クライアント**に集約し、統一エラー型で返す。
- ローカル UI 状態は `useState`。サーバ状態と混ぜない。
- `isLoading` / `error` を必ず UI で扱う（ローディング・エラー表示）。

## 描画ロジックの分離（DOM 外描画を含む）

- 描画は React の再レンダーから分離する。**Canvas/WebGL 等の命令的描画**は `requestAnimationFrame` で回し、React state に乗せない。
- 入力 → 座標/イベント → 判定 のような純粋ロジックは `lib/` か描画ディレクトリの**純粋関数**にして単体テストする。
- React と描画層の橋渡しは最小限の state／コールバックで。
- React 内で完結する重い表示は `React.memo` / `useRef` で再レンダーを抑える（高頻度更新の値を props で毎回流さない）。

## TypeScript / 品質

- strict 厳守。**`any` 禁止**（`unknown`＋絞り込み、または正確な型）。
- API の戻り値型を定義（`api/` に置く）。
- ESLint / Prettier / `tsc --noEmit` / build を緑に。

## テスト戦略（Vitest + React Testing Library）

テスト名は「振る舞い・条件・期待」が1文で分かる形にする。

| レベル | 対象 | 戦略 | モック |
| --- | --- | --- | --- |
| 1. 純粋ロジック | `lib/`・描画ディレクトリの純粋関数 | 入出力の検証 | 不要 |
| 2. Dumb | `components/`（表示部品） | `props` にダミーデータと `vi.fn()` を渡し、表示・発火を検証 | 不要 |
| 3. フック | `api/`（SWR フック） | 取得・エラー・ローディングの分岐を検証 | `vi.mock` で `fetch`（または fetch 層）を置換 |
| 4. Smart/Page | ページ・コンテナ | 繋ぎ込み責務（分岐・props 受け渡し）の検証 | `vi.mock` でフックを置換 |

## E2E のための約束（`e2e-testing` 参照）

- ユーザー操作・検証対象の **DOM 要素**に `data-testid` を付ける。
- **DOM に無い描画（Canvas 等）**は testid を付けられないので、E2E 用のテストシーム（座標・状態の露出）を用意する。

## 強制（参考）

- 責務ディレクトリ間の依存方向: **dependency-cruiser**（`npm run arch:check`・ルールは `frontend/.dependency-cruiser.cjs`）。lib の純粋性・api 集約（Smart のみ）・canvas 分離・循環禁止を機械検証。型だけの import（`import type`）は対象外。
- 型: tsc strict。lint/format: ESLint / Prettier。ビルド: vite build。

## 見た目

- 色・余白・字は `design`（デザイントークン）に従う。描画層の色もトークンと揃える。
