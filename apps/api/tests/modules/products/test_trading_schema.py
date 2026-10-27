from modules.products.model import ProductQuoteTable, ProductSaleTable


def test_trading_schema_preserves_legacy_columns():
    common = {"id", "created_at", "updated_at"}
    assert ProductQuoteTable.__tablename__ == "product_quotes"
    assert set(ProductQuoteTable.__table__.columns.keys()) == common | {
        "product_id", "vendor_id", "vendor_country", "currency", "original_amount",
        "exchange_rate", "amount_twd", "note", "revision", "created_by", "updated_by",
    }
    assert ProductSaleTable.__tablename__ == "product_sales"
    assert set(ProductSaleTable.__table__.columns.keys()) == common | {
        "product_id", "quote_id", "vendor_id", "vendor_name", "vendor_country", "currency",
        "original_amount", "exchange_rate", "amount_twd", "cost_price", "profit_amount",
        "is_current", "changed_by", "operator_name", "sold_at", "returned_at",
        "returned_by", "return_reason",
    }
