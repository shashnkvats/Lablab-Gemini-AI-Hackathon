import os
import json
import logging
import zipfile
import shutil
from typing import List


from google.cloud import storage
from pydantic import BaseModel
import functions_framework
from trulens_eval import Tru
from llama_index.embeddings import OpenAIEmbedding
from llama_index.llms import OpenAI
from llama_index import StorageContext, load_index_from_storage, ServiceContext


logger = logging.getLogger()
logger.setLevel(logging.INFO)
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
VECTOR_INDEX_BUCKET = "influencers_records"

class InsaProfile(BaseModel):
    """Data model for a InsaProfile."""
    handle: str
    name: str
    email: str
    country: str
    location: str
    bio: str
    profile_image_url: str
    frequent_hashtags: List[str]
    followers_count: int
    engagement_rate: float
    post_summary: str


"""
{
  "search_query": "which influencer is commited for sustainable fashion?"
}
"""

@functions_framework.http
def create(request):
    try:
        request_json = request.get_json(silent=True)
        print(f"===== request_json =====\n{request_json}")
        if "search_query" not in request_json:
            return json.dumps({"handle": "please provide a query", "name": "please provide a query", "email": "",
                               "bio": ""})

        storage_client = storage.Client(project=os.environ['PROJECT_ID'])
        download_dir = f'{os.getcwd()}/storage'
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)
        for blob in storage_client.list_blobs(VECTOR_INDEX_BUCKET, prefix='storage'):
            file_name = blob.name.split('/')[-1]
            print(f"blob.name {blob.name}")
            print(f"file_name {file_name}")
            download_path = download_dir + f'/{file_name}'
            blob.download_to_filename(download_path)

        print(f"all files : {os.listdir()}")
        print(f"all files in storage : {os.listdir(download_dir)}")

        # with open(local_index_store_path, 'wb') as f:
        #     storage_client.download_blob_to_file(cloud_index_store_path, f)
        # print(f"all files : {os.listdir()}")
        # with zipfile.ZipFile(local_index_store_path, 'r') as zip_ref:
        #     zip_ref.extractall(os.getcwd())

        embed_model = OpenAIEmbedding(
            model_name="text-embedding-ada-002", api_key=OPENAI_API_KEY
        )
        service_context = ServiceContext.from_defaults(
            llm=OpenAI(api_key=OPENAI_API_KEY), embed_model=embed_model
        )

        storage_context = StorageContext.from_defaults(persist_dir=f'{os.getcwd()}/storage')
        index = load_index_from_storage(storage_context, service_context=service_context)

        query_engine = index.as_query_engine(output_cls=InsaProfile)
        response = query_engine.query(request_json['search_query'])
        print(f"Response: {response}")
        return json.dumps([dict(response.response)])
    except Exception as exc:
        logger.error(exc)
        return json.dumps({"status": 500, "data": {}, "message": "Opps! Something went wrong."})
