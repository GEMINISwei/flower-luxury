from shared.jobs.contracts import TaskSpec
from shared.module import ModuleManifest

from .jobs import download_photo, expire_receipt, expire_reply, refresh_group_name, send_reply
from .model import EventReceiptTable, GroupTable, MessageLinkTable, ReplyTable
from .router import router

MODULE = ModuleManifest(
    name="line_collection", routers=(router,),
    tables=(GroupTable, EventReceiptTable, MessageLinkTable, ReplyTable),
    tasks=(TaskSpec("line_collection.download", download_photo),
           TaskSpec("line_collection.group_name", refresh_group_name),
           TaskSpec("line_collection.expire", expire_receipt),
           TaskSpec("line_collection.reply", send_reply, max_attempts=1, timeout_seconds=10),
           TaskSpec("line_collection.expire_reply", expire_reply)),
)
