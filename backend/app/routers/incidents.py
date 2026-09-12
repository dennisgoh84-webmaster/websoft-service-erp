"""Incident Module -- the Helpdesk front door for an incoming call or
email, before it's routed to a Quotation, Job Order, or Software Task.
See app/models/incidents.py and app/services/incidents.py for the
confirmed rules (docs/open-business-decisions.md #36).

Lives under "service_operations" (already labelled "Helpdesk / Service
Operations (Job Orders)" in the module catalog) rather than a new
module key.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.models.incidents import Incident, IncidentSource, IncidentStatus
from app.models.job_orders import JobOrderPriority
from app.schemas.schemas import (
    IncidentCallback,
    IncidentClose,
    IncidentConvertToJobOrder,
    IncidentConvertToQuotation,
    IncidentConvertToSoftwareTask,
    IncidentCreate,
    IncidentFromEmail,
    IncidentFromEmailResult,
    IncidentOut,
    IncidentSetCustomer,
    JobOrderOut,
    QuotationOut,
    SoftwareTaskOut,
)
from app.services import audit
from app.services import incidents as incident_svc
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/incidents", tags=["incidents"])
MODULE = "service_operations"


def _get_incident(db: Session, incident_id: uuid.UUID, company_id: uuid.UUID) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident or incident.company_id != company_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    status: IncidentStatus | None = None,
    customer_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(Incident).filter(Incident.company_id == current_user.company_id)
    if status is not None:
        query = query.filter(Incident.status == status)
    if customer_id is not None:
        query = query.filter(Incident.customer_id == customer_id)
    return query.order_by(Incident.created_at.desc()).all()


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _get_incident(db, incident_id, current_user.company_id)


@router.post("", response_model=IncidentOut)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    customer_id = payload.customer_id
    if customer_id is None:
        customer_id = incident_svc.try_match_customer_by_email(db, current_user.company_id, payload.sender_email)
    incident = incident_svc.create_incident(
        db,
        company_id=current_user.company_id,
        customer_id=customer_id,
        source=payload.source,
        subject=payload.subject,
        description=payload.description,
        sender_name=payload.sender_name,
        sender_email=payload.sender_email,
        sender_phone=payload.sender_phone,
        created_by_user_id=current_user.id,
    )
    db.commit()
    db.refresh(incident)
    return incident


# ---- Outlook Add-in endpoints -- see outlook-addin/README.md ----------
# These act directly on an email with no Incident yet in existence, so
# they take the raw sender/subject/body rather than an incident_id.
# Registered here, before any "/{incident_id}/..." route below, because
# FastAPI matches routes in registration order and "/{incident_id}"
# would otherwise swallow "from-email" as a (garbage) incident_id --
# same reasoning as app/routers/billing.py's literal /export.csv routes
# needing to come before any "/{id}"-style route.


@router.post("/from-email", response_model=IncidentOut)
def create_incident_from_email(
    payload: IncidentFromEmail,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """The Outlook Add-in's "Convert to Incident" button."""
    customer_id = incident_svc.try_match_customer_by_email(db, current_user.company_id, payload.sender_email)
    incident = incident_svc.create_incident(
        db,
        company_id=current_user.company_id,
        customer_id=customer_id,
        source=IncidentSource.EMAIL,
        subject=payload.subject,
        description=payload.body,
        sender_name=payload.sender_name,
        sender_email=payload.sender_email,
        sender_phone=None,
        created_by_user_id=current_user.id,
    )
    db.commit()
    db.refresh(incident)
    return incident


