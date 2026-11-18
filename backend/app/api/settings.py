"""Tag and prompt-pool management."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import User
from app.schemas import PromptCreate, PromptOut, PromptUpdate, TagCreate, TagOut, TagUpdate
from app.storage import prompts as prompts_store
from app.storage import tags as tags_store

router = APIRouter()


def _tag_out(db: Session, user_id: int, tag_id: int) -> TagOut:
    for t in tags_store.list_with_usage(db, user_id, include_archived=True):
        if t.id == tag_id:
            return TagOut.model_validate(t)
    raise AssertionError("tag vanished")


@router.get("/tags", response_model=list[TagOut], tags=["tags"])
def list_tags(
    include_archived: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    return tags_store.list_with_usage(db, user.id, include_archived=include_archived)


@router.post("/tags", response_model=TagOut, status_code=201, tags=["tags"])
def create_tag(body: TagCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    tag = tags_store.create(db, user.id, body.name)
    return _tag_out(db, user.id, tag.id)


@router.patch("/tags/{tag_id}", response_model=TagOut, tags=["tags"])
def update_tag(
    tag_id: int, body: TagUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    if body.name is not None:
        tags_store.rename(db, user.id, tag_id, body.name)
    if body.archived is not None:
        tags_store.set_archived(db, user.id, tag_id, body.archived)
    tags_store.get(db, user.id, tag_id)
    return _tag_out(db, user.id, tag_id)


@router.delete("/tags/{tag_id}", tags=["tags"])
def delete_tag(tag_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {"result": tags_store.delete(db, user.id, tag_id)}


@router.get("/prompts", response_model=list[PromptOut], tags=["prompts"])
def list_prompts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return prompts_store.list_all(db, user.id)


@router.post("/prompts", response_model=PromptOut, status_code=201, tags=["prompts"])
def create_prompt(body: PromptCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return prompts_store.create(db, user.id, body.text, body.quick_answers)


@router.patch("/prompts/{prompt_id}", response_model=PromptOut, tags=["prompts"])
def update_prompt(
    prompt_id: int,
    body: PromptUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return prompts_store.update(db, user.id, prompt_id, **body.model_dump(exclude_unset=True))


@router.delete("/prompts/{prompt_id}", status_code=204, tags=["prompts"])
def delete_prompt(prompt_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    prompts_store.delete(db, user.id, prompt_id)
    return Response(status_code=204)
