import os
import json
import requests
import numpy as np
import pandas as pd
from io import BytesIO
from datetime import datetime
from google.cloud import storage
from apify_client import ApifyClient

import config

def save_igtv_videos(influencerData, IgtvVideos, handle):
    storage_client = storage.Client(project=config.PROJECT_NAME)
    bucket = storage_client.bucket(config.BUCKET)
    caption_video_mapping = []
    for idx, video in enumerate(IgtvVideos):
        url, caption = video["displayUrl"], video["caption"]
        response = requests.get(url, stream=True)
        temp_caption_video_mapping = []
        if response.status_code == 200:
            blob_name = f"{handle}/videos/downloaded_video_{idx}.mp4"
            authenticated_url = f"https://storage.cloud.google.com/{blob_name}"
            blob = bucket.blob(blob_name)
            buffer = BytesIO()
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    buffer.write(chunk)
            buffer.seek(0)
            blob.upload_from_file(buffer, content_type='video/mp4')
            temp_caption_video_mapping.append(handle)
            temp_caption_video_mapping.append(influencerData["fullName"])
            temp_caption_video_mapping.append(influencerData["biography"])
            temp_caption_video_mapping.append(influencerData["followersCount"])
            temp_caption_video_mapping.append(influencerData["followsCount"])
            temp_caption_video_mapping.append(influencerData["verified"])
            temp_caption_video_mapping.append("Video")
            temp_caption_video_mapping.append(video["commentsCount"])
            temp_caption_video_mapping.append(video["likesCount"])
            temp_caption_video_mapping.append(video["videoDuration"])
            temp_caption_video_mapping.append(video["videoViewCount"])
            temp_caption_video_mapping.append(np.nan)
            temp_caption_video_mapping.append(np.nan)
            temp_caption_video_mapping.append(url)
            temp_caption_video_mapping.append(caption)
            temp_caption_video_mapping.append(authenticated_url)
            temp_caption_video_mapping.append(influencerData["profilePicUrlHD"])
            caption_video_mapping.append(temp_caption_video_mapping)

    return caption_video_mapping


def extract_comments(handle, urls, client):
    url_comment_mapping = []
    run_input = {
      "directUrls": urls,
      "resultsLimit": 24
    }
    run = client.actor("apify/instagram-comment-scraper").call(run_input=run_input)
    for _, item in enumerate(client.dataset(run["defaultDatasetId"]).iterate_items()):
        temp_url_comment_mapping = []
        temp_url_comment_mapping.append(handle)
        temp_url_comment_mapping.append(item["postUrl"])
        temp_url_comment_mapping.append(item["text"])
        temp_url_comment_mapping.append(item["likesCount"])
        url_comment_mapping.append(temp_url_comment_mapping)
        
    return url_comment_mapping


