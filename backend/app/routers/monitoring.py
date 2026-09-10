"""Support Monitoring -- see app/services/monitoring.py for the metrics
and their open items."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import User
from app.models.groups import AccessLevel
from app.schemas.schemas import MonitoringSummaryOut, StaffMonitoringOut, SupportMonitoringOut
from app.services import monitoring as monitoring_svc
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])
MODULE = "reporting"


@router.get("/support", response_model=SupportMonitoringOut)
def support_monitoring(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    result = monitoring_svc.get_support_monitoring(db, company_id=current_user.company_id)
    return SupportMonitoringOut(
        as_at=result.as_at,
        summary=MonitoringSummaryOut.model_validate(result.summary),
        staff=[StaffMonitoringOut.model_validate(s) for s in result.staff],
        unassigned=StaffMonitoringOut.model_validate(result.unassigned),
    )
