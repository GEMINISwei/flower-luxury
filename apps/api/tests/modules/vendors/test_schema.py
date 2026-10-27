from modules.vendors.model import VendorTable


def test_vendor_schema_preserves_legacy_columns():
    assert VendorTable.__tablename__ == "vendors"
    assert set(VendorTable.__table__.columns.keys()) == {
        "id", "created_at", "updated_at", "name", "country", "note", "is_active", "country_locked",
    }
