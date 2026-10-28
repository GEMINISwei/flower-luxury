from shared.jobs.contracts import TaskSpec
from shared.module import ModuleManifest

from .collection import expire_receipt
from .model import ApprovalTable, DraftTable, MessageTable, PhotoTable, ReceiptTable, StreamTable
from .router import router
from .storage import cleanup_files

MODULE = ModuleManifest(
    name="product_drafts", routers=(router,),
    tables=(StreamTable, DraftTable, MessageTable, PhotoTable, ReceiptTable, ApprovalTable),
    tasks=(TaskSpec("product_drafts.cleanup", cleanup_files),
           TaskSpec("product_drafts.expire_receipt", expire_receipt)),
)
