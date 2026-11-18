from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Tag, entry_tags
from app.storage.errors import Conflict, Invalid, NotFound


@dataclass
class TagWithUsage:
    id: int
    name: str
    archived: bool
    usage: int


def _clean(name: str) -> str:
    name = " ".join(name.split()).lower()
    if not name or len(name) > 40:
        raise Invalid("Tag name must be 1-40 characters")
    return name


def list_with_usage(db: Session, user_id: int, include_archived: bool = False) -> list[TagWithUsage]:
    """Tags ordered most-used first, then alphabetically."""
    usage = func.count(entry_tags.c.entry_id)
    stmt = (
        select(Tag.id, Tag.name, Tag.archived, usage.label("usage"))
        .outerjoin(entry_tags, entry_tags.c.tag_id == Tag.id)
        .where(Tag.user_id == user_id)
        .group_by(Tag.id)
        .order_by(usage.desc(), Tag.name)
    )
    if not include_archived:
        stmt = stmt.where(Tag.archived.is_(False))
    return [TagWithUsage(*row) for row in db.execute(stmt).all()]


def get(db: Session, user_id: int, tag_id: int) -> Tag:
    tag = db.scalar(select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))
    if tag is None:
        raise NotFound("Tag not found")
    return tag


def get_many(db: Session, user_id: int, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    ids = set(tag_ids)
    found = list(db.scalars(select(Tag).where(Tag.user_id == user_id, Tag.id.in_(ids))))
    if len(found) != len(ids):
        raise Invalid("Unknown tag id")
    return found


def create(db: Session, user_id: int, name: str) -> Tag:
    name = _clean(name)
    existing = db.scalar(select(Tag).where(Tag.user_id == user_id, Tag.name == name))
    if existing:
        if existing.archived:  # re-adding an archived tag revives it
            existing.archived = False
            db.commit()
            return existing
        raise Conflict("Tag already exists")
    tag = Tag(user_id=user_id, name=name)
    db.add(tag)
    db.commit()
    return tag


def rename(db: Session, user_id: int, tag_id: int, name: str) -> Tag:
    tag = get(db, user_id, tag_id)
    name = _clean(name)
    clash = db.scalar(
        select(Tag).where(Tag.user_id == user_id, Tag.name == name, Tag.id != tag_id)
    )
    if clash:
        raise Conflict("Tag already exists")
    tag.name = name
    db.commit()
    return tag


def set_archived(db: Session, user_id: int, tag_id: int, archived: bool) -> Tag:
    tag = get(db, user_id, tag_id)
    tag.archived = archived
    db.commit()
    return tag


def delete(db: Session, user_id: int, tag_id: int) -> str:
    """Hard-delete an unused tag; archive a used one so history keeps it.

    Returns "deleted" or "archived".
    """
    tag = get(db, user_id, tag_id)
    used = db.scalar(select(func.count()).where(entry_tags.c.tag_id == tag_id))
    if used:
        tag.archived = True
        db.commit()
        return "archived"
    db.delete(tag)
    db.commit()
    return "deleted"
