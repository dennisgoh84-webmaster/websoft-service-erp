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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    auth,
    billing,
    contracts,
    customers,
    dashboard,
    excess_usage,
    groups,
    job_orders,
    modules,
    service_records,
    users,
)

app = FastAPI(title=settings.app_name)

# Demo-only CORS: the React dev server runs on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(groups.router)
app.include_router(modules.router)
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
