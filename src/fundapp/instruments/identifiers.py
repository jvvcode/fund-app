from __future__ import annotations

# OpenFIGI identifier mapping (ticker <-> ISIN <-> FIGI <-> CUSIP).
# Stub for Phase 1: wire the real HTTP call in the ingestion step. The point is
# that the security master keys on the internal security_id, and this module keeps
# the external identifiers reconciled and stable.


def map_identifiers(query: dict) -> dict:
    # query example: {"idType": "ID_ISIN", "idValue": "US0378331005"}
    # Returns a normalized dict of {figi, ticker, name, ...}. Not implemented yet.
    raise NotImplementedError("OpenFIGI mapping is wired in the ingestion step")
