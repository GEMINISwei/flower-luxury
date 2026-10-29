import json
from datetime import UTC, datetime

from modules.line_collection.schema import LineEvent

BASE = datetime(2026, 10, 28, 1)


def event(kind="image", *, group="group-a", event_id="event-a", message_id="message-a",
          text="原文\n  保留空白  ", second=0, event_type="message") -> LineEvent:
    value = {"type": event_type, "webhookEventId": event_id,
             "timestamp": int(BASE.replace(tzinfo=UTC).timestamp() * 1000) + second * 1000,
             "source": {"type": "group", "groupId": group, "userId": "sender-a"}}
    if event_type == "message":
        value["message"] = {"id": message_id, "type": kind, "text": text}
    if event_type == "unsend":
        value["unsend"] = {"messageId": message_id}
    return LineEvent.model_validate(value)


def body(events) -> bytes:
    return json.dumps({"events": [item.model_dump(by_alias=True, exclude_none=True)
                                  for item in events]}, ensure_ascii=False).encode()
