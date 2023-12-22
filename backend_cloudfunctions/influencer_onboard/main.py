import os
import re
import io
import requests
import numpy as np
import pandas as pd
from PIL import Image
from io import BytesIO
from datetime import datetime
from apify_client import ApifyClient

import functions_framework

import prompts
import config
import save_posts
import index

import pathlib
import textwrap
import json
import time

import ast
import base64
import vertexai
import PIL.Image
from vertexai.preview.generative_models import GenerativeModel, Part

from google.cloud import storage
import google.generativeai as genai
genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))


from starlette import status as http_status_codes


def convert_video_to_base64(bucket, video_path, auth=None):
    blob_name = video_path.split("https://storage.cloud.google.com/")[-1]
    blob = bucket.blob(blob_name)
    video_data = BytesIO()
    blob.download_to_file(video_data)
    video_data.seek(0)  # Move to the beginning of the BytesIO object
    video_base64 = base64.b64encode(video_data.read())
    return video_base64.decode('utf-8')
    
    
def generateVideoDescription(video):
    model = GenerativeModel("gemini-pro-vision")
    try:
        response = model.generate_content(
            [video, """Extract category and attributes in RFC8259 compliant JSON format for each apparel found in the video. If no apparel is present then give an empty JSON"""],
            generation_config={
                "max_output_tokens": 2048,
                "temperature": 0.4,
                "top_p": 1,
                "top_k": 32
            },
        stream=True,
        )
        # response.resolve()
        cleaned_string = response.candidates[0].content.parts[0].text.lower().replace("```json", "").replace("``` json", "").replace("```", "").strip()
        print(cleaned_string)
        json_data = json.loads(cleaned_string)
    except:
        json_data = ''
    return json_data


def fix_json(json_string):
    fixed_string = re.sub(r',\s*}', '}', re.sub(r',\s*\]', ']', json_string))
    return fixed_string

