from shared.jobs.contracts import TaskSpec
from shared.module import ModuleManifest

from .buffer import process_buffer
from .collection import expire_receipt
from .model import (
    ApprovalTable,
    BatchIssueTable,
    BatchTable,
    BufferedEventTable,
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
            BatchTable, WindowTable, BatchIssueTable, PrefillSettingsTable, BufferedEventTable),
    tasks=(TaskSpec("product_drafts.cleanup", cleanup_files, queue="maintenance"),
           TaskSpec("product_drafts.buffer", process_buffer),
           TaskSpec("product_drafts.expire_receipt", expire_receipt, queue="maintenance"),
           TaskSpec("product_drafts.prefill", run_prefill, max_attempts=1, timeout_seconds=45,
                    queue="ai")),
)
