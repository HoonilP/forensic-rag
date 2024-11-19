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

def get_logs(computer_name, task_type):
    s3_client = get_s3_client()
    # S3에서 파일 이름 생성
    version = get_latest_version(s3_client, s3_bucket_name, computer_name, task_type)
    object_name = f"{computer_name}_{task_type}_{version}.json"
    
    # S3 클라이언트 생성
    
    try:
        # S3에서 파일 다운로드
        response = s3_client.get_object(Bucket=s3_bucket_name, Key=object_name)
        logs_data = response['Body'].read().decode('utf-8')
        
        # JSON으로 변환
        logs = json.loads(logs_data)

        return logs

    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            raise HTTPException(status_code=404, detail="Logs not found for the specified time range and computer ID.")
        else:
            raise HTTPException(status_code=500, detail="An error occurred while accessing S3.")

def download_image(image_url: str) -> bytes: 
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        return response.content 
    
    except requests.exceptions.RequestException as e:
        raise Exception(f'Failed to download image: {e}')

def upload_to_s3_image(bucket_name: str, object_name: str, data: bytes) -> str:
    s3_client = boto3.client('s3', region_name=s3_region)
    try:
        s3_client.put_object(Bucket=s3_bucket_name2, Key=object_name, Body=data)
        return f"https://{bucket_name}.s3.amazonaws.com/{object_name}"  # S3 URL 반환
    except NoCredentialsError:
        print('Credentials not available')
    except ClientError as e:
        print(f'Failed to upload to S3: {e}')

def get_latest_version(s3_client, bucket_name, computer_name, task_type):
        """ S3에서 가장 최신 버전 번호를 가져오는 메서드 """
        try:
            response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=f"{computer_name}_{task_type}_")

            if 'Contents' in response:
                # 기존 객체들의 버전 번호 추출
                versions = []
                for obj in response['Contents']:
                    # 파일 이름에서 버전 번호 추출
                    obj_key = obj['Key']
                    version_str = obj_key.split('_')[-1].split('.')[0]  # 'computerName_version.pf'에서 version 추출
                    versions.append(int(version_str))
                return max(versions)  # 가장 큰 버전 번호 반환
            else:
                return 0  # 기존 파일이 없으면 버전 0 반환
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            return 0  # 오류 발생 시 기본값 0 반환