@router.post("/from-email/convert-to-job-order", response_model=IncidentFromEmailResult)
def create_job_order_from_email(
    payload: IncidentFromEmail,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    """The Outlook Add-in's "Convert to Job Order" button. Confirmed
    2026-09-12: if the sender's email doesn't match an existing
    Company/Individual, or that customer has no valid contract, this
    falls back to creating a plain Incident instead of erroring --
    exactly what "Convert to Incident" would have done."""
    customer_id = incident_svc.try_match_customer_by_email(db, current_user.company_id, payload.sender_email)
    fallback_reason = None
    contract = None
    if customer_id is None:
        fallback_reason = f"No Company/Individual matches sender email {payload.sender_email}."
    else:
        contract = incident_svc.find_valid_contract(db, current_user.company_id, customer_id)
        if contract is None:
            fallback_reason = "No active contract found for this customer."

    incident = incident_svc.create_incident(
        db,
        company_id=current_user.company_id,
        customer_id=customer_id,
        source=IncidentSource.EMAIL,
        subject=payload.subject,
        description=payload.body,
        sender_name=payload.sender_name,
        sender_email=payload.sender_email,
        sender_phone=None,
        created_by_user_id=current_user.id,
    )

    if fallback_reason is not None:
        db.commit()
        db.refresh(incident)
        return IncidentFromEmailResult(incident=incident, job_order_created=False, fallback_reason=fallback_reason)

    incident_svc.convert_to_job_order(
        db, incident, contract_id=contract.id, priority=JobOrderPriority.NORMAL, actor_user_id=current_user.id
    )
    db.commit()
    db.refresh(incident)
    return IncidentFromEmailResult(incident=incident, job_order_created=True, fallback_reason=None)


@router.patch("/{incident_id}/customer", response_model=IncidentOut)
def set_incident_customer(
    incident_id: uuid.UUID,
    payload: IncidentSetCustomer,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    incident = _get_incident(db, incident_id, current_user.company_id)
    old = str(incident.customer_id) if incident.customer_id else None
    incident.customer_id = payload.customer_id
    audit.record(
        db, entity_type="incident", entity_id=incident.id, action="customer_set",
        actor_user_id=current_user.id, old_value={"customer_id": old},
        new_value={"customer_id": str(payload.customer_id)},
    )
    db.commit()
    db.refresh(incident)
    return incident


@router.post("/{incident_id}/callback", response_model=IncidentOut)
def set_incident_callback(
    incident_id: uuid.UUID,
    payload: IncidentCallback,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    incident = _get_incident(db, incident_id, current_user.company_id)
    try:
        incident_svc.set_callback(db, incident, assigned_to_user_id=payload.assigned_to_user_id, actor_user_id=current_user.id)
    except incident_svc.IncidentRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(incident)
    return incident


@router.post("/{incident_id}/close", response_model=IncidentOut)
def close_incident(
    incident_id: uuid.UUID,
    payload: IncidentClose,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    incident = _get_incident(db, incident_id, current_user.company_id)
    try:
        incident_svc.close_incident(db, incident, reason=payload.reason, actor_user_id=current_user.id)
    except incident_svc.IncidentRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(incident)
    return incident


@router.post("/{incident_id}/convert-to-quotation", response_model=QuotationOut)
def convert_incident_to_quotation(
    incident_id: uuid.UUID,
    payload: IncidentConvertToQuotation,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    incident = _get_incident(db, incident_id, current_user.company_id)
    try:
        quotation = incident_svc.convert_to_quotation(
            db, incident, quotation_date=payload.quotation_date, actor_user_id=current_user.id
        )
    except incident_svc.IncidentRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(quotation)
    return quotation


@router.post("/{incident_id}/convert-to-job-order", response_model=JobOrderOut)
def convert_incident_to_job_order(
    incident_id: uuid.UUID,
    payload: IncidentConvertToJobOrder,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    incident = _get_incident(db, incident_id, current_user.company_id)
    try:
        job_order = incident_svc.convert_to_job_order(
            db, incident, contract_id=payload.contract_id, priority=payload.priority, actor_user_id=current_user.id
        )
    except incident_svc.IncidentRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(job_order)
    return job_order


@router.post("/{incident_id}/convert-to-software-task", response_model=SoftwareTaskOut)
def convert_incident_to_software_task(
    incident_id: uuid.UUID,
    payload: IncidentConvertToSoftwareTask,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    incident = _get_incident(db, incident_id, current_user.company_id)
    try:
        task = incident_svc.convert_to_software_task(
            db, incident, assigned_programmer_id=payload.assigned_programmer_id, actor_user_id=current_user.id
        )
    except incident_svc.IncidentRuleViolation as e:
        raise HTTPException(status_code=422, detail=str(e))
    db.commit()
    db.refresh(task)
    return task
