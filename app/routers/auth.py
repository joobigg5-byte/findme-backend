import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from ..auth import limiter
from ..email_utils import send_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def signup(request: Request, payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    """
    Creates a brand new Organization (the paying customer) plus its first
    admin User, and returns a real access token — this is what the
    onboarding wizard's first step calls. Rate-limited to 5/hour per IP
    to blunt automated account-creation abuse.
    """
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    org = models.Organization(name=payload.organization_name)
    db.add(org)
    db.flush()  # assigns org.id without committing yet

    user = models.User(
        organization_id=org.id,
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(org)

    token = auth.create_access_token(user_id=user.id, organization_id=org.id)
    return schemas.TokenResponse(access_token=token, organization_id=org.id, organization_name=org.name)


@router.post("/login", response_model=schemas.TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Standard OAuth2 password-flow login (this is also what powers the
    'Authorize' button in the /docs page). email goes in the 'username'
    field per the OAuth2 spec form fields. Rate-limited to 10/minute per
    IP — generous for real use, tight enough to blunt brute-forcing.
    """
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    org = db.query(models.Organization).filter(models.Organization.id == user.organization_id).first()
    token = auth.create_access_token(user_id=user.id, organization_id=user.organization_id)
    return schemas.TokenResponse(access_token=token, organization_id=org.id, organization_name=org.name)


@router.post("/forgot-password", response_model=schemas.MessageResponse)
@limiter.limit("3/hour")
def forgot_password(request: Request, payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Always returns the same message whether or not the email exists —
    that's deliberate, so this endpoint can't be used to check which
    emails have accounts. If the email *does* match a user, a real reset
    token is generated and "sent" (see email_utils.py for the honest
    caveat on what "sent" means right now).
    """
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user:
        token = auth.generate_reset_token()
        user.reset_token = token
        user.reset_token_expires_at = datetime.datetime.utcnow() + datetime.timedelta(
            minutes=auth.RESET_TOKEN_EXPIRE_MINUTES
        )
        db.commit()
        reset_link = f"https://your-frontend-domain.example/reset-password?token={token}"
        send_email(
            to=user.email,
            subject="Reset your find-me password",
            body=f"Click here to reset your password (expires in {auth.RESET_TOKEN_EXPIRE_MINUTES} minutes):\n{reset_link}",
        )
    return schemas.MessageResponse(message="If that email has an account, a reset link has been sent.")


@router.post("/reset-password", response_model=schemas.MessageResponse)
@limiter.limit("10/hour")
def reset_password(request: Request, payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .filter(models.User.reset_token == payload.token)
        .first()
    )
    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="That reset link is invalid or has expired")

    user.hashed_password = auth.hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()
    return schemas.MessageResponse(message="Password updated. You can now log in with your new password.")
