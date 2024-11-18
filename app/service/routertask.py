from datetime import datetime
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import TaskRepository, Database, Task, ComputerRepository

db = Database()  # 데이터베이스 인스턴스 생성
task_repo = TaskRepository(db.session) 
computer_repo = ComputerRepository(db.session)

router = APIRouter(
    prefix="/task",
)

metadata = {
    "name": "Task",
    "description": "Task API"
}

class TaskCreate(BaseModel):
    computer_id: int

    class Config:
        orm_mode = True  # ORM 모드 활성화
        from_attributes = True  # from_orm 사용을 위한 설정

class TaskResponse(TaskCreate):
    id: int
    created_at: datetime
    analysis_result: Optional[str] = None  # Optional로 설정하여 None 허용
    visualization_chart1: Optional[str] = None  # Optional로 설정하여 None 허용
    visualization_chart2: Optional[str] = None  # Optional로 설정하여 None 허용
    visualization_chart3: Optional[str] = None  # Optional로 설정하여 None 허용
    visualization_chart4: Optional[str] = None  # Optional로 설정하여 None 허용

    class Config:
        orm_mode = True  # ORM 모드 활성화
        from_attributes = True  # from_orm 사용을 위한 설정

@router.post("/tasks/", response_model=TaskResponse)
def create_task(task: TaskCreate):
    computer = computer_repo.get_computer(task.computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    new_task = Task(
        computer_id = task.computer_id,
        created_at = datetime.utcnow()
    )
    created_task = task_repo.create_task(new_task)
    return TaskResponse.from_orm(created_task)

@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int):
    task = task_repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.from_orm(task)

@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_update: TaskCreate):
    updated_task = task_repo.update_task(task_id, Task(**task_update.dict()))
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse.from_orm(updated_task)

@router.delete("/tasks/{task_id}", response_model=dict)
def delete_task(task_id: int):
    success = task_repo.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"detail": "Task deleted successfully"}

