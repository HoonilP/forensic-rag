import os
import boto3
import json
from botocore.exceptions import NoCredentialsError, ClientError

from fastapi import HTTPException, requests
from dotenv import load_dotenv

load_dotenv()
s3_region = os.getenv("S3_REGION")
s3_bucket_name = os.getenv("S3_BUCKET_NAME")
s3_bucket_name2 = os.getenv("S3_BUCKET_NAME2")


def get_s3_client():
    return boto3.client('s3', region_name=s3_region)

async def get_logs(task_id, user_id, task_type):
    # S3에서 파일 이름 생성
    object_name = f"{task_id}_{user_id}_{task_type}.json"
    
    # S3 클라이언트 생성
    s3_client = get_s3_client()
    
    try:
        # S3에서 파일 다운로드
        response = await s3_client.get_object(Bucket=s3_bucket_name, Key=object_name)
        logs_data = response['Body'].read().decode('utf-8')
        
        # JSON으로 변환
        logs = await json.loads(logs_data)

        return logs

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(status_code=404, detail="Logs not found for the specified time range and computer ID.")
        else:
            raise HTTPException(status_code=500, detail="An error occurred while accessing S3.")

async def download_image(image_url: str) -> bytes: 
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        return response.content 
    
    except requests.exceptions.RequestException as e:
        raise Exception(f'Failed to download image: {e}')

async def upload_to_s3_image(bucket_name: str, object_name: str, data: bytes) -> str:
    s3_client = boto3.client('s3', region_name=s3_region)
    try:
        s3_client.put_object(Bucket=s3_bucket_name2, Key=object_name, Body=data)
        return f"https://{bucket_name}.s3.amazonaws.com/{object_name}"  # S3 URL 반환
    except NoCredentialsError:
        print('Credentials not available')
    except ClientError as e:
        print(f'Failed to upload to S3: {e}')
