from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import User
from app.schemas import DayOut, EntryIn, EntryOut, PromptOut, TodayOut
from app.config import get_settings
from app.storage import NotFound
from app.storage import entries as entries_store
from app.storage import prompts as prompts_store
from app.timeutil import today

router = APIRouter(tags=["entries"])


@router.get("/today", response_model=TodayOut)
def get_today(_: User = Depends(current_user)):
    return TodayOut(today=today(), tz=get_settings().tz)


@router.get("/days/{day}", response_model=DayOut)
def get_day(day: date, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Entry (if any) plus the prompt to show for that date."""
    entry = entries_store.get(db, user.id, day)
    prompt = None
    if entry and entry.prompt_id:
        try:
            prompt = PromptOut.model_validate(prompts_store.get(db, user.id, entry.prompt_id))
        except NotFound:
            prompt = None
    if prompt is None:
        p = prompts_store.for_date(db, user.id, day)
        prompt = PromptOut.model_validate(p) if p else None
    return DayOut(
        date=day,
        today=today(),
        entry=EntryOut.model_validate(entry) if entry else None,
        prompt=prompt,
    )


@router.get("/entries", response_model=list[EntryOut])
def list_entries(
    q: str | None = Query(default=None, max_length=200),
    tag: list[int] = Query(default_factory=list),
    before: date | None = None,
    limit: int = Query(default=30, ge=1, le=200),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return entries_store.search(db, user.id, q=q, tag_ids=tag, before=before, limit=limit)


@router.get("/entries/{day}", response_model=EntryOut)
def get_entry(day: date, user: User = Depends(current_user), db: Session = Depends(get_db)):
    entry = entries_store.get(db, user.id, day)
    if entry is None:
        raise HTTPException(404, "No entry for that date")
    return entry


@router.put("/entries/{day}", response_model=EntryOut)
def put_entry(
    day: date,
    body: EntryIn,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    entry, created = entries_store.upsert(
        db, user.id, day, entries_store.EntryData(**body.model_dump()), today=today()
    )
    response.status_code = 201 if created else 200
    return entry


@router.delete("/entries/{day}", status_code=204)
def delete_entry(day: date, user: User = Depends(current_user), db: Session = Depends(get_db)):
    entries_store.delete(db, user.id, day)
    return Response(status_code=204)
