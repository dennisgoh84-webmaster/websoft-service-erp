import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import User
from app.models.tickets import HelpdeskTicket
from app.schemas.schemas import TicketAssign, TicketCreate, TicketOut
from app.models.tickets import TicketStatus

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.post("", response_model=TicketOut)
def create_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = HelpdeskTicket(
        customer_id=payload.customer_id,
        contract_id=payload.contract_id,
        subject=payload.subject,
        priority=payload.priority,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("", response_model=list[TicketOut])
def list_tickets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(HelpdeskTicket).all()


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.get(HelpdeskTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.post("/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(
    ticket_id: uuid.UUID,
    payload: TicketAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.get(HelpdeskTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.assigned_to_user_id = payload.assigned_to_user_id
    ticket.status = TicketStatus.ASSIGNED
    db.commit()
    db.refresh(ticket)
    return ticket
