from sqlalchemy import Numeric

from modules.exchange_rates.model import ExchangeRateTable


def test_exchange_rate_schema_preserves_legacy_columns():
    assert ExchangeRateTable.__tablename__ == "exchange_rate_settings"
    assert set(ExchangeRateTable.__table__.columns.keys()) == {
        "id", "created_at", "updated_at", "currency", "rate", "updated_by", "operator_name",
    }
    rate_type = ExchangeRateTable.__table__.c.rate.type
    assert isinstance(rate_type, Numeric)
    assert (rate_type.precision, rate_type.scale) == (16, 6)
