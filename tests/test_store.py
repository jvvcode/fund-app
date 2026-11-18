from fundapp.store.models import Base, Instrument


def test_metadata_has_core_tables():
    tables = set(Base.metadata.tables)
    assert {"security_master", "derivative_terms", "transactions", "accounts", "tax_lots"} <= tables


def test_self_referential_underlying_fk():
    fks = Instrument.__table__.c.underlying_security_id.foreign_keys
    assert any(fk.column.table.name == "security_master" for fk in fks)
