from urllib.parse import quote

import httpx

from .schema import DownloadedImage, GroupName

MAX_IMAGE_BYTES = 15 * 1024 * 1024


class LineTransportError(Exception):
    pass


class LineClient(httpx.AsyncClient):
    def __init__(self) -> None:
        super().__init__(timeout=httpx.Timeout(20, connect=5), follow_redirects=False,
                         trust_env=False)


def _check_status(response: httpx.Response) -> None:
    if response.status_code != 200:
        # LINE 的錯誤內容及請求標頭不可進 exception/log.
        raise LineTransportError()


async def download_image(message_id: str, token: str) -> DownloadedImage:
    url = f"https://api-data.line.me/v2/bot/message/{quote(message_id, safe='')}/content"
    try:
        async with LineClient() as client, client.stream(
            "GET", url, headers={"Authorization": f"Bearer {token}"},
        ) as response:
            _check_status(response)
            content = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=65536):
                if len(content) + len(chunk) > MAX_IMAGE_BYTES:
                    raise LineTransportError()
                content.extend(chunk)
            return DownloadedImage(content=bytes(content))
    except httpx.HTTPError:
        raise LineTransportError() from None


async def group_name(group_id: str, token: str) -> GroupName:
    url = f"https://api.line.me/v2/bot/group/{quote(group_id, safe='')}/summary"
    try:
        async with LineClient() as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            _check_status(response)
            name = response.json().get("groupName")
            if not isinstance(name, str) or not name.strip():
                raise LineTransportError()
            return GroupName(name=name)
    except (httpx.HTTPError, ValueError, AttributeError):
        raise LineTransportError() from None
