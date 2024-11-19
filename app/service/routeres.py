from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import TaskRepository, Database, Task, ComputerRepository

router = APIRouter(
    prefix="/es",
)

metadata = {
    "name": "User",
    "description": "Login API"
}