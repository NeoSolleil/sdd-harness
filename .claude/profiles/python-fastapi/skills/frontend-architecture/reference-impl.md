# reference-impl — 縦切りの実装見本（few-shot）

React ＋ TypeScript strict ＋ SWR で1機能を **api（集約）→ lib（純粋ロジック）→ Dumb → Smart → テスト** に通す最小見本。

> **題材（Note 一覧）は中立の書式見本。** 実プロジェクトの語彙・仕様は specs/ と design.md が正であり、題材は必ず差し替える。
> 初回のコード生成前に読み、**api 集約・Dumb/Smart 分離・testid・純粋ロジック分離**のパターンをそのまま踏襲する。

## 1) api/ — backend 呼び出しの集約（`fetch` はここだけ・URL を外へ漏らさない）

fetch のボイラープレート（ヘッダ・エラー変換・ネットワーク例外）は**共通クライアント1枚**に集約する。

```typescript
// frontend/src/api/client.ts
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly cause?: unknown,
  ) {
    super(message);
  }
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

/** HTTP エラー・ネットワーク例外を ApiError に一元変換する。 */
export async function apiClient<T>(endpoint: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${endpoint}`, {
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      ...options,
    });
  } catch (cause) {
    throw new ApiError(0, 'network error', cause);
  }
  if (!res.ok) throw new ApiError(res.status, `API error: ${res.statusText}`);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
```

```typescript
// frontend/src/api/notes.ts
import useSWR from 'swr';
import useSWRMutation from 'swr/mutation';

import { apiClient } from './client';

export type Note = {
  id: number;
  title: string;
  viewCount: number;
};

const NOTES_KEY = '/api/notes'; // SWR キーは API パスに対応

/** サーバ状態は SWR。コンポーネントはこのフックだけを知る（URL を知らない）。 */
export function useNotes() {
  const { data, error, isLoading } = useSWR(NOTES_KEY, () => apiClient<Note[]>(NOTES_KEY));
  return { notes: data ?? [], error, isLoading };
}

/** 書き込みは useSWRMutation。成功時に同キーのキャッシュが再検証される。 */
export function useCreateNote() {
  const { trigger, isMutating, error } = useSWRMutation(
    NOTES_KEY,
    (key: string, { arg }: { arg: { title: string } }) =>
      apiClient<Note>(key, { method: 'POST', body: JSON.stringify(arg) }),
  );
  return { createNote: trigger, isCreating: isMutating, error };
}
```

## 2) lib/ — フレームワーク非依存の純粋ロジック（描画から剥がす）

```typescript
// frontend/src/lib/sortNotes.ts
import type { Note } from '../api/notes';

/** 閲覧数の降順（同数は id 昇順）。純粋関数なのでそのまま単体テストできる。 */
export function sortByViewCount(notes: readonly Note[]): Note[] {
  return [...notes].sort((a, b) => b.viewCount - a.viewCount || a.id - b.id);
}
```

## 3) Dumb — props のみで描画（testid は `[コンテキスト]-[役割]-[要素]`）

```tsx
// frontend/src/components/organisms/NoteList.tsx
import type { Note } from '../../api/notes';

type Props = {
  notes: readonly Note[];
};

/** 表示専念。データ取得・副作用を持たない（テストは props を渡すだけ）。 */
export function NoteList({ notes }: Props) {
  if (notes.length === 0) {
    return <p data-testid="notes-empty-message">まだありません</p>;
  }
  return (
    <ul data-testid="notes-list">
      {notes.map((note) => (
        <li key={note.id} data-testid="notes-list-item">
          {note.title}（{note.viewCount}）
        </li>
      ))}
    </ul>
  );
}
```

## 4) Smart — 唯一フック（サーバ状態）を呼ぶ側。`isLoading` / `error` を必ず扱う

```tsx
// frontend/src/components/pages/NotesPage.tsx
import { useNotes } from '../../api/notes';
import { sortByViewCount } from '../../lib/sortNotes';
import { NoteList } from '../organisms/NoteList';

export function NotesPage() {
  const { notes, error, isLoading } = useNotes();

  if (isLoading) return <p data-testid="notes-loading-message">読み込み中…</p>;
  if (error) return <p data-testid="notes-error-message">読み込みに失敗しました</p>;

  return <NoteList notes={sortByViewCount(notes)} />;
}
```

## 5) テスト — Dumb は props、lib は純粋関数（vitest）

```tsx
// frontend/src/components/organisms/NoteList.test.tsx
import { render, screen } from '@testing-library/react';
import { NoteList } from './NoteList';

test('ノートが無い場合は空メッセージを表示する', () => {
  render(<NoteList notes={[]} />);
  expect(screen.getByTestId('notes-empty-message')).toBeInTheDocument();
});
```

```typescript
// frontend/src/lib/sortNotes.test.ts
import { sortByViewCount } from './sortNotes';

test('閲覧数の降順に並ぶ', () => {
  const sorted = sortByViewCount([
    { id: 1, title: 'a', viewCount: 1 },
    { id: 2, title: 'b', viewCount: 5 },
  ]);
  expect(sorted.map((n) => n.id)).toEqual([2, 1]);
});
```

## パターンの要点（生成コードのセルフチェック）

- **URL / `fetch` は `api/` に閉じる**。コンポーネントは `useXxx` フックだけを知る。
- **fetch のボイラープレートとエラー変換は `api/client.ts` に集約**（HTTP／ネットワークエラーを `ApiError` に統一）。
- **書き込みは `useSWRMutation`**（`trigger`）で行い、成功時にキャッシュを再検証する。
- **Dumb を厚く**（props のみ・testid 付与）、**Smart は薄く**（取得と分岐だけ）。
- **計算・並べ替えは `lib/` の純粋関数へ**（描画から剥がす → そのまま単体テスト）。
- **`isLoading` / `error` の分岐にも testid**（E2E が状態を観測できる）。
- **`any` を書かない**（`unknown`＋絞り込み、または正確な型）。
- **DOM 外描画（Canvas 等）はこの見本の対象外**: テストシームの作法は `e2e-testing` と SKILL.md の「描画ロジックの分離」参照。