@functions_framework.http
def onboard_influencers(request):
    request_json = request.get_json(silent=True)

    if request_json and 'handle' in request_json and request_json["handle"] != "" and "uid" in request_json:
        handle = request_json['handle']
        uid = request_json['uid']
    else:
        return {
                "data": {"error": "invalid handle"},
                "status": False,
                "status_code": http_status_codes.HTTP_500_INTERNAL_SERVER_ERROR
        }

    client = ApifyClient(os.environ.get('APIFY_API_KEY'))
    run_input = {
    "usernames": [handle]
    }
    run = client.actor("apify/instagram-profile-scraper").call(run_input=run_input)

    for idx, item in enumerate(client.dataset(run["defaultDatasetId"]).iterate_items()):
        caption_path_mapping, handle = [], item["username"]
        caption_video_mapping = save_posts.save_igtv_videos(item, item["latestIgtvVideos"], handle)
        caption_image_mapping, comments_df = save_posts.save_ig_posts(item, item["latestPosts"], handle, client)
        caption_path_mapping = caption_video_mapping + caption_image_mapping
        temp_df = pd.DataFrame(caption_path_mapping)
        temp_df.columns = config.COLUMN_NAMES
        if not idx:
            df = temp_df.copy()
        else:
            df = pd.concat([df, temp_df])

    grouped = df.groupby(["handle", "influencerName", "biography", "postType", "caption"])['authenticatedUrl'].apply(list).reset_index()
    model = GenerativeModel("gemini-pro-vision")
    finalDescriptionList = []
    storage_client = storage.Client()
    bucket = storage_client.bucket(config.BUCKET)
    for idx, row in grouped.iterrows():
            postUrls = row["authenticatedUrl"]
            print(postUrls)
            if row["postType"] == "Video":
                descriptionList = []
                for video_path in postUrls:
                    print(f"Video Path = {video_path}")
                    video = convert_video_to_base64(bucket, video_path)
                    if video == "":
                        continue
                    description = generateVideoDescription(video)
                    descriptionList.append(description)
            else:
                descriptionList = []
                for image in postUrls:
                    print(f"Image Path = {image}")
                    blob_name = image.split("https://storage.cloud.google.com/")[-1]
                    blob = bucket.blob(blob_name)
                    image_data = BytesIO()
                    blob.download_to_file(image_data)
                    image_data.seek(0)
                    img = Image.open(image_data)
                    model = genai.GenerativeModel('gemini-pro-vision')
                    try:
                        response = model.generate_content(["Extract category and attributes in RFC8259 compliant JSON format for each apparel found in the image. If no apparel is present then give an empty JSON", img])
                    except Exception as e:
                        print(f"caught exception {e}")
                        time.sleep(5)
                        response = model.generate_content(["Extract category and attributes in RFC8259 compliant JSON format for each apparel found in the image. If no apparel is present then give an empty JSON", img])
                    response.resolve()
                    if "{" not in response.text:
                        data = {"apparel": []}
                        json_data = json.dumps(data)
                    else:
                        try:
                            cleaned_string = response.text.lower().replace("```json", "").replace("``` json", "").replace("```", "").strip()
                            print(cleaned_string)
                            try:
                                json_data = json.loads(cleaned_string)
                                descriptionList.append(json_data)
                            except:
                                descriptionList.append(cleaned_string)
                        except:
                            cleaned_string = response.text.lower().replace("```json", "").replace("``` json", "").replace("```", "").strip()
                            print(cleaned_string)
                            try:
                                fixed_json_string = fix_json(cleaned_string)
                                json_data = json.loads(fixed_json_string)
                                descriptionList.append(json_data)
                            except:
                                descriptionList.append(cleaned_string)
                    time.sleep(5)
            finalDescriptionList.append(descriptionList)

    grouped["json_description"] = finalDescriptionList
    
    df_copy = df.copy()
    for col in df_copy.columns:
        df_copy[col] = df_copy[col].astype(str)
    df_copy = df_copy[['handle', 'influencerName', 'biography', 'followersCount',
       'followingCount', 'verified', 'postType', 'commentsCount', 'likesCount',
       'videoDuration', 'videoViewCount', 'hashtags', 'mentions',
       'caption', 'profileImageUrl']].drop_duplicates()
    merged_df = pd.merge(grouped, df_copy[["handle", "caption", "followersCount", "followingCount", "verified", "commentsCount", "likesCount", "videoDuration", "videoViewCount", "hashtags", "mentions", "profileImageUrl"]], how='left', left_on = ["handle", "caption"], right_on = ["handle", "caption"])

    merged_df["commentsCount"].fillna(0, inplace=True)
    merged_df["likesCount"].fillna(0, inplace=True)
    merged_df["videoDuration"].fillna(0, inplace=True)
    merged_df["videoViewCount"].fillna(0, inplace=True)
    merged_df["hashtags"].fillna(0, inplace=True)
    merged_df["mentions"].fillna(0, inplace=True)

    merged_df["engagementRate"] = (merged_df["commentsCount"].astype(int) + merged_df["likesCount"].astype(int))/merged_df["followersCount"].astype(int)

    merged_df["followersCount"] = merged_df["followersCount"].astype(int)
    merged_df["commentsCount"] = merged_df["commentsCount"].astype(int)
    merged_df["likesCount"] = merged_df["likesCount"].astype(int)

    averaged_df = merged_df.groupby(["handle", "influencerName", "biography", "verified", "profileImageUrl"]).agg({
        'followersCount': 'mean',
        'commentsCount': 'mean',
        'likesCount': 'mean',
        'engagementRate': 'mean'
        }).reset_index()
    
    df["hashtags"] = df["hashtags"].fillna("")
    result_df = df.groupby(["handle", "influencerName", "biography", "verified"]).agg({
        'caption': lambda x: ' '.join(x.astype(str)),
        'hashtags': lambda x: ' '.join(x.astype(str))
    }).reset_index()

    influencerProfile = {}
    model = genai.GenerativeModel("gemini-pro")
    for idx, row in averaged_df.iterrows():
        response = model.generate_content(f"{prompts.PROMPT_SUMMARY} + ' \n' {row['biography']} ")
        output_response = response.text.replace("```", "")
        print(output_response)
        try:
            user_info = ast.literal_eval(output_response)
        except:
            response = model.generate_content(f"{prompts.PROMPT_LOCATION} + ' \n' {row['biography']} ")
            try:
                location = response.text
            except:
                location = ""
            response = model.generate_content(f"{prompts.PROMPT_COUNTRY} + ' \n' {row['biography']} ")
            try:
                country = response.text
            except:
                country = ""
            response = model.generate_content(f"{prompts.PROMPT_EMAIL} + ' \n' {row['biography']} ")
            try:
                email = response.text
            except:
                email = ""
            response = model.generate_content(f"{prompts.PROMPT_WEBSITE} + ' \n' {row['biography']} ")
            try:
                website = response.text
            except:
                website = ""

            user_info = {
                "location": location,
                "country": country,
                "email": email,
                "website": website
            }
        influencerName = row["influencerName"]
        influencerProfile[influencerName] = {}
        influencerProfile[influencerName]["handle"] = row["handle"]
        influencerProfile[influencerName]["bio"] = row["biography"]
        influencerProfile[influencerName]["verified"] = row["verified"]
        influencerProfile[influencerName]["profileImageUrl"] = row["profileImageUrl"]
        influencerProfile[influencerName]["platform"] = "Instagram"
        influencerProfile[influencerName]["followersCount"] = row["followersCount"]
        influencerProfile[influencerName]["engagementRate"] = row["engagementRate"]
        influencerProfile[influencerName]["handle"] = row["handle"]
        influencerProfile[influencerName]["contactInfo"] = {}
        influencerProfile[influencerName]["contactInfo"]["location"] = "" if "location" not in user_info.keys() else str(user_info["location"])
        influencerProfile[influencerName]["contactInfo"]["country"] = "" if "country" not in user_info.keys() else str(user_info["country"])
        influencerProfile[influencerName]["contactInfo"]["email"] = "" if "email" not in user_info.keys() else str(user_info["email"])
        influencerProfile[influencerName]["contactInfo"]["website"] = "" if "website" not in user_info.keys() else str(user_info["website"])
        hashtags = result_df.iloc[idx]["hashtags"]
        response = model.generate_content(f"{prompts.PROMPT_HASHTAG} + ' \n' {hashtags} ")
        output_response = response.text.replace("```", "")
        influencerProfile[influencerName]["frequentHashtags"] = output_response.split('\n', 1)[0]
        caption = result_df.iloc[idx]["caption"]
        response = model.generate_content(f"{prompts.PROMPT_CAPTIONS} + ' \n' {caption} ")
        output_response = response.text.replace("```", "")
        influencerProfile[influencerName]["postThemes"] = output_response

    print(influencerProfile)
    save_posts.save_influencer_profile(influencerProfile, handle)

    storage_client = storage.Client()
    bucket = storage_client.bucket(config.STATUS_BUCKET)
    blob = bucket.blob(config.STATUS_BLOB)
    content = blob.download_as_bytes()
    df = pd.read_csv(io.BytesIO(content))
    print("downloaded status csv")
    print(df)
    df['status'] = np.where(df['uid'] == uid, "completed", df['status'])
    print("updated status to completed")
    print(df)
    csv_content = df.to_csv(index=False)
    blob.upload_from_string(csv_content, content_type='text/csv')

    json_data = {
        "data": "jesh whbjafq whhf."
    }
    print("building index")
    index.create_index(handle)
    print("index created")

    return ("success", 200)

    
