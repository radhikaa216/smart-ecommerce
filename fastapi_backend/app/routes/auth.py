from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from app.utils.auth import create_access_token, get_current_user, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    if get_settings().auth_mode == "auth0":
        raise HTTPException(status_code=400, detail="Register through Auth0 Universal Login")
    email = user_data.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(name=user_data.name.strip(), email=email, password_hash=hash_password(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    if get_settings().auth_mode == "auth0":
        raise HTTPException(status_code=400, detail="Log in through Auth0 Universal Login")
    user = db.query(User).filter(User.email == user_data.email.lower()).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")
    return TokenResponse(access_token=create_access_token(user.id), user=user)


@router.get("/me", response_model=UserResponse)
def current_user(user: User = Depends(get_current_user)):
    return user
