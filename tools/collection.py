from langchain.tools import tool
from pydantic import BaseModel, Field
import subprocess
import os
import win32evtlog
from elasticsearch import Elasticsearch
from datetime import datetime

class RunCollectionInput(BaseModel):
    image_description: str = Field(
        description="A detailed description of the desired image."
    )
    es_host: str = Field(
        description="Elasticsearch host."
    )
    es_port: str = Field(
        description="Elasticsearch port."
    )
    index_name: str = Field(
        description="Elasticsearch index name."
    )
    prefetch_dir: str = Field(
        description="Directory containing the prefetch files."
    )

@tool("run_collection", args_schema=RunCollectionInput)
def run_collection(param: RunCollectionInput) -> None:
    # Prefetch data 수집
    collect_prefetch_data(param.prefetch_dir, param.es_host, param.es_port, param.index_name)
    
    # Event logs 수집
    collect_event_logs(param.es_host, param.index_name)

def collect_prefetch_data(prefetch_dir, es_host, es_port, index_name):
    for filename in os.listdir(prefetch_dir):
        if filename.endswith('.pf'):
            file_path = os.path.join(prefetch_dir, filename)
            print(f'Collecting: {file_path}')

            subprocess.run(['prefetch2es', file_path, '--host', es_host, '--port', es_port, '--index', index_name])
            print(f'Collected data from {file_path} to Elasticsearch.')

def create_index(es, index_name):
    if not es.indices.exists(index=index_name):
        es.indices.create(
            index=index_name,
            body={
                "mappings": {
                    "properties": {
                        "EventID": { "type": "integer" },
                        "TimeGenerated": { "type": "date" },
                        "SourceName": { "type": "keyword" },
                        "Message": { "type": "text" }
                    }
                }
            }
        )
        print(f'Index {index_name} created.')
    else:
        print(f'Index {index_name} already exists.')

def collect_event_logs(es_host, index_name):
    es = Elasticsearch(es_host)
    create_index(es, index_name)
    server = 'localhost'
    log_type = 'System'

    hand = win32evtlog.OpenEventLog(server, log_type)

    while True:
        try:
            records = win32evtlog.ReadEventLog(hand, win32evtlog.EVENTLOG_FORWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ, 0)

            for record in records:
                event_data = {
                    'EventID': record.EventID,
                    'TimeGenerated': datetime.strptime(record.TimeGenerated.Format(), '%a %b %d %H:%M:%S %Y').isoformat(),
                    'SourceName': record.SourceName,
                    'Message': record.StringInserts,
                }
                es.index(index=index_name, document=event_data)

        except Exception as e:
            print(f'Error reading event log: {e}')
            break

    print('Event logs collected and sent to Elasticsearch.')
