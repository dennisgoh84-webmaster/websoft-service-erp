"""Login sequence (2026-09-12: password complexity, forced first-login
password change, email OTP second factor -- see app/services/auth.py's
module docstring for the token-purpose design behind this).

The sequence a client follows:
1. POST /login (email + password). Returns a LoginResult:
   - status="must_change_password" if this account has never set its
     own password yet (new hire, or just reset by an admin) -- go to
     step 2 first.
   - status="otp_required" if SMTP is configured -- a 6-digit code was
     just emailed; go to step 3.
   - status="ok" -- signed in immediately (no OTP configured).
2. POST /change-password (change_token + new_password). On success,
   re-runs the same "issue OTP or sign in" decision as step 1's tail,
   returning the same LoginResult shape.
3. POST /verify-otp (otp_token + code). Returns status="ok" with the
   real access_token once the code matches.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.core import LoginOtp, User
from app.schemas.schemas import ChangePasswordRequest, CurrentUser, LoginResult, VerifyOtpRequest
from app.services import audit, mailer
from app.services.auth import (
    create_access_token,
    create_purpose_token,
    decode_purpose_token,
    hash_password,
    validate_password_complexity,
    verify_password,
)
from app.services.authority import get_user_group_id

router = APIRouter(prefix="/api/auth", tags=["auth"])

OTP_EXPIRE_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
CHANGE_PASSWORD_TOKEN_EXPIRE_MINUTES = 15


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _issue_login_result(db: Session, user: User) -> LoginResult:
    """The final step of every successful credential/password/OTP check:
    hand back a real access token, unless email OTP is configured, in
    which case issue a challenge instead. Never blocks sign-in when
    SMTP isn't set up -- see app/models/core.py's LoginOtp docstring."""
    if mailer.is_configured():
        code = f"{secrets.randbelow(1_000_000):06d}"
        otp = LoginOtp(
            user_id=user.id,
            code_hash=_hash_otp(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES),
        )
        db.add(otp)
        db.commit()
        try:
            mailer.send_email(
                to_email=user.email,
                subject="Your Websoft Service ERP login code",
                body_text=(
                    f"Your one-time login code is {code}.\n\n"
                    f"It expires in {OTP_EXPIRE_MINUTES} minutes. If you didn't just try to "
                    "sign in, you can ignore this email."
                ),
            )
        except (mailer.MailerNotConfigured, mailer.MailerError):
            # SMTP looked configured but the actual send failed (bad
            # credentials, network hiccup) -- fail OPEN rather than
            # stranding every user outside a login page they can't get
            # past. The unusable OTP row is simply left unconsumed.
            return LoginResult(status="ok", access_token=create_access_token(user.id))
        return LoginResult(
            status="otp_required",
            otp_token=create_purpose_token(user.id, "otp", expire_minutes=OTP_EXPIRE_MINUTES),
        )
    return LoginResult(status="ok", access_token=create_access_token(user.id))


@router.post("/login", response_model=LoginResult)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This account has been deactivated.")

    if user.must_change_password:
        return LoginResult(
            status="must_change_password",
            change_token=create_purpose_token(
                user.id, "password_change", expire_minutes=CHANGE_PASSWORD_TOKEN_EXPIRE_MINUTES
            ),
        )
    return _issue_login_result(db, user)


@router.post("/change-password", response_model=LoginResult)
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db)):
    data = decode_purpose_token(payload.change_token, "password_change")
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This session has expired -- please sign in again.",
        )
    user = db.get(User, uuid.UUID(data["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found or inactive.")

    try:
        validate_password_complexity(payload.new_password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    user.hashed_password = hash_password(payload.new_password)
    user.must_change_password = False
    audit.record(
        db,
        entity_type="user",
        entity_id=user.id,
        action="password_changed_self",
        actor_user_id=user.id,
    )
    db.commit()
    return _issue_login_result(db, user)


@router.post("/verify-otp", response_model=LoginResult)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    data = decode_purpose_token(payload.otp_token, "otp")
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This code has expired -- please sign in again to get a new one.",
        )
    user = db.get(User, uuid.UUID(data["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found or inactive.")

    otp = (
        db.query(LoginOtp)
        .filter(LoginOtp.user_id == user.id, LoginOtp.consumed_at.is_(None))
        .order_by(LoginOtp.created_at.desc())
        .first()
    )
    now = datetime.now(timezone.utc)
    if not otp or otp.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This code has expired -- please sign in again to get a new one.",
        )
    if otp.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Too many incorrect attempts -- please sign in again to get a new code.",
        )
    if _hash_otp(payload.code) != otp.code_hash:
        otp.attempts += 1
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect code.")

    otp.consumed_at = now
    db.commit()
    return LoginResult(status="ok", access_token=create_access_token(user.id))


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
