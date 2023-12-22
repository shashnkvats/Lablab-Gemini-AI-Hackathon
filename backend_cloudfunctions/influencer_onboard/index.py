from llama_index import VectorStoreIndex, StorageContext, ServiceContext
from llama_index.embeddings import OpenAIEmbedding
from llama_index.llms import OpenAI
from llama_index.vector_stores import QdrantVectorStore
from llama_index import StorageContext

from llama_index import VectorStoreIndex, SimpleDirectoryReader

import os
import pathlib
import textwrap
import json
import time
from google.cloud import storage
import google.generativeai as genai
import chromadb
from llama_index.vector_stores import ChromaVectorStore

import config

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

def create_index(handle):
    if not os.path.exists(f"/tmp/data"):
        os.mkdir("/tmp/data")
    # with open(f"/tmp/data/{handle}.json", 'w') as json_file:
    #     json.dump(json_data, json_file, indent=4)

    storage_client = storage.Client()
    bucket = storage_client.bucket(config.BUCKET)
    folder_path = config.JSON_FOLDER_NAME if config.JSON_FOLDER_NAME.endswith('/') else config.JSON_FOLDER_NAME + '/'
    blobs = bucket.list_blobs(prefix=folder_path)

    for blob in blobs:
        if blob.name.endswith('.json'):
            local_file_path = os.path.join(config.JSON_DOWNLOAD_PATH, os.path.basename(blob.name))
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            blob.download_to_filename(local_file_path)
    
    print("json data path")
    print(os.listdir("/tmp/data/"))
    chroma_client = chromadb.EphemeralClient()
    vector_store = ChromaVectorStore(
        chroma_collection="chroma_store",
    )
    embed_model = OpenAIEmbedding(
        model_name="text-embedding-ada-002", api_key=OPENAI_API_KEY
    )
    service_context = ServiceContext.from_defaults(
        llm=OpenAI(api_key=OPENAI_API_KEY), embed_model=embed_model
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    documents = SimpleDirectoryReader("/tmp/data").load_data()
    index = VectorStoreIndex.from_documents(
        documents, service_context=service_context
    )
    index.storage_context.persist()
    print("index created! uploading it in the bucket.")
    print(os.listdir("/workspace"))
    storage_client = storage.Client()
    bucket = storage_client.bucket(config.BUCKET)
    for local_file in os.listdir("/workspace/storage/"):
        local_file_path = os.path.join("/workspace/storage", local_file)
        if os.path.isfile(local_file_path):
            print(local_file_path)
            blob_name = os.path.join(f"storage", local_file)
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_file_path)