def save_ig_posts(influencerData, instaPosts, handle, client):
    storage_client = storage.Client(project=config.PROJECT_NAME)
    bucket = storage_client.bucket(config.BUCKET)
    caption_posts_mapping, postUrls = [], []
    for idx, item in enumerate(instaPosts):
        caption = item["caption"]
        postUrl = item["url"]
        biography = influencerData["biography"]
        fullName = influencerData["fullName"]
        followersCount = influencerData["followersCount"]
        followsCount = influencerData["followsCount"]
        verified = influencerData["verified"]
        profileImageUrl = influencerData["profilePicUrlHD"]
        commentsCount = item["commentsCount"]
        likesCount = item["likesCount"]
        hashtags = item["hashtags"]
        mentions = item["mentions"]
        postUrls.append(postUrl)
        if len(item["images"]):
            for idx_, url in enumerate(item["images"]):
                temp_caption_posts_mapping = []
                response = requests.get(url)
                if response.status_code == 200:
                    blob_name = f"{handle}/images/downloaded_image_{idx}_{idx_}.png"
                    authenticated_url = f"https://storage.cloud.google.com/{blob_name}"
                    blob = bucket.blob(blob_name)
                    blob.upload_from_string(response.content, content_type='image/png')
                    temp_caption_posts_mapping.append(handle)
                    temp_caption_posts_mapping.append(fullName)
                    temp_caption_posts_mapping.append(biography)
                    temp_caption_posts_mapping.append(followersCount)
                    temp_caption_posts_mapping.append(followsCount)
                    temp_caption_posts_mapping.append(verified)
                    temp_caption_posts_mapping.append("Image")
                    temp_caption_posts_mapping.append(commentsCount)
                    temp_caption_posts_mapping.append(likesCount)
                    temp_caption_posts_mapping.append(np.nan)
                    temp_caption_posts_mapping.append(np.nan)
                    temp_caption_posts_mapping.append(hashtags)
                    temp_caption_posts_mapping.append(mentions)
                    temp_caption_posts_mapping.append(url)
                    temp_caption_posts_mapping.append(caption)
                    temp_caption_posts_mapping.append(authenticated_url)
                    temp_caption_posts_mapping.append(profileImageUrl)
                    caption_posts_mapping.append(temp_caption_posts_mapping)
        elif "videoUrl" in item.keys():
            url = item["displayUrl"]
            response = requests.get(url, stream=True)
            temp_caption_posts_mapping = []
            if response.status_code == 200:
                blob_name = f"{handle}/videos/downloaded_video_{idx}_{idx}.mp4"
                authenticated_url = f"https://storage.cloud.google.com/{blob_name}"
                blob = bucket.blob(blob_name)
                buffer = BytesIO()
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        buffer.write(chunk)
                buffer.seek(0)
                blob.upload_from_file(buffer, content_type='video/mp4')
                temp_caption_posts_mapping.append(handle)
                temp_caption_posts_mapping.append(fullName)
                temp_caption_posts_mapping.append(biography)
                temp_caption_posts_mapping.append(followersCount)
                temp_caption_posts_mapping.append(followsCount)
                temp_caption_posts_mapping.append(verified)
                temp_caption_posts_mapping.append("Videos")
                temp_caption_posts_mapping.append(commentsCount)
                temp_caption_posts_mapping.append(likesCount)
                temp_caption_posts_mapping.append(np.nan)
                temp_caption_posts_mapping.append(np.nan)
                temp_caption_posts_mapping.append(hashtags)
                temp_caption_posts_mapping.append(mentions)
                temp_caption_posts_mapping.append(postUrl)
                temp_caption_posts_mapping.append(caption)
                temp_caption_posts_mapping.append(authenticated_url)
                temp_caption_posts_mapping.append(profileImageUrl)
                caption_posts_mapping.append(temp_caption_posts_mapping)
        else:
            url = item["displayUrl"]
            temp_caption_posts_mapping = []
            response = requests.get(url)
            if response.status_code == 200:
                blob_name = f"{handle}/images/downloaded_image_{idx}_{idx}.png"
                authenticated_url = f"https://storage.cloud.google.com/{blob_name}"
                blob = bucket.blob(blob_name)
                temp_caption_posts_mapping.append(handle)
                temp_caption_posts_mapping.append(fullName)
                temp_caption_posts_mapping.append(biography)
                temp_caption_posts_mapping.append(followersCount)
                temp_caption_posts_mapping.append(followsCount)
                temp_caption_posts_mapping.append(verified)
                temp_caption_posts_mapping.append("Image")
                temp_caption_posts_mapping.append(commentsCount)
                temp_caption_posts_mapping.append(likesCount)
                temp_caption_posts_mapping.append(np.nan)
                temp_caption_posts_mapping.append(np.nan)
                temp_caption_posts_mapping.append(hashtags)
                temp_caption_posts_mapping.append(mentions)
                temp_caption_posts_mapping.append(postUrl)
                temp_caption_posts_mapping.append(caption)
                temp_caption_posts_mapping.append(authenticated_url)
                temp_caption_posts_mapping.append(profileImageUrl)
                caption_posts_mapping.append(temp_caption_posts_mapping)


    comments = extract_comments(handle, postUrls, client)
    comments_df = pd.DataFrame(comments)
    comments_df.columns = ["handle", "postUrl", "comment", "likesCount"]

    return caption_posts_mapping, comments_df

def save_influencer_profile(influencerProfile, handle):
    storage_client = storage.Client(project=config.PROJECT_NAME)
    bucket = storage_client.bucket(config.BUCKET)
    blob_name = f"{handle}/profile.json"
    blob = bucket.blob(blob_name)
    json_data = json.dumps(influencerProfile)
    blob.upload_from_string(json_data, content_type='application/json')

    blob_name = f"details_json/{handle}.json"
    blob = bucket.blob(blob_name)
    json_data = json.dumps(influencerProfile)
    blob.upload_from_string(json_data, content_type='application/json')
