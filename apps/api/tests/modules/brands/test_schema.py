from modules.brands.model import BrandTable


def test_brand_schema_preserves_legacy_columns():
    assert BrandTable.__tablename__ == "brands"
    assert set(BrandTable.__table__.columns.keys()) == {
        "id", "created_at", "updated_at", "name", "is_active",
    }
