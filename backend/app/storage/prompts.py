from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Prompt
from app.storage.errors import Invalid, NotFound


def _clean_text(text: str) -> str:
    text = " ".join(text.split())
    if not text or len(text) > 200:
        raise Invalid("Prompt must be 1-200 characters")
    return text


def _clean_answers(answers: list[str]) -> list[str]:
    out: list[str] = []
    for a in answers:
        a = " ".join(a.split())
        if a and a not in out:
            if len(a) > 60:
                raise Invalid("Quick answers must be at most 60 characters")
            out.append(a)
    if len(out) > 8:
        raise Invalid("At most 8 quick answers")
    return out


def list_all(db: Session, user_id: int) -> list[Prompt]:
    return list(db.scalars(select(Prompt).where(Prompt.user_id == user_id).order_by(Prompt.id)))


def get(db: Session, user_id: int, prompt_id: int) -> Prompt:
    p = db.scalar(select(Prompt).where(Prompt.id == prompt_id, Prompt.user_id == user_id))
    if p is None:
        raise NotFound("Prompt not found")
    return p


def create(db: Session, user_id: int, text: str, quick_answers: list[str] | None = None) -> Prompt:
    p = Prompt(
        user_id=user_id,
        text=_clean_text(text),
        quick_answers=_clean_answers(quick_answers or []),
        active=True,
    )
    db.add(p)
    db.commit()
    return p


def update(
    db: Session,
    user_id: int,
    prompt_id: int,
    *,
    text: str | None = None,
    quick_answers: list[str] | None = None,
    active: bool | None = None,
) -> Prompt:
    p = get(db, user_id, prompt_id)
    if text is not None:
        p.text = _clean_text(text)
    if quick_answers is not None:
        p.quick_answers = _clean_answers(quick_answers)
    if active is not None:
        p.active = active
    db.commit()
    return p


def delete(db: Session, user_id: int, prompt_id: int) -> None:
    """Entries keep their prompt_text snapshot; prompt_id becomes NULL."""
    p = get(db, user_id, prompt_id)
    db.delete(p)
    db.commit()


def pick_for_date(active_prompts: list[Prompt], day: date) -> Prompt | None:
    """Deterministic daily rotation: same prompt all day, next one tomorrow."""
    if not active_prompts:
        return None
    ordered = sorted(active_prompts, key=lambda p: p.id)
    return ordered[day.toordinal() % len(ordered)]


def for_date(db: Session, user_id: int, day: date) -> Prompt | None:
    active = list(
        db.scalars(select(Prompt).where(Prompt.user_id == user_id, Prompt.active.is_(True)))
    )
    return pick_for_date(active, day)
