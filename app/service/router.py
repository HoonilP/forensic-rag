from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from typing import Optional

from pydantic import BaseModel
from app.database import  Database, UserRepository
from .. import DB
from ..database import User, Token

db = Database()  # 데이터베이스 인스턴스 생성
user_repo = UserRepository(db.session)

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(
    prefix="/user",
)

metadata = {
    "name": "User",
    "description": "Login API"
}

class UserSignup(BaseModel):
    email: str
    password: str
    organization: str
    
@router.post("/signup", response_model=str,tags=["User"])
def signup(user: UserSignup):
    exist = DB.check_email_duplication(user.email)

    if exist:
        raise HTTPException(status_code=400, detail="Email Not Available.")

    try:
        hashed_password = pwd_context.hash(user.password)
        new_user = User(email=user.email, password=hashed_password, organization=user.organization)
        DB.push_data(new_user)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
        
    return 'SignUp Successful.'

class UserSignIn(BaseModel):
    email: str
    password: str

@router.post("/signin", tags=["User"])
def signin(user:UserSignIn) -> Token:
    try:
        authenticated = DB.authenticate_user(user.email, user.password)
        
        if not authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = user_repo.get_user_by_email(user.email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id}, expires_delta=access_token_expires
        )

        refresh_token = create_refresh_token(
            data={"sub": user.email}
        )

        return Token(access_token=access_token, token_type="bearer", refresh_token=refresh_token)

    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))

    
@router.post("/token/refresh", tags=["User"])
def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": email}, expires_delta=access_token_expires
        )

        return {"access_token": new_access_token, "token_type": "bearer"}
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt