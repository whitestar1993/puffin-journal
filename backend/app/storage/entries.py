from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Entry, entry_tags
from app.storage import prompts as prompts_store
from app.storage import tags as tags_store
from app.storage.errors import Invalid, NotFound


@dataclass
class EntryData:
    mood: int
    energy: int | None = None
    sleep: int | None = None
    tag_ids: list[int] = field(default_factory=list)
    prompt_id: int | None = None
    prompt_answer: str | None = None
    note: str | None = None


def _scale(value: int | None, name: str, required: bool = False) -> int | None:
    if value is None:
        if required:
            raise Invalid(f"{name} is required")
        return None
    if not isinstance(value, int) or not 1 <= value <= 5:
        raise Invalid(f"{name} must be 1-5")
    return value


def _text(value: str | None, limit: int = 10_000) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) > limit:
        raise Invalid(f"Text too long (max {limit} characters)")
    return value or None


def get(db: Session, user_id: int, day: date) -> Entry | None:
    return db.scalar(select(Entry).where(Entry.user_id == user_id, Entry.date == day))


def upsert(db: Session, user_id: int, day: date, data: EntryData, today: date) -> tuple[Entry, bool]:
    """Create or replace the entry for ``day``. Returns (entry, created)."""
    if day > today:
        raise Invalid("Cannot write entries for future dates")
    mood = _scale(data.mood, "mood", required=True)
    energy = _scale(data.energy, "energy")
    sleep = _scale(data.sleep, "sleep")
    answer = _text(data.prompt_answer, 2_000)
    note = _text(data.note)
    tags = tags_store.get_many(db, user_id, data.tag_ids)

    entry = get(db, user_id, day)
    created = entry is None
    if entry is None:
        entry = Entry(user_id=user_id, date=day)
        db.add(entry)

    entry.mood, entry.energy, entry.sleep, entry.note = mood, energy, sleep, note
    entry.tags = tags

    # Prompt: a skipped prompt (no answer) stores nothing. When answered, snapshot
    # the prompt text the first time so later pool edits never rewrite history.
    if answer is None:
        entry.prompt_id = entry.prompt_text = entry.prompt_answer = None
    else:
        if data.prompt_id is not None and (created or data.prompt_id != entry.prompt_id):
            try:
                prompt = prompts_store.get(db, user_id, data.prompt_id)
            except NotFound:
                db.rollback()
                raise Invalid("Unknown prompt id") from None
            entry.prompt_id, entry.prompt_text = prompt.id, prompt.text
        elif data.prompt_id is None and not entry.prompt_text:
            raise Invalid("prompt_id is required when answering a prompt")
        entry.prompt_answer = answer

    db.commit()
    db.refresh(entry)
    return entry, created


def delete(db: Session, user_id: int, day: date) -> None:
    entry = get(db, user_id, day)
    if entry is None:
        raise NotFound("No entry for that date")
    db.delete(entry)
    db.commit()


def _escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search(
    db: Session,
    user_id: int,
    *,
    q: str | None = None,
    tag_ids: list[int] | None = None,
    before: date | None = None,
    limit: int = 30,
) -> list[Entry]:
    """History list, newest first. ``before`` is an exclusive date cursor.

    Multiple tag_ids match entries carrying ALL of them.
    """
    stmt = select(Entry).where(Entry.user_id == user_id)
    if before is not None:
        stmt = stmt.where(Entry.date < before)
    if q and q.strip():
        pattern = f"%{_escape_like(q.strip())}%"
        stmt = stmt.where(
            or_(
                Entry.note.ilike(pattern, escape="\\"),
                Entry.prompt_answer.ilike(pattern, escape="\\"),
                Entry.prompt_text.ilike(pattern, escape="\\"),
            )
        )
    for tag_id in set(tag_ids or []):
        stmt = stmt.where(
            Entry.id.in_(select(entry_tags.c.entry_id).where(entry_tags.c.tag_id == tag_id))
        )
    stmt = stmt.order_by(Entry.date.desc()).limit(max(1, min(limit, 200)))
    return list(db.scalars(stmt))
