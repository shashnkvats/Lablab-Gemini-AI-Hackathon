COLUMN_NAMES = ["handle", "influencerName", "biography", "followersCount", "followingCount", "verified", "postType", "commentsCount", "likesCount", "videoDuration", "videoViewCount", "hashtags", "mentions", "postUrl", "caption", "authenticatedUrl", "profileImageUrl"]

PROJECT_NAME = os.environ['PROJECT_ID']
BUCKET = "influencers_records"
STATUS_BUCKET = "onboarding_status"
STATUS_BLOB = "status.csv"

JSON_DOWNLOAD_PATH = '/tmp/data'
JSON_FOLDER_NAME = 'details_json'
