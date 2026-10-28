from shared.http.errors import LangException

from .errors import DraftError
from .schema import CollectionDecision


def decide_collection(
    kind: str, *, has_current: bool, has_text: bool, is_late: bool,
) -> CollectionDecision:
    if is_late or (kind == "text" and not has_current):
        return CollectionDecision(assign=False, start_new=False)
    return CollectionDecision(
        assign=True, start_new=kind == "image" and (not has_current or has_text),
    )


def check_version(actual: int, expected: int | None) -> None:
    if actual != expected:
        raise LangException(409, DraftError.STALE)
