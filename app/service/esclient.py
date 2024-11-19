import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from datetime import datetime
from dotenv import load_dotenv
import json
import win32evtlog
import os

load_dotenv()
s3_region = "ap-northeast-2"

def create_s3_client():
    # AWS S3 클라이언트 생성
    return boto3.client('s3')

def upload_to_s3(bucket_name, object_name, data):
    s3_client = boto3.client('s3', region_name=s3_region)
    try:
        s3_client.put_object(Bucket=bucket_name, Key=object_name, Body=data)
        print(f'Successfully uploaded {object_name} to {bucket_name}')
    except NoCredentialsError:
        print('Credentials not available')
    except ClientError as e:
        print(f'Failed to upload to S3: {e}')

def collect_event_logs(logtype: str, task_id: str, user_id: str, max_logs: int = 500):
    '''
    logtype: Application, Security, Forwarded, Setup, System
    max_logs: 가져올 최대 로그 수
    '''
    server = "localhost"  # Local machine
    log_data = []

    try:
        # Open the event log
        handle = win32evtlog.OpenEventLog(server, logtype)
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

        print(f"Reading the last {max_logs} {logtype} logs...")

        while len(log_data) < max_logs:
            events = win32evtlog.ReadEventLog(handle, flags, 0)
            if not events:
                break
            for event in events:
                event_time = datetime.fromtimestamp(event.TimeGenerated.timestamp())
                log_data.append({
                    "TimeGenerated": event_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "SourceName": event.SourceName,
                    "EventID": event.EventID & 0xFFFF,  # Normalize Event ID
                    "EventType": event.EventType,
                    "Message": " | ".join(event.StringInserts) if event.StringInserts else "N/A",
                })
                # Stop if we've collected enough logs
                if len(log_data) >= max_logs:
                    break

        win32evtlog.CloseEventLog(handle)

    except Exception as err:
        print(f"Error while reading logs: {err}")

    finally:
        if log_data:
            object_name = f"{task_id}_{user_id}_{logtype}.json"
            upload_to_s3(bucket_name, object_name, json.dumps(log_data, indent=2))
        else:
            print(f"No logs found for {logtype}")

# 실행
types = ['Application', 'Security', 'Forwarded', 'Setup', 'System']
logtype = types[0]
user_id = "1"  # 사용자 ID
task_id = "task_1"  # 작업 ID
bucket_name = 'eventlog123'  # S3 버킷 이름

collect_event_logs(logtype, task_id, user_id, max_logs=500)