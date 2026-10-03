from datetime import datetime, timedelta, timezone
from functools import lru_cache

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    return bool(hashed_password) and password_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expires, "iss": "smart-ecommerce-local"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


@lru_cache(maxsize=4)
def _get_auth0_jwks(domain: str) -> dict:
    response = httpx.get(f"https://{domain}/.well-known/jwks.json", timeout=10)
    response.raise_for_status()
    return response.json()


def _decode_auth0_token(token: str) -> dict:
    settings = get_settings()
    if not settings.auth0_domain or not settings.auth0_audience:
        raise HTTPException(status_code=503, detail="Auth0 is not configured")
    try:
        header = jwt.get_unverified_header(token)
        key = next(item for item in _get_auth0_jwks(settings.auth0_domain)["keys"] if item["kid"] == header["kid"])
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )
    except (JWTError, KeyError, StopIteration, httpx.HTTPError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Auth0 access token") from exc


def authenticate_token(token: str, db: Session) -> User:
    settings = get_settings()
    if settings.auth_mode == "auth0":
        claims = _decode_auth0_token(token)
        subject = claims.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="Token subject is missing")
        user = db.query(User).filter(User.auth0_id == subject).first()
        if not user:
            email = claims.get("email") or f"{subject.replace('|', '_')}@auth0.local"
            user = User(
                auth0_id=subject,
                email=email,
                name=claims.get("name") or claims.get("nickname") or email.split("@")[0],
                avatar_url=claims.get("picture"),
                email_verified=bool(claims.get("email_verified")),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        try:
            claims = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            user = db.get(User, int(claims["sub"]))
        except (JWTError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive or unavailable")
    user.last_login_at = datetime.utcnow()
    db.commit()
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    return authenticate_token(credentials.credentials, db)


def require_roles(*allowed_roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return checker
