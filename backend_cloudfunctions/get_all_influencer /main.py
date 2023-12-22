import os
import json
import logging
import glob
import shutil

from google.cloud import storage
import functions_framework



logger = logging.getLogger()
logger.setLevel(logging.INFO)
VECTOR_INDEX_BUCKET = "influencers_records"


@functions_framework.http
def create(request):
    try:
        storage_client = storage.Client(project=os.environ['PROJECT_ID'])
        download_dir = f'{os.getcwd()}/details_json'
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)
        for blob in storage_client.list_blobs(VECTOR_INDEX_BUCKET, prefix='details_json'):
            file_name = blob.name.split('/')[-1]
            download_path = download_dir + f'/{file_name}'
            blob.download_to_filename(download_path)

        all_influencer_data = []
        for json_path in glob.glob(download_dir + "/*.json"):
            with open(json_path, 'r') as f:
                data = json.load(f)
            insta_name = list(data.keys())[0]
            insta_details = data[insta_name]
            all_influencer_data.append({"handle": insta_details['handle'],
                            "name": insta_name,
                            "email": insta_details['contactInfo']['email'],
                             "country": insta_details['contactInfo']['country'],
                             "location": insta_details['contactInfo']['location'],
                             "bio": insta_details['bio'],
                             "profile_image_url": insta_details['profileImageUrl'],
                             "frequent_hashtags": insta_details['frequentHashtags'],
                             "followers_count": insta_details['followersCount'],
                             "engagement_rate": round(insta_details['engagementRate'], 5),
                             "post_summary": insta_details['postThemes']})

        print(f"all insta account details:{all_influencer_data}")
        return json.dumps(all_influencer_data)
    except Exception as exc:
        logger.error(exc)
        return json.dumps({"status": 500, "data": {}, "message": "Opps! Something went wrong."})
