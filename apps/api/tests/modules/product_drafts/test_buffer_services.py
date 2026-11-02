from datetime import timedelta

import pytest

from modules.product_drafts import collection_rules
from tests.modules.product_drafts.helpers import BASE


def event(id, kind, second, sequence=0):
    return collection_rules.GroupEvent(id=id, kind=kind,
        occurred_at=BASE + timedelta(seconds=second), sequence=sequence)


def test_grouping_sorts_by_original_time_and_preserves_every_id():
    events = [event("b", "image", 5), event("t", "text", 3), event("a2", "image", 2),
              event("a", "image", 1)]
    plan = collection_rules.propose_groups(events)
    assert plan.groups == [["a", "a2", "t"], ["b"]] and plan.unassigned == []


def test_leading_text_is_retained_for_manual_assignment():
    plan = collection_rules.propose_groups([event("t", "text", 0), event("a", "image", 1)])
    assert plan.groups == [["a"]] and plan.unassigned == ["t"]


def test_ambiguous_timestamp_creates_barrier_instead_of_guessing():
    plan = collection_rules.propose_groups([event("a", "image", 1), event("b", "image", 2),
        event("t", "text", 2), event("after", "text", 3), event("c", "image", 4)])
    assert plan.groups == [["a"], ["c"]]
    assert set(plan.unassigned) == {"b", "t", "after"}


def test_same_kind_timestamp_uses_sequence_without_creating_false_conflict():
    plan = collection_rules.propose_groups([event("b", "image", 1, 2), event("a", "image", 1, 1),
                                           event("t", "text", 2, 3)])
    assert plan.groups == [["a", "b", "t"]] and plan.unassigned == []


@pytest.mark.parametrize("events", [[], [event("t", "text", 0)]])
def test_no_images_never_creates_an_empty_product(events):
    plan = collection_rules.propose_groups(events)
    assert plan.groups == []
    assert len(plan.unassigned) == len(events)
