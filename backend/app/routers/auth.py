from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import User
from app.schemas.schemas import CurrentUser, Token
from app.services.auth import create_access_token, verify_password
from app.services.authority import get_user_group_id

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=CurrentUser)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Group is per company, so report the one that applies in the company
    # this user is currently working in.
    return CurrentUser(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
        group_id=get_user_group_id(db, current_user),
        company_id=current_user.company_id,
    )
