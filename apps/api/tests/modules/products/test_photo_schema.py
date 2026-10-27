from modules.products.model import ProductPhotoTable


def test_photo_schema_preserves_legacy_columns():
    assert ProductPhotoTable.__tablename__ == "product_photos"
    assert set(ProductPhotoTable.__table__.columns.keys()) == {
        "id", "created_at", "updated_at", "product_id", "storage_key",
        "original_storage_key", "original_filename", "original_media_type",
        "sort_order", "uploaded_by",
    }


