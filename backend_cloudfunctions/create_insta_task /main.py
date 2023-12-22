import io
import json
import datetime
import numpy as np
import pandas as pd
from datetime import datetime
from starlette import status as http_status_codes
import functions_framework

import config

from google.cloud import storage
from google.cloud import tasks_v2

client = tasks_v2.CloudTasksClient()
queue_path = client.queue_path(config.CLOUD_TASK_PROJECT, config.CLOUD_TASK_LOCATION, config.CLOUD_TASK_QUEUE)

@functions_framework.http
def create_cloudtask(request):
    
    request_json = request.get_json(silent=True)
    print("===== request_json =====")
    print(request_json)

    if 'handle' in request_json and request_json['handle'] != "":
        handle = request_json['handle']
    else:
        return {
                    "data": {"error": "invalid handle"},
                    "status": False,
                    "status_code": http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR
                }
    
    # Generate uid
    uid = datetime.now().strftime("%Y%m%d%H%M%S%f")

    storage_client = storage.Client()
    bucket = storage_client.bucket(config.STATUS_BUCKET)
    blob = bucket.blob(config.STATUS_BLOB)

    # Download the blob to a BytesIO object and update
    content = blob.download_as_bytes()
    df = pd.read_csv(io.BytesIO(content))
    new_row = {'uid': uid, 'status': 'pending', 'handle': handle}
    df = df.append(new_row, ignore_index=True)
    csv_content = df.to_csv(index=False)
    blob.upload_from_string(csv_content, content_type='text/csv')

    payload = {
            "handle": handle,
            "uid": uid
        }
    
    converted_payload = json.dumps(payload).encode()
    task = {
        'http_request': {
            'http_method': 'POST',
            'url': config.TASK_ENDPOINT_URL,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': converted_payload
        }
    }
    response = client.create_task(request={"parent": queue_path, "task": task})
    print('Task created: {}'.format(response.name))
    
    return {
            "data": {"message": "Your request is being processed. We will notify you once it's done.", "uid": uid},
            "status": True,
            "status_code": http_status_codes.HTTP_200_OK
        }
