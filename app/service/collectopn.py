import win32evtlog
from datetime import datetime
import json
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
from dotenv import load_dotenv

load_dotenv()
s3_region="ap-northeast-2"

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

def collect_event_logs(log_type='System', start_time=None, end_time=None, user_id=None, computer_id=None, bucket_name=None):
    server = 'localhost'  # 이벤트 로그를 읽을 서버
    hand = win32evtlog.OpenEventLog(server, log_type)

    logs = []

    while True:
        try:
            records = win32evtlog.ReadEventLog(hand, win32evtlog.EVENTLOG_FORWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ, 0)

            if len(records) < 1:
                print("No more records to read.")
                break

            for record in records:
                event_time = datetime.strptime(record.TimeGenerated.Format(), '%a %b %d %H:%M:%S %Y')

                # 날짜 범위 체크
                if (start_time is None or event_time >= start_time) and (end_time is None or event_time <= end_time):
                    event_data = {
                        'EventID': record.EventID,
                        'TimeGenerated': event_time.isoformat(),
                        'SourceName': record.SourceName,
                        'Message': record.StringInserts,
                        'UserID': user_id,
                        'ComputerID': computer_id,
                    }
                    logs.append(event_data)
                    print(f"Event ID: {event_data['EventID']}, Time: {event_data['TimeGenerated']}, Source: {event_data['SourceName']}, Message: {event_data['Message']}")
                else:
                    print(f"Skipping event ID: {record.EventID} - out of date range.")

        except Exception as e:
            print(f'Error reading event log: {e}')
            break

    # S3에 업로드
    if logs:
        object_name = f"{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}_{user_id}_{computer_id}.json"
        upload_to_s3(bucket_name, object_name, json.dumps(logs, indent=2))
    else:
        print("No logs collected in the specified time range.")

# 실행
start_time = datetime(2024, 11, 18, 0, 0, 0)  # 시작 날짜
end_time = datetime(2024, 11, 19, 23, 59, 59)  # 종료 날짜
user_id = 1  # 사용자 ID
computer_id = 1  # 컴퓨터 ID
bucket_name = 'eventlog123'  # S3 버킷 이름

collect_event_logs('System', start_time, end_time, user_id, computer_id, bucket_name)  # 'Application' 또는 'Security' 타입으로 변경 가능
