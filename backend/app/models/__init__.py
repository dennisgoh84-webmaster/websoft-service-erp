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
from app.models.groups import (  # noqa: F401
    ACCESS_LEVEL_ORDER,
    AccessLevel,
    Group,
    GroupModuleAuthority,
)
from app.models.job_orders import JobOrder, JobOrderPriority, JobOrderStatus  # noqa: F401
from app.models.service_records import (  # noqa: F401
    ServiceRecord,
    ServiceRecordOutcome,
    ServiceRecordStatus,
)
from app.models.licensing import CompanyModule, LicenseType, Module  # noqa: F401
