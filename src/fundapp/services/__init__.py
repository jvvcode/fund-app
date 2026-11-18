"""Service-layer business logic (Phase 2+): portfolio_service, market_data_service,
analytics_service, event_service. This is what src/fundapp/api/ routes call into —
api/ handles HTTP, services/ handles logic — and it's the only layer allowed to
query fundapp.store directly. Application modules (portfolio/, risk/, dashboard/)
call services/, never the store.
"""
