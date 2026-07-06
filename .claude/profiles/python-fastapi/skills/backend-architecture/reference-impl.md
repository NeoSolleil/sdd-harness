# reference-impl — 縦切りの実装見本（few-shot）

このスタック（FastAPI ＋ SQLAlchemy 2.0）で1機能を **domain → application → infrastructure → adapters → 結線 → テスト** に通す最小見本。

> **題材（Note）は中立の書式見本。** 実プロジェクトの語彙・仕様は specs/ と design.md が正であり、題材は必ず差し替える。
> 初回のコード生成前に読み、**置き場所・変換・注入・エラー写像・原子的更新**のパターンをそのまま踏襲する。

## 1) domain — 純粋なエンティティ・不変条件・安定エラーコード（標準ライブラリのみ）

```python
# backend/app/domain/errors.py
from enum import StrEnum


class ErrorCode(StrEnum):
    """安定した内部エラーコードの台帳（ログ・API 双方から追跡できる）。"""

    NOTE_TITLE_EMPTY = "NOTE_TITLE_EMPTY"
    NOTE_TITLE_TOO_LONG = "NOTE_TITLE_TOO_LONG"
    NOTE_NOT_FOUND = "NOTE_NOT_FOUND"


class DomainError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
```

```python
# backend/app/domain/note.py
from dataclasses import dataclass

from app.domain.errors import DomainError, ErrorCode

TITLE_MAX = 100


@dataclass(frozen=True)
class Note:
    """不変条件はエンティティ自身が守る（生成できた時点で常に正しい）。"""

    id: int | None
    title: str
    view_count: int = 0

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise DomainError(ErrorCode.NOTE_TITLE_EMPTY, "title must not be empty")
        if len(self.title) > TITLE_MAX:
            raise DomainError(ErrorCode.NOTE_TITLE_TOO_LONG, f"title must be <= {TITLE_MAX} chars")
```

## 2) application — リポジトリ抽象＋ユースケース（domain のみに依存・素の dataclass DTO）

```python
# backend/app/application/note_repository.py
from typing import Protocol

from app.domain.note import Note


class NoteRepository(Protocol):
    """application が定義する抽象。具象は infrastructure（依存性逆転）。"""

    def add(self, note: Note) -> Note: ...
    def get(self, note_id: int) -> Note | None: ...
    def increment_view_count(self, note_id: int) -> None: ...
```

```python
# backend/app/application/view_note.py
from dataclasses import dataclass

from app.application.note_repository import NoteRepository
from app.domain.errors import DomainError, ErrorCode
from app.domain.note import Note


@dataclass(frozen=True)
class ViewNoteInput:
    note_id: int


class ViewNoteUseCase:
    def __init__(self, notes: NoteRepository) -> None:  # 抽象を注入（具象を知らない）
        self._notes = notes

    def execute(self, data: ViewNoteInput) -> Note:
        note = self._notes.get(data.note_id)
        if note is None:
            raise DomainError(ErrorCode.NOTE_NOT_FOUND, f"note {data.note_id} not found")
        self._notes.increment_view_count(data.note_id)  # 原子的更新は具象側の責務
        return note
```

## 3) infrastructure — ORM モデル・具象リポジトリ（entity↔ORM 変換・原子的更新）

```python
# backend/app/infrastructure/models.py
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base  # 宣言ベースはスキャフォールド（db.py）のものを共用


class NoteModel(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column()
    view_count: Mapped[int] = mapped_column(default=0)
```

```python
# backend/app/infrastructure/note_repository.py
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.domain.note import Note
from app.infrastructure.models import NoteModel


class SqlNoteRepository:
    """NoteRepository（application の抽象）の SQLAlchemy 実装。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, note: Note) -> Note:
        row = NoteModel(title=note.title, view_count=note.view_count)
        self._session.add(row)
        self._session.flush()  # id 採番
        return self._to_entity(row)

    def get(self, note_id: int) -> Note | None:
        row = self._session.get(NoteModel, note_id)
        return self._to_entity(row) if row else None

    def increment_view_count(self, note_id: int) -> None:
        # 原子的更新: read→modify→write で上書きしない（同時要求で欠損する）
        self._session.execute(
            update(NoteModel)
            .where(NoteModel.id == note_id)
            .values(view_count=NoteModel.view_count + 1)
        )

    @staticmethod
    def _to_entity(row: NoteModel) -> Note:  # ORM モデルを外へ漏らさない
        return Note(id=row.id, title=row.title, view_count=row.view_count)
```

## 4) adapters — schemas（Pydantic v2）と api（薄いルーター・エラー写像）

```python
# backend/app/adapters/schemas/note.py
from pydantic import BaseModel, ConfigDict


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # entity から model_validate で生成

    id: int
    title: str
    view_count: int
```

