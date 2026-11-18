from datetime import date
from decimal import Decimal

from fundapp.ingestion.connectors.broker import BrokerImportConnector, _dec_eq, _values_match
from fundapp.store.models import Transaction


def _txn(**overrides) -> Transaction:
    fields = dict(
        account_id=1,
        security_id=1,
        txn_type="buy",
        trade_date=date(2026, 1, 5),
        quantity=Decimal("10"),
        price=Decimal("100"),
        amount=Decimal("1000"),
        currency="USD",
    )
    fields.update(overrides)
    return Transaction(**fields)


def _row(**overrides) -> dict:
    row = dict(
        security_id=1,
        txn_type="buy",
        trade_date=date(2026, 1, 5),
        quantity=Decimal("10"),
        price=Decimal("100"),
        amount=Decimal("1000"),
        currency="USD",
    )
    row.update(overrides)
    return row


def test_dec_eq_treats_matching_decimal_and_string_as_equal():
    assert _dec_eq(Decimal("10.5"), "10.50")
    assert not _dec_eq(Decimal("10.5"), "10.6")
    assert _dec_eq(None, None)
    assert not _dec_eq(None, Decimal("1"))


def test_identical_row_matches_existing():
    assert _values_match(_txn(), _row())


def test_amended_quantity_does_not_match():
    # This is the case the original DO-NOTHING fix silently dropped.
    assert not _values_match(_txn(), _row(quantity=Decimal("12"), amount=Decimal("1200")))


def test_reversal_negates_quantity_and_amount_but_keeps_the_trade_as_filed():
    existing = _txn(quantity=Decimal("10"), amount=Decimal("1000"), price=Decimal("100"))
    reversal = BrokerImportConnector()._reversal_of(existing)
    assert reversal["quantity"] == Decimal("-10")
    assert reversal["amount"] == Decimal("-1000")
    assert reversal["price"] == Decimal("100")  # price is restated, not flipped
    assert reversal["security_id"] == existing.security_id


def test_reversal_of_none_quantity_stays_none():
    existing = _txn(quantity=None, amount=None)
    reversal = BrokerImportConnector()._reversal_of(existing)
    assert reversal["quantity"] is None
    assert reversal["amount"] is None
