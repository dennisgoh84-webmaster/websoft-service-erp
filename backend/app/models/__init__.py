"""Import all model modules so Base.metadata is fully populated for
Alembic autogenerate and for `create_all` in scripts/tests."""
from app.models.accounting import (  # noqa: F401
    Account,
    AccountType,
    JournalEntry,
    JournalLine,
    JournalStatus,
    VoucherType,
)
from app.models.payables import (  # noqa: F401
    BillMatchStatus,
    BillStatus,
    PurchaseOrder,
    PurchaseOrderStatus,
    Supplier,
    SupplierInvoice,
    SupplierPayment,
    SupplierPaymentAllocation,
)
from app.models.billing import Invoice, InvoiceStatus, InvoiceType  # noqa: F401
from app.models.payments import (  # noqa: F401
    Payment,
    PaymentAllocation,
    PaymentMethod,
)
from app.models.tax import TaxCode  # noqa: F401
from app.services.numbering import DocumentSequence  # noqa: F401
from app.models.contracts import (  # noqa: F401
    Contract,
    ContractKind,
    ContractProduct,
    ContractStatus,
    ExcessTreatment,
    ExcessUsageRecord,
    ExpiredHoursRecord,
)
from app.models.core import (  # noqa: F401
    AuditLogEntry,
    Company,
    User,
    UserCompanyAccess,
    UserRole,
)
from app.models.customers import (  # noqa: F401
    Branch,
    Contact,
    Customer,
    CustomerGroup,
    CustomerRelationship,
    CustomerType,
)
from app.models.catalog import Product, ProductType  # noqa: F401
from app.models.quotations import Quotation, QuotationLine, QuotationStatus  # noqa: F401
from app.models.groups import (  # noqa: F401
    ACCESS_LEVEL_ORDER,
    AccessLevel,
    Group,
    GroupModuleAuthority,
)
from app.models.job_orders import JobOrder, JobOrderPriority, JobOrderStatus  # noqa: F401
from app.models.service_records import (  # noqa: F401
    ServiceRecord,
    ServiceRecordCompletion,
    ServiceRecordOutcome,
    ServiceRecordStatus,
)
from app.models.licensing import CompanyModule, LicenseType, Module  # noqa: F401
from app.models.software_tasks import SoftwareTask  # noqa: F401
from app.models.accounting import GLType  # noqa: F401
from app.models.setup import SetupListItem, SetupListType  # noqa: F401
from app.models.treasury import BankAccount, CurrencyRate  # noqa: F401
from app.models.periods import AccountingPeriod, FiscalYearClosure, PeriodStatus  # noqa: F401
