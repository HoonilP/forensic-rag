from datetime import datetime
from elasticsearch import Elasticsearch

# Elasticsearch 클라이언트 초기화
es = Elasticsearch(["http://localhost:9200"])

def upload_task_to_es(user_id: int, computer_id: int, analysis_result: str, visualization_chart: str, timestamp: datetime):
    task_data = {
        "user_id": user_id,
        "computer_id": computer_id,
        "analysis_result": analysis_result,
        "visualization_chart": visualization_chart,
        "created_at": timestamp
    }
    
    # Elasticsearch에 데이터 업로드
    es.index(index="tasks", document=task_data)
