from shared.jobs.contracts import TaskSpec
from shared.module import ModuleManifest

from .collection import expire_receipt
from .model import (
    ApprovalTable,
    DraftTable,
    IntervalTable,
    MessageTable,
    PhotoTable,
    PrefillSettingsTable,
    ReceiptTable,
    StreamTable,
)
from .prefill import run_prefill
from .prefill_jobs import recover_prefill
from .prefill_router import router as prefill_router
from .raw_photos import render_photo
from .router import router
from .storage import cleanup_files

MODULE = ModuleManifest(
    name="product_drafts", routers=(router, prefill_router),
    tables=(StreamTable, DraftTable, MessageTable, PhotoTable, ReceiptTable, ApprovalTable,
            IntervalTable, PrefillSettingsTable),
    tasks=(TaskSpec("product_drafts.cleanup", cleanup_files, queue="maintenance"),
           TaskSpec("product_drafts.render_photo", render_photo, queue="images"),
           TaskSpec("product_drafts.expire_receipt", expire_receipt, queue="maintenance"),
           TaskSpec("product_drafts.prefill", run_prefill, max_attempts=3, timeout_seconds=45,
                    queue="ai", retry_delay_seconds=60),
           TaskSpec("product_drafts.recover_prefill", recover_prefill, queue="maintenance",
                    interval_seconds=60)),
)
