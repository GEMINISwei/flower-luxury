from modules.vendors.model import VendorTable


def test_vendor_schema_drops_country_but_preserves_quote_history():
    assert VendorTable.__tablename__ == "vendors"
    assert set(VendorTable.__table__.columns.keys()) == {
        "id", "created_at", "updated_at", "name", "note", "is_active", "has_quotes",
    }
