from pathlib import Path

from sqlalchemy import event
from sqlalchemy.orm import Session

from shared.db.session import active_session


def track_files(*, created: list[Path], deleted: list[Path]) -> None:
    session = active_session().sync_session
    pending = session.info.setdefault("product_files", {"created": [], "deleted": []})
    pending["created"].extend(created)
    pending["deleted"].extend(deleted)
    if session.info.get("product_file_hooks"):
        return
    session.info["product_file_hooks"] = True
    event.listen(session, "after_commit", _committed)
    event.listen(session, "after_rollback", _rolled_back)


def _cleanup(session: Session, key: str) -> None:
    # SAVEPOINT 成功仍可能被外層回滾, 只在根交易結束才清檔。
    if session.in_nested_transaction():
        return
    pending = session.info.pop("product_files", {"created": [], "deleted": []})
    for path in pending[key]:
        path.unlink(missing_ok=True)


def _committed(session: Session) -> None:
    _cleanup(session, "deleted")


def _rolled_back(session: Session) -> None:
    _cleanup(session, "created")
