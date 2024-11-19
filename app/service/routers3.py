from datetime import datetime
import json
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import TaskRepository, Database, Task, ComputerRepository
import boto3
import os
from botocore.exceptions import ClientError
from ..guard.userguard import get_current_user

router = APIRouter(
    prefix="/s3")

s3_region = os.getenv("AWS_REGION")
s3_bucket = os.getenv("S3_BUCKET")

metadata = {
    "name": "User",
    "description": "Login API"
}

# 요청 모델 정의
class LogRequest(BaseModel):
    computer_id: int
    start_date: datetime
    end_date: datetime

def get_s3_client():
    return boto3.client('s3', region_name=s3_region)

@router.post("/get_logs", response_model=List[dict])
async def get_logs(request: LogRequest, current_user_id: int = Depends(get_current_user)):
    # 요청 데이터에서 정보 추출
    computer_id = request.computer_id
    user_id = current_user_id
    start_date = request.start_date
    end_date = request.end_date
    
    # S3에서 파일 이름 생성
    object_name = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{user_id}_{computer_id}.json"
    
    s3_client = get_s3_client()
    
    try:
        # S3에서 파일 다운로드
        response = s3_client.get_object(Bucket=s3_bucket, Key=object_name)
        logs_data = response['Body'].read().decode('utf-8')
        
        # JSON으로 변환
        logs = json.loads(logs_data)
        return logs

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(status_code=404, detail="Logs not found for the specified time range and computer ID.")
        else:
            raise HTTPException(status_code=500, detail="An error occurred while accessing S3.")