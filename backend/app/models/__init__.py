"""Import all model modules so Base.metadata is fully populated for
Alembic autogenerate and for `create_all` in scripts/tests."""
from app.models.billing import Invoice, InvoiceType  # noqa: F401
from app.models.contracts import (  # noqa: F401
    Contract,
    ContractStatus,
    ExcessTreatment,
    ExcessUsageRecord,
    ExpiredHoursRecord,
)
from app.models.core import AuditLogEntry, Company, User, UserRole  # noqa: F401
from app.models.customers import Contact, Customer  # noqa: F401
from app.models.tickets import HelpdeskTicket, TicketPriority, TicketStatus  # noqa: F401
from app.models.timesheets import (  # noqa: F401
    TimesheetEntry,
    TimesheetOutcome,
    TimesheetStatus,
)
