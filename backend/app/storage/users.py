from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Prompt, Tag, User

DEFAULT_TAGS = ["work", "social", "exercise", "outside", "family", "rest", "rough day"]

DEFAULT_PROMPTS: list[tuple[str, list[str]]] = [
    ("One good thing today?", ["Good food", "A nice chat", "Got stuff done", "Fresh air"]),
    ("What drained you?", ["Work", "People", "Bad sleep", "Nothing much"]),
    ("What are you looking forward to?", ["Weekend", "Seeing friends", "Rest", "Not sure"]),
    ("What made you smile?", ["Someone I love", "Something funny", "A small win"]),
    ("What would make tomorrow better?", ["More sleep", "Less screen time", "Moving more"]),
    ("Who did you connect with?", ["Family", "Friends", "Coworkers", "Nobody, and that's ok"]),
]


def get_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def get(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_or_create(db: Session, username: str) -> User:
    """Return the user, creating it with default tags and prompts on first run."""
    user = get_by_username(db, username)
    if user:
        return user
    user = User(username=username)
    db.add(user)
    db.flush()
    seed_defaults(db, user.id)
    db.commit()
    return user


def seed_defaults(db: Session, user_id: int) -> None:
    for name in DEFAULT_TAGS:
        db.add(Tag(user_id=user_id, name=name))
    for text, answers in DEFAULT_PROMPTS:
        db.add(Prompt(user_id=user_id, text=text, quick_answers=answers))
    db.flush()
