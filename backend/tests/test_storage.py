from datetime import date, timedelta

import pytest

from app.storage import Conflict, Invalid, NotFound
from app.storage import entries, prompts, tags, users
from app.storage.entries import EntryData

TODAY = date(2026, 11, 17)


def tag_id(db, uid, name):
    return next(t.id for t in tags.list_with_usage(db, uid) if t.name == name)


# --- users / seeding ---------------------------------------------------------


def test_get_or_create_seeds_defaults_once(db):
    u1 = users.get_or_create(db, "me")
    u2 = users.get_or_create(db, "me")
    assert u1.id == u2.id
    names = {t.name for t in tags.list_with_usage(db, u1.id)}
    assert names == set(users.DEFAULT_TAGS)
    assert len(prompts.list_all(db, u1.id)) == len(users.DEFAULT_PROMPTS)


# --- entries -----------------------------------------------------------------


def test_upsert_taps_only_entry_is_complete(db, user_id):
    e, created = entries.upsert(db, user_id, TODAY, EntryData(mood=4), today=TODAY)
    assert created and e.mood == 4 and e.energy is None and e.note is None


def test_upsert_replaces_existing_entry(db, user_id):
    work = tag_id(db, user_id, "work")
    entries.upsert(db, user_id, TODAY, EntryData(mood=2, tag_ids=[work], note="meh"), today=TODAY)
    e, created = entries.upsert(db, user_id, TODAY, EntryData(mood=5, energy=3), today=TODAY)
    assert not created
    assert (e.mood, e.energy, e.note, e.tags) == (5, 3, None, [])
    assert len(entries.search(db, user_id)) == 1


def test_backfill_past_ok_future_rejected(db, user_id):
    entries.upsert(db, user_id, TODAY - timedelta(days=30), EntryData(mood=3), today=TODAY)
    with pytest.raises(Invalid):
        entries.upsert(db, user_id, TODAY + timedelta(days=1), EntryData(mood=3), today=TODAY)


@pytest.mark.parametrize("field,value", [("mood", 0), ("mood", 6), ("energy", 9), ("sleep", -1)])
def test_scale_validation(db, user_id, field, value):
    data = EntryData(mood=3)
    setattr(data, field, value)
    with pytest.raises(Invalid):
        entries.upsert(db, user_id, TODAY, data, today=TODAY)


def test_blank_text_stored_as_null(db, user_id):
    e, _ = entries.upsert(db, user_id, TODAY, EntryData(mood=3, note="   "), today=TODAY)
    assert e.note is None


def test_cannot_use_other_users_tag(db, user_id, other_user_id):
    foreign = tag_id(db, other_user_id, "work")
    with pytest.raises(Invalid):
        entries.upsert(db, user_id, TODAY, EntryData(mood=3, tag_ids=[foreign]), today=TODAY)


def test_entries_are_scoped_per_user(db, user_id, other_user_id):
    entries.upsert(db, user_id, TODAY, EntryData(mood=1), today=TODAY)
    entries.upsert(db, other_user_id, TODAY, EntryData(mood=5), today=TODAY)
    assert entries.get(db, user_id, TODAY).mood == 1
    assert entries.get(db, other_user_id, TODAY).mood == 5
    assert [e.mood for e in entries.search(db, user_id)] == [1]
    entries.delete(db, other_user_id, TODAY)
    assert entries.get(db, user_id, TODAY) is not None


def test_delete_missing_raises(db, user_id):
    with pytest.raises(NotFound):
        entries.delete(db, user_id, TODAY)


def test_delete_entry_keeps_tags(db, user_id):
    work = tag_id(db, user_id, "work")
    entries.upsert(db, user_id, TODAY, EntryData(mood=3, tag_ids=[work]), today=TODAY)
    entries.delete(db, user_id, TODAY)
    assert tags.get(db, user_id, work).name == "work"


# --- prompts on entries ------------------------------------------------------


def test_prompt_answer_snapshots_text(db, user_id):
    p = prompts.list_all(db, user_id)[0]
    original = p.text
    e, _ = entries.upsert(
        db, user_id, TODAY, EntryData(mood=3, prompt_id=p.id, prompt_answer="tea"), today=TODAY
    )
    assert e.prompt_text == original
    prompts.update(db, user_id, p.id, text="Something else?")
    # editing the entry later keeps the original wording
    e, _ = entries.upsert(
        db, user_id, TODAY, EntryData(mood=4, prompt_id=p.id, prompt_answer="coffee"), today=TODAY
    )
    assert (e.prompt_text, e.prompt_answer) == (original, "coffee")


def test_skipped_prompt_stores_nothing(db, user_id):
    p = prompts.list_all(db, user_id)[0]
    e, _ = entries.upsert(
        db, user_id, TODAY, EntryData(mood=3, prompt_id=p.id, prompt_answer=""), today=TODAY
    )
    assert (e.prompt_id, e.prompt_text, e.prompt_answer) == (None, None, None)


def test_deleted_prompt_keeps_history_and_allows_edit(db, user_id):
    p = prompts.list_all(db, user_id)[0]
    entries.upsert(db, user_id, TODAY, EntryData(mood=3, prompt_id=p.id, prompt_answer="a"), today=TODAY)
    prompts.delete(db, user_id, p.id)
    db.expire_all()
    e = entries.get(db, user_id, TODAY)
    assert e.prompt_id is None and e.prompt_text == p.text
    e, _ = entries.upsert(db, user_id, TODAY, EntryData(mood=3, prompt_answer="b"), today=TODAY)
    assert (e.prompt_text, e.prompt_answer) == (p.text, "b")


