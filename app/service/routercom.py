from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.database import Computer, Database, ComputerRepository, UserRepository
from ..guard.userguard import get_current_user

router = APIRouter(
    prefix="/computer",
)

db = Database()  # 데이터베이스 인스턴스 생성
computer_repo = ComputerRepository(db.session)  
user_repo = UserRepository(db.session)

class TaskResponse(BaseModel):
    id: int
    computer_id: int
    analysis_result: str = None
    visualization_chart1: str = None
    visualization_chart2: str = None
    visualization_chart3: str = None
    visualization_chart4: str = None
    created_at: datetime

    class Config:
        orm_mode = True  # ORM 모드 활성화
        from_attributes = True  # from_orm 사용을 위한 설정

class ComputerCreate(BaseModel):
    name: str

    class Config:
        orm_mode = True  # ORM 모드 활성화
        from_attributes = True  # from_orm 사용을 위한 설정

class ComputerResponse(ComputerCreate):
    id: int

    class Config:
        orm_mode = True  # ORM 모드 활성화
        from_attributes = True  # from_orm 사용을 위한 설정

@router.post("/computers/", response_model=ComputerResponse)
def create_computer(computer: ComputerCreate, current_user_id: int = Depends(get_current_user)):
    new_computer = Computer(
        name=computer.name,
        user_id=current_user_id
    )

    created_computer = computer_repo.create_computer(new_computer)
    return ComputerResponse.from_orm(created_computer)

@router.get("/computers/{computer_id}", response_model=ComputerResponse)
def get_computer(computer_id: int):
    computer = computer_repo.get_computer(computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    return ComputerResponse.from_orm(computer)

@router.put("/computers/{computer_id}", response_model=ComputerResponse)
def update_computer(computer_id: int, computer_update: ComputerCreate):
    updated_computer = computer_repo.update_computer(computer_id, Computer(**computer_update.dict()))
    if not updated_computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    return ComputerResponse.from_orm(updated_computer)

@router.delete("/computers/{computer_id}", response_model=dict)
def delete_computer(computer_id: int):
    success = computer_repo.delete_computer(computer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Computer not found")
    return {"detail": "Computer deleted successfully"}

@router.get("/computers/", response_model=List[ComputerResponse])
def list_computers():
    computers = computer_repo.get_all_computers()
    return [ComputerResponse.from_orm(computer) for computer in computers]

@router.get("/computers/{computer_id}/tasks", response_model=List[TaskResponse])
def get_computer_tasks(computer_id: int):
    tasks = computer_repo.get_computer_tasks(computer_id)
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found for this computer")
    return [TaskResponse.from_orm(task) for task in tasks]
