from datetime import datetime
from fastapi import Depends, FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import TaskRepository, Database, Task, ComputerRepository, TaskType
from graph.langgraph import MultiAgentForensic
from s3service import download_image, get_logs, upload_to_s3_image
from guard.userguard import get_current_user
import os

s3_bucket_name2 = os.getenv("S3_BUCKET_NAME2")

multiAgentForensic = MultiAgentForensic()
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
    task_type: TaskType  # TaskType 추가
    
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
    task_type: TaskType

    class Config:
        orm_mode = True  # ORM 모드 활성화
        from_attributes = True  # from_orm 사용을 위한 설정

@router.post("/tasks/", response_model=TaskResponse)
async def create_task(task: TaskCreate, current_user_id: int = Depends(get_current_user)):
    # 컴퓨터 확인
    computer = await computer_repo.get_computer(task.computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    
    # S3에서 로그 가져오기
    logs = await get_logs(task.computer_id, current_user_id, task.task_type)

    # MultiAgentForensic 실행
    result = await MultiAgentForensic(logs)

    # Task 객체 생성
    new_task = Task(
        computer_id=task.computer_id,
        analysis_result=result['summary'].strip(),
        created_at=datetime.utcnow(),
        task_type=task.task_type,
    )

    images = result.get('images', [])
    s3_urls = []

    for image_url in images:
        datas = await download_image(image_url)
        name = os.path.basename(image_url)
        s3_url = await upload_to_s3_image(s3_bucket_name2, name, datas)
        s3_urls.append(s3_url)
    
    if s3_urls:
        new_task.visualization_chart1 = s3_urls[0]
        new_task.visualization_chart2 = s3_urls[1] if len(s3_urls) > 1 else None
        new_task.visualization_chart3 = s3_urls[2] if len(s3_urls) > 2 else None
        new_task.visualization_chart4 = s3_urls[3] if len(s3_urls) > 3 else None
    
    # 데이터베이스에 저장
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

