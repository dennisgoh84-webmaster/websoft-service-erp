"""
Websoft Service ERP Solution -- API entrypoint.

Scope for this build: the Service Operations core slice (Customer,
Service Contract, Job Order, Service Record, Excess Usage Review,
Billing/Invoice) implementing the confirmed SRV-001..018 business rules,
plus Module Control / multi-company licensing and a summary dashboard.
Commission Management, further Service Record business-rule decisions,
and Odoo migration work are deferred for now at the user's request.
See ../../docs/business-requirements.md for the source of truth on rules.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    auth,
    billing,
    contracts,
    customers,
    dashboard,
    event_logs,
    excess_usage,
    groups,
    job_orders,
    modules,
    service_records,
    users,
)
from app.services import audit

app = FastAPI(title=settings.app_name)

# Demo-only CORS: the React dev server runs on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def audit_request_context_middleware(request: Request, call_next):
    """Captures who/what made this request (client IP, browser User-Agent,
    and the frontend's persisted per-browser device id -- see
    frontend/src/lib/deviceId.ts) so app.services.audit.record() can
    stamp every audit entry written during this request without every
    caller having to pass a Request through. See app/services/audit.py."""
    audit.set_request_context(
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        device_id=request.headers.get("x-device-id"),
    )
    return await call_next(request)


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(modules.router)
app.include_router(event_logs.router)
app.include_router(customers.router)
app.include_router(contracts.router)
app.include_router(job_orders.router)
app.include_router(service_records.router)
app.include_router(excess_usage.router)
app.include_router(billing.router)
app.include_router(dashboard.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}
