from shared.jobs.contracts import TaskSpec
from shared.module import ModuleManifest

from .jobs import download_photo, expire_receipt, refresh_group_name
from .model import EventReceiptTable, GroupTable, MessageLinkTable
from .router import router

MODULE = ModuleManifest(
    name="line_collection", routers=(router,),
    tables=(GroupTable, EventReceiptTable, MessageLinkTable),
    tasks=(TaskSpec("line_collection.download", download_photo),
           TaskSpec("line_collection.group_name", refresh_group_name),
           TaskSpec("line_collection.expire", expire_receipt)),
)
