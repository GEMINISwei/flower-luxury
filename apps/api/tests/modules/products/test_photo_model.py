import pytest

from modules.products import photos, service
from modules.products.model import ProductTable
from modules.products.schema import ProductCreate
from shared.db.session import active_session
from shared.http.errors import LangException
from tests.modules.products.test_model import ACTOR, product
from tests.modules.products.test_photo_originals import source_file, uploads  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_more_than_ten_photos_and_main_replacement(db):
    item = await product()
    uploaded = await photos.upload_photos(item.id, [source_file()[0] for _ in range(12)], ACTOR)
    assert uploaded.count == 12 and sum(photo.is_main for photo in uploaded.list_data) == 1
    assert uploaded.list_data[0].is_main
    selected = uploaded.list_data[3].id
    await photos.set_main_photo(item.id, selected, ACTOR)
    assert (await service.get_product(item.id)).main_photo_id == selected
    await photos.delete_photo(item.id, selected, ACTOR)
    assert (await service.get_product(item.id)).main_photo_id == uploaded.list_data[0].id
    assert (await photos.list_photos(item.id)).count == 11


async def test_sold_photos_are_readable_but_mutations_are_locked(db):
    item = await product()
    photo = (await photos.upload_photos(item.id, [source_file()[0]], ACTOR)).list_data[0]
    row = await ProductTable.find_by_id(item.id)
    assert row is not None
    row.status = "sold"
    await active_session().flush()
    assert (await photos.list_photos(item.id)).count == 1
    assert (await photos.photo_path(photo.id)).path.is_file()
    for operation in [
        lambda: photos.upload_photos(item.id, [source_file()[0]], ACTOR),
        lambda: photos.set_main_photo(item.id, photo.id, ACTOR),
        lambda: photos.delete_photo(item.id, photo.id, ACTOR),
    ]:
        with pytest.raises(LangException) as error:
            await operation()
        assert error.value.status_code == 409


async def test_photo_cannot_be_changed_through_another_product(db):
    first = await product()
    second = await service.create_product(ProductCreate(
        name="Second", brand_id=first.brand_id, category="包包", cost_price=0,
    ), ACTOR)
    photo = (await photos.upload_photos(first.id, [source_file()[0]], ACTOR)).list_data[0]
    for operation in [photos.set_main_photo, photos.delete_photo]:
        with pytest.raises(LangException) as error:
            await operation(second.id, photo.id, ACTOR)
        assert error.value.status_code == 404
    assert (await photos.list_photos(first.id)).count == 1


async def test_deleted_product_hides_display_and_photo_list(db):
    item = await product()
    photo = (await photos.upload_photos(item.id, [source_file()[0]], ACTOR)).list_data[0]
    await service.delete_product(item.id, ACTOR)
    for operation, id in [(photos.photo_path, photo.id), (photos.list_photos, item.id)]:
        with pytest.raises(LangException) as error:
            await operation(id)
        assert error.value.status_code == 404
