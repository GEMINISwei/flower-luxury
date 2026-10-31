from shared.jobs.contracts import TaskSpec
from shared.module import ModuleManifest

from .collection import expire_receipt
from .model import (
    ApprovalTable,
    BatchIssueTable,
    BatchTable,
    DraftTable,
    MessageTable,
    PhotoTable,
    PrefillSettingsTable,
    ReceiptTable,
    StreamTable,
    WindowTable,
)
from .prefill import run_prefill
from .prefill_router import router as prefill_router
from .router import router
from .storage import cleanup_files

MODULE = ModuleManifest(
    name="product_drafts", routers=(router, prefill_router),
    tables=(StreamTable, DraftTable, MessageTable, PhotoTable, ReceiptTable, ApprovalTable,
            BatchTable, WindowTable, BatchIssueTable, PrefillSettingsTable),
    tasks=(TaskSpec("product_drafts.cleanup", cleanup_files),
           TaskSpec("product_drafts.expire_receipt", expire_receipt),
           TaskSpec("product_drafts.prefill", run_prefill, timeout_seconds=45)),
)
