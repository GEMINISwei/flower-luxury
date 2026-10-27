from modules.products.model import ProductHistoryTable, ProductTable


def test_product_schema_preserves_legacy_columns():
    common = {"id", "created_at", "updated_at"}
    assert ProductTable.__tablename__ == "products"
    assert set(ProductTable.__table__.columns.keys()) == common | {
        "sku", "name", "brand_id", "category", "model_name", "serial_number", "color",
        "year", "cost_price", "internal_note", "status", "main_photo_id", "created_by",
        "updated_by", "deleted_at",
    }
    assert ProductHistoryTable.__tablename__ == "product_status_history"
    assert set(ProductHistoryTable.__table__.columns.keys()) == common | {
        "product_id", "from_status", "to_status", "action", "reason", "changed_by",
        "operator_name", "changed_at",
    }