def test_answer_without_prompt_rejected(db, user_id):
    with pytest.raises(Invalid):
        entries.upsert(db, user_id, TODAY, EntryData(mood=3, prompt_answer="x"), today=TODAY)


def test_other_users_prompt_rejected(db, user_id, other_user_id):
    foreign = prompts.list_all(db, other_user_id)[0]
    with pytest.raises(Invalid):
        entries.upsert(
            db, user_id, TODAY, EntryData(mood=3, prompt_id=foreign.id, prompt_answer="x"), today=TODAY
        )
    assert entries.get(db, user_id, TODAY) is None


# --- search / history --------------------------------------------------------


def _seed_history(db, uid):
    work, social = tag_id(db, uid, "work"), tag_id(db, uid, "social")
    rows = [
        (TODAY, EntryData(mood=4, tag_ids=[work, social], note="Lunch with Ana")),
        (TODAY - timedelta(days=1), EntryData(mood=2, tag_ids=[work], note="deadline 100% done")),
        (TODAY - timedelta(days=2), EntryData(mood=3, tag_ids=[social])),
        (TODAY - timedelta(days=5), EntryData(mood=5)),
    ]
    for d, data in rows:
        entries.upsert(db, uid, d, data, today=TODAY)
    return work, social


def test_search_newest_first_and_cursor(db, user_id):
    _seed_history(db, user_id)
    all_ = entries.search(db, user_id)
    assert [e.date for e in all_] == sorted((e.date for e in all_), reverse=True)
    page = entries.search(db, user_id, limit=2)
    rest = entries.search(db, user_id, before=page[-1].date)
    assert [e.date for e in page + rest] == [e.date for e in all_]


def test_search_text_case_insensitive_and_literal(db, user_id):
    _seed_history(db, user_id)
    assert [e.mood for e in entries.search(db, user_id, q="ana")] == [4]
    assert [e.mood for e in entries.search(db, user_id, q="100%")] == [2]
    assert entries.search(db, user_id, q="%") == entries.search(db, user_id, q="100%")


def test_search_by_tags_requires_all(db, user_id):
    work, social = _seed_history(db, user_id)
    assert len(entries.search(db, user_id, tag_ids=[work])) == 2
    assert [e.mood for e in entries.search(db, user_id, tag_ids=[work, social])] == [4]


# --- tags --------------------------------------------------------------------


def test_tags_sorted_by_usage(db, user_id):
    _seed_history(db, user_id)
    names = [t.name for t in tags.list_with_usage(db, user_id)]
    assert names[:2] == ["social", "work"]  # both used twice, then alphabetical
    assert names[2:] == sorted(names[2:])


def test_tag_create_normalises_and_conflicts(db, user_id):
    t = tags.create(db, user_id, "  Board   Games ")
    assert t.name == "board games"
    with pytest.raises(Conflict):
        tags.create(db, user_id, "board games")
    with pytest.raises(Invalid):
        tags.create(db, user_id, "   ")


def test_tag_rename_follows_history(db, user_id):
    work = tag_id(db, user_id, "work")
    entries.upsert(db, user_id, TODAY, EntryData(mood=3, tag_ids=[work]), today=TODAY)
    tags.rename(db, user_id, work, "job")
    db.expire_all()
    assert [t.name for t in entries.get(db, user_id, TODAY).tags] == ["job"]
    with pytest.raises(Conflict):
        tags.rename(db, user_id, work, "social")


def test_delete_used_tag_archives_unused_deletes(db, user_id):
    work, rest = tag_id(db, user_id, "work"), tag_id(db, user_id, "rest")
    entries.upsert(db, user_id, TODAY, EntryData(mood=3, tag_ids=[work]), today=TODAY)
    assert tags.delete(db, user_id, work) == "archived"
    assert tags.delete(db, user_id, rest) == "deleted"
    visible = {t.name for t in tags.list_with_usage(db, user_id)}
    assert "work" not in visible and "rest" not in visible
    all_ = {t.name: t for t in tags.list_with_usage(db, user_id, include_archived=True)}
    assert all_["work"].archived and "rest" not in all_
    # re-adding an archived tag revives it
    assert tags.create(db, user_id, "work").id == work


def test_tag_ops_scoped(db, user_id, other_user_id):
    foreign = tag_id(db, other_user_id, "work")
    with pytest.raises(NotFound):
        tags.rename(db, user_id, foreign, "x")
    with pytest.raises(NotFound):
        tags.delete(db, user_id, foreign)


# --- prompt pool -------------------------------------------------------------


def test_prompt_rotation_deterministic_and_rotates(db, user_id):
    picks = [prompts.for_date(db, user_id, TODAY + timedelta(days=i)).id for i in range(12)]
    n = len(users.DEFAULT_PROMPTS)
    assert picks[:n] != [picks[0]] * n
    assert picks[:n] == picks[n : 2 * n]  # cycles through the whole pool
    assert len(set(picks[:n])) == n
    assert prompts.for_date(db, user_id, TODAY).id == picks[0]


def test_prompt_rotation_skips_inactive_and_empty(db, user_id):
    all_ = prompts.list_all(db, user_id)
    for p in all_[1:]:
        prompts.update(db, user_id, p.id, active=False)
    assert prompts.for_date(db, user_id, TODAY).id == all_[0].id
    prompts.update(db, user_id, all_[0].id, active=False)
    assert prompts.for_date(db, user_id, TODAY) is None


def test_prompt_quick_answers_cleaned(db, user_id):
    p = prompts.create(db, user_id, " Best  meal? ", ["pizza", " pizza ", "", "soup"])
    assert p.text == "Best meal?" and p.quick_answers == ["pizza", "soup"]
    with pytest.raises(Invalid):
        prompts.create(db, user_id, "x" * 201)