```python
# backend/app/adapters/api/notes.py
from fastapi import APIRouter, Depends, HTTPException

from app.adapters.schemas.note import NoteResponse
from app.application.view_note import ViewNoteInput, ViewNoteUseCase
from app.domain.errors import DomainError, ErrorCode

router = APIRouter(prefix="/api/notes", tags=["notes"])

# エラー写像表: 内部コード → HTTP（design.md の API 契約と一致させる）
_STATUS: dict[ErrorCode, int] = {
    ErrorCode.NOTE_NOT_FOUND: 404,
    ErrorCode.NOTE_TITLE_EMPTY: 422,
    ErrorCode.NOTE_TITLE_TOO_LONG: 422,
}


def get_view_note_usecase() -> ViewNoteUseCase:
    """抽象の供給点。結線は composition root（main.py）が dependency_overrides で行う。"""
    raise NotImplementedError("wired in app.main")


@router.get("/{note_id}", response_model=NoteResponse)
def view_note(
    note_id: int,
    usecase: ViewNoteUseCase = Depends(get_view_note_usecase),
) -> NoteResponse:
    try:
        note = usecase.execute(ViewNoteInput(note_id=note_id))
    except DomainError as e:  # ビジネス例外を 500 で漏らさない
        raise HTTPException(
            status_code=_STATUS.get(e.code, 500),
            detail={"code": e.code, "message": str(e)},
        ) from e
    return NoteResponse.model_validate(note)
```

## 5) 結線 — composition root（main.py はレイヤ契約の外）

セッション供給はスキャフォールドの `db.py` に FastAPI 依存として足す（1リクエスト1セッション、UoW 定石どおり commit／rollback）。

```python
# backend/app/infrastructure/db.py（抜粋: リクエストごとのセッション供給）
from collections.abc import Iterator

from sqlalchemy.orm import Session


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

```python
# backend/app/main.py（抜粋: 抽象↔具象の配線だけを担う）
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.adapters.api import notes
from app.application.view_note import ViewNoteUseCase
from app.infrastructure.db import get_session  # 1リクエスト1セッションの供給元
from app.infrastructure.note_repository import SqlNoteRepository

app = FastAPI(title="<project> API")
app.include_router(notes.router)


def _view_note_usecase(session: Session = Depends(get_session)) -> ViewNoteUseCase:
    return ViewNoteUseCase(SqlNoteRepository(session))


app.dependency_overrides[notes.get_view_note_usecase] = _view_note_usecase
```

## 6) テスト — application は in-memory フェイクで（DB 不要・高速）

```python
# backend/tests/unit/test_view_note.py
import pytest

from app.application.view_note import ViewNoteInput, ViewNoteUseCase
from app.domain.errors import DomainError, ErrorCode
from app.domain.note import Note


class InMemoryNoteRepository:
    """NoteRepository 互換のフェイク（Protocol なので継承不要）。"""

    def __init__(self) -> None:
        self.rows: dict[int, Note] = {}

    def add(self, note: Note) -> Note:
        note_id = note.id or len(self.rows) + 1
        saved = Note(id=note_id, title=note.title, view_count=note.view_count)
        self.rows[note_id] = saved
        return saved

    def get(self, note_id: int) -> Note | None:
        return self.rows.get(note_id)

    def increment_view_count(self, note_id: int) -> None:
        note = self.rows[note_id]
        self.rows[note_id] = Note(id=note.id, title=note.title, view_count=note.view_count + 1)


# 命名: test_<振る舞い>_<条件>_<期待>
def test_view_note_存在しないID_NOT_FOUNDエラー() -> None:
    usecase = ViewNoteUseCase(InMemoryNoteRepository())

    with pytest.raises(DomainError) as e:
        usecase.execute(ViewNoteInput(note_id=999))

    assert e.value.code is ErrorCode.NOTE_NOT_FOUND


def test_view_note_閲覧成功_閲覧数が1増える() -> None:
    repo = InMemoryNoteRepository()
    repo.rows[1] = Note(id=1, title="t", view_count=0)
    usecase = ViewNoteUseCase(repo)

    usecase.execute(ViewNoteInput(note_id=1))

    assert repo.rows[1].view_count == 1
```

## パターンの要点（生成コードのセルフチェック）

- **依存方向**: adapters/api が import するのは application の抽象＋schemas だけ（infrastructure を知らない）。
- **変換の境界**: ORM↔entity は infrastructure、entity↔DTO は adapters/schemas。domain は誰にも依存しない。
- **注入**: 抽象の供給点（`get_*`）を adapters に置き、結線は main.py の `dependency_overrides`。
- **エラー**: domain の安定コード（enum）→ adapters の写像表で HTTP へ。500 で漏らさない。
- **原子的更新**: カウンター等は式更新。read→modify→write しない。
- **BDD との関係**: 上の単体テストは TDD の産物（シナリオ非対応で正当）。`@backend` シナリオのバインドは implement スキルの手順（`@scenario` の明示バインド）に従う。
