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


AUTH0_CLAIM_NAMESPACE = "https://smart-ecommerce.local"


def _auth0_profile_claim(claims: dict, name: str):
    """Read the namespaced profile claims added by the Auth0 Post-Login Action."""
    return claims.get(f"{AUTH0_CLAIM_NAMESPACE}/{name}") or claims.get(name)


def authenticate_token(token: str, db: Session) -> User:
    settings = get_settings()
    token_algorithm = jwt.get_unverified_header(token).get("alg")
    is_auth0_token = token_algorithm == "RS256"
    if settings.auth_mode == "auth0" or (settings.auth_mode == "hybrid" and is_auth0_token):
        claims = _decode_auth0_token(token)
        subject = claims.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="Token subject is missing")

        email = _auth0_profile_claim(claims, "email")
        if not email:
            raise HTTPException(
                status_code=401,
                detail="Auth0 access token is missing the email profile claim. Configure the Smart Ecommerce Post-Login Action.",
            )
        email = str(email).lower()
        name = _auth0_profile_claim(claims, "name") or _auth0_profile_claim(claims, "nickname") or email.split("@")[0]
        picture = _auth0_profile_claim(claims, "picture")
        email_verified = bool(_auth0_profile_claim(claims, "email_verified"))

        user = db.query(User).filter(User.auth0_id == subject).first()
        if user:
            # Repair profiles created before the Auth0 profile claims were configured.
            if user.email.endswith("@auth0.local"):
                email_owner = db.query(User).filter(User.email == email, User.id != user.id).first()
                if email_owner:
                    raise HTTPException(status_code=409, detail="This email already belongs to a local account; contact an administrator to link it")
                user.email = email
            user.name = str(name)[:150]
            user.avatar_url = picture
            user.email_verified = email_verified
        else:
            # Safely link a pre-existing local-demo account with the identity
            # Auth0 authenticated, rather than creating a duplicate email.
            user = db.query(User).filter(User.email == email).first()
            if user and user.auth0_id and user.auth0_id != subject:
                raise HTTPException(status_code=409, detail="This email is already linked to another Auth0 identity")
            if user:
                user.auth0_id = subject
                user.name = str(name)[:150]
                user.avatar_url = picture
                user.email_verified = email_verified
            else:
                user = User(
                    auth0_id=subject,
                    email=email,
                    name=str(name)[:150],
                    avatar_url=picture,
                    email_verified=email_verified,
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
