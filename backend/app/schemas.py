from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

Scale = Field(ge=1, le=5)


class LoginIn(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=1024)


class MeOut(BaseModel):
    username: str


class TagRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    archived: bool
    usage: int


class TagCreate(BaseModel):
    name: str = Field(max_length=100)


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    archived: bool | None = None


class PromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    text: str
    quick_answers: list[str]
    active: bool


class PromptCreate(BaseModel):
    text: str = Field(max_length=400)
    quick_answers: list[str] = Field(default_factory=list, max_length=20)


class PromptUpdate(BaseModel):
    text: str | None = Field(default=None, max_length=400)
    quick_answers: list[str] | None = Field(default=None, max_length=20)
    active: bool | None = None


class EntryIn(BaseModel):
    mood: int = Scale
    energy: int | None = Field(default=None, ge=1, le=5)
    sleep: int | None = Field(default=None, ge=1, le=5)
    tag_ids: list[int] = Field(default_factory=list, max_length=50)
    prompt_id: int | None = None
    prompt_answer: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=10000)


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    date: date
    mood: int
    energy: int | None
    sleep: int | None
    tags: list[TagRef]
    prompt_id: int | None
    prompt_text: str | None
    prompt_answer: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime


class DayOut(BaseModel):
    """Everything the check-in screen needs for one date."""

    date: date
    today: date
    entry: EntryOut | None
    prompt: PromptOut | None


class TodayOut(BaseModel):
    today: date
    tz: str
