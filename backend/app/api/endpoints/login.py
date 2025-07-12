from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.orm import Session

from app import crud
from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.security_logging import get_client_ip, get_user_agent, security_logger

router = APIRouter()


@router.post("/access-token", dependencies=[Depends(RateLimiter(times=5, minutes=1))])
def login_access_token(
    request: Request,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    user = crud.user.get_by_username(db, username=form_data.username)
    if not user or not security.verify_password(
        form_data.password, user.hashed_password
    ):
        # Log failed authentication attempt
        security_logger.log_authentication_attempt(
            username=form_data.username,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason="invalid_credentials",
        )
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    elif not user.is_active:
        # Log failed authentication attempt for inactive user
        security_logger.log_authentication_attempt(
            username=form_data.username,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason="inactive_user",
        )
        raise HTTPException(status_code=400, detail="Inactive user")

    # Log successful authentication
    security_logger.log_authentication_attempt(
        username=form_data.username,
        success=True,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
