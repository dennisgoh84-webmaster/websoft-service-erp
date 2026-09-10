from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import User
from app.schemas.schemas import CurrentUser

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[CurrentUser])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(User).filter(User.company_id == current_user.company_id, User.is_active).all()
