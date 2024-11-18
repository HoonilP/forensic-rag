from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from typing import Optional

from .. import DB
from ..database import User, Token

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

@router.post("/signup", tags=["User"])
def signup(id: str, email: str, password: str, organization: str) -> str:
    exist = DB.check_id_duplication(id)

    if exist:
        return 'ID Not Available.'
    
    else:
        try:
            hashed_password = pwd_context.hash(password)
            DB.push_data(User(id, email, hashed_password, organization))
        except Exception as err:
            return err
        
        return 'SignUp Successfull.'
    
@router.post("/signin", tags=["User"])
def signin(id: str, password: str) -> str:
    authenticated = DB.authenticate_user(id, password)

    if authenticated:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": id}, expires_delta=access_token_expires
        )

        return Token(access_token=access_token, token_type="bearer")

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt